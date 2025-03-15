import json
from io import StringIO
from pathlib import Path
from typing import Any, TypeVar

import numpy as np
import pandas as pd
import requests
import shapely
import shapely.geometry as sgeom
from numpy.typing import ArrayLike, NDArray
from prcoords import gcj_wgs_bored
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient


def get_api_json(url: str) -> Any:
    """请求 API 的 JSON 数据"""
    resp = requests.get(url)
    obj = json.loads(resp.content)
    return obj


def load_json(filepath: str | Path) -> dict:
    """加载本地 JSON 文件"""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def dump_json(filepath: str | Path, obj: Any) -> None:
    """导出本地 JSON 文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def polyline_to_polygon(polyline: str) -> shapely.Polygon | shapely.MultiPolygon:
    """将高德的 polyline 字符串转为多边形对象"""
    polygons = []
    for part in polyline.replace(";", "\n").split("|"):
        with StringIO(part) as f:
            coordinates = np.loadtxt(f, delimiter=",")
        polygon = shapely.Polygon(coordinates)
        polygons.append(polygon)
    polygon = shapely.union_all(polygons)

    return polygon


PolygonT = TypeVar("PolygonT", shapely.Polygon, shapely.MultiPolygon)


def orient_polygon(polygon: PolygonT, sign: float = 1.0) -> PolygonT:
    """改变多边形内外环绕行方向"""
    if isinstance(polygon, shapely.Polygon):
        return orient(polygon, sign)
    elif isinstance(polygon, shapely.MultiPolygon):
        return shapely.MultiPolygon([orient(x, sign) for x in polygon.geoms])
    else:
        raise TypeError(polygon)


# TODO: shapely.to_geojson
def geometry_to_geometry_dict(geometry: BaseGeometry) -> dict:
    """将 shapely 的几何对象转为 geojson 的 geometry 字典"""

    def get_coordinates(geometry: BaseGeometry) -> list:
        return shapely.get_coordinates(geometry).tolist()

    def get_point_coordinates(point: shapely.Point) -> list:
        return [point.x, point.y]

    def get_multi_point_coordinates(multi_point: shapely.MultiPoint) -> list:
        return get_coordinates(multi_point)

    def get_line_string_coordinates(line_string: shapely.LineString) -> list:
        return get_coordinates(line_string)

    def get_multi_line_string_coordinates(
        multi_line_string: shapely.MultiLineString,
    ) -> list:
        return list(map(get_line_string_coordinates, multi_line_string.geoms))

    def get_linear_ring_coordinates(linear_ring: shapely.LinearRing) -> list:
        return get_coordinates(linear_ring)

    def get_polygon_coordinates(polygon: shapely.Polygon) -> list:
        polygon = orient_polygon(polygon)
        coordinates = [
            get_linear_ring_coordinates(polygon.exterior),
            *map(get_linear_ring_coordinates, polygon.interiors),
        ]
        return coordinates

    def get_multi_polygon_coordinates(multi_polygon: shapely.MultiPolygon) -> list:
        return list(map(get_polygon_coordinates, multi_polygon.geoms))

    if isinstance(geometry, shapely.GeometryCollection):
        return {
            "type": "GeometryCollection",
            "geometries": list(map(geometry_to_geometry_dict, geometry.geoms)),
        }

    match geometry:
        case shapely.Point():
            geometry_type = "Point"
            getter = get_point_coordinates
        case shapely.MultiPoint():
            geometry_type = "MultiPoint"
            getter = get_multi_point_coordinates
        case shapely.LineString():
            geometry_type = "LineString"
            getter = get_line_string_coordinates
        case shapely.MultiLineString():
            geometry_type = "MultiLineString"
            getter = get_multi_line_string_coordinates
        case shapely.LinearRing():
            geometry_type = "LineString"
            getter = get_linear_ring_coordinates
        case shapely.Polygon():
            geometry_type = "Polygon"
            getter = get_polygon_coordinates
        case shapely.MultiPolygon():
            geometry_type = "MultiPolygon"
            getter = get_multi_polygon_coordinates
        case _:
            raise TypeError(geometry)

    return {"type": geometry_type, "coordinates": getter(geometry)}


def get_geometry_center(geometry: BaseGeometry) -> tuple[float, float]:
    """获取代表多边形中心的坐标"""
    point = geometry.representative_point()
    return point.x, point.y


def gcj_to_wgs(lon: float, lat: float) -> tuple[float, float]:
    """将一个点从 gcj 坐标系转换到 wgs 坐标系"""
    lat, lon = gcj_wgs_bored((lat, lon))
    return lon, lat


def gcj_coordinates_to_wgs(coordinates: ArrayLike) -> NDArray:
    """将形如 (n, 2) 的坐标数组从 gcj 坐标系转换到 wgs 坐标系"""
    coordinates = np.asarray(coordinates)
    assert coordinates.ndim == 2 and coordinates.shape[1] == 2
    coordinates = np.array([gcj_to_wgs(lon, lat) for lon, lat in coordinates])

    return coordinates


GeometryT = TypeVar("GeometryT", bound=BaseGeometry)


def _python_round(x: float, decimals: int | None = None) -> float:
    if decimals is not None:
        return round(x, decimals)
    return x


def _numpy_round(x: NDArray, decimals: int | None = None) -> NDArray:
    if decimals is not None:
        return np.round(x, decimals)
    return x


def gcj_geometry_to_wgs(
    geometry: GeometryT, decimals: int | None = None, check_validity: bool = False
) -> GeometryT:
    def transform(coordinates: NDArray) -> NDArray:
        return _numpy_round(gcj_coordinates_to_wgs(coordinates), decimals)

    geometry = shapely.transform(geometry, transform)
    if check_validity and not geometry.is_valid:
        raise ValueError(f"无效几何对象: {geometry}")

    return geometry


def gcj_geometry_dict_to_wgs(
    geometry_dict: dict, decimals: int | None = None, check_validity: bool = False
) -> dict:
    """将 geojson 的 geometry 字典从 gcj 坐标系转换到 wgs 坐标系"""

    def transform_point_coordinates(coordinates: list) -> list:
        lon, lat = coordinates
        lon, lat = gcj_to_wgs(lon, lat)
        lon = _python_round(lon, decimals)
        lat = _python_round(lat, decimals)

        return [lon, lat]

    def transform_multi_point_coordinates(coordinates: list) -> list:
        return list(map(transform_point_coordinates, coordinates))

    def transform_line_string_coordinates(coordinates: list) -> list:
        return transform_multi_point_coordinates(coordinates)

    def transform_multi_line_string_coordinates(coordinates: list) -> list:
        return list(map(transform_line_string_coordinates, coordinates))

    def transform_polygon_coordinates(coordinates: list) -> list:
        return transform_multi_line_string_coordinates(coordinates)

    def transform_multi_polygon_coordinates(coordinates: list) -> list:
        return list(map(transform_polygon_coordinates, coordinates))

    def do_recursion(geometry_dict: dict) -> dict:
        geometry_type = geometry_dict["type"]
        if geometry_type == "GeometryCollection":
            return {
                "type": geometry_type,
                "geometries": list(map(do_recursion, geometry_dict["geometries"])),
            }

        match geometry_type:
            case "Point":
                transform = transform_point_coordinates
            case "MultiPoint":
                transform = transform_multi_point_coordinates
            case "LineString":
                transform = transform_line_string_coordinates
            case "MultiLineString":
                transform = transform_multi_line_string_coordinates
            case "Polygon":
                transform = transform_polygon_coordinates
            case "MultiPolygon":
                transform = transform_multi_polygon_coordinates
            case _:
                raise ValueError(geometry_type)

        return {
            "type": geometry_type,
            "coordinates": transform(geometry_dict["coordinates"]),
        }

    geometry_dict = do_recursion(geometry_dict)
    if check_validity:
        geometry = sgeom.shape(geometry_dict)
        if not geometry.is_valid:
            raise ValueError(f"无效几何对象: {geometry}")

    return geometry_dict


def geojson_to_df(data: dict) -> pd.DataFrame:
    """提取 geojson 中的 properties 字典为 DataFrame"""
    properties_list = [feature["properties"] for feature in data["features"]]
    return pd.DataFrame.from_records(properties_list)


def geojson_to_geometries(data: dict) -> list[BaseGeometry]:
    """提取 geojson 中的 geometry 字典为几何对象的列表"""
    return [sgeom.shape(feature["geometry"]) for feature in data["features"]]


def make_feature(geometry_dict: dict, properties: dict) -> dict:
    """构造 geojson 的 feature 字典"""
    return {"type": "Feature", "geometry": geometry_dict, "properties": properties}


def make_geojson(features: list[dict]) -> dict:
    """构造 geojson 字典"""
    return {"type": "FeatureCollection", "features": features}


def shorten_province_name(name: str) -> str:
    """缩短省名。只保留前几个字。"""
    if name.startswith("内蒙古") or name.startswith("黑龙江"):
        return name[:3]
    return name[:2]


def shorten_city_name(name: str) -> str:
    """缩短市名。只保留前几个字。"""
    if name.startswith("重庆"):
        return name

    for word in [
        "土家族苗族自治州",
        "布依族苗族自治州",
        "哈尼族彝族自治州",
        "蒙古族藏族自治州",
        "傣族景颇族自治州",
        "苏柯尔克孜自治州",
        "黎族苗族自治县",
        "苗族侗族自治州",
        "藏族羌族自治州",
        "壮族苗族自治州",
        "朝鲜族自治州",
        "傈僳族自治州",
        "哈萨克自治州",
        "彝族自治州",
        "藏族自治州",
        "黎族自治县",
        "傣族自治州",
        "回族自治州",
        "蒙古自治州",
        "白族自治州",
        "特别行政区",
        "林区",
        "地区",
        "城区",
        "县",
        "盟",
        "省",
        "市",
    ]:
        if word in name:
            index = name.index(word)
            return name[:index]
    else:
        raise ValueError(name)


def shorten_district_name(name: str) -> str:
    """缩短区县名。只省略掉民族部分，保留行政区划单字。"""
    if name == "喀喇沁左翼蒙古族自治县":
        return "喀左县"

    if name == "东乡族自治县":
        return "东乡县"

    if name == "鄂温克族自治旗":
        return "鄂温克旗"

    if name == "海西蒙古族藏族自治州直辖":
        return "自治州直辖"

    for word in [
        "拉祜族佤族布朗族傣族自治县",
        "彝族回族苗族自治县",
        "彝族哈尼族拉祜族自治县",
        "哈尼族彝族傣族自治县",
        "傣族拉祜族佤族自治县",
        "苗族瑶族傣族自治县",
        "保安族东乡族撒拉族自治县",
        "白族普米族自治县",
        "独龙族怒族自治县",
        "满族蒙古族自治县",
        "苗族侗族自治县",
        "黎族苗族自治县",
        "土家族苗族自治县",
        "苗族土家族自治县",
        "仡佬族苗族自治县",
        "布依族苗族自治县",
        "苗族布依族自治县",
        "壮族瑶族自治县",
        "回族彝族自治县",
        "回族土族自治县",
        "哈尼族彝族自治县",
        "傣族彝族自治县",
        "傣族佤族自治县",
        "彝族苗族自治县",
        "彝族傣族自治县",
        "彝族回族自治县",
        "蒙古族自治县",
        "满族自治县",
        "回族自治县",
        "朝鲜族自治县",
        "畲族自治县",
        "侗族自治县",
        "苗族自治县",
        "黎族自治县",
        "土族自治县",
        "土家族自治县",
        "瑶族自治县",
        "仫佬族自治县",
        "毛南族自治县",
        "羌族自治县",
        "彝族自治县",
        "藏族自治县",
        "水族自治县",
        "纳西族自治县",
        "哈尼族自治县",
        "拉祜族自治县",
        "佤族自治县",
        "傈僳族自治县",
        "裕固族自治县",
        "哈萨克族自治县",
        "撒拉族自治县",
        "哈萨克自治县",
        "塔吉克自治县",
        "锡伯自治县",
        "蒙古自治县",
        "各族自治县",
        "达斡尔族自治旗",
        "达斡尔族区",
        "回族区",
        "自治旗",
    ]:
        if word in name:
            index = name.index(word)
            return name[:index] + word[-1]

    return name
