# amap-shp

从 [高德地图行政区域查询接口](https://lbs.amap.com/api/webservice/guide/api/district) 下载县级行政区划数据，再合并出市级、省级和国界的 GeoJSON。

从 [DataV.GeoAtlas](https://datav.aliyun.com/portal/school/atlas/area_selector) 下载九段线数据并生成 GeoJSON。

坐标已从 GCJ-02 坐标系处理到了 WGS84 坐标系上。

示例效果如下（用 [frykit](https://github.com/ZhaJiMan/frykit) 制作）

![province_map](image/province_map.png)

![city_map](image/city_map.png)

![district_map](image/district_map.png)
