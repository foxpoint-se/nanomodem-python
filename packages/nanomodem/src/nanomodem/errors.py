"""Domain errors for acoustic modem operations."""

from __future__ import annotations


class ModemIdMismatchError(Exception):
    """CLI/session node id does not match modem NVM id from $?."""

    def __init__(self, expected_id: str, actual_id: str) -> None:
        self.expected_id = expected_id
        self.actual_id = actual_id
        super().__init__(
            f"Node id mismatch: you started as {expected_id} but the modem reports "
            f"{actual_id}. Restart with the correct id, e.g. "
            f"nanomodem-controller {actual_id} --port /dev/ttyUSB0",
        )


class ModemStatusTimeoutError(Exception):
    """No ModemStatusMessage received within the startup verify timeout."""

    def __init__(self, expected_id: str, timeout_s: float) -> None:
        self.expected_id = expected_id
        self.timeout_s = timeout_s
        super().__init__(
            f"Timed out after {timeout_s}s waiting for modem status ($?) "
            f"for node {expected_id}. Check serial connection and power.",
        )
