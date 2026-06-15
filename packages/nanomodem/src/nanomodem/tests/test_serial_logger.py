"""Tests for serial logging utility."""

from __future__ import annotations

import re

from nanomodem.serial_logger import format_serial_log


def test__should_format_log_with_timestamp_when_called() -> None:
    # Arrange
    direction = "TX"
    node_id = "001"
    data = b"$P002"

    # Act
    result = format_serial_log(direction, node_id, data)

    # Assert
    # Format: [HH:MM:SS.mmm] [TX 001] $P002
    pattern = r"\[\d{2}:\d{2}:\d{2}\.\d{3}\] \[TX 001\] \$P002"
    assert re.match(pattern, result)


def test__should_handle_invalid_ascii_when_decoding() -> None:
    # Arrange
    direction = "RX"
    node_id = "002"
    data = b"\xff\xfe#R001T12345"

    # Act
    result = format_serial_log(direction, node_id, data)

    # Assert
    # Invalid bytes replaced by  (U+FFFD)
    assert "#R001T12345" in result


def test__should_strip_whitespace_from_data() -> None:
    # Arrange
    data = b"  #R001T12345\r\n  "

    # Act
    result = format_serial_log("RX", "001", data)

    # Assert
    assert result.endswith("] #R001T12345")


def test__should_handle_empty_node_id() -> None:
    # Arrange
    direction = "BROKER"
    node_id = ""
    data = b"test"

    # Act
    result = format_serial_log(direction, node_id, data)

    # Assert
    assert "[BROKER] test" in result
