"""Tests for nanomodem.core NanomodemV3Driver."""

from __future__ import annotations

import pytest

from nanomodem.core.driver import NanomodemV3Driver
from nanomodem.core.spec import (
    TEST_MESSAGE_PAYLOAD,
    format_test_broadcast_line,
    is_test_broadcast_line,
    normalize_line,
    parse_test_broadcast_sender,
    supply_voltage_volts,
)
from nanomodem.core.wire_types import (
    AddressSetEvent,
    BroadcastCommand,
    BroadcastCommandAckEvent,
    CommandErrorEvent,
    EchoCommand,
    EchoCommandAckEvent,
    PingCommand,
    PingCommandAckEvent,
    PingTimeoutEvent,
    QualityIndicatorEvent,
    QualityQueryCommand,
    QualityRejectedEvent,
    ReceivedBroadcastEvent,
    ReceivedUnicastEvent,
    RemoteVoltageQueryAckEvent,
    RemoteVoltageQueryCommand,
    RemoteVoltageResponseEvent,
    RoundtripResponseEvent,
    SetAddressCommand,
    StatusQueryCommand,
    StatusResponseEvent,
    TestBroadcastReceivedEvent,
    TestRequestAckEvent,
    TestRequestCommand,
    UnicastCommand,
    UnicastCommandAckEvent,
    UnicastWithAckCommand,
    UnicastWithAckCommandAckEvent,
    UnknownLineEvent,
)


@pytest.fixture
def driver() -> NanomodemV3Driver:
    return NanomodemV3Driver()


def test__should_format_set_address_command(driver: NanomodemV3Driver) -> None:
    assert driver.format_command(SetAddressCommand(address="042")) == b"$A042"


def test__should_format_status_query_command(driver: NanomodemV3Driver) -> None:
    assert driver.format_command(StatusQueryCommand()) == b"$?"


def test__should_format_ping_command(driver: NanomodemV3Driver) -> None:
    assert driver.format_command(PingCommand(target_id="002")) == b"$P002"


def test__should_format_remote_voltage_query_command(driver: NanomodemV3Driver) -> None:
    assert driver.format_command(RemoteVoltageQueryCommand(target_id="042")) == b"$V042"


def test__should_format_broadcast_command(driver: NanomodemV3Driver) -> None:
    assert driver.format_command(BroadcastCommand(data=b"AB")) == b"$B02AB"


def test__should_format_unicast_command(driver: NanomodemV3Driver) -> None:
    assert driver.format_command(UnicastCommand(target_id="042", data=b"X")) == b"$U04201X"


def test__should_format_unicast_with_ack_command(driver: NanomodemV3Driver) -> None:
    assert driver.format_command(UnicastWithAckCommand(target_id="002", data=b"hi")) == b"$M00202hi"


def test__should_format_test_request_command(driver: NanomodemV3Driver) -> None:
    assert driver.format_command(TestRequestCommand(target_id="002")) == b"$T002"


def test__should_format_echo_command(driver: NanomodemV3Driver) -> None:
    assert driver.format_command(EchoCommand(target_id="042", data=b"abc")) == b"$E04203abc"


def test__should_format_quality_query_command(driver: NanomodemV3Driver) -> None:
    assert driver.format_command(QualityQueryCommand()) == b"$Q"


def test__should_parse_status_response(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("#A042V48123")
    assert isinstance(event, StatusResponseEvent)
    assert event.address == "042"
    assert event.voltage_raw == 48123
    assert abs(supply_voltage_volts(48123) - 11.01) < 0.01


def test__should_parse_status_response_when_concatenated_on_one_rx_chunk(
    driver: NanomodemV3Driver,
) -> None:
    event = driver.parse_line("#A001V27353R001.006.000B2024-02-15T11:56:51")
    assert isinstance(event, StatusResponseEvent)
    assert event.address == "001"
    assert event.voltage_raw == 27353


def test__should_parse_address_set_event(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("#A042")
    assert isinstance(event, AddressSetEvent)
    assert event.address == "042"


def test__should_parse_ping_command_ack(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("$P002")
    assert isinstance(event, PingCommandAckEvent)
    assert event.target_id == "002"


def test__should_parse_test_request_ack(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("$T002")
    assert isinstance(event, TestRequestAckEvent)
    assert event.target_id == "002"


def test__should_parse_broadcast_command_ack(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("$B32")
    assert isinstance(event, BroadcastCommandAckEvent)
    assert event.byte_count == 32


def test__should_parse_unicast_command_ack(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("$U04201")
    assert isinstance(event, UnicastCommandAckEvent)
    assert event.target_id == "042"
    assert event.byte_count == 1


def test__should_parse_unicast_with_ack_command_ack(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("$M00232")
    assert isinstance(event, UnicastWithAckCommandAckEvent)
    assert event.target_id == "002"
    assert event.byte_count == 32


def test__should_parse_remote_voltage_query_ack(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("$V042")
    assert isinstance(event, RemoteVoltageQueryAckEvent)
    assert event.target_id == "042"


def test__should_parse_echo_command_ack(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("$E04203")
    assert isinstance(event, EchoCommandAckEvent)
    assert event.target_id == "042"
    assert event.byte_count == 3


def test__should_parse_quality_indicator(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("$C4")
    assert isinstance(event, QualityIndicatorEvent)
    assert event.bytes_corrected == 4


def test__should_parse_quality_rejected(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("$C-")
    assert isinstance(event, QualityRejectedEvent)


def test__should_parse_roundtrip_response(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("#R002T12345")
    assert isinstance(event, RoundtripResponseEvent)
    assert event.responder_id == "002"
    assert event.timestamp_counts == 12345


def test__should_parse_ping_timeout(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("#TO")
    assert isinstance(event, PingTimeoutEvent)


def test__should_parse_remote_voltage_response(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("#B04206V48123")
    assert isinstance(event, RemoteVoltageResponseEvent)
    assert event.responder_id == "042"
    assert event.voltage_raw == 48123


def test__should_parse_received_broadcast_with_raw_data(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("#B00202AB")
    assert isinstance(event, ReceivedBroadcastEvent)
    assert event.sender_id == "002"
    assert event.data == b"AB"


def test__should_parse_test_broadcast_received(driver: NanomodemV3Driver) -> None:
    line = format_test_broadcast_line("002")
    event = driver.parse_line(line)
    assert isinstance(event, TestBroadcastReceivedEvent)
    assert event.sender_id == "002"


def test__should_parse_received_unicast(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("#U02AB")
    assert isinstance(event, ReceivedUnicastEvent)
    assert event.data == b"AB"


def test__should_parse_command_error(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("E")
    assert isinstance(event, CommandErrorEvent)


def test__should_return_unknown_event_for_garbage_line(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("#A42V48123")
    assert isinstance(event, UnknownLineEvent)
    assert event.raw == "#A42V48123"


def test__should_treat_invalid_quality_line_as_unknown(driver: NanomodemV3Driver) -> None:
    assert isinstance(driver.parse_line("$C9"), UnknownLineEvent)
    assert isinstance(driver.parse_line("$Cx"), UnknownLineEvent)


def test__should_normalize_line_with_leading_noise() -> None:
    assert normalize_line("\xff$B32") == "$B32"
    assert normalize_line("\x00#R002T12345") == "#R002T12345"


def test__should_parse_line_with_leading_noise(driver: NanomodemV3Driver) -> None:
    event = driver.parse_line("\xff$B32")
    assert isinstance(event, BroadcastCommandAckEvent)
    assert event.byte_count == 32

    event = driver.parse_line("\x00#R002T12345")
    assert isinstance(event, RoundtripResponseEvent)


def test__should_detect_test_broadcast_line() -> None:
    line = f"#B002{len(TEST_MESSAGE_PAYLOAD):02d}{TEST_MESSAGE_PAYLOAD}"
    assert parse_test_broadcast_sender(line) == "002"
    assert is_test_broadcast_line(line) is True


def test__should_reject_non_test_broadcast_as_test_line() -> None:
    assert is_test_broadcast_line("#B00202AB") is False
