"""Tests for Calculation."""

import math

import pytest

from nanomodem.calculation import Calculation, calculate_distance_3d
from nanomodem.types import Coord

calc = Calculation()


# --- Distance calculation ---


def test__should_calculate_correct_distance_between_two_points() -> None:
    # 1 degree lat ~ 111320m
    # At 60 deg lat, 1 degree lon ~ 111320 * cos(60) = 55660m
    a = Coord(lat=60.0, lon=10.0)
    b = Coord(lat=60.001, lon=10.001)
    # lat_diff = 0.001 * 111320 = 111.32m
    # lon_diff = 0.001 * 55660 = 55.66m
    # depth_diff = 10m
    # dist = sqrt(111.32^2 + 55.66^2 + 10^2) = sqrt(12392.1424 + 3098.0356 + 100) = sqrt(15590.178) = 124.86m
    result = calculate_distance_3d(a, 0.0, b, 10.0)
    assert abs(result - 124.86) < 0.01


def test__should_return_zero_distance_for_same_point() -> None:
    a = Coord(lat=63.0, lon=10.0)
    result = calculate_distance_3d(a, 5.0, a, 5.0)
    assert result == 0.0


def test__should_calculate_pure_depth_distance() -> None:
    a = Coord(lat=63.0, lon=10.0)
    result = calculate_distance_3d(a, 0.0, a, 10.0)
    assert abs(result - 10.0) < 1e-6


def test__should_be_symmetrical() -> None:
    a = Coord(lat=63.0, lon=10.0)
    b = Coord(lat=63.001, lon=10.002)
    dist_ab = calculate_distance_3d(a, 0.0, b, 5.0)
    dist_ba = calculate_distance_3d(b, 5.0, a, 0.0)
    assert abs(dist_ab - dist_ba) < 1e-9


# --- Trilateration ---


def test_should_return_correct_position_with_three_beacons() -> None:
    """Three beacons in a triangle, target at known position."""
    # Beacons roughly forming a triangle around (63.0005, 10.0005)
    beacons = [
        Coord(lat=63.0, lon=10.0),
        Coord(lat=63.001, lon=10.0),
        Coord(lat=63.0005, lon=10.001),
    ]
    # Calculate expected distances from (63.0005, 10.0005) to each beacon
    target = Coord(lat=63.0005, lon=10.0005)
    avg_lat = math.radians(63.0005)
    lat_scale = 111320.0
    lon_scale = 111320.0 * math.cos(avg_lat)

    distances = []
    for b in beacons:
        dx = (target.lat - b.lat) * lat_scale
        dy = (target.lon - b.lon) * lon_scale
        distances.append(math.sqrt(dx**2 + dy**2))

    result = calc.trilaterate(beacons, distances)

    assert abs(result.lat - target.lat) < 1e-6
    assert abs(result.lon - target.lon) < 1e-6


def test_should_raise_with_fewer_than_three_beacons() -> None:
    beacons = [Coord(lat=63.0, lon=10.0), Coord(lat=63.001, lon=10.0)]
    distances = [50.0, 60.0]
    with pytest.raises(ValueError):
        calc.trilaterate(beacons, distances)


def test_should_raise_with_mismatched_lengths() -> None:
    beacons = [
        Coord(lat=63.0, lon=10.0),
        Coord(lat=63.001, lon=10.0),
        Coord(lat=63.0, lon=10.001),
    ]
    distances = [50.0, 60.0]  # One too few
    with pytest.raises(ValueError):
        calc.trilaterate(beacons, distances)


# --- 3D to 2D projection ---


def test_should_return_horizontal_distance_when_projecting_3d_to_2d() -> None:
    # 3D distance = 5m, depth difference = 3m → horizontal = 4m (3-4-5 triangle)
    result = calc.project_3d_to_2d(distance_3d=5.0, host_depth=3.0, beacon_depth=0.0)
    assert abs(result - 4.0) < 1e-6


def test_should_return_zero_when_depth_exceeds_3d_distance() -> None:
    # Measurement error: depth diff > 3D distance
    result = calc.project_3d_to_2d(distance_3d=2.0, host_depth=5.0, beacon_depth=0.0)
    assert result == 0.0


def test_should_return_full_distance_when_same_depth() -> None:
    result = calc.project_3d_to_2d(distance_3d=10.0, host_depth=5.0, beacon_depth=5.0)
    assert abs(result - 10.0) < 1e-6


# --- Timestamp to distance ---


def test_should_convert_timestamp_to_distance_using_spec_formula() -> None:
    # 32000 units * 3.125e-5 s/unit * 1500 m/s = 1500m
    result = calc.timestamp_to_distance(timestamp=32000, sound_speed=1500.0)
    assert abs(result - 1500.0) < 0.1


def test_should_convert_small_timestamp() -> None:
    # 213 units * 3.125e-5 * 1500 = ~9.98m (≈10m range)
    result = calc.timestamp_to_distance(timestamp=213, sound_speed=1500.0)
    assert abs(result - 9.984) < 0.1


def test_should_convert_with_different_sound_speed() -> None:
    # Same timestamp, air speed of sound (340 m/s)
    result = calc.timestamp_to_distance(timestamp=32000, sound_speed=340.0)
    assert abs(result - 340.0) < 0.1
