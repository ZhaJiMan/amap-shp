from __future__ import annotations

from amap_shp import (
    download_nine_line,
    download_raw_district,
    make_zip,
    process_raw_district,
)

__all__ = ["main"]


def main() -> None:
    download_nine_line.main()
    download_raw_district.main()
    process_raw_district.main()
    make_zip.main()


if __name__ == "__main__":
    main()
