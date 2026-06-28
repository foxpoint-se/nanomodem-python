"""Wire protocol types for nanomodem v3 — host commands and modem events."""

from __future__ import annotations

from dataclasses import dataclass

# --- Commands (host → modem) ---


@dataclass(frozen=True)
class SetAddressCommand:
    address: str


@dataclass(frozen=True)
class StatusQueryCommand:
    pass


@dataclass(frozen=True)
class PingCommand:
    target_id: str


@dataclass(frozen=True)
class RemoteVoltageQueryCommand:
    target_id: str


@dataclass(frozen=True)
class BroadcastCommand:
    data: bytes


@dataclass(frozen=True)
class UnicastCommand:
    target_id: str
    data: bytes


@dataclass(frozen=True)
class UnicastWithAckCommand:
    target_id: str
    data: bytes


@dataclass(frozen=True)
class TestRequestCommand:
    target_id: str


@dataclass(frozen=True)
class EchoCommand:
    target_id: str
    data: bytes


@dataclass(frozen=True)
class QualityQueryCommand:
    pass


ModemCommand = (
    SetAddressCommand
    | StatusQueryCommand
    | PingCommand
    | RemoteVoltageQueryCommand
    | BroadcastCommand
    | UnicastCommand
    | UnicastWithAckCommand
    | TestRequestCommand
    | EchoCommand
    | QualityQueryCommand
)

# --- Local ack events ($…) ---


@dataclass(frozen=True)
class PingCommandAckEvent:
    target_id: str


@dataclass(frozen=True)
class TestRequestAckEvent:
    target_id: str


@dataclass(frozen=True)
class BroadcastCommandAckEvent:
    byte_count: int


@dataclass(frozen=True)
class UnicastCommandAckEvent:
    target_id: str
    byte_count: int


@dataclass(frozen=True)
class UnicastWithAckCommandAckEvent:
    target_id: str
    byte_count: int


@dataclass(frozen=True)
class RemoteVoltageQueryAckEvent:
    target_id: str


@dataclass(frozen=True)
class EchoCommandAckEvent:
    target_id: str
    byte_count: int


@dataclass(frozen=True)
class QualityIndicatorEvent:
    bytes_corrected: int


@dataclass(frozen=True)
class QualityRejectedEvent:
    pass


LocalAckEvent = (
    PingCommandAckEvent
    | TestRequestAckEvent
    | BroadcastCommandAckEvent
    | UnicastCommandAckEvent
    | UnicastWithAckCommandAckEvent
    | RemoteVoltageQueryAckEvent
    | EchoCommandAckEvent
    | QualityIndicatorEvent
    | QualityRejectedEvent
)

# --- Received events (#…) ---


@dataclass(frozen=True)
class AddressSetEvent:
    address: str


@dataclass(frozen=True)
class StatusResponseEvent:
    address: str
    voltage_raw: int


@dataclass(frozen=True)
class RoundtripResponseEvent:
    responder_id: str
    timestamp_counts: int


@dataclass(frozen=True)
class PingTimeoutEvent:
    pass


@dataclass(frozen=True)
class RemoteVoltageResponseEvent:
    responder_id: str
    voltage_raw: int


@dataclass(frozen=True)
class ReceivedBroadcastEvent:
    sender_id: str
    data: bytes


@dataclass(frozen=True)
class TestBroadcastReceivedEvent:
    sender_id: str


@dataclass(frozen=True)
class ReceivedUnicastEvent:
    data: bytes


ReceivedEvent = (
    AddressSetEvent
    | StatusResponseEvent
    | RoundtripResponseEvent
    | PingTimeoutEvent
    | RemoteVoltageResponseEvent
    | ReceivedBroadcastEvent
    | TestBroadcastReceivedEvent
    | ReceivedUnicastEvent
)

# --- Error events ---


@dataclass(frozen=True)
class CommandErrorEvent:
    pass


@dataclass(frozen=True)
class UnknownLineEvent:
    raw: str


ErrorEvent = CommandErrorEvent | UnknownLineEvent

ModemEvent = LocalAckEvent | ReceivedEvent | ErrorEvent
