"""Tests for nanomodem.core ModemNode."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from nanomodem.core.codecs import RawPayloadCodec
from nanomodem.core.modem_node import ModemNode
from nanomodem.core.protocols import OnModemEventCallback
from nanomodem.core.wire_types import (
    BroadcastCommand,
    ModemCommand,
    ModemEvent,
    PingCommand,
    ReceivedBroadcastEvent,
    ReceivedUnicastEvent,
    RoundtripResponseEvent,
    StatusQueryCommand,
    StatusResponseEvent,
    UnicastCommand,
)


class FakeWireTransport:
    """In-memory WireTransport for unit tests."""

    def __init__(self) -> None:
        self.commands: list[ModemCommand] = []
        self._callback: OnModemEventCallback | None = None
        self.started = False
        self.stopped = False

    def send_command(self, cmd: ModemCommand) -> None:
        self.commands.append(cmd)

    def on_event(self, callback: OnModemEventCallback) -> None:
        self._callback = callback

    def emit(self, event: ModemEvent) -> None:
        if self._callback is None:
            raise RuntimeError("No event callback registered")
        self._callback(event)

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


@dataclass(frozen=True)
class TextPayload:
    text: str


class UppercaseCodec:
    def encode(self, payload: TextPayload) -> bytes:
        return payload.text.upper().encode("ascii")

    def decode(self, data: bytes) -> TextPayload:
        return TextPayload(text=data.decode("ascii").lower())


@pytest.fixture
def transport() -> FakeWireTransport:
    return FakeWireTransport()


@pytest.fixture
def node(transport: FakeWireTransport) -> ModemNode[bytes]:
    return ModemNode(node_id="001", transport=transport, codec=RawPayloadCodec())


def test__should_send_ping_command_when_ping_called(
    node: ModemNode[bytes],
    transport: FakeWireTransport,
) -> None:
    node.ping("002")

    assert transport.commands == [PingCommand(target_id="002")]


def test__should_send_status_query_when_query_status_called(
    node: ModemNode[bytes],
    transport: FakeWireTransport,
) -> None:
    node.query_status()

    assert transport.commands == [StatusQueryCommand()]


def test__should_send_broadcast_command_with_encoded_payload_when_broadcast_called(
    node: ModemNode[bytes],
    transport: FakeWireTransport,
) -> None:
    node.broadcast(b"hello")

    assert transport.commands == [BroadcastCommand(data=b"hello")]


def test__should_send_unicast_command_with_encoded_payload_when_unicast_called(
    node: ModemNode[bytes],
    transport: FakeWireTransport,
) -> None:
    node.unicast("042", b"payload")

    assert transport.commands == [UnicastCommand(target_id="042", data=b"payload")]


def test__should_decode_received_broadcast_and_invoke_callback(
    node: ModemNode[bytes],
    transport: FakeWireTransport,
) -> None:
    received: list[tuple[str, bytes]] = []
    node.on_received_broadcast(lambda sender_id, payload: received.append((sender_id, payload)))

    transport.emit(ReceivedBroadcastEvent(sender_id="002", data=b"abc"))

    assert received == [("002", b"abc")]


def test__should_decode_received_unicast_and_invoke_callback(
    node: ModemNode[bytes],
    transport: FakeWireTransport,
) -> None:
    received: list[bytes] = []
    node.on_received_unicast(lambda payload: received.append(payload))

    transport.emit(ReceivedUnicastEvent(data=b"xyz"))

    assert received == [b"xyz"]


def test__should_pass_through_roundtrip_response_without_codec(
    node: ModemNode[bytes],
    transport: FakeWireTransport,
) -> None:
    received: list[tuple[str, int]] = []
    node.on_roundtrip_response(lambda responder_id, timestamp: received.append((responder_id, timestamp)))

    transport.emit(RoundtripResponseEvent(responder_id="002", timestamp_counts=12345))

    assert received == [("002", 12345)]


def test__should_pass_through_status_response_without_codec(
    node: ModemNode[bytes],
    transport: FakeWireTransport,
) -> None:
    received: list[StatusResponseEvent] = []
    node.on_status_response(lambda status: received.append(status))

    event = StatusResponseEvent(address="001", voltage_raw=12000)
    transport.emit(event)

    assert received == [event]


def test__should_use_custom_codec_for_encode_and_decode(
    transport: FakeWireTransport,
) -> None:
    node = ModemNode(node_id="001", transport=transport, codec=UppercaseCodec())

    node.broadcast(TextPayload(text="hello"))
    assert transport.commands == [BroadcastCommand(data=b"HELLO")]

    received: list[tuple[str, TextPayload]] = []
    node.on_received_broadcast(lambda sender_id, payload: received.append((sender_id, payload)))
    transport.emit(ReceivedBroadcastEvent(sender_id="002", data=b"WORLD"))

    assert received == [("002", TextPayload(text="world"))]


def test__should_invoke_on_event_for_all_events(
    node: ModemNode[bytes],
    transport: FakeWireTransport,
) -> None:
    events: list[ModemEvent] = []
    node.on_event(lambda event: events.append(event))

    status = StatusResponseEvent(address="001", voltage_raw=12000)
    transport.emit(status)

    assert events == [status]


def test__should_register_event_handler_on_construction(
    transport: FakeWireTransport,
) -> None:
    ModemNode(node_id="001", transport=transport, codec=RawPayloadCodec())

    assert transport._callback is not None
