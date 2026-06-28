"""Protocol definitions for positioning layer."""

from __future__ import annotations

from typing import Protocol

from nanomodem.types import Coord


class CalculationProtocol(Protocol):
    """Math functions for localization."""

    def trilaterate(self, positions: list[Coord], distances: list[float]) -> Coord: ...

    def project_3d_to_2d(self, distance_3d: float, host_depth: float, beacon_depth: float) -> float: ...

    def timestamp_to_distance(self, timestamp: int, sound_speed: float) -> float: ...

    def distance_to_timestamp(self, distance: float, sound_speed: float) -> int: ...
