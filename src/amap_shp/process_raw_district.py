from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import cast

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


def assert_polyline_coverage_valid(gdf: gpd.GeoDataFrame) -> None:
    """断言每组 polyline 构成的 coverage 是否有效"""
    assert (  # pyright: ignore[reportGeneralTypeIssues]
        gdf.groupby("district_adcode")["geometry"]
        .agg(gpd.GeoSeries.is_valid_coverage)  # pyright: ignore[reportAttributeAccessIssue]
        .all()
    )


def assert_coverage_valid_excluding(
    gdf: gpd.GeoDataFrame, exclude_adcodes: Sequence[int]
) -> None:
    """断言排除了指定区县后的 coverage 是否有效"""
    assert gdf[~gdf["district_adcode"].isin(exclude_adcodes)].is_valid_coverage()


def union_polylines(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """合并每组 polyline 的多边形"""
    return cast(
        gpd.GeoDataFrame,
        gdf.dissolve("district_adcode", as_index=False, method="coverage")[gdf.columns],
    )


def repair_polygons(gdf: gpd.GeoDataFrame, adcodes: Iterable[int]) -> gpd.GeoDataFrame:
    """修复存在重叠的多边形

    如果有多边形跟邻接多边形有重叠，通过用邻接多边形重新围出它们的形状来进行修复。
    该方法仅限于周围一圈都是正常多边形的情况，因此需要小心使用。
    """
    gdf = cast(gpd.GeoDataFrame, gdf.set_index("district_adcode", drop=False))

    for adcode in adcodes:
        polygon = gdf.loc[adcode, "geometry"]
        polygon = cast(shapely.Polygon | shapely.MultiPolygon, polygon)
        adjacent_polygons = gdf.geometry[
            (gdf.index != adcode) & gdf.intersects(polygon)
        ]
        adjacent_polygons = cast(gpd.GeoSeries, adjacent_polygons)
        # 如果没有飞地，那么邻接的一圈多边形需要填补空洞
        if not isinstance(polygon, shapely.MultiPolygon):
            adjacent_polygons = adjacent_polygons.map(fill_polygon)

        unioned_polygon = adjacent_polygons.union_all(method="coverage")
        unioned_polygon = cast(shapely.Polygon | shapely.MultiPolygon, unioned_polygon)
        filled_polygon = fill_polygon(unioned_polygon)
        gdf.loc[adcode, "geometry"] = filled_polygon - unioned_polygon

    gdf = cast(gpd.GeoDataFrame, gdf.reset_index(drop=True))

    return gdf


def main() -> None:
    dirpath = get_output_dir()
    raw_filepath = dirpath / "cn_district_raw.geojson"
    new_filepath = dirpath / "cn_district.geojson"

    gdf = load_geojson(raw_filepath)
    assert not gdf.is_empty.any()
    assert gdf.is_valid.all()

    # TODO: coverage union 会不会太严格了？
    gdf = round_geometry(gcj_to_wgs(gdf))
    assert_polyline_coverage_valid(gdf)
    gdf = union_polylines(gdf)

    coverage_valid = gdf.is_valid_coverage()
    if not coverage_valid:
        logger.warning("区县数据存在重叠，尝试修复")
        abnormal_adcodes = [360822, 360983]  # 江西省南昌市吉水县和高安市
        assert_coverage_valid_excluding(gdf, abnormal_adcodes)
        gdf = repair_polygons(gdf, abnormal_adcodes)
        gdf = round_geometry(gdf)

    assert not gdf.is_empty.any()
    assert gdf.is_valid.all()
    if not coverage_valid:
        assert gdf.is_valid_coverage()

    dump_geojson(gdf, new_filepath)
    logger.info("区县数据处理完成")


if __name__ == "__main__":
    main()
