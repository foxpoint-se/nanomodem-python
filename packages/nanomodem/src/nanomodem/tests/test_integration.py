"""Integration test: full localization cycle with in-memory transport."""

from nanomodem.core.modem_node import ModemNode
from nanomodem.core.transports import InMemoryBus, InMemoryTransport
from nanomodem.positioning import BasicPositionCodec, PositioningNode
from nanomodem.types import Coord


def _make_node(
    node_id: str,
    position: Coord,
    bus: InMemoryBus,
) -> PositioningNode:
    transport = InMemoryTransport(node_id, bus)
    modem = ModemNode(node_id, transport, BasicPositionCodec())
    node = PositioningNode(node_id, modem, position=position, sound_speed=1500.0)
    transport.position = position
    transport.get_depth_callback = node.get_depth
    return node


def _make_beacon(
    node_id: str,
    position: Coord,
    bus: InMemoryBus,
) -> PositioningNode:
    node = _make_node(node_id, position, bus)
    node.capabilities.is_broadcasting_own_position = True
    return node


def _make_host(
    node_id: str,
    position: Coord,
    bus: InMemoryBus,
) -> PositioningNode:
    node = _make_node(node_id, position, bus)
    node.capabilities.is_inferring_own_position = True
    return node


def test_submerged_node_localizes_from_three_surface_beacons() -> None:
    bus = InMemoryBus(sound_speed=1500.0)

    b1 = _make_beacon("002", Coord(lat=63.0, lon=10.0), bus)
    b2 = _make_beacon("003", Coord(lat=63.001, lon=10.0), bus)
    b3 = _make_beacon("004", Coord(lat=63.0005, lon=10.001), bus)

    actual_pos = Coord(lat=63.0004, lon=10.0003)
    host = _make_host("001", actual_pos, bus)
    host.set_depth(5.0)

    b1.broadcast_position()
    b2.broadcast_position()
    b3.broadcast_position()

    known = host.get_known_nodes()
    assert "002" in known and known["002"].position is not None
    assert "003" in known and known["003"].position is not None
    assert "004" in known and known["004"].position is not None

    host.request_range("002")
    host.request_range("003")
    host.request_range("004")

    result = host.get_position()
    assert result is not None

    lat_error_m = abs(result.lat - actual_pos.lat) * 111320.0
    lon_error_m = abs(result.lon - actual_pos.lon) * 111320.0 * 0.454

    assert lat_error_m < 5.0, f"Latitude error too large: {lat_error_m:.1f}m"
    assert lon_error_m < 5.0, f"Longitude error too large: {lon_error_m:.1f}m"
    assert host.get_depth() == 5.0


def test_host_without_enough_beacons_cannot_localize() -> None:
    bus = InMemoryBus(sound_speed=1500.0)

    b1 = _make_beacon("002", Coord(lat=63.0, lon=10.0), bus)
    b2 = _make_beacon("003", Coord(lat=63.001, lon=10.0), bus)

    host = _make_host("001", Coord(lat=63.0005, lon=10.0005), bus)

    b1.broadcast_position()
    b2.broadcast_position()

    host.request_range("002")
    host.request_range("003")

    pos = host.get_position()
    assert pos is not None
    assert pos.lat == 63.0005


def test_beacon_auto_broadcasts_on_position_change() -> None:
    bus = InMemoryBus()

    beacon = _make_beacon("002", Coord(lat=63.0, lon=10.0), bus)
    host = _make_host("001", Coord(lat=63.0005, lon=10.0005), bus)

    beacon.broadcast_position()
    assert host.get_known_nodes()["002"].position == Coord(lat=63.0, lon=10.0)

    beacon.set_position(Coord(lat=63.002, lon=10.002))
    assert host.get_known_nodes()["002"].position == Coord(lat=63.002, lon=10.002)
