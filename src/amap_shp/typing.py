from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

__all__ = [
    "CityProperties",
    "CountryProperties",
    "DistrictData",
    "DistrictDict",
    "DistrictProperties",
    "ProvinceProperties",
    "RawDistrictProperties",
    "SuggestionDict",
]


class SuggestionDict(TypedDict):
    keywords: list[str]
    cities: list[str]


class DistrictDict(TypedDict):
    citycode: str | list[str]  # country 和 province 的 citycode 是空列表
    adcode: str
    name: str
    polyline: str  # 仅当 extentions=all 时第一级才有 polyline 字段
    center: str
    level: Literal["country", "province", "city", "district", "street"]
    districts: list[DistrictDict]


class DistrictData(TypedDict):
    status: Literal["0", "1"]
    info: str
    infocode: str
    # 仅当 status 为 "1" 时才有以下字段
    count: str
    suggestion: SuggestionDict
    districts: list[DistrictDict]


class RawDistrictProperties(TypedDict):
    province_name: str
    province_adcode: int
    city_name: str
    city_adcode: int
    district_name: str
    district_adcode: int
    short_name: NotRequired[str]


class DistrictProperties(TypedDict):
    province_name: str
    province_adcode: int
    city_name: str
    city_adcode: int
    district_name: str
    district_adcode: int
    short_name: str


class CityProperties(TypedDict):
    province_name: str
    province_adcode: int
    city_name: str
    city_adcode: int
    short_name: str


class ProvinceProperties(TypedDict):
    province_name: str
    province_adcode: int
    short_name: str


class CountryProperties(TypedDict):
    country_name: str
    country_adcode: int
