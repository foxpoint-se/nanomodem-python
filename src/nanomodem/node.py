"""AcousticNode — the only stateful class in the system.

Holds own position, depth, known nodes, distances.
Orchestrates communication and calculation via injected dependencies.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

from .calculation import Calculation
from .drivers.v3_spec import supply_voltage_volts
from .errors import ModemIdMismatchError, ModemStatusTimeoutError
from .protocols import CalculationProtocol, TransportProtocol
from .types import (
    Coord,
    KnownNode,
    LocalAckMessage,
    Message,
    ModemStatusMessage,
    NodeCapabilities,
    PositionMessage,
    QualityIndicatorMessage,
    RangeResponseMessage,
    UnknownMessage,
)

logger = logging.getLogger(__name__)


def _validate_node_id(node_id: str) -> None:
    """Validate that node_id is a 3-digit string representing 1-255."""
    if not isinstance(node_id, str):
        raise TypeError(f"node_id must be a str, got {type(node_id).__name__}")
    if len(node_id) != 3 or not node_id.isdigit():
        raise ValueError(f"node_id must be a 3-digit numeric string (e.g. '001'), got '{node_id}'")
    numeric = int(node_id)
    if numeric < 1 or numeric > 255:
        raise ValueError(f"node_id must represent 1-255, got {numeric}")


class AcousticNode:
    """A single node in the acoustic modem network."""

    def __init__(
        self,
        node_id: str,
        transport: TransportProtocol,
        calculation: Optional[CalculationProtocol] = None,
        position: Optional[Coord] = None,
        sound_speed: float = 1500.0,
        on_position_changed: Optional[Callable[[Optional[Coord]], None]] = None,
        on_depth_changed: Optional[Callable[[float], None]] = None,
        on_known_nodes_changed: Optional[Callable[[dict[str, KnownNode]], None]] = None,
        on_message_received: Optional[Callable[[Message], None]] = None,
    ) -> None:
        _validate_node_id(node_id)

        self._node_id = node_id
        self._transport = transport
        self._calculation: CalculationProtocol = calculation or Calculation()
        self._position = position
        self._depth = 0.0
        self._sound_speed = sound_speed
        self._capabilities = NodeCapabilities()
        self._known_nodes: dict[str, KnownNode] = {}

        self._cb_position_changed = on_position_changed
        self._cb_depth_changed = on_depth_changed
        self._cb_known_nodes_changed = on_known_nodes_changed
        self._on_message_received = on_message_received

        self._transport.on_message(self._handle_message)

    # --- Properties ---

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def transport(self) -> TransportProtocol:
        return self._transport

    @property
    def calculation(self) -> CalculationProtocol:
        return self._calculation

    @property
    def capabilities(self) -> NodeCapabilities:
        return self._capabilities

    def get_position(self) -> Optional[Coord]:
        return self._position

    def get_known_nodes(self) -> dict[str, KnownNode]:
        return dict(self._known_nodes)

    def get_depth(self) -> float:
        return self._depth

    # --- Setters ---

    def set_position(self, position: Optional[Coord]) -> None:
        self._position = position
        self._maybe_broadcast_position()
        if self._cb_position_changed is not None:
            self._cb_position_changed(position)

    def set_depth(self, depth: float) -> None:
        self._depth = depth
        if self._cb_depth_changed is not None:
            self._cb_depth_changed(depth)

    def set_known_node_position(self, node_id: str, position: Optional[Coord]) -> None:
        """Manually set or update the position of a node in the registry."""
        self._ensure_known_node(node_id)
        self._known_nodes[node_id].position = position
        if self._cb_known_nodes_changed is not None:
            self._cb_known_nodes_changed(dict(self._known_nodes))

    def set_known_node_depth(self, node_id: str, depth: float) -> None:
        """Manually update the depth of a node in the registry."""
        self._ensure_known_node(node_id)
        self._known_nodes[node_id].depth = depth
        if self._cb_known_nodes_changed is not None:
            self._cb_known_nodes_changed(dict(self._known_nodes))

    def delete_known_node(self, node_id: str) -> None:
        """Remove a node from the registry."""
        if node_id in self._known_nodes:
            del self._known_nodes[node_id]
            if self._cb_known_nodes_changed is not None:
                self._cb_known_nodes_changed(dict(self._known_nodes))

    # --- Actions ---

    def request_range(self, target_id: str) -> None:
        """Request a range measurement to another node."""
        self._ensure_known_node(target_id)
        self._transport.request_range(target_id)

    def request_test(self, target_id: str) -> None:
        """Request a test transmission from the unit at target_id."""
        self._transport.request_test(target_id)

    def query_quality(self) -> None:
        """Query bytes corrected on the last received data packet."""
        self._transport.query_quality()

    def query_modem_status(self) -> None:
        """Query modem NVM address and supply voltage ($?)."""
        self._transport.query_modem_status()

    def ensure_modem_id_matches(self, timeout_s: float = 2.0) -> ModemStatusMessage:
        """Send $? and verify the modem NVM id matches this node's id."""
        received: list[ModemStatusMessage] = []
        done = threading.Event()
        previous = self._on_message_received

        def capture(msg: Message) -> None:
            if isinstance(msg, ModemStatusMessage):
                received.append(msg)
                done.set()
            if previous is not None:
                previous(msg)

        self._on_message_received = capture
        try:
            self.query_modem_status()
            if not done.wait(timeout_s):
                raise ModemStatusTimeoutError(self._node_id, timeout_s)
            status = received[0]
            if status.node_id != self._node_id:
                raise ModemIdMismatchError(self._node_id, status.node_id)
            return status
        finally:
            self._on_message_received = previous

    def broadcast_position(self) -> None:
        """Broadcast own position to all other nodes."""
        if self._position is not None:
            # The transport interface needs to be updated to accept PositionMessage
            # OR we update the transport interface to accept (Coord, depth)
            self._transport.broadcast_position(self._position, self._depth)

    def calculate_position(self) -> Optional[Coord]:
        """Calculate own position using trilateration from known nodes.

        Requires 3+ known nodes with both a position and a range.
        If own depth is set, projects 3D ranges to 2D before trilateration.
        Returns the estimated position, or None if not enough data.
        """
        usable = [kn for kn in self._known_nodes.values() if kn.position is not None and kn.last_range is not None]

        if len(usable) < 3:
            return None

        positions: list[Coord] = []
        distances: list[float] = []

        for kn in usable:
            assert kn.position is not None
            assert kn.last_range is not None

            distance = kn.last_range

            # Use depth if available on either side
            own_depth = self._depth
            kn_depth = kn.depth

            if own_depth != 0.0 or kn_depth != 0.0:
                distance = self._calculation.project_3d_to_2d(distance, own_depth, kn_depth)

            positions.append(kn.position)
            distances.append(distance)

        result = self._calculation.trilaterate(positions, distances)

        self._position = Coord(lat=result.lat, lon=result.lon)

        if self._cb_position_changed is not None:
            self._cb_position_changed(self._position)
        return self._position

    # --- Message handling ---

    def _handle_message(self, msg: Message) -> None:
        match msg:
            case PositionMessage(node_id=nid, coord=c, depth=d):
                self._ensure_known_node(nid)
                self._known_nodes[nid].position = c
                self._known_nodes[nid].depth = d
                self._known_nodes[nid].last_seen = time.time()
                if self._cb_known_nodes_changed is not None:
                    self._cb_known_nodes_changed(dict(self._known_nodes))
            case RangeResponseMessage(node_id=nid, timestamp=ts):
                self._ensure_known_node(nid)
                distance = self._calculation.timestamp_to_distance(ts, self._sound_speed)
                self._known_nodes[nid].last_range = distance
                self._known_nodes[nid].last_seen = time.time()
                if self._cb_known_nodes_changed is not None:
                    self._cb_known_nodes_changed(dict(self._known_nodes))
                self._maybe_infer_position()
            case LocalAckMessage(command=cmd, target_id=tid):
                logger.info("Local ack %s target=%s", cmd, tid)
            case QualityIndicatorMessage(bytes_corrected=bytes_corrected):
                if bytes_corrected is None:
                    logger.info("Quality: rejected")
                else:
                    logger.info("Quality: %d bytes corrected", bytes_corrected)
            case ModemStatusMessage(node_id=nid, voltage_raw=raw):
                volts = supply_voltage_volts(raw)
                logger.info(
                    "Modem status id=%s voltage_raw=%d (%.2f V)",
                    nid,
                    raw,
                    volts,
                )
            case UnknownMessage(raw=raw):
                logger.info("Unhandled message: %s", raw)

        if self._on_message_received is not None:
            self._on_message_received(msg)

    # --- Internal helpers ---

    def _maybe_broadcast_position(self) -> None:
        """Triggers auto-broadcast when own position changes, if enabled."""
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
                    self._depth,
                )

    def _ensure_known_node(self, node_id: str) -> None:
        """Create a KnownNode entry if it doesn't exist yet."""
        if node_id not in self._known_nodes:
            self._known_nodes[node_id] = KnownNode(node_id=node_id)
