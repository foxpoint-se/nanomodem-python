"""Launcher for a single controller instance (mock, serial, or network)."""

from __future__ import annotations

import argparse
import logging
import sys
import tkinter as tk
from typing import Optional

from nanomodem.constants import SOUND_SPEED_WATER_M_S
from nanomodem.core.transports import InMemoryBus
from nanomodem.types import Coord

from nanomodem_demo.controller import ControllerWindow
from nanomodem_demo.node_builder import build_in_memory_node, build_positioning_node, build_serial_node
from nanomodem_demo.simulator import AcousticTransportConfig, SimulatorInboundHandlers, SimulatorMetadataClient
from nanomodem_demo.startup import verify_modem_id_at_startup
from nanomodem_demo.transports import NetworkMockTransport

MAP_CENTER = (59.310153, 17.975189)
MAP_ZOOM = 16

logger = logging.getLogger(__name__)


def launch_single(
    root: tk.Tk,
    node_id: str,
    port: Optional[str] = None,
    baud: int = 9600,
    network_host: Optional[str] = None,
    network_port: Optional[int] = None,
    world_host: Optional[str] = None,
    world_port: Optional[int] = None,
    world_pty: Optional[str] = None,
    sound_speed: float = SOUND_SPEED_WATER_M_S,
) -> ControllerWindow:
    """Create a single controller with the given ID and transport."""
    acoustic_config: Optional[AcousticTransportConfig] = None

    network_transport: NetworkMockTransport | None = None

    if network_host and network_port:
        network_transport = NetworkMockTransport(node_id, host=network_host, port=network_port)
        node = build_positioning_node(node_id, network_transport, sound_speed=sound_speed)
        acoustic_config = None
    elif port:
        node = build_serial_node(node_id, port, baud=baud, sound_speed=sound_speed)
        acoustic_config = {"type": "serial", "pty_path": world_pty} if world_pty else None
    else:
        bus = InMemoryBus(sound_speed=sound_speed)
        node = build_in_memory_node(node_id, bus, sound_speed=sound_speed)

    controller = ControllerWindow(
        root=root,
        node=node,
        pretty_name=f"Node {node_id}",
        peer_ids=[],
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
    )

    wire_transport = node.transport
    if hasattr(wire_transport, "start"):
        wire_transport.start()

    if network_transport is not None:
        network_transport.on_gps_update(lambda coord: _schedule_position_update(root, controller, coord))

    if world_host and world_port and acoustic_config:
        metadata_client = _start_metadata_client(root, controller, world_host, world_port, acoustic_config)
        controller.register_shutdown_callback(metadata_client.stop)

    verify_modem_id_at_startup(controller.node)

    return controller


def _schedule_position_update(root: tk.Tk, controller: ControllerWindow, coord: Coord) -> None:
    """Apply a GPS position on the Tk main thread."""

    def apply() -> None:
        controller.node.set_position(coord)

    root.after(0, apply)


def _start_metadata_client(
    root: tk.Tk,
    controller: ControllerWindow,
    host: str,
    port: int,
    acoustic_config: AcousticTransportConfig,
) -> SimulatorMetadataClient:
    """Connect to simulator for metadata (serial mode: GPS push, registration)."""
    handlers = SimulatorInboundHandlers(
        on_gps_update=lambda coord: _schedule_position_update(root, controller, coord),
    )
    client = SimulatorMetadataClient(
        node_id=controller.node.node_id,
        host=host,
        port=port,
        acoustic_transport=acoustic_config,
        handlers=handlers,
    )
    client.start()
    return client


def main() -> None:
    parser = argparse.ArgumentParser(description="Acoustic modem controller")
    parser.add_argument("node_id", type=str, help="3-digit node ID (e.g. 001)")
    parser.add_argument("--port", type=str, help="Serial port (e.g. /dev/ttyUSB0 or /dev/pts/4)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate (default: 9600)")
    parser.add_argument("--network", type=str, help="Network simulator address (e.g. 127.0.0.1:5555)")
    parser.add_argument(
        "--world",
        type=str,
        help="World Backend address for metadata (e.g. 127.0.0.1:5555)",
    )
    parser.add_argument(
        "--world-port",
        type=str,
        help="PTY path for Simulator to listen on (serial mode only, e.g. /dev/pts/5)",
    )
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level (default: INFO)")
    parser.add_argument(
        "--sound-speed",
        type=float,
        default=SOUND_SPEED_WATER_M_S,
        help="Speed of sound in m/s for ranging (default: 1500 water; use 340 for air bench)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(message)s",
    )

    node_id = args.node_id

    if not (len(node_id) == 3 and node_id.isdigit()):
        print(f"\nError: Invalid node ID '{node_id}'. Must be a 3-digit numeric string (001-255).\n")
        sys.exit(1)

    network_host = None
    network_port = None
    if args.network:
        parts = args.network.split(":")
        network_host = parts[0]
        network_port = int(parts[1]) if len(parts) > 1 else 5555

    world_host = None
    world_port = None
    if args.world:
        parts = args.world.split(":")
        world_host = parts[0]
        world_port = int(parts[1]) if len(parts) > 1 else 5555

    print("Starting controller")
    print(f"  Node ID: {node_id}")
    if network_host and network_port:
        print(f"  Transport: NetworkMockTransport ({network_host}:{network_port})")
    elif args.port:
        print(f"  Transport: SerialWireTransport ({args.port}, {args.baud} baud)")
        if world_host and world_port and args.world_port:
            print(f"  World Backend: {world_host}:{world_port}")
            print(f"  World PTY: {args.world_port}")
    else:
        print("  Transport: InMemoryTransport (in-memory)")
    print(f"  Log level: {args.log_level.upper()}")
    print(f"  Sound speed: {args.sound_speed:.0f} m/s")
    print("GUI opened. Use console to see incoming messages.")

    root = tk.Tk()
    root.withdraw()

    _controller = launch_single(
        root,
        node_id,
        port=args.port,
        baud=args.baud,
        network_host=network_host,
        network_port=network_port,
        world_host=world_host,
        world_port=world_port,
        world_pty=args.world_port,
        sound_speed=args.sound_speed,
    )

    root.mainloop()


if __name__ == "__main__":
    main()
