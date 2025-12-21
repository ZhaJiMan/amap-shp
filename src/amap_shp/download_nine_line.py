from __future__ import annotations

import geopandas as gpd
import requests
import shapely.geometry as sgeom
from loguru import logger

from amap_shp.utils import dump_geojson, gcj_to_wgs, get_output_dir, round_geometry


def get_nine_line_geodataframe() -> gpd.GeoDataFrame:
    """获取九段线的 GeoDataFrame"""
    url = "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json"
    resp = requests.get(url)
    data = resp.json()

    # 全国数据的最后一个 feature 是九段线的多边形
    geometry = sgeom.shape(data["features"][-1]["geometry"])
    record = {"name": "九段线", "geometry": geometry}

    return gpd.GeoDataFrame([record], crs=4326)


def main() -> None:
    dirpath = get_output_dir()
    dirpath.mkdir(parents=True, exist_ok=True)

    gdf = get_nine_line_geodataframe().pipe(gcj_to_wgs).pipe(round_geometry)
    assert not gdf.is_empty.any(), gdf[gdf.is_empty]
    assert gdf.is_valid.all(), gdf[~gdf.is_valid]

    dump_geojson(gdf, dirpath / "nine_line.geojson")
    logger.info("九段线数据下载完成")


if __name__ == "__main__":
    main()
