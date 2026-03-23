"""Transport interface and mock implementations."""

from __future__ import annotations

import math
from typing import Callable, Optional, Protocol

from .types import (
    Coord,
    Message,
    PositionMessage,
    RangeResponseMessage,
    UnknownMessage,
)

OnMessageCallback = Callable[[Message], None]


class TransportInterface(Protocol):
    """Interface for sending/receiving messages. Inject into AcousticNode.

    Works at the message level, not bytes. Each implementation handles
    encoding/decoding internally (NanomodemTransport uses Codec,
    MockTransport routes typed messages directly).
    """

    def broadcast_position(self, coord: Coord, depth: float) -> None: ...

    def request_range(self, target_id: str) -> None: ...

    def on_message(self, callback: OnMessageCallback) -> None: ...


class MockEther:
    """Shared in-memory bus for MockTransport instances.

    Simulates the acoustic medium. Handles message routing and
    mock range calculation based on node positions.
    """

    def __init__(self, sound_speed: float = 1500.0) -> None:
        self._transports: dict[str, MockTransport] = {}
        self._sound_speed = sound_speed

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
            # Target not in network — simulate timeout
            sender.deliver(UnknownMessage(raw="#TO"))
            return

        if target.position is None or sender.position is None:
            # Position missing — we can't compute distance, so simulate timeout
            sender.deliver(UnknownMessage(raw="#TO"))
            return

        distance = self._calculate_distance(sender, target)

        # Convert to timestamp in 100µs units (per modem spec):
        # timestamp = round(travel_time / 3.125e-5)
        travel_time = distance / self._sound_speed
        timestamp = round(travel_time / 3.125e-5)

        sender.deliver(RangeResponseMessage(node_id=target_id, timestamp=timestamp))

    def _calculate_distance(self, a: MockTransport, b: MockTransport) -> float:
        """Euclidean distance in meters using flat-earth approximation.

        - 1 degree lat ≈ 111320 m
        - 1 degree lon ≈ 111320 * cos(lat) m
        """
        assert a.position is not None
        assert b.position is not None

        lat_m = (b.position.lat - a.position.lat) * 111320.0
        avg_lat = math.radians((a.position.lat + b.position.lat) / 2.0)
        lon_m = (b.position.lon - a.position.lon) * 111320.0 * math.cos(avg_lat)
        
        depth_m = b.depth - a.depth
        
        return math.sqrt(lat_m**2 + lon_m**2 + depth_m**2)


class MockTransport:
    """In-memory transport using MockEther as the communication medium.

    Routes typed Message objects directly — no codec needed.
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

    def on_message(self, callback: OnMessageCallback) -> None:
        self._callback = callback

    def deliver(self, message: Message) -> None:
        """Called by MockEther to deliver a message to this transport."""
        if self._callback is not None:
            self._callback(message)
