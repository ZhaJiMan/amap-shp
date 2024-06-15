from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import shapefile
import shapely.geometry as sgeom
from shapely.ops import unary_union


def polygon_to_polys(polygon: sgeom.Polygon | sgeom.MultiPolygon) -> list:
    '''将多边形对象转为 shapefile 适用的坐标序列'''
    polys = []
    for polygon in getattr(polygon, 'geoms', [polygon]):
        for ring in [polygon.exterior, *polygon.interiors]:
            polys.append(ring.coords[:])

    return polys


def polyline_to_polygon(polyline: str) -> sgeom.Polygon | sgeom.MultiPolygon:
    '''将高德地图的 polyline 字符串转为多边形对象'''
    coordinates = [
        np.loadtxt(StringIO(part), delimiter=',').tolist()
        for part in polyline.replace(';', '\n').split('|')
    ]
    polygon = unary_union(list(map(sgeom.Polygon, coordinates)))

    return polygon


def polygon_center(
    polygon: sgeom.Polygon | sgeom.MultiPolygon,
) -> tuple[float, float]:
    '''获取多边形中心点的坐标'''
    point = polygon.representative_point()
    return point.x, point.y


def make_prj_file(filepath: str | Path) -> None:
    '''制作 WGS-84 坐标系的 prj 文件'''
    wkt = 'GEOGCS["WGS84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.017453292519943295]]'
    with open(str(filepath), 'w', encoding='utf-8') as f:
        f.write(wkt)


def gcj_to_wgs(
    gcj_filepath: str | Path, wgs_filepath: str | Path, validation: bool = True
) -> None:
    '''将 GCJ-02 坐标系的 shapefile 转到 WGS84 坐标系'''
    from prcoords import gcj_wgs_bored

    with shapefile.Reader(str(gcj_filepath)) as reader:
        with shapefile.Writer(str(wgs_filepath)) as writer:
            writer.fields = reader.fields[1:]
            for shapeRec in reader.shapeRecords():
                writer.record(*shapeRec.record)
                shape = shapeRec.shape
                for i in range(len(shape.points)):
                    lon, lat = shape.points[i]
                    lat, lon = gcj_wgs_bored((lat, lon))
                    shape.points[i] = [lon, lat]
                if validation and not sgeom.shape(shape).is_valid:
                    raise ValueError('转换导致几何错误')
                writer.shape(shape)


def shp_to_df(shp_filepath: str | Path) -> pd.DataFrame:
    '''将 shapefile 记录转为 DataFrame'''
    records = []
    with shapefile.Reader(str(shp_filepath)) as reader:
        for record in reader.records():
            records.append(record.as_dict())
    df = pd.DataFrame.from_records(records)

    return df


def shorten_pr_name(name: str) -> str:
    '''缩短省名。只保留前几个字。'''
    if name.startswith('内蒙古') or name.startswith('黑龙江'):
        return name[:3]
    return name[:2]


def shorten_ct_name(name: str) -> str:
    '''缩短市名。只保留前几个字。'''
    if name.startswith('重庆'):
        return name

    for word in [
        '土家族苗族自治州',
        '布依族苗族自治州',
        '哈尼族彝族自治州',
        '蒙古族藏族自治州',
        '傣族景颇族自治州',
        '苏柯尔克孜自治州',
        '黎族苗族自治县',
        '苗族侗族自治州',
        '藏族羌族自治州',
        '壮族苗族自治州',
        '朝鲜族自治州',
        '傈僳族自治州',
        '哈萨克自治州',
        '彝族自治州',
        '藏族自治州',
        '黎族自治县',
        '傣族自治州',
        '回族自治州',
        '蒙古自治州',
        '白族自治州',
        '特别行政区',
        '林区',
        '地区',
        '城区',
        '县',
        '盟',
        '省',
        '市',
    ]:
        if word in name:
            index = name.index(word)
            return name[:index]
    else:
        raise ValueError(name)


def shorten_dt_name(name: str) -> str:
    '''缩短区县名。只省略掉民族部分，保留行政区划单字。'''

    if name == '喀喇沁左翼蒙古族自治县':
        return '喀左县'

    if name == '东乡族自治县':
        return '东乡县'

    if name == '鄂温克族自治旗':
        return '鄂温克旗'

    if name == '海西蒙古族藏族自治州直辖':
        return '自治州直辖'

    for word in [
        '拉祜族佤族布朗族傣族自治县',
        '彝族回族苗族自治县',
        '彝族哈尼族拉祜族自治县',
        '哈尼族彝族傣族自治县',
        '傣族拉祜族佤族自治县',
        '苗族瑶族傣族自治县',
        '保安族东乡族撒拉族自治县',
        '白族普米族自治县',
        '独龙族怒族自治县',
        '满族蒙古族自治县',
        '苗族侗族自治县',
        '黎族苗族自治县',
        '土家族苗族自治县',
        '苗族土家族自治县',
        '仡佬族苗族自治县',
        '布依族苗族自治县',
        '苗族布依族自治县',
        '壮族瑶族自治县',
        '回族彝族自治县',
        '回族土族自治县',
        '哈尼族彝族自治县',
        '傣族彝族自治县',
        '傣族佤族自治县',
        '彝族苗族自治县',
        '彝族傣族自治县',
        '彝族回族自治县',
        '蒙古族自治县',
        '满族自治县',
        '回族自治县',
        '朝鲜族自治县',
        '畲族自治县',
        '侗族自治县',
        '苗族自治县',
        '黎族自治县',
        '土族自治县',
        '土家族自治县',
        '瑶族自治县',
        '仫佬族自治县',
        '毛南族自治县',
        '羌族自治县',
        '彝族自治县',
        '藏族自治县',
        '水族自治县',
        '纳西族自治县',
        '哈尼族自治县',
        '拉祜族自治县',
        '佤族自治县',
        '傈僳族自治县',
        '裕固族自治县',
        '哈萨克族自治县',
        '撒拉族自治县',
        '哈萨克自治县',
        '塔吉克自治县',
        '锡伯自治县',
        '蒙古自治县',
        '各族自治县',
        '达斡尔族自治旗',
        '达斡尔族区',
        '回族区',
        '自治旗',
    ]:
        if word in name:
            index = name.index(word)
            return name[:index] + word[-1]

    return name
