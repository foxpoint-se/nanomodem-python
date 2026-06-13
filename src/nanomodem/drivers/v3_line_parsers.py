"""Pure line parsers for nanomodem v3 serial responses."""

from __future__ import annotations

import re

from ..types import LocalAckMessage, ModemStatusMessage, QualityIndicatorMessage
from .v3_spec import MAX_BYTES_CORRECTED

STATUS_LINE_RE = re.compile(r"^#A(\d{3})V(\d{5})")
QUALITY_LINE_RE = re.compile(r"^\$C(\d)$")
QUALITY_REJECTED_RE = re.compile(r"^\$C-$")
TEST_ACK_RE = re.compile(r"^\$T(\d{3})$")
PING_ACK_RE = re.compile(r"^\$P(\d{3})$")
BROADCAST_ACK_RE = re.compile(r"^\$B(\d{2})$")


def parse_status_line(line: str) -> ModemStatusMessage | None:
    """Parse #AxxxVyyyyy status response from $? query."""
    match = STATUS_LINE_RE.match(line)
    if match is None:
        return None
    return ModemStatusMessage(
        node_id=match.group(1),
        voltage_raw=int(match.group(2)),
    )


def parse_quality_line(line: str) -> QualityIndicatorMessage | None:
    """Parse $Cx or $C- quality indicator lines."""
    if QUALITY_REJECTED_RE.match(line):
        return QualityIndicatorMessage(bytes_corrected=None)

    match = QUALITY_LINE_RE.match(line)
    if match is None:
        return None

    value = int(match.group(1))
    if value > MAX_BYTES_CORRECTED:
        return None
    return QualityIndicatorMessage(bytes_corrected=value)


def parse_local_ack_line(line: str) -> LocalAckMessage | None:
    """Parse immediate local acknowledgements ($T, $P, $Bnn)."""
    test_or_ping = _parse_test_or_ping_ack(line)
    if test_or_ping is not None:
        return test_or_ping

    broadcast_match = BROADCAST_ACK_RE.match(line)
    if broadcast_match is not None:
        return LocalAckMessage(command="broadcast", target_id=broadcast_match.group(1))

    return None


def _parse_test_or_ping_ack(line: str) -> LocalAckMessage | None:
    test_match = TEST_ACK_RE.match(line)
    if test_match:
        return LocalAckMessage(command="test", target_id=test_match.group(1))

    ping_match = PING_ACK_RE.match(line)
    if ping_match:
        return LocalAckMessage(command="ping", target_id=ping_match.group(1))

    return None
