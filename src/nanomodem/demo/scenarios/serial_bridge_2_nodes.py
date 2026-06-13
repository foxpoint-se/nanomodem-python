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

import serial

from nanomodem.calculation import calculate_distance_3d
from nanomodem.codecs.v3 import Codec
from nanomodem.constants import SOUND_SPEED_WATER_M_S
from nanomodem.demo.controller import ControllerWindow
from nanomodem.demo.scenarios.modem_relay import (
    broadcast_ack,
    broadcast_relay,
    parse_broadcast,
    parse_ping,
    parse_quality_query,
    parse_status_query,
    parse_test_request,
    ping_ack,
    range_response,
    relay_quality_query,
    relay_test_request,
    split_modem_command,
    status_response,
)
from nanomodem.demo.startup import verify_modem_id_at_startup
from nanomodem.drivers.v3 import NanomodemV3Driver
from nanomodem.serial_logger import format_serial_log
from nanomodem.transports.mock import MOCK_STATUS_VOLTAGE_RAW
from nanomodem.transports.serial import SerialTransport
from nanomodem.types import Coord

MAP_CENTER = (59.310153, 17.975189)
MAP_ZOOM = 16
SOUND_SPEED = SOUND_SPEED_WATER_M_S
BAUD = 9600
TIMEOUT = 0.1

# Physical positions used by broker for range simulation (lat, lon, depth_m).
# Nodes start with no position; set via GUI or explicitly before ranging.
POSITIONS: dict[str, tuple[float, float, float] | None] = {
    "001": None,
    "002": None,
}

HEARD_DATA_PACKET: dict[str, bool] = {}

PortRegistry = dict[str, tuple[serial.Serial, threading.Lock]]

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
    print(format_serial_log(label, "", raw))


def _write_to_node(node_id: str, data: bytes, ports: PortRegistry) -> None:
    port, lock = ports[node_id]
    _log_bus(f"BROKER→{node_id}", data)
    with lock:
        port.write(data)


def _handle_relay_command(
    command: bytes,
    src_id: str,
    peer_id: str,
    label: str,
    positions: dict[str, tuple[float, float, float] | None],
    ports: PortRegistry,
    heard_data_packet: dict[str, bool],
) -> None:
    _log_bus(label, command)

    def send_message(node_id: str, data: bytes) -> None:
        _write_to_node(node_id, data, ports)

    if parse_status_query(command):
        send_message(src_id, status_response(src_id, MOCK_STATUS_VOLTAGE_RAW))
        return

    broadcast = parse_broadcast(command)
    if broadcast is not None:
        nn, body = broadcast
        send_message(src_id, broadcast_ack(nn))
        send_message(peer_id, broadcast_relay(src_id, nn, body))
        return

    target_id = parse_ping(command)
    if target_id is not None:
        send_message(src_id, ping_ack(target_id))
        sender_pos = positions.get(src_id)
        target_pos = positions.get(target_id)
        if sender_pos is not None and target_pos is not None:
            coord_src = Coord(lat=sender_pos[0], lon=sender_pos[1])
            coord_dst = Coord(lat=target_pos[0], lon=target_pos[1])
            dist = calculate_distance_3d(coord_src, sender_pos[2], coord_dst, target_pos[2])
            send_message(src_id, range_response(target_id, dist, SOUND_SPEED))
        else:
            print(f"[BROKER] Unknown node in range request: {src_id!r} → {target_id!r}")
        return

    test_target = parse_test_request(command)
    if test_target is not None:
        relay_test_request(
            src_id,
            test_target,
            send_message=send_message,
            get_listener_ids=lambda: list(positions.keys()),
            known_node_ids=set(positions.keys()),
            heard_data_packet=heard_data_packet,
        )
        return

    if parse_quality_query(command):
        relay_quality_query(
            src_id,
            send_message=send_message,
            heard_data_packet=heard_data_packet,
        )
        return

    send_message(peer_id, command)


def _relay_loop(
    src: serial.Serial,
    src_id: str,
    peer_id: str,
    label: str,
    positions: dict[str, tuple[float, float, float] | None],
    ports: PortRegistry,
    heard_data_packet: dict[str, bool],
) -> None:
    buffer = b""
    while True:
        try:
            chunk = src.read(src.in_waiting or 1)
            if not chunk:
                continue
            buffer += chunk

            while True:
                split = split_modem_command(buffer)
                if split is None:
                    break
                command, buffer = split
                _handle_relay_command(
                    command, src_id, peer_id, label, positions, ports, heard_data_packet
                )

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
    positions: dict[str, tuple[float, float, float] | None],
) -> None:
    lock_a = threading.Lock()
    lock_b = threading.Lock()
    ports: PortRegistry = {
        node_a_id: (port_a, lock_a),
        node_b_id: (port_b, lock_b),
    }
    threading.Thread(
        target=_relay_loop,
        args=(
            port_a,
            node_a_id,
            node_b_id,
            f"{node_a_id}→{node_b_id}",
            positions,
            ports,
            HEARD_DATA_PACKET,
        ),
        daemon=True,
        name="relay-a",
    ).start()
    threading.Thread(
        target=_relay_loop,
        args=(
            port_b,
            node_b_id,
            node_a_id,
            f"{node_b_id}→{node_a_id}",
            positions,
            ports,
            HEARD_DATA_PACKET,
        ),
        daemon=True,
        name="relay-b",
    ).start()


# ------------------------------------------------------------------ #
#  Broker position sync                                                #
# ------------------------------------------------------------------ #


def _sync_broker_positions(controllers: list[ControllerWindow]) -> None:
    for controller in controllers:
        node_id = controller.node.node_id
        pos = controller.node.get_position()
        if pos is None:
            POSITIONS[node_id] = None
        else:
            POSITIONS[node_id] = (pos.lat, pos.lon, controller.node.get_depth())


def _schedule_broker_position_sync(root: tk.Tk, controllers: list[ControllerWindow]) -> None:
    def tick() -> None:
        _sync_broker_positions(controllers)
        root.after(250, tick)

    root.after(0, tick)


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
    controller_a = ControllerWindow(
        root=root,
        node_id="001",
        pretty_name="Node A (Host)",
        transport=transport_a,
        peer_ids=["002"],
        position=None,
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        window_geometry=f"{win_w}x{win_h}+0+0",
    )

    controller_b = ControllerWindow(
        root=root,
        node_id="002",
        pretty_name="Node B (Beacon)",
        transport=transport_b,
        peer_ids=["001"],
        position=None,
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        window_geometry=f"{win_w}x{win_h}+{win_w}+0",
    )

    # 7. Start serial readers
    transport_a.start()
    transport_b.start()

    verify_modem_id_at_startup(controller_a.node)
    verify_modem_id_at_startup(controller_b.node)

    controllers = [controller_a, controller_b]
    _schedule_broker_position_sync(root, controllers)

    return controllers


def main() -> None:
    root = tk.Tk()
    root.withdraw()

    _controllers = launch_bridge(root)

    root.mainloop()


if __name__ == "__main__":
    main()
