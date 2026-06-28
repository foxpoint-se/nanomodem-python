"""nanomodem — acoustic modem communication and localization library."""

from __future__ import annotations

import importlib
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nanomodem.positioning.basic_position_codec import BasicPositionCodec
    from nanomodem.positioning.calculation import Calculation
    from nanomodem.positioning.positioning_node import PositioningNode
    from nanomodem.positioning.protocols import CalculationProtocol
    from nanomodem.positioning.types import KnownNode, NodeCapabilities

try:
    __version__ = version("nanomodem")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    "PositioningNode",
    "BasicPositionCodec",
    "Calculation",
    "CalculationProtocol",
    "KnownNode",
    "NodeCapabilities",
]

_POSITIONING_EXPORTS = frozenset(
    {
        "PositioningNode",
        "BasicPositionCodec",
        "Calculation",
        "CalculationProtocol",
        "KnownNode",
        "NodeCapabilities",
    },
)


def __getattr__(name: str) -> object:
    if name in _POSITIONING_EXPORTS:
        positioning = importlib.import_module("nanomodem.positioning")
        value = getattr(positioning, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
