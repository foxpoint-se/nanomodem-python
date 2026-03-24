"""Launcher: creates Tkinter root, MockEther, and tiled ControllerWindows.

Usage:
    Called from gui/__main__.py.
    Creates a mock scenario with 1 host + 3 beacons.
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional

from nanomodem.transport import MockEther, MockTransport
from nanomodem.types import Coord

from ..controller import ControllerWindow

MAP_CENTER = (59.310153, 17.975189)
MAP_ZOOM = 17


def launch_mock(root: tk.Tk) -> list[ControllerWindow]:
    """Create a mock scenario with 4 nodes, each in its own ControllerWindow.

    The 'Host' node is the primary unit we are testing, so it receives
    simulation callbacks to control its 'physical' position in the mock ether.
    The 'Beacons' are static units that do not receive simulation controls.
    """

    ether = MockEther(sound_speed=1500.0)

    # 1. Scenario Configuration
    host_config = {
        "id": "001",
        "name": "Host (Tracker)",
        "sim_pos": Coord(lat=59.310153, lon=17.975189),
        "initial_depth": 5.0,
    }

    beacons_config = [
        {"id": "002", "name": "Beacon 1", "sim_pos": Coord(lat=59.310500, lon=17.974500)},
        {"id": "003", "name": "Beacon 2", "sim_pos": Coord(lat=59.310800, lon=17.976000)},
        {"id": "004", "name": "Beacon 3", "sim_pos": Coord(lat=59.309500, lon=17.975500)},
    ]

    all_ids = [host_config["id"]] + [b["id"] for b in beacons_config]

    # 2. Window Tiling Logic
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    win_w = min(480, screen_w // 2)
    win_h = min(780, screen_h // 2)

    def get_geometry(index: int) -> str:
        col = index % 2
        row = index // 2
        x = col * win_w
        y = row * win_h
        return f"{win_w}x{win_h}+{x}+{y}"

    controllers: list[ControllerWindow] = []

    # 3. Instantiate the Host (The node we pretend we are using)
    # This one gets the callbacks so we can move its "Physical" location
    # while its "Logical" location remains unknown.
    host_id: str = str(host_config["id"])
    host_sim_pos: Coord = host_config["sim_pos"]  # type: ignore
    host_transport = MockTransport(host_id, ether)
    host_transport.position = host_sim_pos

    def get_sim_pos(t: MockTransport = host_transport) -> Optional[Coord]:
        return t.position

    def set_sim_pos(coord: Coord, t: MockTransport = host_transport) -> None:
        t.position = coord

    host_controller = ControllerWindow(
        root=root,
        node_id=host_id,
        pretty_name=str(host_config["name"]),
        transport=host_transport,
        peer_ids=[str(b["id"]) for b in beacons_config],
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        window_geometry=get_geometry(0),
        get_sim_pos_callback=get_sim_pos,
        set_sim_pos_callback=set_sim_pos,
    )

    # Set the initial logical depth for the host
    host_controller.node.set_depth(float(host_config["initial_depth"]))  # type: ignore

    # Link the mock transport to pull depth from the node
    host_transport.get_depth_callback = host_controller.node.get_depth

    # Pre-populate host registry with beacon positions (simulating a known environment)
    for b in beacons_config:
        host_controller.node.set_known_node_position(str(b["id"]), b["sim_pos"])  # type: ignore
        host_controller.node.set_known_node_depth(str(b["id"]), 0.0)

    controllers.append(host_controller)

    # 4. Instantiate Beacons (Physical units that just "exist" at a spot)
    # These do NOT get simulation callbacks because they are static in this scenario.
    for i, b_conf in enumerate(beacons_config, start=1):
        b_id: str = str(b_conf["id"])
        b_sim_pos: Coord = b_conf["sim_pos"]  # type: ignore
        b_transport = MockTransport(b_id, ether)
        b_transport.position = b_sim_pos

        b_controller = ControllerWindow(
            root=root,
            node_id=b_id,
            pretty_name=str(b_conf["name"]),
            transport=b_transport,
            peer_ids=[str(nid) for nid in all_ids if nid != b_id],
            map_center=MAP_CENTER,
            map_zoom=MAP_ZOOM,
            window_geometry=get_geometry(i),
            get_sim_pos_callback=None,  # Disabled for beacons
            set_sim_pos_callback=None,
        )

        # Beacons know their own position in this scenario
        b_controller.node.set_position(b_sim_pos)
        b_controller.node.set_depth(0.0)

        # Link the mock transport to pull depth from the node
        b_transport.get_depth_callback = b_controller.node.get_depth

        controllers.append(b_controller)

    return controllers


def main() -> None:
    root = tk.Tk()
    root.withdraw()  # Hide root window; ControllerWindows are Toplevels

    _controllers = launch_mock(root)

    root.mainloop()


if __name__ == "__main__":
    main()
