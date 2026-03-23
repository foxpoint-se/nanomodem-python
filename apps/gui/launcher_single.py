"""Launcher for a single, clean controller instance.

Usage:
    PYTHONPATH=. python -m gui.launcher_single <node_id>
"""

from __future__ import annotations

import sys
import tkinter as tk

from foxpoint.nanomodem.transport import MockEther, MockTransport
from foxpoint.nanomodem.types import Coord

from .controller import ControllerWindow

MAP_CENTER = (59.310153, 17.975189)
MAP_ZOOM = 17


def launch_single(root: tk.Tk, node_id: str) -> ControllerWindow:
    """Create a single clean controller with the given ID."""
    # We create a local ether for this single node. 
    # In a real scenario with multiple processes, we'd use a different transport.
    ether = MockEther(sound_speed=1500.0)
    
    transport = MockTransport(node_id, ether)
    
    def get_sim_pos(t=transport): return t.position
    def set_sim_pos(coord, t=transport): t.position = coord

    controller = ControllerWindow(
        root=root,
        node_id=node_id,
        pretty_name=f"Node {node_id}",
        transport=transport,
        peer_ids=[],  # Starts empty
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        get_sim_pos_callback=get_sim_pos,
        set_sim_pos_callback=set_sim_pos,
    )
    
    # Link mock transport to pull depth from the node
    transport.get_depth_callback = controller.node.get_depth
    
    return controller


def main():
    if len(sys.argv) < 2:
        print("\nError: Missing node ID.")
        print("Usage: PYTHONPATH=. python -m gui.launcher_single <node_id>")
        print("Example: PYTHONPATH=. python -m gui.launcher_single 001\n")
        sys.exit(1)

    node_id = sys.argv[1]
    
    # Simple validation
    if not (len(node_id) == 3 and node_id.isdigit()):
        print(f"\nError: Invalid node ID '{node_id}'. Must be a 3-digit numeric string (001-255).\n")
        sys.exit(1)

    root = tk.Tk()
    root.withdraw()  # Hide the main root window

    _controller = launch_single(root, node_id)
    
    root.mainloop()


if __name__ == "__main__":
    main()
