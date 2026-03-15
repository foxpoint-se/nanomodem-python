"""Launcher: creates Tkinter root, MockEther, and tiled ControllerWindows.

Usage:
    Called from gui/__main__.py.
    Creates a mock scenario with 1 host + 3 beacons.
"""

from __future__ import annotations

import tkinter as tk

from nanomodem.transport import MockEther, MockTransport
from nanomodem.types import Coord

from .controller import ControllerWindow

MAP_CENTER = (59.310153, 17.975189)
MAP_ZOOM = 17


def launch_mock(root: tk.Tk) -> list[ControllerWindow]:
    """Create a mock scenario with 4 nodes, each in its own ControllerWindow."""

    ether = MockEther(sound_speed=1500.0)

    # Initial positions for simulation (mock ether)
    # Host starts at center, beacons in a triangle around it
    initial_sim_positions = {
        "001": Coord(lat=59.310153, lon=17.975189, depth=5.0),
        "002": Coord(lat=59.310500, lon=17.974500, depth=0.0),
        "003": Coord(lat=59.310800, lon=17.976000, depth=0.0),
        "004": Coord(lat=59.309500, lon=17.975500, depth=0.0),
    }

    nodes_config: list[tuple[str, str]] = [
        ("001", "Host"),
        ("002", "Beacon 1"),
        ("003", "Beacon 2"),
        ("004", "Beacon 3"),
    ]

    all_ids = [nid for nid, _ in nodes_config]

    # Compute window tiling (2x2 grid)
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    win_w = min(480, screen_w // 2)
    win_h = min(780, screen_h // 2)

    controllers: list[ControllerWindow] = []

    for i, (node_id, pretty_name) in enumerate(nodes_config):
        transport = MockTransport(node_id, ether)
        
        # Initialize simulated position for mock
        if node_id in initial_sim_positions:
            transport.position = initial_sim_positions[node_id]

        peer_ids = [nid for nid in all_ids if nid != node_id]

        col = i % 2
        row = i // 2
        x = col * win_w
        y = row * win_h
        geometry = f"{win_w}x{win_h}+{x}+{y}"

        # Define mock-only callbacks for simulated position
        def get_sim_pos(t=transport):
            return t.position
        
        def set_sim_pos(coord, t=transport):
            t.position = coord

        controller = ControllerWindow(
            root=root,
            node_id=node_id,
            pretty_name=pretty_name,
            transport=transport,
            peer_ids=peer_ids,
            map_center=MAP_CENTER,
            map_zoom=MAP_ZOOM,
            window_geometry=geometry,
            get_sim_pos_callback=get_sim_pos,
            set_sim_pos_callback=set_sim_pos,
        )
        
        # Pre-populate registry for the Host (001)
        # In a real experiment, you'd know where your beacons are.
        if node_id == "001":
            for bid in ["002", "003", "004"]:
                controller.node.set_known_node_position(bid, initial_sim_positions[bid])
        
        # For beacons, they might also know where each other are
        if node_id in ["002", "003", "004"]:
            controller.node.set_position(initial_sim_positions[node_id])

        controllers.append(controller)

    return controllers
