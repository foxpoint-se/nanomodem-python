"""Serial bridge demo with God View Simulator.

Two controllers on socat PTYs; simulator brokers acoustic traffic and metadata.

Usage:
    python -m nanomodem.demo.scenarios.serial_bridge_with_god_view
"""

from __future__ import annotations

import atexit
import logging
import re
import subprocess
import time
import tkinter as tk

from nanomodem.codecs.v3 import Codec
from nanomodem.demo.controller import ControllerWindow
from nanomodem.demo.scenarios.single_node import _start_metadata_client
from nanomodem.demo.simulator.app import launch_simulator
from nanomodem.demo.startup import verify_modem_id_at_startup
from nanomodem.drivers.v3 import NanomodemV3Driver
from nanomodem.transports.serial import SerialTransport
from nanomodem.types import Coord

MAP_CENTER = (59.310153, 17.975189)
MAP_ZOOM = 16

logger = logging.getLogger(__name__)

_SOCAT_PTY_RE = re.compile(r"PTY is (/dev/[^\s]+)")
_socat_processes: list[subprocess.Popen[bytes]] = []


def spawn_socat_pair() -> tuple[str, str]:
    """Create a virtual serial pair via socat (same as manual §2 setup)."""
    proc = subprocess.Popen(
        ["socat", "-d", "-d", "pty,raw,echo=0", "pty,raw,echo=0"],
        stderr=subprocess.PIPE,
    )
    _socat_processes.append(proc)
    ptys: list[str] = []
    assert proc.stderr is not None
    while len(ptys) < 2:
        line = proc.stderr.readline().decode()
        match = _SOCAT_PTY_RE.search(line)
        if match:
            ptys.append(match.group(1))
    return ptys[0], ptys[1]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("\n=== Serial Bridge with God View Simulator ===\n")

    root = tk.Tk()
    root.withdraw()

    print("Creating virtual serial ports (socat)...")
    pty_a_controller, pty_a_simulator = spawn_socat_pair()
    pty_b_controller, pty_b_simulator = spawn_socat_pair()
    print(f"  Node 001: controller={pty_a_controller}, simulator={pty_a_simulator}")
    print(f"  Node 002: controller={pty_b_controller}, simulator={pty_b_simulator}")

    print("\nLaunching God View Simulator...")
    simulator = launch_simulator(root, host="127.0.0.1", port=5555)
    time.sleep(0.5)

    simulator.state.set_physical_position("001", Coord(lat=59.310153, lon=17.975189), depth=5.0)
    simulator.state.set_physical_position("002", Coord(lat=59.310253, lon=17.975289), depth=5.0)

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    win_w = min(480, screen_w // 3)
    win_h = min(780, screen_h)

    print("Launching controllers...")
    driver_a = NanomodemV3Driver(Codec())
    transport_a = SerialTransport(node_id="001", port=pty_a_controller, driver=driver_a)
    controller_a = ControllerWindow(
        root=root,
        node_id="001",
        pretty_name="Node A (Host)",
        transport=transport_a,
        peer_ids=[],
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        window_geometry=f"{win_w}x{win_h}+0+0",
    )

    driver_b = NanomodemV3Driver(Codec())
    transport_b = SerialTransport(node_id="002", port=pty_b_controller, driver=driver_b)
    controller_b = ControllerWindow(
        root=root,
        node_id="002",
        pretty_name="Node B (Beacon)",
        transport=transport_b,
        peer_ids=[],
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        window_geometry=f"{win_w}x{win_h}+{win_w}+0",
    )

    simulator.window.geometry(f"{win_w}x{win_h}+{win_w * 2}+0")

    transport_a.start()
    transport_b.start()

    verify_modem_id_at_startup(controller_a.node)
    verify_modem_id_at_startup(controller_b.node)

    time.sleep(0.3)
    _start_metadata_client(
        root,
        controller_a,
        host="127.0.0.1",
        port=5555,
        acoustic_config={"type": "serial", "pty_path": pty_a_simulator},
    )
    _start_metadata_client(
        root,
        controller_b,
        host="127.0.0.1",
        port=5555,
        acoustic_config={"type": "serial", "pty_path": pty_b_simulator},
    )

    def cleanup() -> None:
        print("\nCleaning up...")
        transport_a.stop()
        transport_b.stop()
        simulator.backend.stop()
        for proc in _socat_processes:
            proc.terminate()

    atexit.register(cleanup)

    print("\n=== Scenario Ready ===")
    print("1. Push GPS (or edit position) on each controller")
    print("2. Broadcast position on one node")
    print("3. Other node should see it in registry; then Request range\n")

    root.mainloop()


if __name__ == "__main__":
    main()
