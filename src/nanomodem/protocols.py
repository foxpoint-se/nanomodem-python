"""Protocol definitions for the acoustic modem system.

All interfaces live here. Implementations live in their respective packages
(transports/, drivers/, codecs/, calculation.py).
"""

from __future__ import annotations

from typing import Callable, Protocol

from .types import Coord, Message

OnMessageCallback = Callable[[Message], None]


class TransportProtocol(Protocol):
    """Message-level interface for sending/receiving. Inject into AcousticNode.

    Works at the message level, not bytes. Each implementation handles
    encoding/decoding internally (SerialTransport uses a Driver,
    MockTransport routes typed messages directly).
    """

    def broadcast_position(self, coord: Coord, depth: float) -> None: ...

    def request_range(self, target_id: str) -> None: ...

    def on_message(self, callback: OnMessageCallback) -> None: ...


class DriverProtocol(Protocol):
    """Modem command protocol: framing + body encoding/decoding.

    Knows how to format outgoing commands and parse incoming responses
    for a specific modem version. Composed by SerialTransport.
    """

    def format_broadcast(self, node_id: str, coord: Coord, depth: float) -> bytes: ...

    def format_ping(self, target_id: str) -> bytes: ...

    def parse_line(self, line: str) -> Message: ...


class CodecProtocol(Protocol):
    """Body encoding/decoding for message payloads. Composed by drivers."""

    def encode_position(self, node_id: str, coord: Coord, depth: float) -> bytes: ...

    def decode(self, payload: bytes) -> Message: ...


class CalculationProtocol(Protocol):
    """Math functions for localization. Inject into AcousticNode."""

    def trilaterate(self, positions: list[Coord], distances: list[float]) -> Coord: ...

    def project_3d_to_2d(self, distance_3d: float, host_depth: float, beacon_depth: float) -> float: ...

    def timestamp_to_distance(self, timestamp: int, sound_speed: float) -> float: ...
