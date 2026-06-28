"""Types for positioning layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from nanomodem.types import Coord


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
