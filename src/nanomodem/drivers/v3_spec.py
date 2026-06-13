"""Nanomodem v3 protocol constants from the user guide."""

from __future__ import annotations

import re

TEST_MESSAGE_PAYLOAD = (
    "Hello! This is a Nanomodem v3 DSSS test transmission at 640 bps."
)
TEST_MESSAGE_BYTE_COUNT = len(TEST_MESSAGE_PAYLOAD)
MAX_BYTES_CORRECTED = 8
SUPPLY_VOLTAGE_SCALE = 15.0 / 65536.0

_BROADCAST_DATA_RE = re.compile(r"^#B(\d{3})(\d{2})(.+)$")


def supply_voltage_volts(voltage_raw: int) -> float:
    """Convert $? voltage field to volts per the user guide."""
    return voltage_raw * SUPPLY_VOLTAGE_SCALE


def normalize_modem_response_line(line: str) -> str:
    """Extract a modem response line per the user guide ($ or # prefix, or E).

    Hardware may emit a status byte before the ASCII response on the same
    readline chunk. Outbound commands use a different framing (no CRLF).
    """
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
