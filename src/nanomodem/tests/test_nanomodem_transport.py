"""Tests for NanomodemV3Driver.

These tests cover the modem command formatting and response parsing
that was extracted from the old NanomodemTransport into the driver.
"""

from nanomodem.codecs.v3 import Codec
from nanomodem.drivers.v3 import NanomodemV3Driver
from nanomodem.drivers.v3_spec import (
    TEST_MESSAGE_PAYLOAD,
    is_test_broadcast_line,
    normalize_modem_response_line,
    supply_voltage_volts,
)
from nanomodem.types import (
    Coord,
    LocalAckMessage,
    ModemStatusMessage,
    PositionMessage,
    QualityIndicatorMessage,
    RangeResponseMessage,
    UnknownMessage,
)


def _make_driver() -> NanomodemV3Driver:
    return NanomodemV3Driver(codec=Codec())


# --- Parsing tests ---


def test_should_forward_range_response_via_callback() -> None:
    driver = _make_driver()
    msg = driver.parse_line("#R002T12345")
    assert isinstance(msg, RangeResponseMessage)
    assert msg.node_id == "002"
    assert msg.timestamp == 12345


def test_should_write_P_command_format() -> None:
    """Verify the format of a ping command string."""
    driver = _make_driver()
    cmd = driver.format_ping("002")
    assert cmd == b"$P002"


def test_should_write_B_command_format() -> None:
    """Verify the format of a broadcast command string."""
    driver = _make_driver()
    cmd = driver.format_broadcast("001", Coord(lat=63.0, lon=10.0), depth=0.0)
    assert cmd.startswith(b"$B32")


def test_should_decode_broadcast_data_via_codec() -> None:
    """#Bxxxnnddd... -> codec decodes the body."""
    driver = _make_driver()
    codec = Codec()
    body = codec.encode_position("002", Coord(lat=63.0, lon=10.0), depth=5.0)
    line = f"#B002{len(body):02d}" + body.decode("ascii")
    msg = driver.parse_line(line)
    assert isinstance(msg, PositionMessage)
    assert msg.node_id == "002"
    assert abs(msg.coord.lat - 63.0) < 1e-5


def test_should_decode_unicast_data_via_codec() -> None:
    """#Unnddd... -> codec decodes the body (sender ID in payload)."""
    driver = _make_driver()
    codec = Codec()
    body = codec.encode_position("003", Coord(lat=63.5, lon=10.5), depth=0.0)
    line = f"#U{len(body):02d}" + body.decode("ascii")
    msg = driver.parse_line(line)
    assert isinstance(msg, PositionMessage)
    assert msg.node_id == "003"


def test__should_parse_ping_local_ack() -> None:
    driver = _make_driver()
    msg = driver.parse_line("$P002")
    assert isinstance(msg, LocalAckMessage)
    assert msg.command == "ping"
    assert msg.target_id == "002"


def test__should_normalize_leading_noise_before_dollar_response() -> None:
    assert normalize_modem_response_line("\xff$B32") == "$B32"
    driver = _make_driver()
    msg = driver.parse_line("\xff$B32")
    assert isinstance(msg, LocalAckMessage)
    assert msg.command == "broadcast"


def test__should_normalize_leading_noise_before_hash_response() -> None:
    line = normalize_modem_response_line("\x00#R002T12345")
    assert line == "#R002T12345"
    driver = _make_driver()
    msg = driver.parse_line("\x00#R002T12345")
    assert isinstance(msg, RangeResponseMessage)


def test__should_format_test_request_command() -> None:
    driver = _make_driver()
    assert driver.format_test_request("002") == b"$T002"


def test__should_format_quality_query_command() -> None:
    driver = _make_driver()
    assert driver.format_quality_query() == b"$Q"


def test__should_format_status_query_command() -> None:
    driver = _make_driver()
    assert driver.format_status_query() == b"$?"


def test__should_parse_modem_status_line() -> None:
    driver = _make_driver()
    msg = driver.parse_line("#A042V48123")
    assert isinstance(msg, ModemStatusMessage)
    assert msg.node_id == "042"
    assert msg.voltage_raw == 48123
    assert abs(supply_voltage_volts(48123) - 11.01) < 0.01


def test__should_parse_modem_status_when_concatenated_on_one_rx_chunk() -> None:
    """Hardware may append further bytes without CRLF after #AxxxVyyyyy."""
    driver = _make_driver()
    msg = driver.parse_line("#A001V27353R001.006.000B2024-02-15T11:56:51")
    assert isinstance(msg, ModemStatusMessage)
    assert msg.node_id == "001"
    assert msg.voltage_raw == 27353


def test__should_parse_quality_indicator() -> None:
    driver = _make_driver()
    msg = driver.parse_line("$C4")
    assert isinstance(msg, QualityIndicatorMessage)
    assert msg.bytes_corrected == 4


def test__should_parse_quality_rejected() -> None:
    driver = _make_driver()
    msg = driver.parse_line("$C-")
    assert isinstance(msg, QualityIndicatorMessage)
    assert msg.bytes_corrected is None


def test__should_parse_test_local_ack() -> None:
    driver = _make_driver()
    msg = driver.parse_line("$T002")
    assert isinstance(msg, LocalAckMessage)
    assert msg.command == "test"
    assert msg.target_id == "002"


def test__should_treat_invalid_quality_line_as_unknown() -> None:
    driver = _make_driver()
    assert isinstance(driver.parse_line("$C9"), UnknownMessage)
    assert isinstance(driver.parse_line("$Cx"), UnknownMessage)


def test__should_detect_test_broadcast_line() -> None:
    line = f"#B002{len(TEST_MESSAGE_PAYLOAD):02d}{TEST_MESSAGE_PAYLOAD}"
    assert is_test_broadcast_line(line) is True


def test__should_reject_position_broadcast_as_test_line() -> None:
    codec = Codec()
    body = codec.encode_position("002", Coord(lat=63.0, lon=10.0), depth=0.0)
    line = f"#B002{len(body):02d}" + body.decode("ascii")
    assert is_test_broadcast_line(line) is False


def test_should_forward_timeout_as_unknown_message() -> None:
    driver = _make_driver()
    msg = driver.parse_line("#TO")
    assert isinstance(msg, UnknownMessage)
    assert msg.raw == "#TO"


def test_should_forward_error_as_unknown_message() -> None:
    driver = _make_driver()
    msg = driver.parse_line("E")
    assert isinstance(msg, UnknownMessage)
    assert msg.raw == "E"


def test_should_forward_invalid_status_line_as_unknown_message() -> None:
    driver = _make_driver()
    msg = driver.parse_line("#A42V48123")
    assert isinstance(msg, UnknownMessage)
    assert msg.raw == "#A42V48123"


def test_should_write_M_command_format() -> None:
    """Verify the expected format of a unicast-with-ack command."""
    codec = Codec()
    payload = codec.encode_position("001", Coord(lat=63.0, lon=10.0), depth=0.0)
    target = "002"
    nn = f"{len(payload):02d}"
    cmd = f"$M{target}{nn}".encode("ascii") + payload
    assert cmd.startswith(b"$M00232")
