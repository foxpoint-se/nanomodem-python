"""Pure math functions for localization. Stateless, no I/O."""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import least_squares

from .constants import MODEM_TIMESTAMP_QUANTUM_S, validate_sound_speed
from .types import Coord


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


class Calculation:
    """Concrete implementation of calculation functions."""

    def trilaterate(self, positions: list[Coord], distances: list[float]) -> Coord:
        """Estimate position from 3+ beacon positions and distances.

        Uses scipy least_squares for robustness with imperfect circles.
        Works in a flat-earth metric space (meters from first beacon).
        Returns a Coord with the estimated lat/lon (depth=0).
        """
        if len(positions) < 3 or len(positions) != len(distances):
            raise ValueError("Need at least 3 beacons with matching distances")

        # Convert lat/lon to local meters relative to first beacon
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

        # Initial guess: centroid of beacons
        initial_guess = np.mean(beacon_xy, axis=0)

        def residuals(pos: np.ndarray) -> np.ndarray:
            calculated: np.ndarray = np.linalg.norm(beacon_xy - pos, axis=1)
            res: np.ndarray = calculated - dists
            return res

        result = least_squares(residuals, initial_guess, method="lm")

        # Convert back to lat/lon
        est_lat = origin.lat + result.x[0] / lat_scale
        est_lon = origin.lon + result.x[1] / lon_scale

        return Coord(lat=est_lat, lon=est_lon)

    def project_3d_to_2d(self, distance_3d: float, host_depth: float, beacon_depth: float) -> float:
        """Project a 3D distance onto the 2D horizontal plane.

        Formula: 2d_distance = sqrt(d^2 - (z_host - z_beacon)^2)
        If the depth difference exceeds the 3D distance (measurement error),
        returns 0.0.
        """
        dz = host_depth - beacon_depth
        d_squared = distance_3d**2 - dz**2
        if d_squared < 0:
            return 0.0
        return math.sqrt(d_squared)

    def timestamp_to_distance(self, timestamp: int, sound_speed: float) -> float:
        """Convert modem timestamp to distance in meters.

        Formula: distance = timestamp * MODEM_TIMESTAMP_QUANTUM_S * sound_speed
        """
        validate_sound_speed(sound_speed)
        return timestamp * MODEM_TIMESTAMP_QUANTUM_S * sound_speed

    def distance_to_timestamp(self, distance: float, sound_speed: float) -> int:
        """Convert distance in meters to modem timestamp units."""
        validate_sound_speed(sound_speed)
        return round((distance / sound_speed) / MODEM_TIMESTAMP_QUANTUM_S)
