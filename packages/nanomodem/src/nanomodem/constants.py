"""Physical and modem constants for acoustic ranging."""

from __future__ import annotations

# Per nanomodem v3 user guide: timestamp units are 3.125e-5 seconds.
MODEM_TIMESTAMP_QUANTUM_S = 3.125e-5

SOUND_SPEED_WATER_M_S = 1500.0
SOUND_SPEED_AIR_M_S = 340.0


def validate_sound_speed(sound_speed: float) -> float:
    """Return sound_speed if positive; raise ValueError otherwise."""
    if sound_speed <= 0:
        raise ValueError(f"sound_speed must be positive (m/s), got {sound_speed}")
    return sound_speed
