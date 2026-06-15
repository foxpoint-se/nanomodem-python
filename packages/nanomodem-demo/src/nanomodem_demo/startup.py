"""Shared startup checks for demo and consumer entrypoints."""

from __future__ import annotations

import sys

from nanomodem.errors import ModemIdMismatchError, ModemStatusTimeoutError
from nanomodem.node import AcousticNode


def verify_modem_id_at_startup(node: AcousticNode) -> None:
    """Run $? and exit the process if the modem id does not match the node."""
    try:
        node.ensure_modem_id_matches()
    except (ModemIdMismatchError, ModemStatusTimeoutError) as exc:
        print(f"\nError: {exc}\n", file=sys.stderr)
        sys.exit(1)
