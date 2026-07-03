"""Startup checks for CLI one-shot and REPL sessions."""

from __future__ import annotations

import sys
import threading

from nanomodem.core.modem_node import ModemNode
from nanomodem.core.wire_types import StatusResponseEvent
from nanomodem.errors import ModemIdMismatchError, ModemStatusTimeoutError


def verify_modem_id_at_startup(node: ModemNode[bytes], timeout_s: float = 2.0) -> None:
    """Run $? and exit the process if the modem id does not match the node."""
    received: list[StatusResponseEvent] = []
    done = threading.Event()
    prior = node.on_status_response(None)

    def capture(status: StatusResponseEvent) -> None:
        received.append(status)
        done.set()
        if prior is not None:
            prior(status)

    node.on_status_response(capture)
    try:
        node.query_status()
        if not done.wait(timeout_s):
            raise ModemStatusTimeoutError(node.node_id, timeout_s)
        status = received[0]
        if status.address != node.node_id:
            raise ModemIdMismatchError(node.node_id, status.address)
    except (ModemIdMismatchError, ModemStatusTimeoutError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        node.on_status_response(prior)
