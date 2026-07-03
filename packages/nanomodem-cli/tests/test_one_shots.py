"""Tests for nanomodem CLI one-shot commands."""

from __future__ import annotations

import sys
import time
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from nanomodem.core.codecs import RawPayloadCodec
from nanomodem.core.modem_node import ModemNode
from nanomodem.core.spec import supply_voltage_volts, timestamp_to_distance
from nanomodem.core.transports.in_memory import MOCK_STATUS_VOLTAGE_RAW, InMemoryBus, InMemoryTransport
from nanomodem.types import Coord
from nanomodem_cli.__main__ import main
from nanomodem_cli.one_shot import execute_ping, execute_status
from nanomodem_cli.startup import verify_modem_id_at_startup


def _run_cli(argv: list[str]) -> tuple[int | None, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with patch.object(sys, "argv", ["nanomodem", *argv]):
        with patch.object(sys, "stdout", stdout):
            with patch.object(sys, "stderr", stderr):
                with pytest.raises(SystemExit) as exc:
                    main()
                return exc.value.code, stdout.getvalue(), stderr.getvalue()


def test__should_print_status_for_in_memory_one_shot() -> None:
    code, stdout, stderr = _run_cli(["-n", "001", "-m", "status"])

    assert code == 0
    assert stderr == ""
    expected_voltage = supply_voltage_volts(MOCK_STATUS_VOLTAGE_RAW)
    assert f"Node ID: 001, Voltage: {expected_voltage:.2f}V" in stdout


def test__should_timeout_ping_for_in_memory_one_shot_without_peer() -> None:
    code, stdout, stderr = _run_cli(["-n", "001", "-m", "ping", "002"])

    assert code == 1
    assert stdout == ""
    assert "Timed out" in stderr
    assert "002" in stderr


def test__should_fail_when_node_id_missing_for_one_shot() -> None:
    code, _stdout, stderr = _run_cli(["-m", "status"])

    assert code == 1
    assert "--node-id is required" in stderr


def test__should_fail_when_transport_missing_for_one_shot() -> None:
    code, _stdout, stderr = _run_cli(["-n", "001", "status"])

    assert code == 1
    assert "transport" in stderr.lower()


def test__should_fail_when_node_id_is_invalid_for_one_shot() -> None:
    code, _stdout, stderr = _run_cli(["-n", "abc", "-m", "status"])

    assert code == 1
    assert "--node-id" in stderr


def test__should_fail_when_sound_speed_is_invalid_for_one_shot() -> None:
    code, _stdout, stderr = _run_cli(["-n", "001", "-m", "--sound-speed", "-1", "status"])

    assert code == 1
    assert "sound_speed" in stderr


def test__should_fail_when_ping_target_id_is_invalid() -> None:
    code, _stdout, stderr = _run_cli(["-n", "001", "-m", "ping", "bad"])

    assert code == 1
    assert "ping target_id" in stderr


def _mock_serial_port(responses_by_write: dict[int, bytes]) -> MagicMock:
    mock_port = MagicMock()
    mock_port.is_open = True
    write_count = 0
    read_count = 0

    def write_side_effect(data: bytes) -> None:
        nonlocal write_count
        write_count += 1

    def readline_side_effect() -> bytes:
        nonlocal read_count
        deadline = time.monotonic() + 2.0
        while write_count <= read_count and time.monotonic() < deadline:
            time.sleep(0.001)
        read_count += 1
        return responses_by_write.get(read_count, b"")

    mock_port.write.side_effect = write_side_effect
    mock_port.readline.side_effect = readline_side_effect
    return mock_port


@patch("nanomodem.core.transports.serial_wire.serial.Serial")
def test__should_print_status_for_serial_one_shot(mock_serial_class: MagicMock) -> None:
    mock_port = _mock_serial_port({1: b"#A001V48123\n", 2: b"#A001V48123\n"})
    mock_serial_class.return_value = mock_port

    code, stdout, stderr = _run_cli(["-n", "001", "-s", "/dev/ttyUSB0", "status"])

    assert code == 0
    assert stderr == ""
    assert "Node ID: 001" in stdout
    assert mock_port.write.call_count >= 2
    assert mock_port.write.call_args_list[0].args[0] == b"$?"


@patch("nanomodem.core.transports.serial_wire.serial.Serial")
def test__should_print_range_for_serial_ping_one_shot(mock_serial_class: MagicMock) -> None:
    mock_port = _mock_serial_port({1: b"#A001V48123\n", 2: b"#R002T12345\n"})
    mock_serial_class.return_value = mock_port

    code, stdout, stderr = _run_cli(["-n", "001", "-s", "/dev/ttyUSB0", "ping", "002"])

    assert code == 0
    assert stderr == ""
    expected_distance = timestamp_to_distance(12345, 1500.0)
    assert stdout.strip() == f"range 002: {expected_distance:.0f} m"
    assert any(call.args[0] == b"$P002" for call in mock_port.write.call_args_list)


@patch("nanomodem.core.transports.serial_wire.serial.Serial")
def test__should_exit_with_error_on_serial_id_mismatch(mock_serial_class: MagicMock) -> None:
    mock_port = MagicMock()
    mock_port.is_open = True

    def readline_side_effect() -> bytes:
        return b"#A002V48123\n"

    mock_port.readline.side_effect = readline_side_effect
    mock_serial_class.return_value = mock_port

    code, _stdout, stderr = _run_cli(["-n", "001", "-s", "/dev/ttyUSB0", "status"])

    assert code == 1
    assert "Node id mismatch" in stderr
    assert "nanomodem -n 002 -s /dev/ttyUSB0" in stderr


def test__should_execute_status_on_modem_node() -> None:
    bus = InMemoryBus()
    transport = InMemoryTransport("001", bus)
    node = ModemNode("001", transport, RawPayloadCodec())
    transport.start()

    assert execute_status(node) == 0


def test__should_execute_ping_on_modem_node_with_peer() -> None:
    bus = InMemoryBus(sound_speed=1500.0)
    sender_transport = InMemoryTransport("001", bus)
    receiver_transport = InMemoryTransport("002", bus)
    sender_transport.position = Coord(lat=63.0, lon=10.0)
    receiver_transport.position = Coord(lat=63.0001, lon=10.0001)
    sender = ModemNode("001", sender_transport, RawPayloadCodec())
    receiver = ModemNode("002", receiver_transport, RawPayloadCodec())
    sender.transport.start()
    receiver.transport.start()

    assert execute_ping(sender, "002", sound_speed=1500.0, timeout_s=1.0) == 0


def test__should_verify_modem_id_for_in_memory_node() -> None:
    bus = InMemoryBus()
    transport = InMemoryTransport("001", bus)
    node = ModemNode("001", transport, RawPayloadCodec())
    transport.start()

    verify_modem_id_at_startup(node, timeout_s=1.0)
