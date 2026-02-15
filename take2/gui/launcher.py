"""Launcher: creates Tkinter root, MockEther, and tiled ControllerWindows.

Usage:
    Called from gui/__main__.py.
    Creates a mock scenario with 1 host + 3 beacons.
"""

from __future__ import annotations

import tkinter as tk

from nanomodem.transport import MockEther, MockTransport

from .controller import ControllerWindow

MAP_CENTER = (59.310153, 17.975189)
MAP_ZOOM = 17


def launch_mock(root: tk.Tk) -> list[ControllerWindow]:
    """Create a mock scenario with 4 nodes, each in its own ControllerWindow."""

    ether = MockEther(sound_speed=1500.0)

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
        peer_ids = [nid for nid in all_ids if nid != node_id]

        col = i % 2
        row = i // 2
        x = col * win_w
        y = row * win_h
        geometry = f"{win_w}x{win_h}+{x}+{y}"

        controller = ControllerWindow(
            root=root,
            node_id=node_id,
            pretty_name=pretty_name,
            transport=transport,
            peer_ids=peer_ids,
            map_center=MAP_CENTER,
            map_zoom=MAP_ZOOM,
            window_geometry=geometry,
        )
        controllers.append(controller)

    return controllers
