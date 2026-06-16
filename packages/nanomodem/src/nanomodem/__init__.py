"""nanomodem — acoustic modem communication and localization library.

Import from submodules:
    from nanomodem.node import AcousticNode
    from nanomodem.types import Coord
    from nanomodem.transports.serial import SerialTransport
    ...
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nanomodem")
except PackageNotFoundError:
    __version__ = "0.0.0"
