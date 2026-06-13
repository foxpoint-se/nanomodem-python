"""Tests for MockTransport + MockEther."""

from nanomodem.drivers.v3_spec import is_test_broadcast_line
from nanomodem.transports.mock import (
    MOCK_BYTES_CORRECTED,
    MOCK_STATUS_VOLTAGE_RAW,
    MockEther,
    MockTransport,
)
from nanomodem.types import (
    Coord,
    LocalAckMessage,
    Message,
    ModemStatusMessage,
    PositionMessage,
    QualityIndicatorMessage,
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


# --- Test transmission ($T) and quality ($Q) ---


def test__should_deliver_local_ack_and_test_broadcast_on_request_test() -> None:
    ether = MockEther()
    sender = MockTransport("001", ether)
    _target = MockTransport("002", ether)
    listener = MockTransport("003", ether)

    sender_msgs = _collect_messages(sender)
    listener_msgs = _collect_messages(listener)

    sender.request_test("002")

    assert len(sender_msgs) == 2
    assert isinstance(sender_msgs[0], LocalAckMessage)
    assert sender_msgs[0].command == "test"
    assert sender_msgs[0].target_id == "002"
    assert isinstance(sender_msgs[1], UnknownMessage)
    assert is_test_broadcast_line(sender_msgs[1].raw)

    assert len(listener_msgs) == 1
    assert isinstance(listener_msgs[0], UnknownMessage)
    assert is_test_broadcast_line(listener_msgs[0].raw)


def test__should_return_quality_after_test_broadcast() -> None:
    ether = MockEther()
    sender = MockTransport("001", ether)
    _target = MockTransport("002", ether)

    msgs = _collect_messages(sender)
    sender.request_test("002")
    sender.query_quality()

    assert len(msgs) == 3
    assert isinstance(msgs[2], QualityIndicatorMessage)
    assert msgs[2].bytes_corrected == MOCK_BYTES_CORRECTED


def test__should_return_modem_status_on_status_query() -> None:
    ether = MockEther()
    sender = MockTransport("042", ether)

    msgs = _collect_messages(sender)
    sender.query_modem_status()

    assert len(msgs) == 1
    assert isinstance(msgs[0], ModemStatusMessage)
    assert msgs[0].node_id == "042"
    assert msgs[0].voltage_raw == MOCK_STATUS_VOLTAGE_RAW


def test__should_reject_quality_query_without_prior_data() -> None:
    ether = MockEther()
    sender = MockTransport("001", ether)

    msgs = _collect_messages(sender)
    sender.query_quality()

    assert len(msgs) == 1
    assert isinstance(msgs[0], QualityIndicatorMessage)
    assert msgs[0].bytes_corrected is None


def test__should_do_nothing_when_request_test_target_missing() -> None:
    ether = MockEther()
    sender = MockTransport("001", ether)

    msgs = _collect_messages(sender)
    sender.request_test("999")

    assert msgs == []
