"""Serial bus broker for virtual hardware integration testing.

Simulates the acoustic medium using two virtual serial port pairs.
Relays bytes between nodes, logs all traffic, and synthesizes range
responses based on configured node positions.

Usage
-----
Step 1: Create two virtual serial pairs (run each in a separate terminal):

    socat -d -d pty,raw,echo=0 pty,raw,echo=0

Each invocation prints two PTY paths, e.g.:
    2024/01/01 12:00:00 socat[...] N PTY is /dev/pts/2
    2024/01/01 12:00:00 socat[...] N PTY is /dev/pts/3

Step 2: Run the broker with the 4 PTY paths:

    uv run python scripts/serial_broker.py <A_broker> <A_node> <B_broker> <B_node>

    Example:
    uv run python scripts/serial_broker.py /dev/pts/2 /dev/pts/3 /dev/pts/4 /dev/pts/5

    Node A connects to A_node (/dev/pts/3).
    Node B connects to B_node (/dev/pts/5).
    The broker holds the other end of each pair.

Step 3: Launch your nodes pointing at their respective PTYs:
    Node A: SerialTransport(node_id="001", port="/dev/pts/3", ...)
    Node B: SerialTransport(node_id="002", port="/dev/pts/5", ...)
"""

from __future__ import annotations

import sys
import threading
from datetime import datetime

import serial

from nanomodem.gui.scenarios.modem_relay import (
    broadcast_ack,
    broadcast_relay,
    distance_metres,
    parse_broadcast,
    parse_ping,
    ping_ack,
    range_response,
)

# ------------------------------------------------------------------ #
#  Configuration                                                       #
# ------------------------------------------------------------------ #

SOUND_SPEED = 1500.0  # m/s

# Physical positions used for range simulation.
# lat/lon in decimal degrees, depth in metres.
NODE_POSITIONS: dict[str, tuple[float, float, float]] = {
    "001": (59.310153, 17.975189, 0.0),
    "002": (59.310500, 17.974500, 0.0),
}

BAUD = 9600
TIMEOUT = 0.1

# ------------------------------------------------------------------ #
#  Serial port helpers                                                 #
# ------------------------------------------------------------------ #


def _open_port(path: str) -> serial.Serial:
    return serial.Serial(
        port=path,
        baudrate=BAUD,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=TIMEOUT,
    )


# ------------------------------------------------------------------ #
#  Relay threads                                                       #
# ------------------------------------------------------------------ #


def _log(label: str, raw: bytes) -> None:
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] [{label}] {raw.decode('ascii', errors='replace').strip()}")


def _relay_thread(
    src: serial.Serial,
    dst: serial.Serial,
    src_id: str,
    dst_id: str,
    label: str,
    lock: threading.Lock,
) -> None:
    while True:
        try:
            raw = src.readline()
            if not raw:
                continue

            _log(label, raw)

            broadcast = parse_broadcast(raw)
            if broadcast is not None:
                nn, body = broadcast
                src.write(broadcast_ack(nn))
                with lock:
                    dst.write(broadcast_relay(src_id, nn, body))
                continue

            target_id = parse_ping(raw)
            if target_id is not None:
                src.write(ping_ack(target_id))
                sender_pos = NODE_POSITIONS.get(src_id)
                target_pos = NODE_POSITIONS.get(target_id)
                if sender_pos is not None and target_pos is not None:
                    dist = distance_metres(sender_pos, target_pos)
                    resp = range_response(target_id, dist, SOUND_SPEED)
                    _log(f"BROKER→{src_id}", resp)
                    src.write(resp)
                else:
                    print(f"[BROKER] Unknown node in range request: {src_id!r} → {target_id!r}")
                continue

            with lock:
                dst.write(raw)

        except serial.SerialException as e:
            print(f"[BROKER] Serial error on {label}: {e}")
            break
        except Exception as e:
            print(f"[BROKER] Unexpected error on {label}: {e}")


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

def main(port_a_broker: str, port_b_broker: str, node_a_id: str, node_b_id: str) -> None:
    print(f"[BROKER] Opening ports: A={port_a_broker}  B={port_b_broker}")
    port_a = _open_port(port_a_broker)
    port_b = _open_port(port_b_broker)

    lock_a = threading.Lock()
    lock_b = threading.Lock()

    thread_a = threading.Thread(
        target=_relay_thread,
        args=(port_a, port_b, node_a_id, node_b_id, f"{node_a_id}→{node_b_id}", lock_b),
        daemon=True,
        name="relay-a",
    )
    thread_b = threading.Thread(
        target=_relay_thread,
        args=(port_b, port_a, node_b_id, node_a_id, f"{node_b_id}→{node_a_id}", lock_a),
        daemon=True,
        name="relay-b",
    )

    thread_a.start()
    thread_b.start()

    print(f"[BROKER] Running. Node A ({node_a_id}) ↔ Node B ({node_b_id}). Ctrl+C to stop.")
    print("[BROKER] Edit NODE_POSITIONS at the top of this script to change simulated positions.")

    try:
        thread_a.join()
        thread_b.join()
    except KeyboardInterrupt:
        print("\n[BROKER] Stopped.")
    finally:
        port_a.close()
        port_b.close()


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(__doc__)
        print("Error: expected 4 arguments: <A_broker_pty> <A_node_pty> <B_broker_pty> <B_node_pty>")
        sys.exit(1)

    _, port_a_broker, port_a_node, port_b_broker, port_b_node = sys.argv

    print(f"[BROKER] Node A connects to: {port_a_node}")
    print(f"[BROKER] Node B connects to: {port_b_node}")

    # node IDs are looked up from NODE_POSITIONS by position in the arg list
    node_a_id = list(NODE_POSITIONS.keys())[0]
    node_b_id = list(NODE_POSITIONS.keys())[1]

    main(port_a_broker, port_b_broker, node_a_id, node_b_id)
