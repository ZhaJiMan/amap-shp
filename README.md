# amap-shp

## 简介

从 [高德地图行政区域查询接口](https://lbs.amap.com/api/webservice/guide/api/district) 下载县级行政区划数据，再合成市级、省级和国界的 GeoJSON，最后打包成 ZIP。

从 [DataV.GeoAtlas](https://datav.aliyun.com/portal/school/atlas/area_selector) 下载九段线数据并保存 GeoJSON。

坐标已从 GCJ-02 处理成了 WGS84。

## 用法

注册高德开放平台账号并申请密钥（key），将 key 填入 `.env` 配置文件。

在项目根目录下运行：

```bash
uv sync      # 同步依赖
uv run main  # 运行主程序
```

结果默认输出到项目根目录下的 `output` 目录，也可以通过 `.env` 里的 `OUTPUT_DIR` 进行配置。

## 图例

由 [frykit](https://github.com/ZhaJiMan/frykit) 制作：

![province_map](image/province_map.png)

![city_map](image/city_map.png)

![district_map](image/district_map.png)
