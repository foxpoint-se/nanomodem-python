"""nanomodem — acoustic modem communication and localization library."""

from .calculation import Calculation
from .codecs.v3 import Codec
from .constants import (
    MODEM_TIMESTAMP_QUANTUM_S,
    SOUND_SPEED_AIR_M_S,
    SOUND_SPEED_WATER_M_S,
    validate_sound_speed,
)
from .drivers.v3 import NanomodemV3Driver
from .drivers.v3_spec import (
    MAX_BYTES_CORRECTED,
    TEST_MESSAGE_BYTE_COUNT,
    TEST_MESSAGE_PAYLOAD,
    format_test_broadcast_line,
    is_test_broadcast_line,
    supply_voltage_volts,
)
from .errors import ModemIdMismatchError, ModemStatusTimeoutError
from .node import AcousticNode
from .protocols import (
    CalculationProtocol,
    CodecProtocol,
    DriverProtocol,
    OnMessageCallback,
    TransportProtocol,
)
from .transports.mock import MockEther, MockTransport
from .transports.serial import SerialTransport
from .types import (
    Coord,
    KnownNode,
    LocalAckKind,
    LocalAckMessage,
    Message,
    ModemStatusMessage,
    NodeCapabilities,
    PositionMessage,
    QualityIndicatorMessage,
    RangeResponseMessage,
    UnknownMessage,
    V3TestBroadcastMessage,
)

__all__ = [
    "AcousticNode",
    "Calculation",
    "CalculationProtocol",
    "Codec",
    "CodecProtocol",
    "Coord",
    "DriverProtocol",
    "format_test_broadcast_line",
    "KnownNode",
    "LocalAckKind",
    "LocalAckMessage",
    "MAX_BYTES_CORRECTED",
    "Message",
    "MODEM_TIMESTAMP_QUANTUM_S",
    "ModemIdMismatchError",
    "ModemStatusMessage",
    "ModemStatusTimeoutError",
    "MockEther",
    "MockTransport",
    "NanomodemV3Driver",
    "NodeCapabilities",
    "OnMessageCallback",
    "PositionMessage",
    "QualityIndicatorMessage",
    "RangeResponseMessage",
    "V3TestBroadcastMessage",
    "SerialTransport",
    "SOUND_SPEED_AIR_M_S",
    "SOUND_SPEED_WATER_M_S",
    "supply_voltage_volts",
    "TEST_MESSAGE_BYTE_COUNT",
    "TEST_MESSAGE_PAYLOAD",
    "TransportProtocol",
    "UnknownMessage",
    "is_test_broadcast_line",
    "validate_sound_speed",
]
