from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping
from functools import wraps
from typing import cast

import frykit.shp as fshp
import requests
import shapely
from dotenv import load_dotenv
from frykit.shp.typing import FeatureDict, GeoJSONDict
from frykit.utils import new_dir
from loguru import logger
from retrying import retry

from amap_shp.exceptions import AmapDataError, AmapStatusError
from amap_shp.typing import DistrictData, DistrictProperties, RawDistrictProperties
from amap_shp.utils import (
    dump_json,
    gcj_geometry_to_wgs,
    get_data_dir,
    polyline_to_polygon,
    round_geometry,
    shorten_district_name,
)

load_dotenv()


def amap_retry[T, **P](func: Callable[P, T]) -> Callable[P, T]:
    """当高德 API 的 status 为 0 时重试"""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return retry(
            wait_fixed=1000,
            stop_max_attempt_number=5,
            retry_on_exception=(AmapStatusError,),
        )(func)(*args, **kwargs)

    return wrapper


def _check_amap_status(data: DistrictData) -> None:
    """当 status 为 0 时抛出异常以触发重试的装饰器"""
    if data["status"] == "0":
        info = data["info"]
        infocode = data["infocode"]
        raise AmapStatusError(info, infocode)


@amap_retry
def get_district_data(url: str, params: Mapping[str, str]) -> DistrictData:
    """请求高德行政区域查询的 API"""
    resp = requests.get(url, params=params)
    data = cast(DistrictData, resp.json())
    _check_amap_status(data)

    return data


def get_district_properties_list() -> list[DistrictProperties]:
    """获取所有区县的元数据。没有区县的省市用它自己代替区县。"""
    params = {"key": os.getenv("AMAP_KEY", ""), "subdistrict": "3"}
    url = "http://restapi.amap.com/v3/config/district"
    data = get_district_data(url, params)

    country_dict = data["districts"][0]
    properties_list: list[RawDistrictProperties] = []
    properties: RawDistrictProperties

    for province_dict in country_dict["districts"]:
        # 台湾没有下级数据
        if not province_dict["districts"]:
            properties = {
                "province_name": province_dict["name"],
                "province_adcode": int(province_dict["adcode"]),
                "city_name": province_dict["name"],
                "city_adcode": int(province_dict["adcode"]),
                "district_name": province_dict["name"],
                "district_adcode": int(province_dict["adcode"]),
            }
            properties_list.append(properties)
            continue

        assert province_dict["level"] == "province"
        for city_dict in province_dict["districts"]:
            # 香港和澳门下一级就是区县
            if city_dict["level"] == "district":
                properties = {
                    "province_name": province_dict["name"],
                    "province_adcode": int(province_dict["adcode"]),
                    "city_name": province_dict["name"],
                    "city_adcode": int(province_dict["adcode"]),
                    "district_name": city_dict["name"],
                    "district_adcode": int(city_dict["adcode"]),
                }
                properties_list.append(properties)
                continue

            assert city_dict["level"] == "city"
            for district_dict in city_dict["districts"]:
                # 部分城市和省直辖县下一级就是街道
                if district_dict["level"] == "street":
                    properties = {
                        "province_name": province_dict["name"],
                        "province_adcode": int(province_dict["adcode"]),
                        "city_name": city_dict["name"],
                        "city_adcode": int(city_dict["adcode"]),
                        "district_name": city_dict["name"],
                        "district_adcode": int(city_dict["adcode"]),
                    }
                    properties_list.append(properties)
                    break

                assert district_dict["level"] == "district"
                properties = {
                    "province_name": province_dict["name"],
                    "province_adcode": int(province_dict["adcode"]),
                    "city_name": city_dict["name"],
                    "city_adcode": int(city_dict["adcode"]),
                    "district_name": district_dict["name"],
                    "district_adcode": int(district_dict["adcode"]),
                }
                properties_list.append(properties)

    for properties in properties_list:
        # 将上海、重庆、天津、北京四个地方多余的市级区划去掉
        if properties["city_name"] in {
            "上海城区",
            "重庆城区",
            "重庆郊县",
            "天津城区",
            "北京城区",
        }:
            properties["city_name"] = properties["province_name"]
            properties["city_adcode"] = properties["province_adcode"]

        if properties["district_name"] == "澳门大学横琴校区(由澳门实施管辖)":
            properties["district_name"] = "澳门大学横琴校区"

        if properties["district_name"] == "海西蒙古族藏族自治州直辖":
            properties["district_name"] = "大柴旦行政委员会"

        properties["short_name"] = shorten_district_name(properties["district_name"])

    properties_list.sort(key=lambda x: x["district_adcode"])

    return cast(list[DistrictProperties], properties_list)


def get_district_geometry(adcode: int) -> shapely.Polygon | shapely.MultiPolygon:
    """
    获取一个区县的几何对象字典

    extensions=all 时高德 API 会返回表示多边形坐标序列的 polyline 字符串，经度和纬度
    用逗号分隔，点与点之间用分号分隔。MultiPolygon 的子多边形用竖线分隔。

    对于带洞的多边形，polyline 并不直接保存外环和内环，而是将带洞的多边形分割成几个独立的
    不带洞的多边形，将这些多边形用 shapely.union_all 拼在一起能还原带洞的多边形。
    具体实现见 polyline_to_polygon 函数。

    高德数据应该是 GCJ-02 坐标系的，这里用 PRCoords 库转换成 WGS84 坐标系。
    polyline 里经纬度的精度是 6 位小数，因此转换后的坐标也取 6 位小数。
    """
    url = "https://restapi.amap.com/v3/config/district"
    params = {
        "key": os.getenv("AMAP_KEY", ""),
        "keywords": str(adcode),
        "subdistrict": "0",
        "extensions": "all",
        "filter": str(adcode),
    }
    data = get_district_data(url, params)

    # 检查是否含有 polyline 字段
    if not data["districts"]:
        raise AmapDataError(f"{adcode=} not found")
    assert len(data["districts"]) == 1
    district_dict = data["districts"][0]
    if "polyline" not in district_dict:
        raise AmapDataError(f"{adcode=} has no polyline")

    polygon = polyline_to_polygon(district_dict["polyline"])
    polygon = gcj_geometry_to_wgs(polygon)
    polygon = round_geometry(polygon, 6)
    if not polygon.is_valid:
        raise ValueError(f"{polygon} is invalid")

    return polygon


def make_district_geojson() -> GeoJSONDict:
    """制作区县的 GeoJSON。导出的多边形满足外环逆时针内环顺时针的方向。"""
    features: list[FeatureDict] = []
    properties_list = get_district_properties_list()
    for properties in properties_list:
        geometry = get_district_geometry(properties["district_adcode"])
        geometry_dict = fshp.geometry_to_dict(geometry)
        feature = fshp.make_feature(geometry_dict, properties)
        features.append(feature)
        logger.info(properties)
        time.sleep(0.25)  # 控制请求频率

    data = fshp.make_geojson(features)

    return data


def make_nine_line_geojson() -> GeoJSONDict:
    """制作九段线的 GeoJSON"""
    url = "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json"
    resp = requests.get(url)
    data = cast(GeoJSONDict, resp.json())

    # 全国数据的最后一个 feature 是九段线的多边形
    geometry_dict = data["features"][-1]["geometry"]
    polygon = fshp.dict_to_geometry(geometry_dict)
    polygon = gcj_geometry_to_wgs(polygon)
    polygon = round_geometry(polygon, 6)
    if not polygon.is_valid:
        raise ValueError(f"{polygon} is invalid")

    geometry_dict = fshp.geometry_to_dict(polygon)
    properties = {"name": "九段线"}
    feature = fshp.make_feature(geometry_dict, properties)
    data = fshp.make_geojson([feature])

    return data


def main() -> None:
    dirpath = new_dir(get_data_dir())

    dump_json(dirpath / "cn_district.json", make_district_geojson())
    logger.info("区县数据下载完成")

    dump_json(dirpath / "nine_line.json", make_nine_line_geojson())
    logger.info("九段线数据下载完成")


if __name__ == "__main__":
    main()
