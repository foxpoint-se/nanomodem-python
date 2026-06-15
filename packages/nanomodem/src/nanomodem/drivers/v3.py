"""Nanomodem v3 driver — modem command protocol and response parsing.

Formats outgoing commands ($P, $B, $T, $Q, $?) and parses incoming responses
(#R, #B, #U, #A status, local acks $B/$P/$T, quality $C/$C-) per the
nanomodem v3 user guide. Uses a CodecProtocol for body encoding/decoding.
"""

from __future__ import annotations

import re

from ..protocols import CodecProtocol
from ..types import (
    Coord,
    Message,
    RangeResponseMessage,
    UnknownMessage,
    V3TestBroadcastMessage,
)
from .v3_line_parsers import parse_local_ack_line, parse_quality_line, parse_status_line
from .v3_spec import normalize_modem_response_line, parse_test_broadcast_sender

RANGE_RESPONSE_RE = re.compile(r"^#R(\d{3})T(\d{5})$")
BROADCAST_DATA_RE = re.compile(r"^#B(\d{3})(\d{2})(.+)$")
UNICAST_DATA_RE = re.compile(r"^#U(\d{2})(.+)$")


class NanomodemV3Driver:
    """Driver for nanomodem v3 hardware protocol.

    Handles command formatting and response parsing.
    Body encoding/decoding is delegated to the injected codec.
    """

    def __init__(self, codec: CodecProtocol) -> None:
        self._codec = codec

    def format_broadcast(self, node_id: str, coord: Coord, depth: float) -> bytes:
        """Format a broadcast position command: $Bnn{body}."""
        payload = self._codec.encode_position(node_id, coord, depth)
        nn = f"{len(payload):02d}"
        return f"$B{nn}".encode("ascii") + payload

    def format_ping(self, target_id: str) -> bytes:
        """Format a ping command: $Pxxx."""
        return f"$P{target_id}".encode("ascii")

    def format_test_request(self, target_id: str) -> bytes:
        """Format a test message request: $Txxx."""
        return f"$T{target_id}".encode("ascii")

    def format_quality_query(self) -> bytes:
        """Format a link quality query: $Q."""
        return b"$Q"

    def format_status_query(self) -> bytes:
        """Format a modem status query: $?."""
        return b"$?"

    def parse_line(self, line: str) -> Message:
        """Parse a serial line into a typed Message."""
        line = normalize_modem_response_line(line)
        parsed = (
            self._parse_range(line)
            or parse_status_line(line)
            or parse_quality_line(line)
            or parse_local_ack_line(line)
            or self._parse_broadcast_data(line)
            or self._parse_unicast_data(line)
        )
        if parsed is not None:
            return parsed
        return UnknownMessage(raw=line)

    def _parse_range(self, line: str) -> RangeResponseMessage | None:
        match = RANGE_RESPONSE_RE.match(line)
        if match is None:
            return None
        return RangeResponseMessage(
            node_id=match.group(1),
            timestamp=int(match.group(2)),
        )

    def _parse_broadcast_data(self, line: str) -> Message | None:
        match = BROADCAST_DATA_RE.match(line)
        if match is None:
            return None
        sender_id = parse_test_broadcast_sender(line)
        if sender_id is not None:
            return V3TestBroadcastMessage(node_id=sender_id)
        body = match.group(3)
        return self._codec.decode(body.encode("ascii"))

    def _parse_unicast_data(self, line: str) -> Message | None:
        match = UNICAST_DATA_RE.match(line)
        if match is None:
            return None
        body = match.group(2)
        return self._codec.decode(body.encode("ascii"))
