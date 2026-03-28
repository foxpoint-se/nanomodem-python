"""Bridge scenario: two nodes over virtual serial ports, all in one process.

Spawns two socat pairs automatically, starts broker relay threads, and opens
two ControllerWindows backed by real SerialTransport, driver, and codec.

Prerequisite: socat must be installed.
    sudo apt install socat
"""

from __future__ import annotations

import atexit
import re
import subprocess
import threading
import tkinter as tk
from datetime import datetime
from typing import Callable, Optional

import serial

from nanomodem.codecs.v3 import Codec
from nanomodem.drivers.v3 import NanomodemV3Driver
from nanomodem.gui.controller import ControllerWindow
from nanomodem.gui.scenarios.modem_relay import (
    broadcast_ack,
    broadcast_relay,
    distance_metres,
    parse_broadcast,
    parse_ping,
    ping_ack,
    range_response,
)
from nanomodem.transports.serial import SerialTransport
from nanomodem.types import Coord

MAP_CENTER = (59.310153, 17.975189)
MAP_ZOOM = 17
SOUND_SPEED = 1500.0
BAUD = 9600
TIMEOUT = 0.1

# Physical positions used by broker for range simulation (lat, lon, depth_m).
# Node A's position is updated at runtime via its sim_pos panel.
POSITIONS: dict[str, tuple[float, float, float]] = {
    "001": (59.310153, 17.975189, 0.0),
    "002": (59.310500, 17.974500, 0.0),
}

_SOCAT_PTY_RE = re.compile(r"PTY is (/dev/[^\s]+)")


# ------------------------------------------------------------------ #
#  socat                                                               #
# ------------------------------------------------------------------ #


def _spawn_socat_pair() -> tuple[str, str, subprocess.Popen[bytes]]:
    """Spawn a socat virtual serial pair. Returns (pty_a, pty_b, process)."""
    proc = subprocess.Popen(
        ["socat", "-d", "-d", "pty,raw,echo=0", "pty,raw,echo=0"],
        stderr=subprocess.PIPE,
    )
    ptys: list[str] = []
    assert proc.stderr is not None
    while len(ptys) < 2:
        line = proc.stderr.readline().decode()
        m = _SOCAT_PTY_RE.search(line)
        if m:
            ptys.append(m.group(1))
    return ptys[0], ptys[1], proc


# ------------------------------------------------------------------ #
#  Broker relay                                                        #
# ------------------------------------------------------------------ #


def _open_broker_port(path: str) -> serial.Serial:
    return serial.Serial(
        port=path,
        baudrate=BAUD,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=TIMEOUT,
    )


def _log_bus(label: str, raw: bytes) -> None:
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] [{label}] {raw.decode('ascii', errors='replace').strip()}")


def _relay_loop(
    src: serial.Serial,
    dst: serial.Serial,
    src_id: str,
    dst_id: str,
    label: str,
    positions: dict[str, tuple[float, float, float]],
    dst_lock: threading.Lock,
) -> None:
    while True:
        try:
            raw = src.readline()
            if not raw:
                continue

            _log_bus(label, raw)

            broadcast = parse_broadcast(raw)
            if broadcast is not None:
                nn, body = broadcast
                src.write(broadcast_ack(nn))
                with dst_lock:
                    dst.write(broadcast_relay(src_id, nn, body))
                continue

            target_id = parse_ping(raw)
            if target_id is not None:
                src.write(ping_ack(target_id))
                sender_pos = positions.get(src_id)
                target_pos = positions.get(target_id)
                if sender_pos is not None and target_pos is not None:
                    dist = distance_metres(sender_pos, target_pos)
                    resp = range_response(target_id, dist, SOUND_SPEED)
                    _log_bus(f"BROKER→{src_id}", resp)
                    src.write(resp)
                else:
                    print(f"[BROKER] Unknown node in range request: {src_id!r} → {target_id!r}")
                continue

            with dst_lock:
                dst.write(raw)

        except serial.SerialException as e:
            print(f"[BROKER] Serial error on {label}: {e}")
            break
        except Exception as e:
            print(f"[BROKER] Unexpected error on {label}: {e}")


def _start_broker_threads(
    port_a: serial.Serial,
    port_b: serial.Serial,
    node_a_id: str,
    node_b_id: str,
    positions: dict[str, tuple[float, float, float]],
) -> None:
    lock_a = threading.Lock()
    lock_b = threading.Lock()
    threading.Thread(
        target=_relay_loop,
        args=(port_a, port_b, node_a_id, node_b_id, f"{node_a_id}→{node_b_id}", positions, lock_b),
        daemon=True,
        name="relay-a",
    ).start()
    threading.Thread(
        target=_relay_loop,
        args=(port_b, port_a, node_b_id, node_a_id, f"{node_b_id}→{node_a_id}", positions, lock_a),
        daemon=True,
        name="relay-b",
    ).start()


# ------------------------------------------------------------------ #
#  Sim pos callbacks                                                   #
# ------------------------------------------------------------------ #


def _make_get_sim_pos(node_id: str) -> Callable[[], Optional[Coord]]:
    def get_sim_pos() -> Optional[Coord]:
        lat, lon, _ = POSITIONS[node_id]
        return Coord(lat=lat, lon=lon)

    return get_sim_pos


def _make_set_sim_pos(node_id: str) -> Callable[[Coord], None]:
    def set_sim_pos(coord: Coord) -> None:
        _, _, depth = POSITIONS[node_id]
        POSITIONS[node_id] = (coord.lat, coord.lon, depth)

    return set_sim_pos


# ------------------------------------------------------------------ #
#  Scenario launcher                                                   #
# ------------------------------------------------------------------ #


def launch_bridge(root: tk.Tk) -> list[ControllerWindow]:
    """Spawn socat pairs, start broker, and open two ControllerWindows."""
    # 1. Create virtual serial pairs
    pty_a_broker, pty_a_node, socat_a = _spawn_socat_pair()
    pty_b_broker, pty_b_node, socat_b = _spawn_socat_pair()

    print(f"[BRIDGE] Node A → {pty_a_node}  (broker: {pty_a_broker})")
    print(f"[BRIDGE] Node B → {pty_b_node}  (broker: {pty_b_broker})")

    # 2. Open broker-side ports and start relay threads
    broker_port_a = _open_broker_port(pty_a_broker)
    broker_port_b = _open_broker_port(pty_b_broker)
    _start_broker_threads(broker_port_a, broker_port_b, "001", "002", POSITIONS)

    # 3. Create node transports (node-side PTYs, real driver + codec)
    transport_a = SerialTransport(node_id="001", port=pty_a_node, driver=NanomodemV3Driver(Codec()))
    transport_b = SerialTransport(node_id="002", port=pty_b_node, driver=NanomodemV3Driver(Codec()))

    # 4. Register cleanup
    def _cleanup() -> None:
        transport_a.stop()
        transport_b.stop()
        broker_port_a.close()
        broker_port_b.close()
        socat_a.terminate()
        socat_b.terminate()

    atexit.register(_cleanup)

    # 5. Window layout (side by side)
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    win_w = min(480, screen_w // 2)
    win_h = min(780, screen_h)

    # 6. Instantiate ControllerWindows
    # Node A: sim_pos panel enabled — moving it updates POSITIONS["001"] for the broker
    controller_a = ControllerWindow(
        root=root,
        node_id="001",
        pretty_name="Node A (Host)",
        transport=transport_a,
        peer_ids=["002"],
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        window_geometry=f"{win_w}x{win_h}+0+0",
        get_sim_pos_callback=_make_get_sim_pos("001"),
        set_sim_pos_callback=_make_set_sim_pos("001"),
    )

    # Node B: static beacon, no sim_pos panel
    controller_b = ControllerWindow(
        root=root,
        node_id="002",
        pretty_name="Node B (Beacon)",
        transport=transport_b,
        peer_ids=["001"],
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        window_geometry=f"{win_w}x{win_h}+{win_w}+0",
        get_sim_pos_callback=None,
        set_sim_pos_callback=None,
    )

    # 7. Start serial readers
    transport_a.start()
    transport_b.start()

    return [controller_a, controller_b]


def main() -> None:
    root = tk.Tk()
    root.withdraw()

    _controllers = launch_bridge(root)

    root.mainloop()


if __name__ == "__main__":
    main()
