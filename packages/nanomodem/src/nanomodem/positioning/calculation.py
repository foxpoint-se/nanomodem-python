"""LBL math functions. Stateless, no I/O."""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import least_squares

from nanomodem.core.spec import distance_to_timestamp, timestamp_to_distance
from nanomodem.types import Coord


class Calculation:
    """Concrete implementation of calculation functions."""

    def trilaterate(self, positions: list[Coord], distances: list[float]) -> Coord:
        """Estimate position from 3+ beacon positions and distances."""
        if len(positions) < 3 or len(positions) != len(distances):
            raise ValueError("Need at least 3 beacons with matching distances")

        origin = positions[0]
        avg_lat = math.radians(sum(p.lat for p in positions) / len(positions))
        lat_scale = 111320.0
        lon_scale = 111320.0 * math.cos(avg_lat)

        beacon_xy = np.array(
            [
                [
                    (p.lat - origin.lat) * lat_scale,
                    (p.lon - origin.lon) * lon_scale,
                ]
                for p in positions
            ]
        )
        dists = np.array(distances)

        initial_guess = np.mean(beacon_xy, axis=0)

        def residuals(pos: np.ndarray) -> np.ndarray:
            calculated: np.ndarray = np.linalg.norm(beacon_xy - pos, axis=1)
            res: np.ndarray = calculated - dists
            return res

        result = least_squares(residuals, initial_guess, method="lm")

        est_lat = origin.lat + result.x[0] / lat_scale
        est_lon = origin.lon + result.x[1] / lon_scale

        return Coord(lat=est_lat, lon=est_lon)

    def project_3d_to_2d(self, distance_3d: float, host_depth: float, beacon_depth: float) -> float:
        """Project a 3D distance onto the 2D horizontal plane."""
        dz = host_depth - beacon_depth
        d_squared = distance_3d**2 - dz**2
        if d_squared < 0:
            return 0.0
        return math.sqrt(d_squared)

    def timestamp_to_distance(self, timestamp: int, sound_speed: float) -> float:
        """Convert modem timestamp to distance in meters."""
        return timestamp_to_distance(timestamp, sound_speed)

    def distance_to_timestamp(self, distance: float, sound_speed: float) -> int:
        """Convert distance in meters to modem timestamp units."""
        return distance_to_timestamp(distance, sound_speed)
