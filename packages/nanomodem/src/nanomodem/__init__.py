"""nanomodem — acoustic modem communication and localization library."""

from importlib.metadata import PackageNotFoundError, version

from nanomodem.positioning import (
    BasicPositionCodec,
    Calculation,
    CalculationProtocol,
    KnownNode,
    NodeCapabilities,
    PositioningNode,
)

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
