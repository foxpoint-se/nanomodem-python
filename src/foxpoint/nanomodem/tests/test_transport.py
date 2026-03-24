"""Tests for MockTransport + MockEther."""

from foxpoint.nanomodem.transport import MockEther, MockTransport
from foxpoint.nanomodem.types import (
    Coord,
    Message,
    PositionMessage,
    RangeResponseMessage,
    UnknownMessage,
)


def _collect_messages(transport: MockTransport) -> list[Message]:
    """Register a callback that collects messages into a list."""
    received: list[Message] = []
    transport.on_message(lambda msg: received.append(msg))
    return received


# --- Broadcasting ---


def test_should_deliver_broadcast_to_all_registered_nodes() -> None:
    ether = MockEther()
    sender = MockTransport("001", ether)
    receiver_a = MockTransport("002", ether)
    receiver_b = MockTransport("003", ether)

    msgs_a = _collect_messages(receiver_a)
    msgs_b = _collect_messages(receiver_b)

    sender.broadcast_position(Coord(lat=63.0, lon=10.0), depth=0.0)

    assert len(msgs_a) == 1
    assert len(msgs_b) == 1
    assert isinstance(msgs_a[0], PositionMessage)
    assert msgs_a[0].node_id == "001"


def test_should_not_deliver_broadcast_to_sender() -> None:
    ether = MockEther()
    sender = MockTransport("001", ether)
    _other = MockTransport("002", ether)

    sender_msgs = _collect_messages(sender)
    sender.broadcast_position(Coord(lat=63.0, lon=10.0), depth=0.0)

    assert len(sender_msgs) == 0


# --- Ranging ---


def test_should_deliver_range_response_when_target_is_reachable() -> None:
    ether = MockEther(sound_speed=1500.0)
    sender = MockTransport("001", ether)
    sender.position = Coord(lat=63.0, lon=10.0)
    target = MockTransport("002", ether)
    target.position = Coord(lat=63.0, lon=10.0)

    msgs = _collect_messages(sender)
    sender.request_range("002")

    assert len(msgs) == 1
    assert isinstance(msgs[0], RangeResponseMessage)
    assert msgs[0].node_id == "002"


def test_should_deliver_unknown_message_when_target_is_unreachable() -> None:
    ether = MockEther()
    sender = MockTransport("001", ether)
    sender.position = Coord(lat=63.0, lon=10.0)

    msgs = _collect_messages(sender)
    sender.request_range("999")  # No such node

    assert len(msgs) == 1
    assert isinstance(msgs[0], UnknownMessage)
    assert "#TO" in msgs[0].raw


def test_should_deliver_unknown_message_when_sender_has_no_position() -> None:
    ether = MockEther()
    sender = MockTransport("001", ether)
    # sender.position is None
    target = MockTransport("002", ether)
    target.position = Coord(lat=63.0, lon=10.0)

    msgs = _collect_messages(sender)
    sender.request_range("002")

    assert len(msgs) == 1
    assert isinstance(msgs[0], UnknownMessage)


def test_should_calculate_correct_range_timestamp() -> None:
    """Two nodes 1500m apart at 1500 m/s → 1 second → 32000 timestamp units."""
    ether = MockEther(sound_speed=1500.0)

    sender = MockTransport("001", ether)
    # 1 degree lat ≈ 111320m, so ~0.01348 degrees ≈ 1500m
    sender.position = Coord(lat=63.0, lon=10.0)

    target = MockTransport("002", ether)
    target.position = Coord(lat=63.0 + 1500.0 / 111320.0, lon=10.0)

    msgs = _collect_messages(sender)
    sender.request_range("002")

    assert len(msgs) == 1
    assert isinstance(msgs[0], RangeResponseMessage)
    # 1500m / 1500 m/s = 1.0s, 1.0 / 3.125e-5 = 32000
    assert abs(msgs[0].timestamp - 32000) < 10  # Allow small rounding


def test_should_calculate_range_with_depth_difference() -> None:
    """Two nodes at same lat/lon but 10m depth difference."""
    ether = MockEther(sound_speed=1500.0)

    sender = MockTransport("001", ether)
    sender.position = Coord(lat=63.0, lon=10.0)
    # Mock depth pull manually for this test since there's no AcousticNode
    sender.get_depth_callback = lambda: 0.0

    target = MockTransport("002", ether)
    target.position = Coord(lat=63.0, lon=10.0)
    target.get_depth_callback = lambda: 10.0

    msgs = _collect_messages(sender)
    sender.request_range("002")

    assert len(msgs) == 1
    assert isinstance(msgs[0], RangeResponseMessage)
    # 10m / 1500 m/s = 0.00667s, 0.00667 / 3.125e-5 ≈ 213
    expected_ts = round(10.0 / 1500.0 / 3.125e-5)
    assert abs(msgs[0].timestamp - expected_ts) < 2


# --- Edge cases ---


def test_should_not_deliver_if_no_callback_registered() -> None:
    """deliver() with no callback should not raise."""
    ether = MockEther()
    transport = MockTransport("001", ether)
    # No callback registered — should not raise
    transport.deliver(UnknownMessage(raw="test"))


def test_should_unregister_transport() -> None:
    ether = MockEther()
    sender = MockTransport("001", ether)
    receiver = MockTransport("002", ether)
    msgs = _collect_messages(receiver)

    ether.unregister("002")
    sender.broadcast_position(Coord(lat=63.0, lon=10.0), depth=0.0)

    assert len(msgs) == 0
