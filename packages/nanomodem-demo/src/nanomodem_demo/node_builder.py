"""Helpers for constructing PositioningNode stacks in demo scenarios."""

from __future__ import annotations

from typing import Callable, Optional

from nanomodem.constants import SOUND_SPEED_WATER_M_S
from nanomodem.core.driver import NanomodemV3Driver
from nanomodem.core.modem_node import ModemNode
from nanomodem.core.protocols import WireTransport
from nanomodem.core.transports import InMemoryBus, InMemoryTransport, SerialWireTransport
from nanomodem.core.transports.in_memory import InMemoryTransport as InMemoryTransportType
from nanomodem.positioning import BasicPositionCodec, PositioningNode
from nanomodem.positioning.types import KnownNode
from nanomodem.types import Coord

PositionChangedCallback = Callable[[Optional[Coord]], None]
DepthChangedCallback = Callable[[float], None]
KnownNodesChangedCallback = Callable[[dict[str, KnownNode]], None]


def build_positioning_node(
    node_id: str,
    transport: WireTransport,
    *,
    position: Optional[Coord] = None,
    sound_speed: float = SOUND_SPEED_WATER_M_S,
    on_position_changed: Optional[PositionChangedCallback] = None,
    on_depth_changed: Optional[DepthChangedCallback] = None,
    on_known_nodes_changed: Optional[KnownNodesChangedCallback] = None,
) -> PositioningNode:
    """Wire a PositioningNode on top of a WireTransport."""
    modem = ModemNode(node_id, transport, BasicPositionCodec())
    node = PositioningNode(
        node_id=node_id,
        modem_node=modem,
        position=position,
        sound_speed=sound_speed,
        on_position_changed=on_position_changed,
        on_depth_changed=on_depth_changed,
        on_known_nodes_changed=on_known_nodes_changed,
    )
    _link_in_memory_transport(node, transport)
    return node


def build_in_memory_node(
    node_id: str,
    bus: InMemoryBus,
    *,
    position: Optional[Coord] = None,
    sound_speed: float = SOUND_SPEED_WATER_M_S,
    on_position_changed: Optional[PositionChangedCallback] = None,
    on_depth_changed: Optional[DepthChangedCallback] = None,
    on_known_nodes_changed: Optional[KnownNodesChangedCallback] = None,
) -> PositioningNode:
    """Create a PositioningNode backed by InMemoryTransport."""
    transport = InMemoryTransport(node_id, bus)
    return build_positioning_node(
        node_id,
        transport,
        position=position,
        sound_speed=sound_speed,
        on_position_changed=on_position_changed,
        on_depth_changed=on_depth_changed,
        on_known_nodes_changed=on_known_nodes_changed,
    )


def build_serial_node(
    node_id: str,
    port: str,
    *,
    baud: int = 9600,
    position: Optional[Coord] = None,
    sound_speed: float = SOUND_SPEED_WATER_M_S,
    on_position_changed: Optional[PositionChangedCallback] = None,
    on_depth_changed: Optional[DepthChangedCallback] = None,
    on_known_nodes_changed: Optional[KnownNodesChangedCallback] = None,
) -> PositioningNode:
    """Create a PositioningNode backed by SerialWireTransport."""
    transport = SerialWireTransport(port=port, driver=NanomodemV3Driver(), baud=baud)
    return build_positioning_node(
        node_id,
        transport,
        position=position,
        sound_speed=sound_speed,
        on_position_changed=on_position_changed,
        on_depth_changed=on_depth_changed,
        on_known_nodes_changed=on_known_nodes_changed,
    )


def _link_in_memory_transport(node: PositioningNode, transport: WireTransport) -> None:
    if isinstance(transport, InMemoryTransportType):
        transport.position = node.get_position()
        transport.get_depth_callback = node.get_depth
