from __future__ import annotations

import geopandas as gpd
import shapely
from loguru import logger

from amap_shp.utils import (
    dump_geojson,
    fill_polygon,
    gcj_to_wgs,
    get_output_dir,
    load_geojson,
    round_geometry,
)


def union_polylines(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """合并每组 polyline 的多边形"""
    return gdf.dissolve("district_adcode", as_index=False, method="coverage")[
        gdf.columns
    ]


def repair_polygons(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """修复存在重叠的多边形

    如果有多边形跟邻接多边形有重叠，通过用邻接多边形重新围出它们的形状来进行修复。
    该方法仅限于周围一圈都是正常多边形的情况，因此需要小心使用。
    """
    gdf = gdf.set_index("district_adcode", drop=False)

    for adcode in [360822, 360983]:  # 江西省南昌市吉水县和高安市
        polygon = gdf.loc[adcode, "geometry"]
        adjacent_polygons = gdf.geometry[
            (gdf.index != adcode) & gdf.intersects(polygon)
        ]
        # 如果没有飞地，那么邻接的一圈多边形需要填补空洞
        if not isinstance(polygon, shapely.MultiPolygon):
            adjacent_polygons = adjacent_polygons.map(fill_polygon)

        union_polygon = adjacent_polygons.union_all(method="coverage")
        filled_polygon = fill_polygon(union_polygon)
        gdf.loc[adcode, "geometry"] = filled_polygon - union_polygon

    return gdf.reset_index(drop=True)


def main() -> None:
    dirpath = get_output_dir()
    raw_filepath = dirpath / "cn_district_raw.geojson"
    new_filepath = dirpath / "cn_district.geojson"

    gdf = (
        load_geojson(raw_filepath)
        .pipe(gcj_to_wgs)
        .pipe(round_geometry)
        .pipe(union_polylines)
        .pipe(repair_polygons)  # 多边形没问题时注释此行
        .pipe(round_geometry)
    )

    assert not gdf.is_empty.any(), gdf[gdf.is_empty]
    assert gdf.is_valid.all(), gdf[~gdf.is_valid]
    assert gdf.is_valid_coverage(), gdf[~gdf.is_valid_coverage()]

    dump_geojson(gdf, new_filepath)
    logger.info("区县数据处理完成")


if __name__ == "__main__":
    main()
