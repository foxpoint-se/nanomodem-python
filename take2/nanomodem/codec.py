"""Codec for encoding/decoding message bodies. Stateless, pure, no I/O.

Injected into NanomodemTransport, NOT into AcousticNode.
The node never knows this exists.

Body format (for position messages):
  - 1 byte: message type ('P' = position)
  - 3 bytes: sender node ID (ASCII, e.g. "001")
  - remaining: payload depending on type

Position payload:
  - lat as signed float, 10 chars, zero-padded (e.g. "+63.000000")
  - lon as signed float, 11 chars, zero-padded (e.g. "+010.000000")
  - depth as unsigned float, 7 chars, zero-padded (e.g. "005.000")
  Total body: 1 + 3 + 10 + 11 + 7 = 32 bytes (fits in 64-byte limit)
"""

from __future__ import annotations

from typing import Protocol

from .types import Coord, Message, PositionMessage, UnknownMessage


class CodecInterface(Protocol):
    """Interface for body encoding/decoding."""

    def encode_position(self, node_id: str, coord: Coord, depth: float) -> bytes: ...

    def decode(self, payload: bytes) -> Message: ...


MSG_TYPE_POSITION = ord("P")


class Codec:
    """Concrete codec for the nanomodem protocol body format."""

    def encode_position(self, node_id: str, coord: Coord, depth: float) -> bytes:
        """Encode a position message body.

        Format: 'P' + node_id(3) + lat(10) + lon(11) + depth(7) = 32 bytes.
        """
        lat_str = f"{coord.lat:+010.6f}"  # e.g. "+63.000000"
        lon_str = f"{coord.lon:+011.6f}"  # e.g. "+010.000000"
        depth_str = f"{depth:07.3f}"  # e.g. "005.000"
        
        body = f"P{node_id[:3]:>03s}{lat_str}{lon_str}{depth_str}"
        return body.encode("ascii")

    def decode(self, payload: bytes) -> Message:
        """Decode a message body. Returns UnknownMessage if it can't parse."""
        try:
            text = payload.decode("ascii")
        except (UnicodeDecodeError, ValueError):
            return UnknownMessage(raw=repr(payload))

        if len(text) < 1:
            return UnknownMessage(raw=text)

        msg_type = text[0]

        if msg_type == "P":
            return self._decode_position(text)

        return UnknownMessage(raw=text)

    def _decode_position(self, text: str) -> Message:
        """Decode a position message body: 'P' + id(3) + lat(10) + lon(11) + depth(7)."""
        if len(text) < 32:
            return UnknownMessage(raw=text)
        try:
            node_id = text[1:4]
            lat = float(text[4:14])
            lon = float(text[14:25])
            depth = float(text[25:32])
            return PositionMessage(
                node_id=node_id,
                coord=Coord(lat=lat, lon=lon),
                depth=depth,
            )
        except (ValueError, IndexError):
            return UnknownMessage(raw=text)
