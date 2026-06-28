"""Tests for BasicPositionCodec."""

from __future__ import annotations

import pytest

from nanomodem.positioning.basic_position_codec import BasicPositionCodec
from nanomodem.types import Coord, PositionMessage


def test__should_encode_position_message_as_32_bytes() -> None:
    codec = BasicPositionCodec()
    message = PositionMessage(node_id="001", coord=Coord(lat=63.0, lon=10.0), depth=5.0)
    result = codec.encode(message)
    assert isinstance(result, bytes)
    assert len(result) == 32


def test__should_decode_position_bytes_to_position_message() -> None:
    codec = BasicPositionCodec()
    message = PositionMessage(node_id="001", coord=Coord(lat=63.0, lon=10.0), depth=5.0)
    decoded = codec.decode(codec.encode(message))
    assert decoded.node_id == "001"
    assert abs(decoded.coord.lat - 63.0) < 1e-5
    assert abs(decoded.coord.lon - 10.0) < 1e-5
    assert abs(decoded.depth - 5.0) < 1e-3


def test__should_raise_for_invalid_payload() -> None:
    codec = BasicPositionCodec()
    with pytest.raises(ValueError, match="Invalid position payload"):
        codec.decode(b"garbage")


def test__should_raise_for_empty_payload() -> None:
    codec = BasicPositionCodec()
    with pytest.raises(ValueError, match="Invalid position payload"):
        codec.decode(b"")


def test__should_encode_sender_id_in_payload() -> None:
    codec = BasicPositionCodec()
    message = PositionMessage(node_id="042", coord=Coord(lat=0.0, lon=0.0), depth=0.0)
    decoded = codec.decode(codec.encode(message))
    assert decoded.node_id == "042"


def test__should_roundtrip_negative_coordinates() -> None:
    codec = BasicPositionCodec()
    message = PositionMessage(
        node_id="007",
        coord=Coord(lat=-33.8688, lon=-151.2093),
        depth=12.5,
    )
    decoded = codec.decode(codec.encode(message))
    assert abs(decoded.coord.lat - (-33.8688)) < 1e-4
    assert abs(decoded.coord.lon - (-151.2093)) < 1e-4
    assert abs(decoded.depth - 12.5) < 1e-3


def test__should_raise_for_truncated_position() -> None:
    codec = BasicPositionCodec()
    with pytest.raises(ValueError, match="Invalid position payload"):
        codec.decode(b"P001+63.000")


def test__should_raise_for_unknown_message_type() -> None:
    codec = BasicPositionCodec()
    with pytest.raises(ValueError, match="Invalid position payload"):
        codec.decode(b"Xsome_unknown_stuff_here_padding!")


def test__should_zero_pad_numeric_node_id_on_encode() -> None:
    codec = BasicPositionCodec()
    message = PositionMessage(node_id="1", coord=Coord(lat=0.0, lon=0.0), depth=0.0)
    encoded = codec.encode(message)
    assert encoded[1:4] == b"001"


def test__should_raise_value_error_for_non_ascii_payload() -> None:
    codec = BasicPositionCodec()
    with pytest.raises(ValueError, match="Invalid position payload"):
        codec.decode(b"\xff\xfe\xfd")


def test__should_raise_when_encoded_payload_exceeds_32_bytes() -> None:
    codec = BasicPositionCodec()
    message = PositionMessage(node_id="001", coord=Coord(lat=123.0, lon=10.0), depth=5.0)
    with pytest.raises(ValueError, match="Position payload must be 32 bytes"):
        codec.encode(message)


def test__should_raise_when_depth_field_expands_payload() -> None:
    codec = BasicPositionCodec()
    message = PositionMessage(node_id="001", coord=Coord(lat=63.0, lon=10.0), depth=1000.0)
    with pytest.raises(ValueError, match="Position payload must be 32 bytes"):
        codec.encode(message)
