"""Startup checks for CLI one-shot and REPL sessions."""

from __future__ import annotations

import sys
import threading
from typing import Callable

from nanomodem.core.modem_node import ModemNode
from nanomodem.core.wire_types import StatusResponseEvent
from nanomodem.errors import ModemIdMismatchError, ModemStatusTimeoutError


def _format_id_mismatch_error(exc: ModemIdMismatchError) -> str:
    return (
        f"Node id mismatch: you started as {exc.expected_id} but the modem reports "
        f"{exc.actual_id}. Restart with the correct id, e.g. "
        f"nanomodem -n {exc.actual_id} -s /dev/ttyUSB0 status"
    )


def verify_modem_id_at_startup(node: ModemNode[bytes], timeout_s: float = 2.0) -> None:
    """Run $? and exit the process if the modem id does not match the node."""
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
            raise ModemStatusTimeoutError(node.node_id, timeout_s)
        status = received[0]
        if status.address != node.node_id:
            raise ModemIdMismatchError(node.node_id, status.address)
    except ModemIdMismatchError as exc:
        print(f"Error: {_format_id_mismatch_error(exc)}", file=sys.stderr)
        sys.exit(1)
    except ModemStatusTimeoutError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        node.on_status_response(prior)
