"""One-shot command execution for the nanomodem CLI."""

from __future__ import annotations

import sys
import threading
from typing import Callable

from nanomodem.core.modem_node import ModemNode
from nanomodem.core.spec import supply_voltage_volts, timestamp_to_distance
from nanomodem.core.wire_types import StatusResponseEvent

STATUS_TIMEOUT_S = 2.0
PING_TIMEOUT_S = 5.0


def execute_status(node: ModemNode[bytes], timeout_s: float = STATUS_TIMEOUT_S) -> int:
    """Query modem status and print id and voltage."""
    received: list[StatusResponseEvent] = []
    done = threading.Event()
    prior: Callable[[StatusResponseEvent], None] | None = None

    def capture(status: StatusResponseEvent) -> None:
        received.append(status)
        done.set()
        if prior is not None:
            prior(status)

    prior = node.on_status_response(capture)
    try:
        node.query_status()
        if not done.wait(timeout_s):
            print(
                f"Error: Timed out after {timeout_s}s waiting for modem status ($?) "
                f"for node {node.node_id}.",
                file=sys.stderr,
            )
            return 1
        status = received[0]
        voltage = supply_voltage_volts(status.voltage_raw)
        print(f"Node ID: {status.address}, Voltage: {voltage:.2f}V")
        return 0
    finally:
        node.on_status_response(prior)


def execute_ping(
    node: ModemNode[bytes],
    target_id: str,
    sound_speed: float,
    timeout_s: float = PING_TIMEOUT_S,
) -> int:
    """Ping a target node and print range in meters."""
    received_timestamp: int | None = None
    done = threading.Event()
    prior: Callable[[str, int], None] | None = None

    def capture(responder_id: str, timestamp_counts: int) -> None:
        nonlocal received_timestamp
        if responder_id == target_id:
            received_timestamp = timestamp_counts
            done.set()
        if prior is not None:
            prior(responder_id, timestamp_counts)

    prior = node.on_roundtrip_response(capture)
    try:
        node.ping(target_id)
        if not done.wait(timeout_s):
            print(
                f"Error: Timed out after {timeout_s}s waiting for ping response from {target_id}.",
                file=sys.stderr,
            )
            return 1
        assert received_timestamp is not None
        distance = timestamp_to_distance(received_timestamp, sound_speed)
        print(f"range {target_id}: {distance:.0f} m")
        return 0
    finally:
        node.on_roundtrip_response(prior)
