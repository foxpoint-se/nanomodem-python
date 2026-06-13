"""Core types for the acoustic modem localization system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

LocalAckKind = Literal["test", "ping", "broadcast"]


@dataclass(frozen=True)
class Coord:
    """An immutable geographic coordinate (lat, lon)."""

    lat: float
    lon: float


@dataclass
class KnownNode:
    """Mutable record of what we know about another node."""

    node_id: str
    position: Optional[Coord] = None
    depth: float = 0.0
    last_range: Optional[float] = None
    last_seen: Optional[float] = None


@dataclass
class NodeCapabilities:
    """Boolean capabilities that gate automatic node behavior."""

    is_inferring_own_position: bool = False
    is_broadcasting_own_position: bool = False


# --- Messages (discriminated union with catch-all) ---


@dataclass(frozen=True)
class PositionMessage:
    """A node is broadcasting its position."""

    node_id: str
    coord: Coord
    depth: float = 0.0


@dataclass(frozen=True)
class RangeResponseMessage:
    """A range response with a raw timestamp (100 µs units)."""

    node_id: str
    timestamp: int


@dataclass(frozen=True)
class QualityIndicatorMessage:
    """Result of $Q — bytes corrected on last data packet, or rejected."""

    bytes_corrected: int | None


@dataclass(frozen=True)
class LocalAckMessage:
    """Immediate local acknowledgement ($T, $P, $Bnn) before acoustic result."""

    command: LocalAckKind
    target_id: str | None


@dataclass(frozen=True)
class ModemStatusMessage:
    """Result of $? — modem address and supply voltage raw reading."""

    node_id: str
    voltage_raw: int


@dataclass(frozen=True)
class V3TestBroadcastMessage:
    """Received #B broadcast of the fixed v3 DSSS test payload from node_id."""

    node_id: str


@dataclass(frozen=True)
class UnknownMessage:
    """Catch-all for anything the system can't parse yet. Nothing is lost."""

    raw: str


Message = (
    PositionMessage
    | RangeResponseMessage
    | QualityIndicatorMessage
    | LocalAckMessage
    | ModemStatusMessage
    | V3TestBroadcastMessage
    | UnknownMessage
)
