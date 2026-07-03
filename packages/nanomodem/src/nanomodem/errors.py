"""Domain errors for acoustic modem operations."""

from __future__ import annotations


class ModemIdMismatchError(Exception):
    """CLI/session node id does not match modem NVM id from $?."""

    def __init__(self, expected_id: str, actual_id: str) -> None:
        self.expected_id = expected_id
        self.actual_id = actual_id
        super().__init__(
            f"Node id mismatch: expected {expected_id}, modem reports {actual_id}.",
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
