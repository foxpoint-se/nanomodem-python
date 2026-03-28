"""Nanomodem v3 driver — modem command protocol and response parsing.

Formats outgoing commands ($P, $B) and parses incoming responses
(#R, #B, #U) per the nanomodem v3 user guide. Uses a CodecProtocol
for body encoding/decoding.
"""

from __future__ import annotations

import re

from ..protocols import CodecProtocol
from ..types import (
    Coord,
    Message,
    RangeResponseMessage,
    UnknownMessage,
)

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

    def parse_line(self, line: str) -> Message:
        """Parse a serial line into a typed Message.

        Known patterns:
          - #RxxxTyyyyy  -> RangeResponseMessage
          - #Bxxxnnddd... -> decode broadcast body via codec
          - #Unnddd...  -> decode unicast body via codec
          - Everything else -> UnknownMessage (nothing lost)
        """
        m = RANGE_RESPONSE_RE.match(line)
        if m:
            node_id = m.group(1)
            timestamp = int(m.group(2))
            return RangeResponseMessage(node_id=node_id, timestamp=timestamp)

        m = BROADCAST_DATA_RE.match(line)
        if m:
            body = m.group(3)
            return self._codec.decode(body.encode("ascii"))

        m = UNICAST_DATA_RE.match(line)
        if m:
            body = m.group(2)
            return self._codec.decode(body.encode("ascii"))

        return UnknownMessage(raw=line)
