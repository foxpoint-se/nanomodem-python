"""Tests for PositioningNode."""

from __future__ import annotations

from nanomodem.core.modem_node import ModemNode
from nanomodem.core.transports.in_memory import InMemoryBus, InMemoryTransport
from nanomodem.positioning.basic_position_codec import BasicPositionCodec
from nanomodem.positioning.calculation import Calculation
from nanomodem.positioning.positioning_node import PositioningNode
from nanomodem.types import Coord, PositionMessage


def _make_node(
    node_id: str = "001",
    position: Coord | None = None,
    ether: InMemoryBus | None = None,
) -> PositioningNode:
    bus = ether or InMemoryBus(sound_speed=1500.0)
    transport = InMemoryTransport(node_id, bus)
    modem = ModemNode(node_id, transport, BasicPositionCodec())
    node = PositioningNode(
        node_id=node_id,
        modem_node=modem,
        calculation=Calculation(),
        position=position,
        sound_speed=1500.0,
    )
    transport.position = position
    transport.get_depth_callback = node.get_depth
    return node


def test__should_update_known_node_on_position_broadcast() -> None:
    bus = InMemoryBus(sound_speed=1500.0)
    beacon = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=bus)
    host = _make_node("001", position=Coord(lat=63.001, lon=10.001), ether=bus)

    beacon.broadcast_position()

    known = host.get_known_nodes()
    assert "002" in known
    assert known["002"].position == Coord(lat=63.0, lon=10.0)


def test__should_use_wire_sender_id_when_payload_node_id_mismatches() -> None:
    host = _make_node("001")
    host._handle_position_broadcast(
        "002",
        PositionMessage(node_id="999", coord=Coord(lat=63.0, lon=10.0), depth=1.5),
    )

    known = host.get_known_nodes()
    assert "002" in known
    assert "999" not in known
    assert known["002"].position == Coord(lat=63.0, lon=10.0)
    assert known["002"].depth == 1.5


def test__should_calculate_range_on_roundtrip_response() -> None:
    bus = InMemoryBus(sound_speed=1500.0)
    host = _make_node("001", position=Coord(lat=63.0, lon=10.0), ether=bus)
    beacon = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=bus)
    beacon.set_depth(10.0)

    host.request_range("002")

    known = host.get_known_nodes()
    assert "002" in known
    assert known["002"].last_range is not None
    assert abs(known["002"].last_range - 10.0) < 0.5


def test__should_trilaterate_position_with_three_beacons() -> None:
    bus = InMemoryBus(sound_speed=1500.0)
    host_pos = Coord(lat=63.0005, lon=10.0005)
    host = _make_node("001", position=host_pos, ether=bus)

    b1 = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=bus)
    b2 = _make_node("003", position=Coord(lat=63.001, lon=10.0), ether=bus)
    b3 = _make_node("004", position=Coord(lat=63.0005, lon=10.001), ether=bus)

    b1.broadcast_position()
    b2.broadcast_position()
    b3.broadcast_position()

    host.request_range("002")
    host.request_range("003")
    host.request_range("004")

    result = host.calculate_position()
    assert result is not None
    assert abs(result.lat - host_pos.lat) < 1e-4
    assert abs(result.lon - host_pos.lon) < 1e-4


def test__should_auto_broadcast_when_enabled() -> None:
    bus = InMemoryBus(sound_speed=1500.0)
    beacon = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=bus)
    beacon.capabilities.is_broadcasting_own_position = True
    receiver = _make_node("001", ether=bus)

    beacon.set_position(Coord(lat=63.001, lon=10.001))

    known = receiver.get_known_nodes()
    assert "002" in known
    assert known["002"].position == Coord(lat=63.001, lon=10.001)


def test__should_auto_infer_when_enabled() -> None:
    bus = InMemoryBus(sound_speed=1500.0)
    host = _make_node("001", position=Coord(lat=63.0005, lon=10.0005), ether=bus)
    host.capabilities.is_inferring_own_position = True

    b1 = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=bus)
    b2 = _make_node("003", position=Coord(lat=63.001, lon=10.0), ether=bus)
    b3 = _make_node("004", position=Coord(lat=63.0005, lon=10.001), ether=bus)

    b1.broadcast_position()
    b2.broadcast_position()
    b3.broadcast_position()

    host.request_range("002")
    host.request_range("003")
    host.request_range("004")

    result = host.get_position()
    assert result is not None
    assert abs(result.lat - 63.0005) < 1e-3
    assert abs(result.lon - 10.0005) < 1e-3
