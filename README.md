# amap-shp

从 [高德地图行政区域查询接口](https://lbs.amap.com/api/webservice/guide/api/district) 下载县级行政区划数据，再合并出市级、省级和国界的 shapefile。

从 [DataV.GeoAtlas](https://datav.aliyun.com/portal/school/atlas/area_selector) 下载九段线数据并生成 shapefile。

原理和注意事项在 notebook 中已有详述。

示例效果如下（用 [frykit](https://github.com/ZhaJiMan/frykit) 制作）

![province_map](image/province_map.png)

![city_map](image/city_map.png)

![district_map](image/district_map.png)