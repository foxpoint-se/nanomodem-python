"""Tests for nanomodem.core wire protocol types."""

from __future__ import annotations

import dataclasses

import pytest

from nanomodem.core.wire_types import (
    AddressSetEvent,
    BroadcastCommand,
    BroadcastCommandAckEvent,
    CommandErrorEvent,
    EchoCommand,
    EchoCommandAckEvent,
    ErrorEvent,
    LocalAckEvent,
    ModemCommand,
    ModemEvent,
    PingCommand,
    PingCommandAckEvent,
    PingTimeoutEvent,
    QualityIndicatorEvent,
    QualityQueryCommand,
    QualityRejectedEvent,
    ReceivedBroadcastEvent,
    ReceivedEvent,
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

ALL_COMMANDS: list[ModemCommand] = [
    SetAddressCommand(address="042"),
    StatusQueryCommand(),
    PingCommand(target_id="042"),
    RemoteVoltageQueryCommand(target_id="042"),
    BroadcastCommand(data=b"hello"),
    UnicastCommand(target_id="042", data=b"hi"),
    UnicastWithAckCommand(target_id="042", data=b"ack"),
    TestRequestCommand(target_id="042"),
    EchoCommand(target_id="042", data=b"echo"),
    QualityQueryCommand(),
]

ALL_LOCAL_ACK_EVENTS: list[LocalAckEvent] = [
    PingCommandAckEvent(target_id="042"),
    TestRequestAckEvent(target_id="042"),
    BroadcastCommandAckEvent(byte_count=2),
    UnicastCommandAckEvent(target_id="042", byte_count=1),
    UnicastWithAckCommandAckEvent(target_id="042", byte_count=3),
    RemoteVoltageQueryAckEvent(target_id="042"),
    EchoCommandAckEvent(target_id="042", byte_count=4),
    QualityIndicatorEvent(bytes_corrected=2),
    QualityRejectedEvent(),
]

ALL_RECEIVED_EVENTS: list[ReceivedEvent] = [
    AddressSetEvent(address="042"),
    StatusResponseEvent(address="042", voltage_raw=48123),
    RoundtripResponseEvent(responder_id="042", timestamp_counts=12345),
    PingTimeoutEvent(),
    RemoteVoltageResponseEvent(responder_id="042", voltage_raw=48123),
    ReceivedBroadcastEvent(sender_id="001", data=b"A"),
    TestBroadcastReceivedEvent(sender_id="002"),
    ReceivedUnicastEvent(data=b"payload"),
]

ALL_ERROR_EVENTS: list[ErrorEvent] = [
    CommandErrorEvent(),
    UnknownLineEvent(raw="garbage"),
]

ALL_MODEM_EVENTS: list[ModemEvent] = [
    *ALL_LOCAL_ACK_EVENTS,
    *ALL_RECEIVED_EVENTS,
    *ALL_ERROR_EVENTS,
]


@pytest.mark.parametrize("command", ALL_COMMANDS, ids=lambda c: type(c).__name__)
def test__should_accept_command_in_modem_command_union(command: ModemCommand) -> None:
    assert command in ALL_COMMANDS


@pytest.mark.parametrize("event", ALL_LOCAL_ACK_EVENTS, ids=lambda e: type(e).__name__)
def test__should_accept_event_in_local_ack_union(event: LocalAckEvent) -> None:
    assert event in ALL_LOCAL_ACK_EVENTS


@pytest.mark.parametrize("event", ALL_RECEIVED_EVENTS, ids=lambda e: type(e).__name__)
def test__should_accept_event_in_received_union(event: ReceivedEvent) -> None:
    assert event in ALL_RECEIVED_EVENTS


@pytest.mark.parametrize("event", ALL_ERROR_EVENTS, ids=lambda e: type(e).__name__)
def test__should_accept_event_in_error_union(event: ErrorEvent) -> None:
    assert event in ALL_ERROR_EVENTS


@pytest.mark.parametrize("event", ALL_MODEM_EVENTS, ids=lambda e: type(e).__name__)
def test__should_accept_event_in_modem_event_union(event: ModemEvent) -> None:
    assert event in ALL_MODEM_EVENTS


def test__should_match_ping_command_in_union() -> None:
    cmd: ModemCommand = PingCommand(target_id="042")
    match cmd:
        case PingCommand(target_id=target_id):
            assert target_id == "042"
        case _:
            pytest.fail("Expected PingCommand")


def test__should_match_roundtrip_response_in_modem_event_union() -> None:
    event: ModemEvent = RoundtripResponseEvent(responder_id="042", timestamp_counts=999)
    match event:
        case RoundtripResponseEvent(responder_id=responder_id, timestamp_counts=counts):
            assert responder_id == "042"
            assert counts == 999
        case _:
            pytest.fail("Expected RoundtripResponseEvent")


def test__should_match_unknown_line_as_error_event() -> None:
    event: ModemEvent = UnknownLineEvent(raw="#???")
    match event:
        case UnknownLineEvent(raw=raw):
            assert raw == "#???"
        case _:
            pytest.fail("Expected UnknownLineEvent")


@pytest.mark.parametrize(
    "instance",
    [
        PingCommand(target_id="001"),
        StatusResponseEvent(address="001", voltage_raw=100),
        CommandErrorEvent(),
        QualityQueryCommand(),
    ],
    ids=["command", "received_event", "error_event", "empty_command"],
)
def test__should_be_immutable(instance: object) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, "_immutable_check", True)
