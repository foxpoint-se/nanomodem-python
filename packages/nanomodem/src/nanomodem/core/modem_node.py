"""ModemNode — generic modem controller with pluggable payload codec."""

from __future__ import annotations

from typing import Callable, Generic, TypeVar

from .protocols import OnModemEventCallback, PayloadCodec, WireTransport
from .wire_types import (
    BroadcastCommand,
    BroadcastCommandAckEvent,
    EchoCommandAckEvent,
    LocalAckEvent,
    ModemEvent,
    PingCommand,
    PingCommandAckEvent,
    QualityIndicatorEvent,
    QualityRejectedEvent,
    ReceivedBroadcastEvent,
    ReceivedUnicastEvent,
    RemoteVoltageQueryAckEvent,
    RoundtripResponseEvent,
    StatusQueryCommand,
    StatusResponseEvent,
    TestRequestAckEvent,
    UnicastCommand,
    UnicastCommandAckEvent,
    UnicastWithAckCommandAckEvent,
)

T = TypeVar("T")


def _validate_node_id(node_id: str) -> None:
    if not isinstance(node_id, str):
        raise TypeError(f"node_id must be a str, got {type(node_id).__name__}")
    if len(node_id) != 3 or not node_id.isdigit():
        raise ValueError(f"node_id must be a 3-digit numeric string (e.g. '001'), got '{node_id}'")
    numeric = int(node_id)
    if numeric < 1 or numeric > 255:
        raise ValueError(f"node_id must represent 1-255, got {numeric}")


class ModemNode(Generic[T]):
    """Thin modem controller — codec-aware, positioning-agnostic."""

    def __init__(
        self,
        node_id: str,
        transport: WireTransport,
        codec: PayloadCodec[T],
    ) -> None:
        _validate_node_id(node_id)
        self._node_id = node_id
        self._transport = transport
        self._codec = codec
        self._on_received_broadcast: Callable[[str, T], None] | None = None
        self._on_received_unicast: Callable[[T], None] | None = None
        self._on_roundtrip_response: Callable[[str, int], None] | None = None
        self._on_status_response: Callable[[StatusResponseEvent], None] | None = None
        self._on_local_ack: Callable[[LocalAckEvent], None] | None = None
        self._on_event: OnModemEventCallback | None = None

        self._transport.on_event(self._handle_event)

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def transport(self) -> WireTransport:
        return self._transport

    @property
    def codec(self) -> PayloadCodec[T]:
        return self._codec

    def ping(self, target_id: str) -> None:
        self._transport.send_command(PingCommand(target_id=target_id))

    def query_status(self) -> None:
        self._transport.send_command(StatusQueryCommand())

    def broadcast(self, payload: T) -> None:
        data = self._codec.encode(payload)
        self._transport.send_command(BroadcastCommand(data=data))

    def unicast(self, target_id: str, payload: T) -> None:
        data = self._codec.encode(payload)
        self._transport.send_command(UnicastCommand(target_id=target_id, data=data))

    def on_received_broadcast(self, callback: Callable[[str, T], None]) -> None:
        self._on_received_broadcast = callback

    def on_received_unicast(self, callback: Callable[[T], None]) -> None:
        self._on_received_unicast = callback

    def on_roundtrip_response(
        self,
        callback: Callable[[str, int], None] | None,
    ) -> Callable[[str, int], None] | None:
        prior = self._on_roundtrip_response
        self._on_roundtrip_response = callback
        return prior

    def on_status_response(
        self,
        callback: Callable[[StatusResponseEvent], None] | None,
    ) -> Callable[[StatusResponseEvent], None] | None:
        prior = self._on_status_response
        self._on_status_response = callback
        return prior

    def on_local_ack(self, callback: Callable[[LocalAckEvent], None]) -> None:
        self._on_local_ack = callback

    def on_event(self, callback: OnModemEventCallback) -> None:
        self._on_event = callback

    def _decode_payload(self, data: bytes) -> T | None:
        try:
            return self._codec.decode(data)
        except (ValueError, UnicodeDecodeError):
            return None

    def _handle_event(self, event: ModemEvent) -> None:
        match event:
            case ReceivedBroadcastEvent(sender_id=sender_id, data=data):
                if self._on_received_broadcast is not None:
                    decoded = self._decode_payload(data)
                    if decoded is not None:
                        self._on_received_broadcast(sender_id, decoded)
            case ReceivedUnicastEvent(data=data):
                if self._on_received_unicast is not None:
                    decoded = self._decode_payload(data)
                    if decoded is not None:
                        self._on_received_unicast(decoded)
            case RoundtripResponseEvent(responder_id=responder_id, timestamp_counts=timestamp_counts):
                if self._on_roundtrip_response is not None:
                    self._on_roundtrip_response(responder_id, timestamp_counts)
            case StatusResponseEvent() as status:
                if self._on_status_response is not None:
                    self._on_status_response(status)
            case (
                PingCommandAckEvent()
                | TestRequestAckEvent()
                | BroadcastCommandAckEvent()
                | UnicastCommandAckEvent()
                | UnicastWithAckCommandAckEvent()
                | RemoteVoltageQueryAckEvent()
                | EchoCommandAckEvent()
                | QualityIndicatorEvent()
                | QualityRejectedEvent()
            ) as local_ack:
                if self._on_local_ack is not None:
                    self._on_local_ack(local_ack)

        if self._on_event is not None:
            self._on_event(event)
