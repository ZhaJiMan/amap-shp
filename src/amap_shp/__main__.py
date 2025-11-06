from __future__ import annotations

from amap_shp import download_district_data, make_geojson, make_zip


def main() -> None:
    download_district_data.main()
    make_geojson.main()
    make_zip.main()


if __name__ == "__main__":
    main()
