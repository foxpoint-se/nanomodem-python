"""Parse nanomodem v3 serial response lines into ModemEvent variants."""

from __future__ import annotations

import re

from .spec import MAX_BYTES_CORRECTED
from .wire_types import (
    AddressSetEvent,
    BroadcastCommandAckEvent,
    EchoCommandAckEvent,
    PingCommandAckEvent,
    QualityIndicatorEvent,
    QualityRejectedEvent,
    RemoteVoltageQueryAckEvent,
    StatusResponseEvent,
    TestRequestAckEvent,
    UnicastCommandAckEvent,
    UnicastWithAckCommandAckEvent,
)

STATUS_LINE_RE = re.compile(r"^#A(\d{3})V(\d{5})")
ADDRESS_SET_RE = re.compile(r"^#A(\d{3})$")
QUALITY_LINE_RE = re.compile(r"^\$C(\d)$")
QUALITY_REJECTED_RE = re.compile(r"^\$C-$")
PING_ACK_RE = re.compile(r"^\$P(\d{3})$")
TEST_ACK_RE = re.compile(r"^\$T(\d{3})$")
BROADCAST_ACK_RE = re.compile(r"^\$B(\d{2})$")
UNICAST_ACK_RE = re.compile(r"^\$U(\d{3})(\d{2})$")
UNICAST_WITH_ACK_ACK_RE = re.compile(r"^\$M(\d{3})(\d{2})$")
REMOTE_VOLTAGE_ACK_RE = re.compile(r"^\$V(\d{3})$")
ECHO_ACK_RE = re.compile(r"^\$E(\d{3})(\d{2})$")


def parse_status_line(line: str) -> StatusResponseEvent | None:
    """Parse #AxxxVyyyyy status response from $? query."""
    match = STATUS_LINE_RE.match(line)
    if match is None:
        return None
    return StatusResponseEvent(
        address=match.group(1),
        voltage_raw=int(match.group(2)),
    )


def parse_address_set(line: str) -> AddressSetEvent | None:
    """Parse #Axxx address confirmation from $Axxx command."""
    match = ADDRESS_SET_RE.match(line)
    if match is None:
        return None
    return AddressSetEvent(address=match.group(1))


def parse_quality_line(line: str) -> QualityIndicatorEvent | QualityRejectedEvent | None:
    """Parse $Cx or $C- quality indicator lines."""
    if QUALITY_REJECTED_RE.match(line):
        return QualityRejectedEvent()

    match = QUALITY_LINE_RE.match(line)
    if match is None:
        return None

    value = int(match.group(1))
    if value > MAX_BYTES_CORRECTED:
        return None
    return QualityIndicatorEvent(bytes_corrected=value)


def parse_ping_ack(line: str) -> PingCommandAckEvent | None:
    match = PING_ACK_RE.match(line)
    if match is None:
        return None
    return PingCommandAckEvent(target_id=match.group(1))


def parse_test_ack(line: str) -> TestRequestAckEvent | None:
    match = TEST_ACK_RE.match(line)
    if match is None:
        return None
    return TestRequestAckEvent(target_id=match.group(1))


def parse_broadcast_ack(line: str) -> BroadcastCommandAckEvent | None:
    match = BROADCAST_ACK_RE.match(line)
    if match is None:
        return None
    return BroadcastCommandAckEvent(byte_count=int(match.group(1)))


def parse_unicast_ack(line: str) -> UnicastCommandAckEvent | None:
    match = UNICAST_ACK_RE.match(line)
    if match is None:
        return None
    return UnicastCommandAckEvent(
        target_id=match.group(1),
        byte_count=int(match.group(2)),
    )


def parse_unicast_with_ack_ack(line: str) -> UnicastWithAckCommandAckEvent | None:
    match = UNICAST_WITH_ACK_ACK_RE.match(line)
    if match is None:
        return None
    return UnicastWithAckCommandAckEvent(
        target_id=match.group(1),
        byte_count=int(match.group(2)),
    )


def parse_remote_voltage_ack(line: str) -> RemoteVoltageQueryAckEvent | None:
    match = REMOTE_VOLTAGE_ACK_RE.match(line)
    if match is None:
        return None
    return RemoteVoltageQueryAckEvent(target_id=match.group(1))


def parse_echo_ack(line: str) -> EchoCommandAckEvent | None:
    match = ECHO_ACK_RE.match(line)
    if match is None:
        return None
    return EchoCommandAckEvent(
        target_id=match.group(1),
        byte_count=int(match.group(2)),
    )
