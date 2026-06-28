"""Nanomodem v3 protocol constants and utilities from user guide."""

from __future__ import annotations

import re

from nanomodem.constants import MODEM_TIMESTAMP_QUANTUM_S, validate_sound_speed

TEST_MESSAGE_PAYLOAD = "Hello! This is a Nanomodem v3 DSSS test transmission at 640 bps."
TEST_MESSAGE_BYTE_COUNT = len(TEST_MESSAGE_PAYLOAD)
MAX_BYTES_CORRECTED = 8
MAX_WIRE_PAYLOAD_BYTES = 99
SUPPLY_VOLTAGE_SCALE = 15.0 / 65536.0

_BROADCAST_DATA_RE = re.compile(r"^#B(\d{3})(\d{2})(.+)$")


def supply_voltage_volts(voltage_raw: int) -> float:
    """Convert voltage raw value to volts per user guide."""
    return voltage_raw * SUPPLY_VOLTAGE_SCALE


def format_wire_byte_count(data: bytes) -> str:
    """Format a 2-digit payload length field for $B/$U/$M/$E commands."""
    length = len(data)
    if length > MAX_WIRE_PAYLOAD_BYTES:
        raise ValueError(f"Payload length must be 0..{MAX_WIRE_PAYLOAD_BYTES}, got {length}")
    return f"{length:02d}"


def normalize_line(line: str) -> str:
    """Extract modem response from line (handles leading noise)."""
    text = line.strip()
    if not text:
        return text
    if text[0] in "$#":
        return text
    if text == "E":
        return text
    dollar = text.find("$")
    hash_mark = text.find("#")
    start_indexes = [index for index in (dollar, hash_mark) if index >= 0]
    if start_indexes:
        return text[min(start_indexes) :]
    return text


def format_test_broadcast_line(node_id: str) -> str:
    """Format a received test broadcast line: #Bxxx64{payload}."""
    byte_count = f"{TEST_MESSAGE_BYTE_COUNT:02d}"
    return f"#B{node_id}{byte_count}{TEST_MESSAGE_PAYLOAD}"


def parse_test_broadcast_sender(line: str) -> str | None:
    """Return sender node id if line is a received v3 test broadcast."""
    match = _BROADCAST_DATA_RE.match(line)
    if match is None:
        return None
    byte_count = int(match.group(2))
    if byte_count != TEST_MESSAGE_BYTE_COUNT:
        return None
    if match.group(3) != TEST_MESSAGE_PAYLOAD:
        return None
    return match.group(1)


def is_test_broadcast_line(line: str) -> bool:
    """True if line is a received broadcast of the fixed v3 test payload."""
    return parse_test_broadcast_sender(line) is not None


def timestamp_to_distance(timestamp: int, sound_speed: float) -> float:
    """Convert modem timestamp counts to distance in meters per user guide."""
    validate_sound_speed(sound_speed)
    return timestamp * MODEM_TIMESTAMP_QUANTUM_S * sound_speed


def distance_to_timestamp(distance: float, sound_speed: float) -> int:
    """Convert distance in meters to modem timestamp counts per user guide."""
    validate_sound_speed(sound_speed)
    return round((distance / sound_speed) / MODEM_TIMESTAMP_QUANTUM_S)
