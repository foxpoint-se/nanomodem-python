"""PositioningNode — LBL positioning on top of ModemNode."""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from nanomodem.constants import SOUND_SPEED_WATER_M_S, validate_sound_speed
from nanomodem.core.modem_node import ModemNode
from nanomodem.core.protocols import WireTransport
from nanomodem.core.transports.in_memory import InMemoryTransport
from nanomodem.core.wire_types import QualityQueryCommand, TestRequestCommand
from nanomodem.types import Coord, PositionMessage

from .calculation import Calculation
from .protocols import CalculationProtocol
from .types import KnownNode, NodeCapabilities

logger = logging.getLogger(__name__)


def _validate_node_id(node_id: str) -> None:
    if not isinstance(node_id, str):
        raise TypeError(f"node_id must be a str, got {type(node_id).__name__}")
    if len(node_id) != 3 or not node_id.isdigit():
        raise ValueError(f"node_id must be a 3-digit numeric string (e.g. '001'), got '{node_id}'")
    numeric = int(node_id)
    if numeric < 1 or numeric > 255:
        raise ValueError(f"node_id must represent 1-255, got {numeric}")


class PositioningNode:
    """LBL positioning controller wrapping ModemNode[PositionMessage]."""

    def __init__(
        self,
        node_id: str,
        modem_node: ModemNode[PositionMessage],
        calculation: Optional[CalculationProtocol] = None,
        position: Optional[Coord] = None,
        sound_speed: float = SOUND_SPEED_WATER_M_S,
        on_position_changed: Optional[Callable[[Optional[Coord]], None]] = None,
        on_depth_changed: Optional[Callable[[float], None]] = None,
        on_known_nodes_changed: Optional[Callable[[dict[str, KnownNode]], None]] = None,
    ) -> None:
        _validate_node_id(node_id)
        if modem_node.node_id != node_id:
            raise ValueError(
                f"modem_node.node_id {modem_node.node_id!r} must match node_id {node_id!r}",
            )

        self._node_id = node_id
        self._modem_node = modem_node
        self._calculation: CalculationProtocol = calculation or Calculation()
        self._position = position
        self._depth = 0.0
        self._sound_speed = validate_sound_speed(sound_speed)
        self._capabilities = NodeCapabilities()
        self._known_nodes: dict[str, KnownNode] = {}

        self._cb_position_changed = on_position_changed
        self._cb_depth_changed = on_depth_changed
        self._cb_known_nodes_changed = on_known_nodes_changed

        self._modem_node.on_received_broadcast(self._handle_position_broadcast)
        self._modem_node.on_roundtrip_response(self._handle_roundtrip_response)
        self._sync_in_memory_transport()

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def modem_node(self) -> ModemNode[PositionMessage]:
        return self._modem_node

    @property
    def transport(self) -> WireTransport:
        return self._modem_node.transport

    @property
    def calculation(self) -> CalculationProtocol:
        return self._calculation

    @property
    def sound_speed(self) -> float:
        return self._sound_speed

    @property
    def capabilities(self) -> NodeCapabilities:
        return self._capabilities

    def get_position(self) -> Optional[Coord]:
        return self._position

    def get_known_nodes(self) -> dict[str, KnownNode]:
        return dict(self._known_nodes)

    def get_depth(self) -> float:
        return self._depth

    def set_position(self, position: Optional[Coord]) -> None:
        self._position = position
        self._sync_in_memory_transport()
        self._maybe_broadcast_position()
        if self._cb_position_changed is not None:
            self._cb_position_changed(position)

    def set_depth(self, depth: float) -> None:
        self._depth = depth
        if self._cb_depth_changed is not None:
            self._cb_depth_changed(depth)

    def set_known_node_position(self, node_id: str, position: Optional[Coord]) -> None:
        self._ensure_known_node(node_id)
        self._known_nodes[node_id].position = position
        if self._cb_known_nodes_changed is not None:
            self._cb_known_nodes_changed(dict(self._known_nodes))

    def set_known_node_depth(self, node_id: str, depth: float) -> None:
        self._ensure_known_node(node_id)
        self._known_nodes[node_id].depth = depth
        if self._cb_known_nodes_changed is not None:
            self._cb_known_nodes_changed(dict(self._known_nodes))

    def delete_known_node(self, node_id: str) -> None:
        if node_id in self._known_nodes:
            del self._known_nodes[node_id]
            if self._cb_known_nodes_changed is not None:
                self._cb_known_nodes_changed(dict(self._known_nodes))

    def register_ui_callbacks(
        self,
        *,
        on_position_changed: Optional[Callable[[Optional[Coord]], None]] = None,
        on_depth_changed: Optional[Callable[[float], None]] = None,
        on_known_nodes_changed: Optional[Callable[[dict[str, KnownNode]], None]] = None,
    ) -> None:
        if on_position_changed is not None:
            self._cb_position_changed = on_position_changed
        if on_depth_changed is not None:
            self._cb_depth_changed = on_depth_changed
        if on_known_nodes_changed is not None:
            self._cb_known_nodes_changed = on_known_nodes_changed

    def request_range(self, target_id: str) -> None:
        self._ensure_known_node(target_id)
        self._modem_node.ping(target_id)

    def request_test(self, target_id: str) -> None:
        self._modem_node.transport.send_command(TestRequestCommand(target_id=target_id))

    def query_quality(self) -> None:
        self._modem_node.transport.send_command(QualityQueryCommand())

    def query_modem_status(self) -> None:
        self._modem_node.query_status()

    def broadcast_position(self) -> None:
        if self._position is not None:
            self._modem_node.broadcast(
                PositionMessage(
                    node_id=self._node_id,
                    coord=self._position,
                    depth=self._depth,
                ),
            )

    def calculate_position(self) -> Optional[Coord]:
        usable = [
            known_node
            for known_node in self._known_nodes.values()
            if known_node.position is not None and known_node.last_range is not None
        ]

        if len(usable) < 3:
            return None

        positions: list[Coord] = []
        distances: list[float] = []

        for known_node in usable:
            assert known_node.position is not None
            assert known_node.last_range is not None

            distance = known_node.last_range
            if self._depth != 0.0 or known_node.depth != 0.0:
                distance = self._calculation.project_3d_to_2d(
                    distance,
                    self._depth,
                    known_node.depth,
                )

            positions.append(known_node.position)
            distances.append(distance)

        result = self._calculation.trilaterate(positions, distances)
        self._position = Coord(lat=result.lat, lon=result.lon)
        self._sync_in_memory_transport()

        if self._cb_position_changed is not None:
            self._cb_position_changed(self._position)
        return self._position

    def _handle_position_broadcast(self, sender_id: str, message: PositionMessage) -> None:
        if message.node_id != sender_id:
            logger.warning(
                "Position broadcast sender_id %s disagrees with payload node_id %s; using sender_id",
                sender_id,
                message.node_id,
            )
        node_id = sender_id
        self._ensure_known_node(node_id)
        self._known_nodes[node_id].position = message.coord
        self._known_nodes[node_id].depth = message.depth
        self._known_nodes[node_id].last_seen = time.time()
        if self._cb_known_nodes_changed is not None:
            self._cb_known_nodes_changed(dict(self._known_nodes))

    def _handle_roundtrip_response(self, responder_id: str, timestamp_counts: int) -> None:
        self._ensure_known_node(responder_id)
        distance = self._calculation.timestamp_to_distance(timestamp_counts, self._sound_speed)
        self._known_nodes[responder_id].last_range = distance
        self._known_nodes[responder_id].last_seen = time.time()
        if self._cb_known_nodes_changed is not None:
            self._cb_known_nodes_changed(dict(self._known_nodes))
        self._maybe_infer_position()

    def _maybe_broadcast_position(self) -> None:
        if self._capabilities.is_broadcasting_own_position:
            self.broadcast_position()

    def _maybe_infer_position(self) -> None:
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
        if node_id not in self._known_nodes:
            self._known_nodes[node_id] = KnownNode(node_id=node_id)

    def _sync_in_memory_transport(self) -> None:
        transport = self._modem_node.transport
        if isinstance(transport, InMemoryTransport):
            transport.position = self._position
            transport.get_depth_callback = self.get_depth
