from __future__ import annotations

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


def union_polylines(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """合并每组 polyline 的多边形"""
    return cast(
        gpd.GeoDataFrame,
        gdf.dissolve("district_adcode", as_index=False, method="coverage")[gdf.columns],
    )


def repair_polygons(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """修复存在重叠的多边形

    如果有多边形跟邻接多边形有重叠，通过用邻接多边形重新围出它们的形状来进行修复。
    该方法仅限于周围一圈都是正常多边形的情况，因此需要小心使用。
    """
    gdf = cast(gpd.GeoDataFrame, gdf.set_index("district_adcode", drop=False))
    for adcode in [360822, 360983]:  # 江西省南昌市吉水县和高安市
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


def make_city_geodataframe(district_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """用区县数据合成市级数据"""
    city_gdf = (
        district_gdf.dissolve("city_adcode", as_index=False, method="coverage")[
            district_gdf.columns
        ]
        .drop(columns=["district_name", "district_adcode"])
        .reset_index(drop=True)
    )

    return cast(gpd.GeoDataFrame, city_gdf)


def make_province_geodataframe(city_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """用市级数据合成省级数据"""
    province_gdf = (
        city_gdf.dissolve("province_adcode", as_index=False, method="coverage")[
            city_gdf.columns
        ]
        .drop(columns=["city_name", "city_adcode"])
        .reset_index(drop=True)
    )

    return cast(gpd.GeoDataFrame, province_gdf)


def make_border_geodataframe(province_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """用省级数据合成国界数据"""
    record = {
        "country_name": "中华人民共和国",
        "country_adcode": 100000,
        "geometry": province_gdf.union_all(method="coverage"),
    }

    return gpd.GeoDataFrame([record], crs=4326)


def main() -> None:
    dirpath = get_output_dir()
    raw_district_gdf = load_geojson(dirpath / "cn_district_raw.geojson")
    district_gdf = raw_district_gdf.pipe(gcj_to_wgs).pipe(union_polylines)
    district_gdf = repair_polygons(district_gdf)  # 临时修复

    city_gdf = make_city_geodataframe(district_gdf)
    province_gdf = make_province_geodataframe(city_gdf)
    border_gdf = make_border_geodataframe(province_gdf)

    for level, gdf in [
        ("district", district_gdf),
        ("city", city_gdf),
        ("province", province_gdf),
        ("border", border_gdf),
    ]:
        gdf = round_geometry(gdf)
        assert not gdf.is_empty.any()
        assert gdf.is_valid.all()
        assert gdf.is_valid_coverage()
        filename = f"cn_{level}.geojson"
        dump_geojson(gdf, dirpath / filename)
        logger.info(f"{filename} 制作完成")


if __name__ == "__main__":
    main()
