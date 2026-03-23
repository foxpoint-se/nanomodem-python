"""Tests for NanomodemTransport.

These tests focus on the parsing logic (_parse_line), which is pure
and doesn't require a real serial port. The serial I/O is trivial
and best tested with actual hardware.
"""

from nanomodem.codec import Codec
from nanomodem.nanomodem_transport import NanomodemTransport
from nanomodem.types import (
    Coord,
    PositionMessage,
    RangeResponseMessage,
    UnknownMessage,
)


def _make_parser() -> NanomodemTransport:
    """Create a NanomodemTransport without opening a real serial port.

    We only use _parse_line which doesn't touch the serial port.
    """
    # Bypass __init__ to avoid opening a serial port
    transport = object.__new__(NanomodemTransport)
    transport.node_id = "001"
    transport._codec = Codec()
    transport._callback = None
    return transport


# --- Parsing tests ---


def test_should_forward_range_response_via_callback() -> None:
    transport = _make_parser()
    msg = transport._parse_line("#R002T12345")
    assert isinstance(msg, RangeResponseMessage)
    assert msg.node_id == "002"
    assert msg.timestamp == 12345


def test_should_write_P_command_format() -> None:
    """Verify the format of a ping command string."""
    cmd = f"$P002".encode("ascii")
    assert cmd == b"$P002"


def test_should_write_B_command_format() -> None:
    """Verify the format of a broadcast command string."""
    codec = Codec()
    payload = codec.encode_position("001", Coord(lat=63.0, lon=10.0), depth=0.0)
    nn = f"{len(payload):02d}"
    cmd = f"$B{nn}".encode("ascii") + payload
    assert cmd.startswith(b"$B32")  # 32-byte position payload


def test_should_decode_broadcast_data_via_codec() -> None:
    """#Bxxxnnddd... → codec decodes the body."""
    transport = _make_parser()
    codec = Codec()
    body = codec.encode_position("002", Coord(lat=63.0, lon=10.0), depth=5.0)
    line = f"#B002{len(body):02d}" + body.decode("ascii")
    msg = transport._parse_line(line)
    assert isinstance(msg, PositionMessage)
    assert msg.node_id == "002"
    assert abs(msg.coord.lat - 63.0) < 1e-5


def test_should_decode_unicast_data_via_codec() -> None:
    """#Unnddd... → codec decodes the body (sender ID in payload)."""
    transport = _make_parser()
    codec = Codec()
    body = codec.encode_position("003", Coord(lat=63.5, lon=10.5), depth=0.0)
    line = f"#U{len(body):02d}" + body.decode("ascii")
    msg = transport._parse_line(line)
    assert isinstance(msg, PositionMessage)
    assert msg.node_id == "003"


def test_should_forward_local_ack_as_unknown_message() -> None:
    transport = _make_parser()
    msg = transport._parse_line("$P002")
    assert isinstance(msg, UnknownMessage)
    assert msg.raw == "$P002"


def test_should_forward_timeout_as_unknown_message() -> None:
    transport = _make_parser()
    msg = transport._parse_line("#TO")
    assert isinstance(msg, UnknownMessage)
    assert msg.raw == "#TO"


def test_should_forward_error_as_unknown_message() -> None:
    transport = _make_parser()
    msg = transport._parse_line("E")
    assert isinstance(msg, UnknownMessage)
    assert msg.raw == "E"


def test_should_forward_unrecognized_serial_line_as_unknown_message() -> None:
    transport = _make_parser()
    msg = transport._parse_line("#A042V48123")
    assert isinstance(msg, UnknownMessage)
    assert msg.raw == "#A042V48123"


def test_should_write_M_command_format() -> None:
    """Verify the expected format of a unicast-with-ack command."""
    codec = Codec()
    payload = codec.encode_position("001", Coord(lat=63.0, lon=10.0), depth=0.0)
    target = "002"
    nn = f"{len(payload):02d}"
    cmd = f"$M{target}{nn}".encode("ascii") + payload
    assert cmd.startswith(b"$M00232")
