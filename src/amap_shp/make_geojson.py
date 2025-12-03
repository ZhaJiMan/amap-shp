from __future__ import annotations

from typing import cast

import geopandas as gpd
from loguru import logger

from amap_shp.utils import dump_geojson, get_output_dir, load_geojson


def make_city_geodataframe(district_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """用区县数据合成市级数据"""
    return cast(
        gpd.GeoDataFrame,
        district_gdf.dissolve("city_adcode", as_index=False, method="coverage")[
            district_gdf.columns
        ]
        .drop(columns=["district_name", "district_adcode"])
        .reset_index(drop=True),
    )


def make_province_geodataframe(city_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """用市级数据合成省级数据"""
    return cast(
        gpd.GeoDataFrame,
        city_gdf.dissolve("province_adcode", as_index=False, method="coverage")[
            city_gdf.columns
        ]
        .drop(columns=["city_name", "city_adcode"])
        .reset_index(drop=True),
    )


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
    district_gdf = load_geojson(dirpath / "cn_district.geojson")

    city_gdf = make_city_geodataframe(district_gdf)
    dump_geojson(city_gdf, dirpath / "cn_city.geojson")
    logger.info("市级数据制作完成")

    province_gdf = make_province_geodataframe(city_gdf)
    dump_geojson(province_gdf, dirpath / "cn_province.geojson")
    logger.info("省级数据制作完成")

    border_gdf = make_border_geodataframe(province_gdf)
    dump_geojson(border_gdf, dirpath / "cn_border.geojson")
    logger.info("国界数据制作完成")


if __name__ == "__main__":
    main()
