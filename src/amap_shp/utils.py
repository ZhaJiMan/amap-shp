from __future__ import annotations

import json
import os
from io import StringIO
from pathlib import Path
from typing import cast

import numpy as np
import shapely
from dotenv import load_dotenv
from frykit.shp.typing import GeoJSONDict
from prcoords import gcj_wgs_bored
from shapely.geometry.base import BaseGeometry

__all__ = [
    "dump_geojson",
    "gcj_geometry_to_wgs",
    "gcj_to_wgs",
    "get_amap_key",
    "get_output_dir",
    "load_geojson",
    "polyline_to_polygon",
    "round_geometry",
]

load_dotenv()


def get_amap_key() -> str:
    return os.getenv("AMAP_KEY", "")


def get_output_dir() -> Path:
    """获取数据目录"""
    return Path(os.getenv("OUTPUT_DIR", "output"))


type StrPath = str | os.PathLike[str]


def load_geojson(filepath: StrPath) -> GeoJSONDict:
    """加载本地 GeoJSON 文件"""
    with open(filepath, encoding="utf-8") as f:
        return cast(GeoJSONDict, json.load(f))


def dump_geojson(filepath: StrPath, data: GeoJSONDict) -> None:
    """导出本地 GeoJSON 文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


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
