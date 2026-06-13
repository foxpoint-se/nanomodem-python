"""Mock transport and shared in-memory bus for testing."""

from __future__ import annotations

from typing import Callable, Optional

from ..calculation import calculate_distance_3d
from ..drivers.v3_spec import format_test_broadcast_line
from ..protocols import OnMessageCallback
from ..types import (
    Coord,
    LocalAckMessage,
    Message,
    ModemStatusMessage,
    PositionMessage,
    QualityIndicatorMessage,
    RangeResponseMessage,
    UnknownMessage,
)

MOCK_BYTES_CORRECTED = 3
MOCK_STATUS_VOLTAGE_RAW = 48123


class MockEther:
    """Shared in-memory bus for MockTransport instances.

    Simulates the acoustic medium. Handles message routing and
    mock range calculation based on node positions.
    """

    def __init__(self, sound_speed: float = 1500.0) -> None:
        self._transports: dict[str, MockTransport] = {}
        self._sound_speed = sound_speed
        self._heard_data_packet: dict[str, bool] = {}

    def register(self, transport: MockTransport) -> None:
        self._transports[transport.node_id] = transport

    def unregister(self, node_id: str) -> None:
        self._transports.pop(node_id, None)

    def get_transport(self, node_id: str) -> MockTransport | None:
        return self._transports.get(node_id)

    def get_all_except(self, node_id: str) -> list[MockTransport]:
        return [t for nid, t in self._transports.items() if nid != node_id]

    def broadcast(self, sender_id: str, message: Message) -> None:
        """Deliver a message to all registered transports except the sender."""
        for transport in self.get_all_except(sender_id):
            transport.deliver(message)

    def request_range(self, sender_id: str, target_id: str) -> None:
        """Simulate a range request. Calculates mock timestamp from positions."""
        sender = self.get_transport(sender_id)
        target = self.get_transport(target_id)

        if sender is None:
            return

        if target is None:
            sender.deliver(UnknownMessage(raw="#TO"))
            return

        if target.position is None or sender.position is None:
            sender.deliver(UnknownMessage(raw="#TO"))
            return

        distance = self._calculate_distance(sender, target)

        # Convert to timestamp in 100us units (per modem spec):
        # timestamp = round(travel_time / 3.125e-5)
        travel_time = distance / self._sound_speed
        timestamp = round(travel_time / 3.125e-5)

        sender.deliver(RangeResponseMessage(node_id=target_id, timestamp=timestamp))

    def request_test(self, sender_id: str, target_id: str) -> None:
        """Simulate $T: local ack to sender, test #B from target to listeners."""
        sender = self.get_transport(sender_id)
        if sender is None:
            return

        if self.get_transport(target_id) is None:
            return

        sender.deliver(
            LocalAckMessage(command="test", target_id=target_id),
        )

        line = format_test_broadcast_line(target_id)
        message = UnknownMessage(raw=line)
        for listener in self.get_all_except(target_id):
            listener.deliver(message)
            self._heard_data_packet[listener.node_id] = True

    def query_quality(self, node_id: str) -> None:
        """Simulate $Q: bytes corrected if last data packet was heard."""
        transport = self.get_transport(node_id)
        if transport is None:
            return

        if self._heard_data_packet.pop(node_id, False):
            transport.deliver(
                QualityIndicatorMessage(bytes_corrected=MOCK_BYTES_CORRECTED),
            )
            return

        transport.deliver(QualityIndicatorMessage(bytes_corrected=None))

    def query_modem_status(self, node_id: str) -> None:
        """Simulate $?: return stored address and default supply voltage raw."""
        transport = self.get_transport(node_id)
        if transport is None:
            return
        transport.deliver(
            ModemStatusMessage(
                node_id=node_id,
                voltage_raw=MOCK_STATUS_VOLTAGE_RAW,
            ),
        )

    def _calculate_distance(self, a: MockTransport, b: MockTransport) -> float:
        """Euclidean distance in meters using flat-earth approximation."""
        assert a.position is not None
        assert b.position is not None
        return calculate_distance_3d(a.position, a.depth, b.position, b.depth)


class MockTransport:
    """In-memory transport using MockEther as the communication medium.

    Routes typed Message objects directly -- no codec needed.
    """

    def __init__(self, node_id: str, ether: MockEther) -> None:
        self.node_id = node_id
        self.position: Optional[Coord] = None
        self.get_depth_callback: Optional[Callable[[], float]] = None
        self._ether = ether
        self._callback: OnMessageCallback | None = None
        ether.register(self)

    @property
    def depth(self) -> float:
        """Pull the logical depth from the node via callback."""
        if self.get_depth_callback is not None:
            return self.get_depth_callback()
        return 0.0

    def broadcast_position(self, coord: Coord, depth: float) -> None:
        """Broadcast own position to all other nodes."""
        msg = PositionMessage(node_id=self.node_id, coord=coord, depth=depth)
        self._ether.broadcast(self.node_id, msg)

    def request_range(self, target_id: str) -> None:
        """Request range to target. Ether simulates the response."""
        self._ether.request_range(self.node_id, target_id)

    def request_test(self, target_id: str) -> None:
        """Request test transmission from target. Ether simulates acoustic result."""
        self._ether.request_test(self.node_id, target_id)

    def query_quality(self) -> None:
        """Query link quality on last received data packet."""
        self._ether.query_quality(self.node_id)

    def query_modem_status(self) -> None:
        """Query modem address and supply voltage."""
        self._ether.query_modem_status(self.node_id)

    def on_message(self, callback: OnMessageCallback) -> None:
        self._callback = callback

    def deliver(self, message: Message) -> None:
        """Called by MockEther to deliver a message to this transport."""
        if self._callback is not None:
            self._callback(message)
