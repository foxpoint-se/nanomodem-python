"""Tests for SerialTransport command writes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nanomodem.codecs.v3 import Codec
from nanomodem.drivers.v3 import NanomodemV3Driver
from nanomodem.transports.serial import SerialTransport


def _make_transport(mock_serial_class: MagicMock) -> SerialTransport:
    mock_serial_class.return_value = MagicMock()
    driver = NanomodemV3Driver(Codec())
    return SerialTransport("001", "/dev/ttyUSB0", driver)


@patch("nanomodem.transports.serial.serial.Serial")
def test__should_write_test_request_on_request_test(mock_serial_class: MagicMock) -> None:
    transport = _make_transport(mock_serial_class)
    port = mock_serial_class.return_value

    transport.request_test("002")

    port.write.assert_called_once_with(b"$T002")


@patch("nanomodem.transports.serial.serial.Serial")
def test__should_write_quality_query_on_query_quality(mock_serial_class: MagicMock) -> None:
    transport = _make_transport(mock_serial_class)
    port = mock_serial_class.return_value

    transport.query_quality()

    port.write.assert_called_once_with(b"$Q")


@patch("nanomodem.transports.serial.serial.Serial")
def test__should_write_status_query_on_query_modem_status(mock_serial_class: MagicMock) -> None:
    transport = _make_transport(mock_serial_class)
    port = mock_serial_class.return_value

    transport.query_modem_status()

    port.write.assert_called_once_with(b"$?")
