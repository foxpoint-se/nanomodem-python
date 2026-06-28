"""Launcher: creates Tkinter root, InMemoryBus, and tiled ControllerWindows.

Creates a mock scenario with 1 host + 3 beacons.
"""

from __future__ import annotations

import tkinter as tk
from typing import TypedDict

from nanomodem.constants import SOUND_SPEED_WATER_M_S
from nanomodem.core.transports import InMemoryBus
from nanomodem.types import Coord

from nanomodem_demo.controller import ControllerWindow
from nanomodem_demo.node_builder import build_in_memory_node
from nanomodem_demo.startup import verify_modem_id_at_startup

MAP_CENTER = (59.310153, 17.975189)
MAP_ZOOM = 16

Config = TypedDict("Config", {"id": str, "name": str, "sim_pos": Coord, "initial_depth": float})


def launch_mock(root: tk.Tk) -> list[ControllerWindow]:
    """Create a mock scenario with 4 nodes, each in its own ControllerWindow."""

    bus = InMemoryBus(sound_speed=SOUND_SPEED_WATER_M_S)

    host_config: Config = {
        "id": "001",
        "name": "Host (Tracker)",
        "sim_pos": Coord(lat=59.310153, lon=17.975189),
        "initial_depth": 5.0,
    }

    beacons_config: list[Config] = [
        {"id": "002", "name": "Beacon 1", "sim_pos": Coord(lat=59.310500, lon=17.974500), "initial_depth": 0.0},
        {"id": "003", "name": "Beacon 2", "sim_pos": Coord(lat=59.310800, lon=17.976000), "initial_depth": 0.0},
        {"id": "004", "name": "Beacon 3", "sim_pos": Coord(lat=59.309500, lon=17.975500), "initial_depth": 0.0},
    ]

    all_ids = [host_config["id"]] + [b["id"] for b in beacons_config]

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

    host_id = host_config["id"]
    host_sim_pos = host_config["sim_pos"]
    host_node = build_in_memory_node(
        host_id,
        bus,
        position=host_sim_pos,
        sound_speed=SOUND_SPEED_WATER_M_S,
    )

    host_controller = ControllerWindow(
        root=root,
        node=host_node,
        pretty_name=str(host_config["name"]),
        peer_ids=[str(b["id"]) for b in beacons_config],
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        window_geometry=get_geometry(0),
    )

    host_controller.node.set_depth(float(host_config["initial_depth"]))

    for b in beacons_config:
        host_controller.node.set_known_node_position(str(b["id"]), b["sim_pos"])
        host_controller.node.set_known_node_depth(str(b["id"]), 0.0)

    controllers.append(host_controller)

    for i, b_conf in enumerate(beacons_config, start=1):
        b_id = str(b_conf["id"])
        b_sim_pos = b_conf["sim_pos"]
        beacon_node = build_in_memory_node(
            b_id,
            bus,
            position=b_sim_pos,
            sound_speed=SOUND_SPEED_WATER_M_S,
        )

        b_controller = ControllerWindow(
            root=root,
            node=beacon_node,
            pretty_name=str(b_conf["name"]),
            peer_ids=[str(nid) for nid in all_ids if nid != b_id],
            map_center=MAP_CENTER,
            map_zoom=MAP_ZOOM,
            window_geometry=get_geometry(i),
        )

        b_controller.node.set_position(b_sim_pos)
        b_controller.node.set_depth(0.0)

        controllers.append(b_controller)

    for controller in controllers:
        verify_modem_id_at_startup(controller.node)

    return controllers


def main() -> None:
    root = tk.Tk()
    root.withdraw()

    _controllers = launch_mock(root)

    root.mainloop()


if __name__ == "__main__":
    main()
