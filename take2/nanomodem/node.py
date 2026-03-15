"""AcousticNode — the only stateful class in the system.

Holds own position, depth, known nodes, distances.
Orchestrates communication and calculation via injected dependencies.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from .calculation import Calculation, CalculationInterface
from .transport import TransportInterface
from .types import (
    Coord,
    KnownNode,
    Message,
    NodeCapabilities,
    PositionMessage,
    RangeResponseMessage,
    UnknownMessage,
)

logger = logging.getLogger(__name__)


def _validate_node_id(node_id: str) -> None:
    """Validate that node_id is a 3-digit string representing 1-255."""
    if not isinstance(node_id, str):
        raise TypeError(f"node_id must be a str, got {type(node_id).__name__}")
    if len(node_id) != 3 or not node_id.isdigit():
        raise ValueError(
            f"node_id must be a 3-digit numeric string (e.g. '001'), got '{node_id}'"
        )
    numeric = int(node_id)
    if numeric < 1 or numeric > 255:
        raise ValueError(
            f"node_id must represent 1-255, got {numeric}"
        )


class AcousticNode:
    """A single node in the acoustic modem network."""

    def __init__(
        self,
        node_id: str,
        transport: TransportInterface,
        calculation: Optional[CalculationInterface] = None,
        position: Optional[Coord] = None,
        sound_speed: float = 1500.0,
        on_state_changed: Optional[Callable[[], None]] = None,
        on_message_received: Optional[Callable[[Message], None]] = None,
    ) -> None:
        _validate_node_id(node_id)

        self._node_id = node_id
        self._transport = transport
        self._calculation: CalculationInterface = calculation or Calculation()
        self._position = position
        self._sound_speed = sound_speed
        self._capabilities = NodeCapabilities()
        self._known_nodes: dict[str, KnownNode] = {}

        self._on_state_changed = on_state_changed
        self._on_message_received = on_message_received

        self._transport.on_message(self._handle_message)

    # --- Properties ---

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def transport(self) -> TransportInterface:
        return self._transport

    @property
    def calculation(self) -> CalculationInterface:
        return self._calculation

    @property
    def capabilities(self) -> NodeCapabilities:
        return self._capabilities

    def get_position(self) -> Optional[Coord]:
        return self._position

    def get_known_nodes(self) -> dict[str, KnownNode]:
        return dict(self._known_nodes)

    # --- Setters ---

    def set_position(self, position: Optional[Coord]) -> None:
        self._position = position
        self._on_position_changed()
        self._notify_state_changed()

    def set_depth(self, depth: float) -> None:
        if self._position is not None:
            self._position = Coord(
                lat=self._position.lat,
                lon=self._position.lon,
                depth=depth,
            )
        else:
            self._position = Coord(lat=0.0, lon=0.0, depth=depth)
        self._notify_state_changed()

    def set_known_node_position(self, node_id: str, position: Optional[Coord]) -> None:
        """Manually set or update the position of a node in the registry."""
        self._ensure_known_node(node_id)
        self._known_nodes[node_id].position = position
        self._notify_state_changed()

    def set_known_node_depth(self, node_id: str, depth: float) -> None:
        """Manually update the depth of a node in the registry."""
        self._ensure_known_node(node_id)
        kn = self._known_nodes[node_id]
        if kn.position is not None:
            kn.position = Coord(
                lat=kn.position.lat,
                lon=kn.position.lon,
                depth=depth,
            )
        else:
            kn.position = Coord(lat=0.0, lon=0.0, depth=depth)
        self._notify_state_changed()

    def delete_known_node(self, node_id: str) -> None:
        """Remove a node from the registry."""
        if node_id in self._known_nodes:
            del self._known_nodes[node_id]
            self._notify_state_changed()

    # --- Actions ---

    def request_range(self, target_id: str) -> None:
        """Request a range measurement to another node."""
        self._ensure_known_node(target_id)
        self._transport.request_range(target_id)

    def broadcast_position(self) -> None:
        """Broadcast own position to all other nodes."""
        if self._position is not None:
            self._transport.broadcast_position(self._position)

    def calculate_position(self) -> Optional[Coord]:
        """Calculate own position using trilateration from known nodes.

        Requires 3+ known nodes with both a position and a range.
        If own depth is set, projects 3D ranges to 2D before trilateration.
        Returns the estimated position, or None if not enough data.
        """
        usable = [
            kn
            for kn in self._known_nodes.values()
            if kn.position is not None and kn.last_range is not None
        ]

        if len(usable) < 3:
            return None

        positions: list[Coord] = []
        distances: list[float] = []

        for kn in usable:
            assert kn.position is not None
            assert kn.last_range is not None

            distance = kn.last_range
            if self._position is not None and self._position.depth != 0.0:
                distance = self._calculation.project_3d_to_2d(
                    distance, self._position.depth, kn.position.depth
                )

            positions.append(kn.position)
            distances.append(distance)

        result = self._calculation.trilaterate(positions, distances)

        depth = self._position.depth if self._position is not None else 0.0
        self._position = Coord(lat=result.lat, lon=result.lon, depth=depth)

        self._notify_state_changed()
        return self._position

    # --- Message handling ---

    def _handle_message(self, msg: Message) -> None:
        match msg:
            case PositionMessage(node_id=nid, coord=c):
                self._ensure_known_node(nid)
                self._known_nodes[nid].position = c
                self._known_nodes[nid].last_seen = time.time()
            case RangeResponseMessage(node_id=nid, timestamp=ts):
                self._ensure_known_node(nid)
                distance = self._calculation.timestamp_to_distance(
                    ts, self._sound_speed
                )
                self._known_nodes[nid].last_range = distance
                self._known_nodes[nid].last_seen = time.time()
                self._maybe_infer_position()
            case UnknownMessage(raw=raw):
                logger.info("Unhandled message: %s", raw)

        self._notify_state_changed()
        if self._on_message_received is not None:
            self._on_message_received(msg)

    # --- Internal helpers ---

    def _notify_state_changed(self) -> None:
        """Notify the GUI (or any listener) that node state has changed."""
        if self._on_state_changed is not None:
            self._on_state_changed()

    def _on_position_changed(self) -> None:
        """Called whenever own position changes. Triggers auto-broadcast if enabled."""
        if self._capabilities.is_broadcasting_own_position:
            self.broadcast_position()

    def _maybe_infer_position(self) -> None:
        """Called after a new range. Triggers auto-calculate if enabled and enough data."""
        if self._capabilities.is_inferring_own_position:
            result = self.calculate_position()
            if result is not None:
                logger.info(
                    "Node %s inferred position: (%f, %f, %f)",
                    self._node_id,
                    result.lat,
                    result.lon,
                    result.depth,
                )

    def _ensure_known_node(self, node_id: str) -> None:
        """Create a KnownNode entry if it doesn't exist yet."""
        if node_id not in self._known_nodes:
            self._known_nodes[node_id] = KnownNode(node_id=node_id)
