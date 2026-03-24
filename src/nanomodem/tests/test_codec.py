"""Tests for Codec."""

from nanomodem.codec import Codec
from nanomodem.types import Coord, PositionMessage, UnknownMessage


def test_should_encode_position_as_bytes() -> None:
    codec = Codec()
    coord = Coord(lat=63.0, lon=10.0)
    result = codec.encode_position("001", coord, depth=5.0)
    assert isinstance(result, bytes)
    assert len(result) == 32


def test_should_decode_position_bytes_to_position_message() -> None:
    codec = Codec()
    coord = Coord(lat=63.0, lon=10.0)
    encoded = codec.encode_position("001", coord, depth=5.0)
    msg = codec.decode(encoded)
    assert isinstance(msg, PositionMessage)
    assert msg.node_id == "001"
    assert abs(msg.coord.lat - 63.0) < 1e-5
    assert abs(msg.coord.lon - 10.0) < 1e-5
    assert abs(msg.depth - 5.0) < 1e-3


def test_should_return_unknown_message_when_decoding_invalid_bytes() -> None:
    codec = Codec()
    msg = codec.decode(b"garbage")
    assert isinstance(msg, UnknownMessage)
    assert msg.raw == "garbage"


def test_should_return_unknown_message_for_empty_payload() -> None:
    codec = Codec()
    msg = codec.decode(b"")
    assert isinstance(msg, UnknownMessage)


def test_should_encode_sender_id_in_payload() -> None:
    codec = Codec()
    coord = Coord(lat=0.0, lon=0.0)
    encoded = codec.encode_position("042", coord, depth=0.0)
    msg = codec.decode(encoded)
    assert isinstance(msg, PositionMessage)
    assert msg.node_id == "042"


def test_should_roundtrip_negative_coordinates() -> None:
    codec = Codec()
    coord = Coord(lat=-33.8688, lon=-151.2093)
    encoded = codec.encode_position("007", coord, depth=12.5)
    msg = codec.decode(encoded)
    assert isinstance(msg, PositionMessage)
    assert abs(msg.coord.lat - (-33.8688)) < 1e-4
    assert abs(msg.coord.lon - (-151.2093)) < 1e-4
    assert abs(msg.depth - 12.5) < 1e-3


def test_should_return_unknown_message_for_truncated_position() -> None:
    codec = Codec()
    msg = codec.decode(b"P001+63.000")  # Too short
    assert isinstance(msg, UnknownMessage)


def test_should_return_unknown_for_unknown_message_type() -> None:
    codec = Codec()
    msg = codec.decode(b"Xsome_unknown_stuff_here_padding!")
    assert isinstance(msg, UnknownMessage)
    assert msg.raw.startswith("X")
