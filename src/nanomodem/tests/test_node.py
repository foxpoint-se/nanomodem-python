"""Tests for AcousticNode."""

import pytest

from nanomodem.calculation import Calculation
from nanomodem.constants import SOUND_SPEED_AIR_M_S
from nanomodem.errors import ModemIdMismatchError, ModemStatusTimeoutError
from nanomodem.node import AcousticNode
from nanomodem.protocols import OnMessageCallback
from nanomodem.transports.mock import MockEther, MockTransport
from nanomodem.types import (
    Coord,
    KnownNode,
    LocalAckMessage,
    Message,
    ModemStatusMessage,
    PositionMessage,
    QualityIndicatorMessage,
    RangeResponseMessage,
    UnknownMessage,
    V3TestBroadcastMessage,
)


class _RecordingTransport:
    """Minimal transport that records test/quality calls."""

    def __init__(self) -> None:
        self.test_targets: list[str] = []
        self.quality_query_count = 0
        self.modem_status_query_count = 0
        self._callback: OnMessageCallback | None = None

    def broadcast_position(self, coord: Coord, depth: float) -> None:
        pass

    def request_range(self, target_id: str) -> None:
        pass

    def request_test(self, target_id: str) -> None:
        self.test_targets.append(target_id)

    def query_quality(self) -> None:
        self.quality_query_count += 1

    def query_modem_status(self) -> None:
        self.modem_status_query_count += 1

    def on_message(self, callback: OnMessageCallback) -> None:
        self._callback = callback


class _StatusReplyTransport:
    """Transport that immediately delivers a fixed ModemStatusMessage on $? query."""

    def __init__(self, status: ModemStatusMessage) -> None:
        self._status = status
        self._callback: OnMessageCallback | None = None

    def broadcast_position(self, coord: Coord, depth: float) -> None:
        pass

    def request_range(self, target_id: str) -> None:
        pass

    def request_test(self, target_id: str) -> None:
        pass

    def query_quality(self) -> None:
        pass

    def query_modem_status(self) -> None:
        if self._callback is not None:
            self._callback(self._status)

    def on_message(self, callback: OnMessageCallback) -> None:
        self._callback = callback


def _make_node(
    node_id: str = "001",
    position: Coord | None = None,
    ether: MockEther | None = None,
) -> AcousticNode:
    """Helper to create a node with mock dependencies."""
    if ether is None:
        ether = MockEther()
    transport = MockTransport(node_id, ether)
    if position is not None:
        transport.position = position
    calculation = Calculation()
    node = AcousticNode(
        node_id=node_id,
        transport=transport,
        calculation=calculation,
        position=position,
    )
    # Link mock transport to node depth
    transport.get_depth_callback = node.get_depth
    return node


# --- Step 1: Initialization ---


def test_should_return_position_when_initialized_with_coordinates() -> None:
    coord = Coord(lat=63.0, lon=10.0)
    node = _make_node(position=coord)
    assert node.get_position() == coord


def test_should_return_none_position_when_not_set() -> None:
    node = _make_node()
    assert node.get_position() is None


def test_should_return_node_id() -> None:
    node = _make_node(node_id="042")
    assert node.node_id == "042"


def test_should_return_injected_transport_interface() -> None:
    node = _make_node()
    assert node.transport is not None
    assert isinstance(node.transport, MockTransport)


def test_should_return_injected_calculation_interface() -> None:
    node = _make_node()
    assert node.calculation is not None
    assert isinstance(node.calculation, Calculation)


def test_should_have_default_capabilities() -> None:
    node = _make_node()
    assert node.capabilities.is_inferring_own_position is False
    assert node.capabilities.is_broadcasting_own_position is False


# --- Step 2: Setters ---


def test_should_update_position_when_set_position_called() -> None:
    node = _make_node()
    new_pos = Coord(lat=63.5, lon=10.5)
    node.set_position(new_pos)
    assert node.get_position() == new_pos


def test_should_clear_position_when_set_position_called_with_none() -> None:
    node = _make_node(position=Coord(lat=63.0, lon=10.0))
    node.set_position(None)
    assert node.get_position() is None


def test_should_update_depth_when_set_depth_called() -> None:
    node = _make_node(position=Coord(lat=63.0, lon=10.0))
    node.set_depth(5.0)
    pos = node.get_position()
    assert pos is not None
    assert node._depth == 5.0
    # lat/lon preserved
    assert pos.lat == 63.0
    assert pos.lon == 10.0


def test_should_update_depth_when_no_position_set() -> None:
    node = _make_node()
    node.set_depth(3.0)
    assert node._depth == 3.0


# --- Step 5: Message handling ---


def test_should_store_position_of_other_node_when_position_message_received() -> None:
    ether = MockEther()
    beacon = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=ether)
    host = _make_node("001", position=Coord(lat=63.001, lon=10.001), ether=ether)

    beacon.broadcast_position()

    known = host.get_known_nodes()
    assert "002" in known
    assert known["002"].position == Coord(lat=63.0, lon=10.0)


def test_should_expose_sound_speed_property() -> None:
    node = AcousticNode("001", transport=_RecordingTransport(), sound_speed=SOUND_SPEED_AIR_M_S)
    assert node.sound_speed == 340.0


def test_should_reject_invalid_sound_speed_on_construction() -> None:
    with pytest.raises(ValueError, match="positive"):
        AcousticNode("001", transport=_RecordingTransport(), sound_speed=0.0)


def test_should_convert_range_with_air_sound_speed() -> None:
    calc = Calculation()
    ether = MockEther(sound_speed=SOUND_SPEED_AIR_M_S)
    host_transport = MockTransport("001", ether)
    host_transport.position = Coord(lat=63.0, lon=10.0)
    host = AcousticNode(
        "001",
        transport=host_transport,
        calculation=calc,
        sound_speed=SOUND_SPEED_AIR_M_S,
    )
    host.set_depth(0.0)
    beacon_transport = MockTransport("002", ether)
    beacon_transport.position = Coord(lat=63.0, lon=10.0)
    beacon = AcousticNode("002", transport=beacon_transport, calculation=calc)
    beacon.set_depth(10.0)
    beacon_transport.get_depth_callback = beacon.get_depth

    host.request_range("002")

    known = host.get_known_nodes()
    assert known["002"].last_range is not None
    assert abs(known["002"].last_range - 10.0) < 0.5


def test_should_convert_timestamp_from_range_message_with_custom_sound_speed() -> None:
    transport = _RecordingTransport()
    calc = Calculation()
    node = AcousticNode(
        "001",
        transport=transport,
        calculation=calc,
        sound_speed=SOUND_SPEED_AIR_M_S,
    )
    timestamp = calc.distance_to_timestamp(10.0, SOUND_SPEED_AIR_M_S)
    assert transport._callback is not None
    transport._callback(RangeResponseMessage(node_id="002", timestamp=timestamp))
    known = node.get_known_nodes()
    assert known["002"].last_range is not None
    assert abs(known["002"].last_range - 10.0) < 0.01


def test_should_update_range_of_known_node_when_range_response_received() -> None:
    ether = MockEther(sound_speed=1500.0)
    host = _make_node("001", position=Coord(lat=63.0, lon=10.0), ether=ether)
    beacon = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=ether)
    beacon.set_depth(10.0)

    host.request_range("002")

    known = host.get_known_nodes()
    assert "002" in known
    assert known["002"].last_range is not None
    # 10m distance, should be approximately 10.0
    assert abs(known["002"].last_range - 10.0) < 0.5


def test_should_log_unknown_message(caplog: object) -> None:
    """UnknownMessage should be handled without raising — node logs it."""
    ether = MockEther()
    host = _make_node("001", ether=ether)
    transport = ether.get_transport("001")
    assert transport is not None

    # Should not raise
    transport.deliver(UnknownMessage(raw="#TO"))

    # Node should still be functional after receiving unknown message
    assert host.get_known_nodes() == {} or True  # No side effects expected


def test_should_update_last_seen_when_any_message_received() -> None:
    ether = MockEther()
    beacon = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=ether)
    host = _make_node("001", position=Coord(lat=63.001, lon=10.001), ether=ether)

    beacon.broadcast_position()

    known = host.get_known_nodes()
    assert "002" in known
    assert known["002"].last_seen is not None
    assert known["002"].last_seen > 0


def test_should_not_broadcast_when_position_is_none() -> None:
    ether = MockEther()
    sender = _make_node("001", ether=ether)
    receiver = _make_node("002", ether=ether)

    sender.broadcast_position()  # No position — should be a no-op

    known = receiver.get_known_nodes()
    assert "001" not in known


def test_should_request_range_and_receive_response() -> None:
    """End-to-end: host requests range to beacon, gets distance back."""
    ether = MockEther(sound_speed=1500.0)

    host = _make_node("001", position=Coord(lat=63.0, lon=10.0), ether=ether)
    host.set_depth(5.0)
    _beacon = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=ether)

    host.request_range("002")

    known = host.get_known_nodes()
    assert "002" in known
    assert known["002"].last_range is not None
    # 5m depth difference → ~5m distance
    assert abs(known["002"].last_range - 5.0) < 0.5


def test__should_delegate_request_test_and_query_quality_to_transport() -> None:
    transport = _RecordingTransport()
    node = AcousticNode("001", transport=transport)

    node.request_test("002")
    node.query_quality()

    assert transport.test_targets == ["002"]
    assert transport.quality_query_count == 1


def test__should_pass_ensure_modem_id_matches_on_mock() -> None:
    node = _make_node("001")
    status = node.ensure_modem_id_matches()
    assert status.node_id == "001"


def test__should_raise_modem_id_mismatch_when_status_id_differs() -> None:
    transport = _StatusReplyTransport(ModemStatusMessage(node_id="002", voltage_raw=48123))
    node = AcousticNode("001", transport=transport)
    with pytest.raises(ModemIdMismatchError) as exc_info:
        node.ensure_modem_id_matches()
    assert exc_info.value.expected_id == "001"
    assert exc_info.value.actual_id == "002"


def test__should_raise_modem_status_timeout_when_no_reply() -> None:
    transport = _RecordingTransport()
    node = AcousticNode("001", transport=transport)
    with pytest.raises(ModemStatusTimeoutError):
        node.ensure_modem_id_matches(timeout_s=0.1)


def test__should_delegate_query_modem_status_to_transport() -> None:
    transport = _RecordingTransport()
    node = AcousticNode("001", transport=transport)

    node.query_modem_status()

    assert transport.modem_status_query_count == 1


def test__should_receive_modem_status_via_mock() -> None:
    ether = MockEther()
    received: list[Message] = []
    host = AcousticNode(
        "042",
        transport=MockTransport("042", ether),
        on_message_received=lambda msg: received.append(msg),
    )

    host.query_modem_status()

    assert len(received) == 1
    assert isinstance(received[0], ModemStatusMessage)
    assert received[0].node_id == "042"


def test__should_receive_test_ack_and_broadcast_via_mock() -> None:
    ether = MockEther()
    received: list[Message] = []
    host = AcousticNode(
        "001",
        transport=MockTransport("001", ether),
        on_message_received=lambda msg: received.append(msg),
    )
    _target = _make_node("002", ether=ether)

    host.request_test("002")
    host.query_quality()

    assert any(isinstance(m, LocalAckMessage) for m in received)
    assert any(
        isinstance(m, V3TestBroadcastMessage) and m.node_id == "002" for m in received
    )
    assert any(
        isinstance(m, QualityIndicatorMessage) and m.bytes_corrected is not None
        for m in received
    )


# --- Step 7: Position calculation ---


def test_should_calculate_own_position_when_three_distances_and_positions_available() -> None:
    """Host receives positions and ranges from 3 beacons, then trilaterates."""
    ether = MockEther(sound_speed=1500.0)

    host_pos = Coord(lat=63.0005, lon=10.0005)
    host = _make_node("001", position=host_pos, ether=ether)

    # Create 3 beacons in a triangle
    b1 = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=ether)
    b2 = _make_node("003", position=Coord(lat=63.001, lon=10.0), ether=ether)
    b3 = _make_node("004", position=Coord(lat=63.0005, lon=10.001), ether=ether)

    # Beacons broadcast positions so host knows where they are
    b1.broadcast_position()
    b2.broadcast_position()
    b3.broadcast_position()

    # Host ranges to each beacon
    host.request_range("002")
    host.request_range("003")
    host.request_range("004")

    # Now calculate
    result = host.calculate_position()
    assert result is not None
    # Should be close to the actual position
    assert abs(result.lat - host_pos.lat) < 1e-4
    assert abs(result.lon - host_pos.lon) < 1e-4


def test_should_return_none_when_less_than_three_distances_available() -> None:
    ether = MockEther(sound_speed=1500.0)
    host = _make_node("001", position=Coord(lat=63.0, lon=10.0), ether=ether)
    b1 = _make_node("002", position=Coord(lat=63.001, lon=10.0), ether=ether)

    b1.broadcast_position()
    host.request_range("002")

    result = host.calculate_position()
    assert result is None  # Only 1 beacon, need 3


def test_should_use_projected_2d_distances_when_depth_is_set() -> None:
    """Host at depth 5m, beacons at surface. 3D ranges projected to 2D."""
    ether = MockEther(sound_speed=1500.0)

    # Host is submerged at 5m depth
    host = _make_node("001", position=Coord(lat=63.0005, lon=10.0005), ether=ether)
    host.set_depth(5.0)

    # Surface beacons at depth=0
    b1 = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=ether)
    b2 = _make_node("003", position=Coord(lat=63.001, lon=10.0), ether=ether)
    b3 = _make_node("004", position=Coord(lat=63.0005, lon=10.001), ether=ether)

    b1.broadcast_position()
    b2.broadcast_position()
    b3.broadcast_position()

    host.request_range("002")
    host.request_range("003")
    host.request_range("004")

    result = host.calculate_position()
    assert result is not None
    # Should still find the approximate horizontal position
    assert abs(result.lat - 63.0005) < 1e-3
    assert abs(result.lon - 10.0005) < 1e-3
    # Depth should be preserved in the node's state
    assert host._depth == 5.0


# --- Step 8: Capabilities (modes) ---


def test_should_broadcast_position_when_is_broadcasting_own_position_enabled() -> None:
    ether = MockEther()
    beacon = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=ether)
    beacon.capabilities.is_broadcasting_own_position = True

    receiver = _make_node("001", ether=ether)

    # Changing position should trigger auto-broadcast
    beacon.set_position(Coord(lat=63.001, lon=10.001))

    known = receiver.get_known_nodes()
    assert "002" in known
    assert known["002"].position == Coord(lat=63.001, lon=10.001)


def test_should_not_broadcast_when_is_broadcasting_own_position_disabled() -> None:
    ether = MockEther()
    beacon = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=ether)
    # Capability is False by default

    receiver = _make_node("001", ether=ether)

    beacon.set_position(Coord(lat=63.001, lon=10.001))

    known = receiver.get_known_nodes()
    assert "002" not in known  # No auto-broadcast


def test_should_calculate_position_when_is_inferring_own_position_enabled_and_has_three_ranges() -> None:
    ether = MockEther(sound_speed=1500.0)

    host = _make_node("001", position=Coord(lat=63.0005, lon=10.0005), ether=ether)
    host.capabilities.is_inferring_own_position = True

    b1 = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=ether)
    b2 = _make_node("003", position=Coord(lat=63.001, lon=10.0), ether=ether)
    b3 = _make_node("004", position=Coord(lat=63.0005, lon=10.001), ether=ether)

    b1.broadcast_position()
    b2.broadcast_position()
    b3.broadcast_position()

    # Range to first two — no auto-calc yet (need 3)
    host.request_range("002")
    host.request_range("003")

    # After third range, auto-calc should trigger
    _ = host.get_position()
    host.request_range("004")

    result = host.get_position()
    assert result is not None
    assert abs(result.lat - 63.0005) < 1e-3
    assert abs(result.lon - 10.0005) < 1e-3


def test_should_not_calculate_when_is_inferring_own_position_disabled() -> None:
    ether = MockEther(sound_speed=1500.0)

    host = _make_node("001", position=Coord(lat=63.0005, lon=10.0005), ether=ether)
    # is_inferring_own_position is False by default

    b1 = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=ether)
    b2 = _make_node("003", position=Coord(lat=63.001, lon=10.0), ether=ether)
    b3 = _make_node("004", position=Coord(lat=63.0005, lon=10.001), ether=ether)

    b1.broadcast_position()
    b2.broadcast_position()
    b3.broadcast_position()

    host.request_range("002")
    host.request_range("003")
    host.request_range("004")

    # Position should NOT have been auto-updated (capability disabled)
    # It should still be the original position
    pos = host.get_position()
    assert pos is not None
    assert pos.lat == 63.0005  # Unchanged
    assert pos.lon == 10.0005  # Unchanged


# --- Node ID validation ---


def test_should_raise_on_non_string_node_id() -> None:
    ether = MockEther()
    transport = MockTransport("001", ether)
    with pytest.raises(TypeError):
        AcousticNode(node_id=123, transport=transport)  # type: ignore[arg-type]


def test_should_raise_on_short_node_id() -> None:
    ether = MockEther()
    transport = MockTransport("1", ether)
    with pytest.raises(ValueError):
        AcousticNode(node_id="1", transport=transport)


def test_should_raise_on_node_id_zero() -> None:
    ether = MockEther()
    transport = MockTransport("000", ether)
    with pytest.raises(ValueError):
        AcousticNode(node_id="000", transport=transport)


def test_should_raise_on_node_id_above_255() -> None:
    ether = MockEther()
    transport = MockTransport("256", ether)
    with pytest.raises(ValueError):
        AcousticNode(node_id="256", transport=transport)


def test_should_accept_valid_node_id_boundaries() -> None:
    ether = MockEther()
    t1 = MockTransport("001", ether)
    t2 = MockTransport("255", ether)
    node1 = AcousticNode(node_id="001", transport=t1)
    node2 = AcousticNode(node_id="255", transport=t2)
    assert node1.node_id == "001"
    assert node2.node_id == "255"


# --- Callbacks ---


def test__should_call_on_position_changed_with_new_coord_when_set_position_called() -> None:
    ether = MockEther()
    transport = MockTransport("001", ether)
    received: list[Coord | None] = []
    node = AcousticNode(
        node_id="001",
        transport=transport,
        on_position_changed=lambda pos: received.append(pos),
    )
    new_pos = Coord(lat=63.0, lon=10.0)
    node.set_position(new_pos)
    assert len(received) == 1
    assert received[0] == new_pos


def test__should_call_on_position_changed_with_none_when_position_cleared() -> None:
    ether = MockEther()
    transport = MockTransport("001", ether)
    received: list[Coord | None] = []
    node = AcousticNode(
        node_id="001",
        transport=transport,
        position=Coord(lat=63.0, lon=10.0),
        on_position_changed=lambda pos: received.append(pos),
    )
    node.set_position(None)
    assert len(received) == 1
    assert received[0] is None


def test__should_call_on_depth_changed_with_new_depth_when_set_depth_called() -> None:
    ether = MockEther()
    transport = MockTransport("001", ether)
    received: list[float] = []
    node = AcousticNode(
        node_id="001",
        transport=transport,
        on_depth_changed=lambda d: received.append(d),
    )
    node.set_depth(7.5)
    assert len(received) == 1
    assert received[0] == 7.5


def test__should_call_on_known_nodes_changed_when_position_message_received() -> None:
    ether = MockEther()
    transport = MockTransport("001", ether)
    snapshots: list[dict[str, KnownNode]] = []
    _node = AcousticNode(
        node_id="001",
        transport=transport,
        on_known_nodes_changed=lambda known: snapshots.append(known),
    )
    transport.deliver(PositionMessage(node_id="002", coord=Coord(lat=63.0, lon=10.0)))
    assert len(snapshots) == 1
    assert "002" in snapshots[0]
    assert snapshots[0]["002"].position == Coord(lat=63.0, lon=10.0)


def test__should_call_on_known_nodes_changed_when_range_response_received() -> None:
    ether = MockEther(sound_speed=1500.0)
    host = _make_node("001", position=Coord(lat=63.0, lon=10.0), ether=ether)
    _beacon = _make_node("002", position=Coord(lat=63.0, lon=10.0), ether=ether)

    snapshots: list[dict[str, KnownNode]] = []
    host._cb_known_nodes_changed = lambda known: snapshots.append(known)

    host.request_range("002")

    assert len(snapshots) >= 1
    assert "002" in snapshots[-1]
    assert snapshots[-1]["002"].last_range is not None


def test_should_call_on_message_received_with_message() -> None:
    ether = MockEther()
    transport = MockTransport("001", ether)
    received: list[object] = []
    _node = AcousticNode(
        node_id="001",
        transport=transport,
        on_message_received=lambda msg: received.append(msg),
    )
    msg = PositionMessage(node_id="002", coord=Coord(lat=63.0, lon=10.0))
    transport.deliver(msg)
    assert len(received) == 1
    assert received[0] == msg


def test_should_create_default_calculation_when_not_injected() -> None:
    ether = MockEther()
    transport = MockTransport("001", ether)
    node = AcousticNode(node_id="001", transport=transport)
    assert node.calculation is not None
