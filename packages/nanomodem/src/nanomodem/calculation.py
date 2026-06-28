"""Pure math functions for localization. Stateless, no I/O."""

from __future__ import annotations

import math

from .types import Coord

__all__ = ["calculate_distance_3d"]


def calculate_distance_3d(
    coord_a: Coord,
    depth_a: float,
    coord_b: Coord,
    depth_b: float,
) -> float:
    """Euclidean distance in meters using flat-earth approximation.

    - 1 degree lat ~ 111320 m
    - 1 degree lon ~ 111320 * cos(lat) m
    """
    lat_m = (coord_b.lat - coord_a.lat) * 111320.0
    avg_lat = math.radians((coord_a.lat + coord_b.lat) / 2.0)
    lon_m = (coord_b.lon - coord_a.lon) * 111320.0 * math.cos(avg_lat)
    depth_m = depth_b - depth_a
    return math.sqrt(lat_m**2 + lon_m**2 + depth_m**2)
