"""Nanomodem v3 driver — command formatting and response parsing."""

from __future__ import annotations

import re

from .line_parsers import (
    parse_address_set,
    parse_broadcast_ack,
    parse_echo_ack,
    parse_ping_ack,
    parse_quality_line,
    parse_remote_voltage_ack,
    parse_status_line,
    parse_test_ack,
    parse_unicast_ack,
    parse_unicast_with_ack_ack,
)
from .spec import TEST_MESSAGE_BYTE_COUNT, TEST_MESSAGE_PAYLOAD, normalize_line
from .wire_types import (
    BroadcastCommand,
    CommandErrorEvent,
    EchoCommand,
    ModemCommand,
    ModemEvent,
    PingCommand,
    PingTimeoutEvent,
    QualityQueryCommand,
    ReceivedBroadcastEvent,
    ReceivedUnicastEvent,
    RemoteVoltageQueryCommand,
    RemoteVoltageResponseEvent,
    RoundtripResponseEvent,
    SetAddressCommand,
    StatusQueryCommand,
    TestBroadcastReceivedEvent,
    TestRequestCommand,
    UnicastCommand,
    UnicastWithAckCommand,
    UnknownLineEvent,
)

ROUNDTRIP_RE = re.compile(r"^#R(\d{3})T(\d{5})")
TIMEOUT_RE = re.compile(r"^#TO$")
BROADCAST_DATA_RE = re.compile(r"^#B(\d{3})(\d{2})(.+)$")
UNICAST_DATA_RE = re.compile(r"^#U(\d{2})(.+)$")
REMOTE_VOLTAGE_RE = re.compile(r"^#B(\d{3})06V(\d{5})")


def _payload_to_bytes(payload: str) -> bytes:
    return payload.encode("ascii", errors="replace")


class NanomodemV3Driver:
    """Wire protocol handler for nanomodem v3 hardware.

    Formats ModemCommand → bytes and parses serial lines → ModemEvent.
    No codec — only handles wire framing per the user guide.
    """

    def format_command(self, cmd: ModemCommand) -> bytes:
        """Format a command to wire bytes."""
        match cmd:
            case SetAddressCommand(address=address):
                return f"$A{address}".encode("ascii")
            case StatusQueryCommand():
                return b"$?"
            case PingCommand(target_id=target_id):
                return f"$P{target_id}".encode("ascii")
            case RemoteVoltageQueryCommand(target_id=target_id):
                return f"$V{target_id}".encode("ascii")
            case BroadcastCommand(data=data):
                byte_count = f"{len(data):02d}"
                return f"$B{byte_count}".encode("ascii") + data
            case UnicastCommand(target_id=target_id, data=data):
                byte_count = f"{len(data):02d}"
                return f"$U{target_id}{byte_count}".encode("ascii") + data
            case UnicastWithAckCommand(target_id=target_id, data=data):
                byte_count = f"{len(data):02d}"
                return f"$M{target_id}{byte_count}".encode("ascii") + data
            case TestRequestCommand(target_id=target_id):
                return f"$T{target_id}".encode("ascii")
            case EchoCommand(target_id=target_id, data=data):
                byte_count = f"{len(data):02d}"
                return f"$E{target_id}{byte_count}".encode("ascii") + data
            case QualityQueryCommand():
                return b"$Q"

    def parse_line(self, line: str) -> ModemEvent:
        """Parse a serial response line into a ModemEvent."""
        line = normalize_line(line)
        if line == "E":
            return CommandErrorEvent()

        event = (
            parse_status_line(line)
            or parse_address_set(line)
            or parse_quality_line(line)
            or parse_ping_ack(line)
            or parse_test_ack(line)
            or parse_broadcast_ack(line)
            or parse_unicast_ack(line)
            or parse_unicast_with_ack_ack(line)
            or parse_remote_voltage_ack(line)
            or parse_echo_ack(line)
            or self._parse_roundtrip(line)
            or self._parse_timeout(line)
            or self._parse_remote_voltage_response(line)
            or self._parse_broadcast_data(line)
            or self._parse_unicast_data(line)
        )
        if event is not None:
            return event
        return UnknownLineEvent(raw=line)

    def _parse_roundtrip(self, line: str) -> RoundtripResponseEvent | None:
        match = ROUNDTRIP_RE.match(line)
        if match is None:
            return None
        return RoundtripResponseEvent(
            responder_id=match.group(1),
            timestamp_counts=int(match.group(2)),
        )

    def _parse_timeout(self, line: str) -> PingTimeoutEvent | None:
        if TIMEOUT_RE.match(line):
            return PingTimeoutEvent()
        return None

    def _parse_remote_voltage_response(self, line: str) -> RemoteVoltageResponseEvent | None:
        match = REMOTE_VOLTAGE_RE.match(line)
        if match is None:
            return None
        return RemoteVoltageResponseEvent(
            responder_id=match.group(1),
            voltage_raw=int(match.group(2)),
        )

    def _parse_broadcast_data(
        self,
        line: str,
    ) -> ReceivedBroadcastEvent | TestBroadcastReceivedEvent | None:
        match = BROADCAST_DATA_RE.match(line)
        if match is None:
            return None

        sender_id = match.group(1)
        byte_count = int(match.group(2))
        payload = match.group(3)

        if byte_count == TEST_MESSAGE_BYTE_COUNT and payload == TEST_MESSAGE_PAYLOAD:
            return TestBroadcastReceivedEvent(sender_id=sender_id)

        return ReceivedBroadcastEvent(
            sender_id=sender_id,
            data=_payload_to_bytes(payload),
        )

    def _parse_unicast_data(self, line: str) -> ReceivedUnicastEvent | None:
        match = UNICAST_DATA_RE.match(line)
        if match is None:
            return None
        return ReceivedUnicastEvent(data=_payload_to_bytes(match.group(2)))
