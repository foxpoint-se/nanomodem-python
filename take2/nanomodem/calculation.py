"""Pure math functions for localization. Stateless, no I/O."""

from __future__ import annotations

import math
from typing import Protocol

import numpy as np
from scipy.optimize import least_squares

from .types import Coord


class CalculationInterface(Protocol):
    """Interface for calculation functions. Inject into AcousticNode."""

    def trilaterate(
        self, positions: list[Coord], distances: list[float]
    ) -> Coord: ...

    def project_3d_to_2d(
        self, distance_3d: float, host_depth: float, beacon_depth: float
    ) -> float: ...

    def timestamp_to_distance(
        self, timestamp: int, sound_speed: float
    ) -> float: ...


class Calculation:
    """Concrete implementation of calculation functions."""

    def trilaterate(
        self, positions: list[Coord], distances: list[float]
    ) -> Coord:
        """Estimate position from 3+ beacon positions and distances.

        Uses scipy least_squares for robustness with imperfect circles.
        Works in a flat-earth metric space (meters from first beacon).
        Returns a Coord with the estimated lat/lon (depth=0).
        """
        if len(positions) < 3 or len(positions) != len(distances):
            raise ValueError("Need at least 3 beacons with matching distances")

        # Convert lat/lon to local meters relative to first beacon
        origin = positions[0]
        avg_lat = math.radians(
            sum(p.lat for p in positions) / len(positions)
        )
        lat_scale = 111320.0
        lon_scale = 111320.0 * math.cos(avg_lat)

        beacon_xy = np.array([
            [
                (p.lat - origin.lat) * lat_scale,
                (p.lon - origin.lon) * lon_scale,
            ]
            for p in positions
        ])
        dists = np.array(distances)

        # Initial guess: centroid of beacons
        initial_guess = np.mean(beacon_xy, axis=0)

        def residuals(pos: np.ndarray) -> np.ndarray:
            calculated = np.linalg.norm(beacon_xy - pos, axis=1)
            return calculated - dists

        result = least_squares(residuals, initial_guess, method="lm")

        # Convert back to lat/lon
        est_lat = origin.lat + result.x[0] / lat_scale
        est_lon = origin.lon + result.x[1] / lon_scale

        return Coord(lat=est_lat, lon=est_lon, depth=0.0)

    def project_3d_to_2d(
        self, distance_3d: float, host_depth: float, beacon_depth: float
    ) -> float:
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

    def timestamp_to_distance(
        self, timestamp: int, sound_speed: float
    ) -> float:
        """Convert modem timestamp (100µs units) to distance in meters.

        Formula: distance = timestamp * 3.125e-5 * sound_speed
        Per nanomodem spec, timestamp is in units of 3.125e-5 seconds.
        """
        return timestamp * 3.125e-5 * sound_speed
