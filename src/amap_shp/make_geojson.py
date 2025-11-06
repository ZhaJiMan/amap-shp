from __future__ import annotations

from typing import cast

import frykit.shp as fshp
import numpy as np
import shapely
from frykit.shp.typing import FeatureDict, GeoJSONDict
from loguru import logger

from amap_shp.typing import (
    CityProperties,
    CountryProperties,
    DistrictProperties,
    ProvinceProperties,
)
from amap_shp.utils import (
    dump_json,
    get_data_dir,
    load_json,
    shorten_city_name,
    shorten_province_name,
)


def make_city_geojson(district_data: GeoJSONDict) -> GeoJSONDict:
    """用区县数据合成市级 GeoJSON"""
    df = fshp.get_geojson_properties(district_data)
    polygons = np.array(fshp.get_geojson_geometries(district_data))

    features: list[FeatureDict] = []
    for _, group in df.groupby(df["city_adcode"]):
        polygon = shapely.union_all(polygons[group.index])
        polygon = cast(shapely.Polygon | shapely.MultiPolygon, polygon)
        geometry_dict = fshp.geometry_to_dict(polygon)

        district_properties: DistrictProperties = group.iloc[0].to_dict()
        city_properties: CityProperties = {
            "province_name": district_properties["province_name"],
            "province_adcode": district_properties["province_adcode"],
            "city_name": district_properties["city_name"],
            "city_adcode": district_properties["city_adcode"],
            "short_name": shorten_city_name(district_properties["city_name"]),
        }

        feature = fshp.make_feature(geometry_dict, city_properties)  # pyright: ignore[reportArgumentType]
        features.append(feature)

    city_data = fshp.make_geojson(features)

    return city_data


def make_province_geojson(city_data: GeoJSONDict) -> GeoJSONDict:
    """用市级数据合成省级 GeoJSON"""
    df = fshp.get_geojson_properties(city_data)
    polygons = np.array(fshp.get_geojson_geometries(city_data))

    features: list[FeatureDict] = []
    for _, group in df.groupby(df["province_adcode"]):
        polygon = shapely.union_all(polygons[group.index])
        polygon = cast(shapely.Polygon | shapely.MultiPolygon, polygon)
        geometry_dict = fshp.geometry_to_dict(polygon)

        city_properties: CityProperties = group.iloc[0].to_dict()
        province_properties: ProvinceProperties = {
            "province_name": city_properties["province_name"],
            "province_adcode": city_properties["province_adcode"],
            "short_name": shorten_province_name(city_properties["province_name"]),
        }

        feature = fshp.make_feature(geometry_dict, province_properties)  # pyright: ignore[reportArgumentType]
        features.append(feature)

    province_data = fshp.make_geojson(features)

    return province_data


def make_border_geojson(province_data: GeoJSONDict) -> GeoJSONDict:
    """用省级数据合成国界 GeoJSON"""
    polygons = fshp.get_geojson_geometries(province_data)
    polygon = cast(shapely.MultiPolygon, shapely.union_all(polygons))
    geometry_dict = fshp.geometry_to_dict(polygon)
    properties: CountryProperties = {
        "country_name": "中华人民共和国",
        "country_adcode": 100000,
    }
    feature = fshp.make_feature(geometry_dict, properties)
    country_data = fshp.make_geojson([feature])

    return country_data


def main() -> None:
    dirpath = get_data_dir()

    district_data = load_json(dirpath / "cn_district.json")
    district_data = cast(GeoJSONDict, district_data)

    city_data = make_city_geojson(district_data)
    dump_json(dirpath / "cn_city.json", city_data)
    logger.info("市级数据制作完成")

    province_data = make_province_geojson(city_data)
    dump_json(dirpath / "cn_province.json", province_data)
    logger.info("省级数据制作完成")

    border_data = make_border_geojson(province_data)
    dump_json(dirpath / "cn_border.json", border_data)
    logger.info("国界数据制作完成")


if __name__ == "__main__":
    main()
