"""BasicPositionCodec — encodes/decodes PositionMessage payloads."""

from __future__ import annotations

from nanomodem.types import Coord, PositionMessage


class BasicPositionCodec:
    """Codec for position broadcast payloads.

    Format: 'P' + node_id(3) + lat(10) + lon(11) + depth(7) = 32 bytes
    """

    def encode(self, msg: PositionMessage) -> bytes:
        """Encode PositionMessage to wire bytes."""
        lat_str = f"{msg.coord.lat:+010.6f}"
        lon_str = f"{msg.coord.lon:+011.6f}"
        depth_str = f"{msg.depth:07.3f}"
        body = f"P{msg.node_id[:3]:>03s}{lat_str}{lon_str}{depth_str}"
        return body.encode("ascii")

    def decode(self, data: bytes) -> PositionMessage:
        """Decode wire bytes to PositionMessage."""
        text = data.decode("ascii")
        if len(text) < 32 or text[0] != "P":
            raise ValueError(f"Invalid position payload: {text!r}")
        node_id = text[1:4]
        lat = float(text[4:14])
        lon = float(text[14:25])
        depth = float(text[25:32])
        return PositionMessage(
            node_id=node_id,
            coord=Coord(lat=lat, lon=lon),
            depth=depth,
        )
