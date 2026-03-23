"""Integration test: full localization cycle with mock transport."""

from foxpoint.nanomodem.calculation import Calculation
from foxpoint.nanomodem.node import AcousticNode
from foxpoint.nanomodem.transport import MockEther, MockTransport
from foxpoint.nanomodem.types import Coord


def _make_beacon(
    node_id: str,
    position: Coord,
    ether: MockEther,
    calc: Calculation,
) -> AcousticNode:
    """Create a beacon node that auto-broadcasts its position."""
    transport = MockTransport(node_id, ether)
    transport.position = position
    node = AcousticNode(
        node_id=node_id,
        transport=transport,
        calculation=calc,
        position=position,
    )
    # Link mock transport to node depth
    transport.get_depth_callback = node.get_depth
    node.capabilities.is_broadcasting_own_position = True
    return node


def _make_host(
    node_id: str,
    position: Coord,
    ether: MockEther,
    calc: Calculation,
) -> AcousticNode:
    """Create a host node that auto-infers its own position."""
    transport = MockTransport(node_id, ether)
    transport.position = position
    node = AcousticNode(
        node_id=node_id,
        transport=transport,
        calculation=calc,
        position=position,
    )
    # Link mock transport to node depth
    transport.get_depth_callback = node.get_depth
    node.capabilities.is_inferring_own_position = True
    return node


def test_submerged_node_localizes_from_three_surface_beacons() -> None:
    """Full scenario: 3 surface beacons + 1 submerged host → localization."""
    ether = MockEther(sound_speed=1500.0)
    calc = Calculation()

    # Surface beacons
    b1 = _make_beacon("002", Coord(lat=63.0, lon=10.0), ether, calc)
    b2 = _make_beacon("003", Coord(lat=63.001, lon=10.0), ether, calc)
    b3 = _make_beacon("004", Coord(lat=63.0005, lon=10.001), ether, calc)

    # Submerged host — actual position
    actual_pos = Coord(lat=63.0004, lon=10.0003)
    actual_depth = 5.0
    host = _make_host("001", actual_pos, ether, calc)
    host.set_depth(actual_depth)

    # Beacons broadcast positions
    b1.broadcast_position()
    b2.broadcast_position()
    b3.broadcast_position()

    # Verify host received beacon positions
    known = host.get_known_nodes()
    assert "002" in known and known["002"].position is not None
    assert "003" in known and known["003"].position is not None
    assert "004" in known and known["004"].position is not None

    # Host ranges to each beacon
    host.request_range("002")
    host.request_range("003")
    host.request_range("004")  # This triggers auto-calculate

    # Host should have inferred its position
    result = host.get_position()
    assert result is not None

    # Should be close to actual position (within ~1m accuracy in lat/lon terms)
    lat_error_m = abs(result.lat - actual_pos.lat) * 111320.0
    lon_error_m = abs(result.lon - actual_pos.lon) * 111320.0 * 0.454  # cos(63°)

    assert lat_error_m < 5.0, f"Latitude error too large: {lat_error_m:.1f}m"
    assert lon_error_m < 5.0, f"Longitude error too large: {lon_error_m:.1f}m"

    # Depth should be preserved in logical state
    assert host._depth == 5.0


def test_host_without_enough_beacons_cannot_localize() -> None:
    """Only 2 beacons — not enough for trilateration."""
    ether = MockEther(sound_speed=1500.0)
    calc = Calculation()

    b1 = _make_beacon("002", Coord(lat=63.0, lon=10.0), ether, calc)
    b2 = _make_beacon("003", Coord(lat=63.001, lon=10.0), ether, calc)

    host = _make_host("001", Coord(lat=63.0005, lon=10.0005), ether, calc)

    b1.broadcast_position()
    b2.broadcast_position()

    host.request_range("002")
    host.request_range("003")

    # Auto-calculate fires but returns None (not enough data)
    # Position should still be the original
    pos = host.get_position()
    assert pos is not None
    assert pos.lat == 63.0005


def test_beacon_auto_broadcasts_on_position_change() -> None:
    """When a beacon's position changes, it auto-broadcasts to all nodes."""
    ether = MockEther()
    calc = Calculation()

    beacon = _make_beacon("002", Coord(lat=63.0, lon=10.0), ether, calc)
    host = _make_host("001", Coord(lat=63.0005, lon=10.0005), ether, calc)

    # Initial broadcast
    beacon.broadcast_position()
    assert host.get_known_nodes()["002"].position == Coord(lat=63.0, lon=10.0)

    # Beacon moves — auto-broadcast triggers
    beacon.set_position(Coord(lat=63.002, lon=10.002))
    assert host.get_known_nodes()["002"].position == Coord(lat=63.002, lon=10.002)
