import json
from io import StringIO
from os import PathLike
from pathlib import Path
from typing import Any, cast

import numpy as np
import shapely
from prcoords import gcj_wgs_bored
from shapely.geometry.base import BaseGeometry

__all__ = [
    "dump_json",
    "gcj_geometry_to_wgs",
    "gcj_to_wgs",
    "get_data_dir",
    "load_json",
    "polyline_to_polygon",
    "round_geometry",
    "shorten_city_name",
    "shorten_district_name",
    "shorten_province_name",
]

type StrPath = str | PathLike[str]


def get_data_dir() -> Path:
    """获取数据目录"""
    dirpath = Path(__file__).parent
    while True:
        if dirpath.name == "src":
            src_dirpath = dirpath.parent
            break
        elif dirpath.parent == dirpath:
            raise FileNotFoundError("src directory not found")
        dirpath = dirpath.parent

    return src_dirpath / "data"


def load_json(filepath: StrPath) -> dict[str, Any]:
    """加载本地 JSON 文件"""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def dump_json(filepath: StrPath, obj: Any) -> None:
    """导出本地 JSON 文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def polyline_to_polygon(polyline: str) -> shapely.Polygon | shapely.MultiPolygon:
    """将高德的 polyline 字符串转为多边形对象"""
    polygons = []
    for part in polyline.replace(";", "\n").split("|"):
        with StringIO(part) as f:
            shell = np.loadtxt(f, delimiter=",")
        polygon = shapely.Polygon(shell)
        polygons.append(polygon)
    polygon = shapely.union_all(polygons)

    return cast(shapely.Polygon | shapely.MultiPolygon, polygon)


def gcj_to_wgs(lon: float, lat: float) -> tuple[float, float]:
    """将一个点从 gcj 坐标系转换到 wgs 坐标系"""
    lat, lon = gcj_wgs_bored((lat, lon))
    return lon, lat


def gcj_geometry_to_wgs[GeometryT: BaseGeometry](geometry: GeometryT) -> GeometryT:
    """将几何对象从 gcj 坐标系转换到 wgs 坐标系"""
    coordinates = shapely.get_coordinates(geometry).tolist()
    coordinates = [gcj_to_wgs(*lonlat) for lonlat in coordinates]
    return shapely.set_coordinates(geometry, coordinates)


def round_geometry[GeometryT: BaseGeometry](
    geometry: GeometryT, decimals: int = 0
) -> GeometryT:
    """将几何对象的坐标四舍五入"""
    coordinates = shapely.get_coordinates(geometry).round(decimals)
    return shapely.set_coordinates(geometry, coordinates)


def shorten_province_name(name: str) -> str:
    """缩短省名。只保留前几个字。"""
    if name.startswith("内蒙古") or name.startswith("黑龙江"):
        return name[:3]
    return name[:2]


def shorten_city_name(name: str) -> str:
    """缩短市名。只保留前几个字。"""
    for suffix in [
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
        if name.endswith(suffix):
            index = name.index(suffix)
            return name[:index]
    else:
        raise ValueError(name)


def shorten_district_name(name: str) -> str:
    """缩短区县名。只省略掉民族部分，保留行政区划单字。"""
    match name:
        case "喀喇沁左翼蒙古族自治县":
            return "喀左县"
        case "东乡族自治县":
            return "东乡县"
        case "鄂温克族自治旗":
            return "鄂温克旗"
        case "大柴旦行政委员会":
            return "大柴旦"

    for suffix in [
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
        if name.endswith(suffix):
            index = name.index(suffix)
            return name[:index] + suffix[-1]

    return name
