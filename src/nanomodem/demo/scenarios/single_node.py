"""Launcher for a single controller instance (mock or serial)."""

from __future__ import annotations

import argparse
import logging
import sys
import tkinter as tk
from typing import Optional

from nanomodem.codecs.v3 import Codec
from nanomodem.demo.controller import ControllerWindow
from nanomodem.drivers.v3 import NanomodemV3Driver
from nanomodem.protocols import TransportProtocol
from nanomodem.transports.mock import MockEther, MockTransport
from nanomodem.transports.serial import SerialTransport
from nanomodem.types import Coord

MAP_CENTER = (59.310153, 17.975189)
MAP_ZOOM = 17

logger = logging.getLogger(__name__)


def launch_single(
    root: tk.Tk,
    node_id: str,
    port: Optional[str] = None,
    baud: int = 9600,
) -> ControllerWindow:
    """Create a single controller with the given ID and transport."""
    transport: TransportProtocol

    if port is None:
        # Mock mode
        ether = MockEther(sound_speed=1500.0)
        mock_transport = MockTransport(node_id, ether)
        transport = mock_transport

        def get_sim_pos(t: MockTransport = mock_transport) -> Optional[Coord]:
            return t.position

        def set_sim_pos(coord: Coord, t: MockTransport = mock_transport) -> None:
            t.position = coord

        get_sim_pos_callback = get_sim_pos
        set_sim_pos_callback = set_sim_pos
    else:
        # Serial mode
        driver = NanomodemV3Driver(Codec())
        transport = SerialTransport(node_id=node_id, port=port, driver=driver, baud=baud)
        get_sim_pos_callback = None
        set_sim_pos_callback = None

    controller = ControllerWindow(
        root=root,
        node_id=node_id,
        pretty_name=f"Node {node_id}",
        transport=transport,
        peer_ids=[],  # Starts empty
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        get_sim_pos_callback=get_sim_pos_callback,
        set_sim_pos_callback=set_sim_pos_callback,
    )

    if isinstance(transport, MockTransport):
        # Link mock transport to pull depth from the node
        transport.get_depth_callback = controller.node.get_depth
    elif isinstance(transport, SerialTransport):
        # Start the background reader thread for real serial
        transport.start()

    return controller


def main() -> None:
    parser = argparse.ArgumentParser(description="Acoustic modem controller")
    parser.add_argument("node_id", type=str, help="3-digit node ID (e.g. 001)")
    parser.add_argument("--port", type=str, help="Serial port (e.g. /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate (default: 9600)")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level (default: INFO)")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(message)s",  # Keep it clean for serial logs
    )

    node_id = args.node_id

    # Simple validation
    if not (len(node_id) == 3 and node_id.isdigit()):
        print(f"\nError: Invalid node ID '{node_id}'. Must be a 3-digit numeric string (001-255).\n")
        sys.exit(1)

    print("Starting controller")
    print(f"  Node ID: {node_id}")
    if args.port:
        print(f"  Transport: SerialTransport ({args.port}, {args.baud} baud)")
    else:
        print("  Transport: MockTransport (in-memory)")
    print(f"  Log level: {args.log_level.upper()}")
    print("GUI opened. Use console to see incoming messages.")

    root = tk.Tk()
    root.withdraw()  # Hide the main root window

    _controller = launch_single(root, node_id, port=args.port, baud=args.baud)

    root.mainloop()


if __name__ == "__main__":
    main()
