from io import StringIO

import numpy as np
import pandas as pd
import shapefile
import shapely.geometry as sgeom
from shapely.ops import unary_union

def polygon_to_polys(polygon):
    '''将多边形对象转为shapefile适用的坐标序列.'''
    polys = []
    for polygon in getattr(polygon, 'geoms', [polygon]):
        for ring in [polygon.exterior, *polygon.interiors]:
            polys.append(ring.coords[:])

    return polys

def polyline_to_polys(polyline):
    '''将高德地图的polyline字符串转为shapefile适用的坐标序列.'''
    coordinates = [
         np.loadtxt(StringIO(part), delimiter=',').tolist()
         for part in polyline.replace(';', '\n').split('|')
    ]
    polygon = unary_union(list(map(sgeom.Polygon, coordinates)))
    polys = polygon_to_polys(polygon)

    return polys

def make_prj_file(filepath):
    '''制作WGS-84坐标系的prj文件.'''
    wkt = 'GEOGCS["WGS84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.017453292519943295]]'
    with open(str(filepath), 'w', encoding='utf-8') as f:
        f.write(wkt)

def convert_gcj_to_wgs(gcj_filepath, wgs_filepath, validation=True):
    '''将GCJ-02坐标系的shapefile文件转到WGS84坐标系.'''
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

def records_to_df(shp_filepath):
    '''将shapefile文件的记录转为DataFrame.'''
    records = []
    with shapefile.Reader(str(shp_filepath)) as reader:
        for record in reader.records():
            records.append(record.as_dict())
    df = pd.DataFrame.from_records(records)

    return df

def shorten_pr_name(name):
    '''缩短省名.'''
    if name.startswith('内蒙古') or name.startswith('黑龙江'):
        return name[:3]
    else:
        return name[:2]

def shorten_ct_name(name):
    '''缩短市名.'''
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
        '县',
        '盟',
        '省',
        '市'
    ]:
        if word in name:
            index = name.index(word)
            name = name[:index]
            break

    return name