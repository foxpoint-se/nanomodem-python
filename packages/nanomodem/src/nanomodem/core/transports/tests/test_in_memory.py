"""Tests for InMemoryTransport and InMemoryBus."""

from __future__ import annotations

from nanomodem.constants import MODEM_TIMESTAMP_QUANTUM_S
from nanomodem.core.transports.in_memory import (
    MOCK_BYTES_CORRECTED,
    MOCK_STATUS_VOLTAGE_RAW,
    InMemoryBus,
    InMemoryTransport,
)
from nanomodem.core.wire_types import (
    BroadcastCommand,
    ModemEvent,
    PingCommand,
    PingTimeoutEvent,
    QualityIndicatorEvent,
    QualityQueryCommand,
    QualityRejectedEvent,
    ReceivedBroadcastEvent,
    RoundtripResponseEvent,
    StatusQueryCommand,
    StatusResponseEvent,
)
from nanomodem.positioning import Calculation
from nanomodem.types import Coord


def _collect_events(transport: InMemoryTransport) -> list[ModemEvent]:
    received: list[ModemEvent] = []
    transport.on_event(lambda event: received.append(event))
    return received


def test__should_deliver_broadcast_to_all_peers() -> None:
    bus = InMemoryBus()
    sender = InMemoryTransport("001", bus)
    receiver_a = InMemoryTransport("002", bus)
    receiver_b = InMemoryTransport("003", bus)

    events_a = _collect_events(receiver_a)
    events_b = _collect_events(receiver_b)

    sender.send_command(BroadcastCommand(data=b"hello"))

    assert len(events_a) == 1
    assert len(events_b) == 1
    assert events_a[0] == ReceivedBroadcastEvent(sender_id="001", data=b"hello")
    assert events_b[0] == ReceivedBroadcastEvent(sender_id="001", data=b"hello")


def test__should_not_deliver_broadcast_to_sender() -> None:
    bus = InMemoryBus()
    sender = InMemoryTransport("001", bus)
    _other = InMemoryTransport("002", bus)

    sender_events = _collect_events(sender)
    sender.send_command(BroadcastCommand(data=b"hello"))

    assert sender_events == []


def test__should_deliver_roundtrip_response_for_ping() -> None:
    bus = InMemoryBus(sound_speed=1500.0)
    sender = InMemoryTransport("001", bus)
    sender.position = Coord(lat=63.0, lon=10.0)
    target = InMemoryTransport("002", bus)
    target.position = Coord(lat=63.0, lon=10.0)

    events = _collect_events(sender)
    sender.send_command(PingCommand(target_id="002"))

    assert len(events) == 1
    assert isinstance(events[0], RoundtripResponseEvent)
    assert events[0].responder_id == "002"


def test__should_deliver_timeout_for_unreachable_target() -> None:
    bus = InMemoryBus()
    sender = InMemoryTransport("001", bus)
    sender.position = Coord(lat=63.0, lon=10.0)

    events = _collect_events(sender)
    sender.send_command(PingCommand(target_id="999"))

    assert events == [PingTimeoutEvent()]


def test__should_calculate_range_from_positions() -> None:
    sound_speed = 1500.0
    bus = InMemoryBus(sound_speed=sound_speed)
    sender = InMemoryTransport("001", bus)
    sender.position = Coord(lat=63.0, lon=10.0)
    target = InMemoryTransport("002", bus)
    target.position = Coord(lat=63.001, lon=10.0)

    events = _collect_events(sender)
    sender.send_command(PingCommand(target_id="002"))

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, RoundtripResponseEvent)

    calculation = Calculation()
    distance = calculation.timestamp_to_distance(event.timestamp_counts, sound_speed)
    assert distance > 0.0


def test__should_deliver_status_response_for_query() -> None:
    bus = InMemoryBus()
    transport = InMemoryTransport("001", bus)

    events = _collect_events(transport)
    transport.send_command(StatusQueryCommand())

    assert events == [
        StatusResponseEvent(address="001", voltage_raw=MOCK_STATUS_VOLTAGE_RAW),
    ]


def test__should_deliver_quality_indicator_after_data_received() -> None:
    bus = InMemoryBus()
    sender = InMemoryTransport("001", bus)
    receiver = InMemoryTransport("002", bus)

    _collect_events(receiver)
    sender.send_command(BroadcastCommand(data=b"packet"))

    events = _collect_events(receiver)
    receiver.send_command(QualityQueryCommand())

    assert events == [QualityIndicatorEvent(bytes_corrected=MOCK_BYTES_CORRECTED)]


def test__should_deliver_quality_rejected_when_no_data() -> None:
    bus = InMemoryBus()
    transport = InMemoryTransport("001", bus)

    events = _collect_events(transport)
    transport.send_command(QualityQueryCommand())

    assert events == [QualityRejectedEvent()]


def test__should_match_timestamp_quantum_for_zero_distance_ping() -> None:
    bus = InMemoryBus(sound_speed=1500.0)
    sender = InMemoryTransport("001", bus)
    sender.position = Coord(lat=63.0, lon=10.0)
    target = InMemoryTransport("002", bus)
    target.position = Coord(lat=63.0, lon=10.0)

    events = _collect_events(sender)
    sender.send_command(PingCommand(target_id="002"))

    event = events[0]
    assert isinstance(event, RoundtripResponseEvent)
    assert event.timestamp_counts == 0

    calculation = Calculation()
    assert calculation.timestamp_to_distance(0, 1500.0) == 0.0
    assert MODEM_TIMESTAMP_QUANTUM_S > 0.0
