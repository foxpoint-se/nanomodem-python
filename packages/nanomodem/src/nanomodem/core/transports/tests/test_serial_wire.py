"""Tests for SerialWireTransport."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nanomodem.core.driver import NanomodemV3Driver
from nanomodem.core.transports.serial_wire import SerialWireTransport
from nanomodem.core.wire_types import (
    BroadcastCommand,
    ModemEvent,
    PingCommand,
    RoundtripResponseEvent,
)


def _make_transport(mock_serial_class: MagicMock) -> tuple[SerialWireTransport, MagicMock]:
    mock_port = MagicMock()
    mock_port.is_open = True
    mock_serial_class.return_value = mock_port
    driver = NanomodemV3Driver()
    transport = SerialWireTransport("/dev/ttyUSB0", driver)
    return transport, mock_port


@patch("nanomodem.core.transports.serial_wire.serial.Serial")
def test__should_format_and_send_ping_command(mock_serial_class: MagicMock) -> None:
    transport, port = _make_transport(mock_serial_class)

    transport.send_command(PingCommand(target_id="002"))

    port.write.assert_called_once_with(b"$P002")


@patch("nanomodem.core.transports.serial_wire.serial.Serial")
def test__should_format_and_send_broadcast_command(mock_serial_class: MagicMock) -> None:
    transport, port = _make_transport(mock_serial_class)

    transport.send_command(BroadcastCommand(data=b"AB"))

    port.write.assert_called_once_with(b"$B02AB")


@patch("nanomodem.core.transports.serial_wire.serial.Serial")
def test__should_parse_received_line_and_emit_event(mock_serial_class: MagicMock) -> None:
    transport, _port = _make_transport(mock_serial_class)
    received: list[ModemEvent] = []
    transport.on_event(received.append)

    transport._dispatch("#R002T12345")

    assert received == [RoundtripResponseEvent(responder_id="002", timestamp_counts=12345)]


@patch("nanomodem.core.transports.serial_wire.serial.Serial")
def test__should_start_and_stop_reader_thread(mock_serial_class: MagicMock) -> None:
    transport, port = _make_transport(mock_serial_class)

    def readline_side_effect() -> bytes:
        transport._running = False
        return b""

    port.readline.side_effect = readline_side_effect

    transport.start()
    transport._reader_thread.join(timeout=1.0)

    assert transport._reader_started is True
    transport.stop()
    port.close.assert_called_once()
