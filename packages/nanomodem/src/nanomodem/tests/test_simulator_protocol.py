"""Tests for simulator JSON protocol dispatch."""

from __future__ import annotations

import base64

from nanomodem.simulator_protocol import (
    SimulatorInboundHandlers,
    dispatch_simulator_inbound,
    parse_gps_update,
)
from nanomodem.types import Coord


def test__should_parse_gps_update_from_json_object() -> None:
    coord = parse_gps_update({"type": "gps_update", "lat": 59.31, "lon": 17.98})
    assert coord == Coord(lat=59.31, lon=17.98)


def test__should_invoke_gps_handler_when_message_is_gps_update() -> None:
    received: list[Coord] = []
    handlers = SimulatorInboundHandlers(on_gps_update=received.append)
    dispatch_simulator_inbound({"type": "gps_update", "lat": 1.0, "lon": 2.0}, handlers)
    assert len(received) == 1
    assert received[0].lat == 1.0


def test__should_invoke_acoustic_handler_when_message_is_acoustic() -> None:
    payload = b"#B00232P002"
    encoded = base64.b64encode(payload).decode("ascii")
    received: list[bytes] = []
    handlers = SimulatorInboundHandlers(on_acoustic_data=received.append)
    dispatch_simulator_inbound({"type": "acoustic_message", "data": encoded}, handlers)
    assert received == [payload]


def test__should_ignore_gps_when_no_handler_registered() -> None:
    dispatch_simulator_inbound({"type": "gps_update", "lat": 1.0, "lon": 2.0}, SimulatorInboundHandlers())
