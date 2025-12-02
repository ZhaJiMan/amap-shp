from __future__ import annotations

import json
import os
from pathlib import Path
from typing import overload

import geopandas as gpd
import numpy as np
import shapely
from dotenv import load_dotenv
from numpy.typing import ArrayLike, NDArray
from prcoords import gcj_wgs_bored

__all__ = [
    "dump_geojson",
    "fill_polygon",
    "gcj_to_wgs",
    "get_amap_key",
    "get_output_dir",
    "load_geojson",
    "round_geometry",
]

load_dotenv()


def get_amap_key() -> str:
    return os.getenv("AMAP_KEY", "")


def get_output_dir() -> Path:
    return Path(os.getenv("OUTPUT_DIR", "output"))


def load_geojson(filepath: str | Path) -> gpd.GeoDataFrame:
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    gdf = gpd.GeoDataFrame.from_features(data["features"], crs=4326)

    return gdf


# to_json 比 pyogrio 快
def dump_geojson(gdf: gpd.GeoDataFrame, filepath: str | Path):
    gdf = gdf.set_geometry(gdf.orient_polygons())
    data = gdf.to_json(drop_id=True, ensure_ascii=False)
    with open(filepath, mode="w", encoding="utf-8") as f:
        f.write(data)


# TODO: vectorize
def _gcj_to_wgs(coords: ArrayLike) -> NDArray[np.float64]:
    coords = np.asarray(coords, dtype=np.float64)
    tups: list[tuple[float, float]] = []
    for lon, lat in coords.tolist():
        lat, lon = gcj_wgs_bored((lat, lon))
        tups.append((lon, lat))

    return np.array(tups)


def gcj_to_wgs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gdf.set_geometry(gdf.transform(_gcj_to_wgs))


# TODO: mode="valid_output"
def round_geometry(gdf: gpd.GeoDataFrame, decimals: int = 6) -> gpd.GeoDataFrame:
    return gdf.set_geometry(gdf.set_precision(10**-decimals, mode="pointwise"))


@overload
def fill_polygon(polygon: shapely.Polygon) -> shapely.Polygon: ...


@overload
def fill_polygon(polygon: shapely.MultiPolygon) -> shapely.MultiPolygon: ...


def fill_polygon(
    polygon: shapely.Polygon | shapely.MultiPolygon,
) -> shapely.Polygon | shapely.MultiPolygon:
    if isinstance(polygon, shapely.Polygon):
        return shapely.Polygon(polygon.exterior)
    else:
        return shapely.MultiPolygon(list(map(fill_polygon, polygon.geoms)))
