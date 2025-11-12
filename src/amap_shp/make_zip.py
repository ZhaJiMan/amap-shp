from __future__ import annotations

from zipfile import ZIP_DEFLATED, ZipFile

from loguru import logger

from amap_shp.utils import get_output_dir


def main() -> None:
    dirpath = get_output_dir()

    with ZipFile(
        dirpath / "geojson.zip", mode="w", compression=ZIP_DEFLATED, compresslevel=7
    ) as f:
        for filepath in dirpath.glob("*.json"):
            f.write(filepath, filepath.name)
            logger.info(f"{filepath.name} 压缩完成")

    for filepath in dirpath.glob("*.json"):
        filepath.unlink()
    logger.info("清理 GeoJSON 文件")


if __name__ == "__main__":
    main()
