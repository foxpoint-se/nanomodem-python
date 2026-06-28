"""BasicPositionCodec — encodes/decodes PositionMessage payloads."""

from __future__ import annotations

from nanomodem.types import Coord, PositionMessage

_POSITION_PAYLOAD_LENGTH = 32


def _format_node_id(node_id: str) -> str:
    if not node_id.isdigit():
        raise ValueError(f"node_id must be numeric, got '{node_id}'")
    numeric = int(node_id)
    if numeric < 1 or numeric > 255:
        raise ValueError(f"node_id must represent 1-255, got {numeric}")
    return f"{numeric:03d}"


class BasicPositionCodec:
    """Codec for position broadcast payloads.

    Format: 'P' + node_id(3) + lat(10) + lon(11) + depth(7) = 32 bytes
    """

    def encode(self, msg: PositionMessage) -> bytes:
        """Encode PositionMessage to wire bytes."""
        lat_str = f"{msg.coord.lat:+010.6f}"
        lon_str = f"{msg.coord.lon:+011.6f}"
        depth_str = f"{msg.depth:07.3f}"
        body = f"P{_format_node_id(msg.node_id)}{lat_str}{lon_str}{depth_str}"
        if len(body) != _POSITION_PAYLOAD_LENGTH:
            raise ValueError(
                f"Position payload must be {_POSITION_PAYLOAD_LENGTH} bytes, got {len(body)}: {body!r}",
            )
        return body.encode("ascii")

    def decode(self, data: bytes) -> PositionMessage:
        """Decode wire bytes to PositionMessage."""
        try:
            text = data.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Invalid position payload: {data!r}") from exc
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
