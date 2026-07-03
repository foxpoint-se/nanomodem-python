"""Shared startup checks for demo and consumer entrypoints."""

from __future__ import annotations

import sys
import threading
from typing import Callable

from nanomodem import PositioningNode
from nanomodem.core.transports.in_memory import InMemoryTransport
from nanomodem.core.transports.serial_wire import SerialWireTransport
from nanomodem.core.wire_types import StatusResponseEvent
from nanomodem.errors import ModemIdMismatchError, ModemStatusTimeoutError

from nanomodem_demo.transports import SimulatorJsonTransport


def _format_demo_restart_hint(node: PositioningNode, exc: ModemIdMismatchError) -> str:
    transport = node.modem_node.transport
    if isinstance(transport, SerialWireTransport):
        return f"Restart with: nanomodem-controller {exc.actual_id} --port {transport.port}"
    if isinstance(transport, SimulatorJsonTransport):
        return (
            f"Restart with: nanomodem-controller {exc.actual_id} "
            f"--network {transport._host}:{transport._port}"
        )
    if isinstance(transport, InMemoryTransport):
        return f"Restart with: nanomodem-controller {exc.actual_id}"
    return f"Restart with: nanomodem-controller {exc.actual_id}"


def verify_modem_id_at_startup(node: PositioningNode, timeout_s: float = 2.0) -> None:
    """Run $? and exit the process if the modem id does not match the node."""
    received: list[StatusResponseEvent] = []
    done = threading.Event()
    prior_status: Callable[[StatusResponseEvent], None] | None = None

    def capture(status: StatusResponseEvent) -> None:
        received.append(status)
        done.set()
        if prior_status is not None:
            prior_status(status)

    prior_status = node.modem_node.on_status_response(capture)
    try:
        node.query_modem_status()
        if not done.wait(timeout_s):
            raise ModemStatusTimeoutError(node.node_id, timeout_s)
        status = received[0]
        if status.address != node.node_id:
            raise ModemIdMismatchError(node.node_id, status.address)
    except ModemIdMismatchError as exc:
        print(f"\nError: {exc}\n", file=sys.stderr)
        print(f"{_format_demo_restart_hint(node, exc)}\n", file=sys.stderr)
        sys.exit(1)
    except ModemStatusTimeoutError as exc:
        print(f"\nError: {exc}\n", file=sys.stderr)
        sys.exit(1)
    finally:
        node.modem_node.on_status_response(prior_status)
