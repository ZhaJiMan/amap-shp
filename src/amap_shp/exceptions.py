from __future__ import annotations

__all__ = ["AmapDataError", "AmapError", "AmapStatusError"]


class AmapError(Exception):
    pass


class AmapDataError(AmapError):
    pass


class AmapStatusError(AmapError):
    def __init__(self, info: str, infocode: str) -> None:
        self.info = info
        self.infocode = infocode
        super().__init__(info, infocode)

    def __str__(self) -> str:
        return f"info='{self.info}', infocode='{self.infocode}'"

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f"{cls_name}(info={self.info!r}, infocode={self.infocode!r})"
