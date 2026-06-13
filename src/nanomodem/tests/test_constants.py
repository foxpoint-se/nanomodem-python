"""Tests for acoustic physical constants and validation."""

from __future__ import annotations

import pytest

from nanomodem.constants import (
    SOUND_SPEED_AIR_M_S,
    SOUND_SPEED_WATER_M_S,
    validate_sound_speed,
)


def test_should_accept_positive_sound_speed() -> None:
    assert validate_sound_speed(1500.0) == 1500.0
    assert validate_sound_speed(SOUND_SPEED_AIR_M_S) == 340.0


def test_should_reject_non_positive_sound_speed() -> None:
    with pytest.raises(ValueError, match="positive"):
        validate_sound_speed(0.0)
    with pytest.raises(ValueError, match="positive"):
        validate_sound_speed(-1.0)


def test_should_define_documented_defaults() -> None:
    assert SOUND_SPEED_WATER_M_S == 1500.0
    assert SOUND_SPEED_AIR_M_S == 340.0
