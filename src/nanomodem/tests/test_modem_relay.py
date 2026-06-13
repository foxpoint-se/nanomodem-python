"""Tests for modem_relay — protocol conversion per nanomodem v3 user guide.

Spec reference (section 5.2):

  $Bnn{body}  -> sender gets $Bnn\\r\\n, others get #B{xxx}nn{body}\\r\\n
  $Pxxx       -> sender gets $Pxxx\\r\\n, then #RxxxTyyyyy\\r\\n on response
  Range:        R = yyyyy * c * 3.125e-5  (where c = sound speed in m/s)
"""

from __future__ import annotations

import pytest

from nanomodem.demo.scenarios.modem_relay import (
    broadcast_ack,
    broadcast_relay,
    distance_metres,
    parse_broadcast,
    parse_ping,
    ping_ack,
    range_response,
    split_modem_command,
)

# ------------------------------------------------------------------ #
#  Broadcast parsing                                                   #
# ------------------------------------------------------------------ #


def test__should_split_broadcast_command_without_newline() -> None:
    raw = b"$B32P001+59.310000+017.975000005.000"
    split = split_modem_command(raw)
    assert split is not None
    command, rest = split
    assert command == raw
    assert rest == b""


def test__should_split_ping_command_without_newline() -> None:
    split = split_modem_command(b"$P002")
    assert split is not None
    command, rest = split
    assert command == b"$P002"
    assert rest == b""


def test__should_return_none_when_broadcast_is_incomplete() -> None:
    assert split_modem_command(b"$B32P001") is None


def test__should_parse_broadcast_command() -> None:
    raw = b"$B32P001+59.310000+017.975000005.000"
    result = parse_broadcast(raw)
    assert result is not None
    nn, body = result
    assert nn == "32"
    assert body == b"P001+59.310000+017.975000005.000"


def test__should_parse_broadcast_with_crlf() -> None:
    raw = b"$B32P001+59.310000+017.975000005.000\r\n"
    result = parse_broadcast(raw)
    assert result is not None
    nn, body = result
    assert nn == "32"


def test__should_return_none_for_ping_command() -> None:
    assert parse_broadcast(b"$P002") is None


def test__should_return_none_for_incoming_broadcast() -> None:
    assert parse_broadcast(b"#B00132body") is None


# ------------------------------------------------------------------ #
#  Broadcast ack (to sender)                                          #
# ------------------------------------------------------------------ #


def test__should_generate_broadcast_ack_per_spec() -> None:
    # Per spec: "$Bnn is returned immediately to confirm nn bytes have been broadcast"
    assert broadcast_ack("32") == b"$B32\r\n"
    assert broadcast_ack("08") == b"$B08\r\n"


# ------------------------------------------------------------------ #
#  Broadcast relay (to other nodes)                                   #
# ------------------------------------------------------------------ #


def test__should_generate_broadcast_relay_per_spec() -> None:
    # Per spec: "All units in range will output #Bxxxnnddd..."
    body = b"P001+59.310000+017.975000005.000"
    relay = broadcast_relay("001", "32", body)
    assert relay == b"#B00132P001+59.310000+017.975000005.000\r\n"


def test__should_include_sender_id_in_relay() -> None:
    relay = broadcast_relay("042", "04", b"data")
    assert relay.startswith(b"#B042")


def test__should_preserve_body_in_relay() -> None:
    body = b"some_payload_bytes"
    relay = broadcast_relay("001", "18", body)
    assert body in relay


# ------------------------------------------------------------------ #
#  Ping parsing                                                        #
# ------------------------------------------------------------------ #


def test__should_parse_ping_command() -> None:
    assert parse_ping(b"$P002") == "002"
    assert parse_ping(b"$P123") == "123"
    assert parse_ping(b"$P255") == "255"


def test__should_parse_ping_with_crlf() -> None:
    assert parse_ping(b"$P002\r\n") == "002"


def test__should_return_none_for_broadcast_command() -> None:
    assert parse_ping(b"$B32body") is None


def test__should_return_none_for_range_response() -> None:
    assert parse_ping(b"#R002T12345") is None


# ------------------------------------------------------------------ #
#  Ping ack (to sender)                                               #
# ------------------------------------------------------------------ #


def test__should_generate_ping_ack_per_spec() -> None:
    # Per spec: "$Pxxx is returned immediately to acknowledge command"
    assert ping_ack("002") == b"$P002\r\n"
    assert ping_ack("123") == b"$P123\r\n"


# ------------------------------------------------------------------ #
#  Range response                                                      #
# ------------------------------------------------------------------ #


def test__should_generate_range_response_per_spec() -> None:
    # Per spec: R = yyyyy * c * 3.125e-5
    # At c=1500 m/s, 150 m → travel_time = 0.1 s → ts = round(0.1 / 3.125e-5) = 3200
    response = range_response("002", distance=150.0, sound_speed=1500.0)
    assert response == b"#R002T03200\r\n"


def test__should_encode_timestamp_with_5_digits() -> None:
    response = range_response("001", distance=1.0, sound_speed=1500.0)
    # Format must be #RxxxTyyyyy (5-digit timestamp)
    assert b"T" in response
    ts_part = response.split(b"T")[1].rstrip(b"\r\n")
    assert len(ts_part) == 5


def test__should_roundtrip_range_via_timestamp() -> None:
    # Encode a distance as timestamp, then decode it — should match within ranging increment
    # User guide: ranging increment = 4.7 cm at c=1500 m/s
    sound_speed = 1500.0
    distance_in = 100.0
    response = range_response("002", distance=distance_in, sound_speed=sound_speed)
    ts_str = response.decode("ascii").split("T")[1].rstrip("\r\n")
    timestamp = int(ts_str)
    distance_out = timestamp * sound_speed * 3.125e-5
    assert abs(distance_out - distance_in) < 0.1  # within 10 cm


def test__should_use_default_sound_speed() -> None:
    r1 = range_response("002", distance=100.0)
    r2 = range_response("002", distance=100.0, sound_speed=1500.0)
    assert r1 == r2


# ------------------------------------------------------------------ #
#  Distance calculation                                                #
# ------------------------------------------------------------------ #


def test__should_return_zero_for_same_position() -> None:
    pos = (59.310153, 17.975189, 0.0)
    assert distance_metres(pos, pos) == 0.0


def test__should_return_positive_distance() -> None:
    a = (59.310153, 17.975189, 0.0)
    b = (59.310500, 17.974500, 0.0)
    assert distance_metres(a, b) > 0


def test__should_include_depth_in_distance() -> None:
    a = (59.310153, 17.975189, 0.0)
    b = (59.310153, 17.975189, 10.0)  # same lat/lon, 10m deeper
    d = distance_metres(a, b)
    assert abs(d - 10.0) < 0.01


def test__should_be_symmetric() -> None:
    a = (59.310153, 17.975189, 0.0)
    b = (59.310500, 17.974500, 5.0)
    assert distance_metres(a, b) == pytest.approx(distance_metres(b, a))
