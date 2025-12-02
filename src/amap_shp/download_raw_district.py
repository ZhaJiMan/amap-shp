from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from functools import wraps
from io import StringIO
from typing import Literal, TypedDict

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely
from loguru import logger
from retrying import retry

from amap_shp.exceptions import AmapDataError, AmapStatusError
from amap_shp.utils import dump_geojson, get_amap_key, get_output_dir

AMAP_KEY = get_amap_key()


class SuggestionDict(TypedDict):
    keywords: list[str]
    cities: list[str]


class DistrictDict(TypedDict):
    citycode: str | list[str]  # country 和 province 的 citycode 是空列表
    adcode: str
    name: str
    polyline: str  # 仅当 extentions=all 时第一级才有 polyline 字段
    center: str
    level: Literal["country", "province", "city", "district", "street"]
    districts: list[DistrictDict]


class DistrictData(TypedDict):
    status: Literal["0", "1"]
    info: str
    infocode: str
    # 仅当 status 为 "1" 时才有以下字段
    count: str
    suggestion: SuggestionDict
    districts: list[DistrictDict]


class DistrictProperties(TypedDict):
    province_name: str
    province_adcode: int
    city_name: str
    city_adcode: int
    district_name: str
    district_adcode: int


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
    data = requests.get(url, params=params).json()
    _check_amap_status(data)

    return data


def get_district_dataframe() -> pd.DataFrame:
    """获取区县的元数据的 DataFrame"""
    params = {"key": AMAP_KEY, "subdistrict": "3"}
    url = "http://restapi.amap.com/v3/config/district"
    data = get_district_data(url, params)

    country_dict = data["districts"][0]
    properties_list: list[DistrictProperties] = []
    properties: DistrictProperties

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

    return (
        pd.DataFrame.from_records(properties_list)
        .sort_values("district_adcode")
        .reset_index(drop=True)
    )


def polyline_to_polygons(polyline: str) -> list[shapely.Polygon]:
    """将高德的 polyline 字符串转为多边形

    经度和纬度用逗号分隔，点与点之间用分号分隔，MultiPolygon 的子多边形用竖线分隔。

    对于带洞的多边形，polyline 并不直接保存外环和内环，而是将带洞的多边形分割成几个独立的
    不带洞的多边形。
    """
    polygons = []
    for part in polyline.replace(";", "\n").split("|"):
        with StringIO(part) as f:
            shell = np.loadtxt(f, delimiter=",")
        polygon = shapely.Polygon(shell)
        polygons.append(polygon)
    assert polygons  # 保证至少有一个多边形

    return polygons


def get_district_polygons(adcode: int) -> list[shapely.Polygon]:
    """获取一个区县的多边形"""
    # extentions=all 时含有 polyline 字符串
    url = "https://restapi.amap.com/v3/config/district"
    params = {
        "key": AMAP_KEY,
        "keywords": str(adcode),
        "subdistrict": "0",
        "extensions": "all",
        "filter": str(adcode),
    }
    data = get_district_data(url, params)

    if not data["districts"]:
        raise AmapDataError(f"{adcode=} not found")
    assert len(data["districts"]) == 1
    district_dict = data["districts"][0]
    if "polyline" not in district_dict:
        raise AmapDataError(f"{adcode=} has no polyline")

    return polyline_to_polygons(district_dict["polyline"])


def get_district_geodataframe() -> gpd.GeoDataFrame:
    """获取区县元数据和多边形的 GeoDataFrame"""
    df = get_district_dataframe()
    polygons_list: list[list[shapely.Polygon]] = []
    for row in df.itertuples(index=False):
        polygons = get_district_polygons(row.district_adcode)  # pyright: ignore[reportAttributeAccessIssue]
        polygons_list.append(polygons)
        logger.info(row)
        time.sleep(0.25)  # 控制请求频率

    df["geometry"] = polygons_list
    df = df.explode("geometry", ignore_index=True)

    return gpd.GeoDataFrame(df, crs=4326)


def main() -> None:
    dirpath = get_output_dir()
    dirpath.mkdir(parents=True, exist_ok=True)

    gdf = get_district_geodataframe()
    dump_geojson(gdf, dirpath / "cn_district_raw.geojson")
    logger.info("区县数据下载完成")


if __name__ == "__main__":
    main()
