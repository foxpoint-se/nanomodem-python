"""Serial logging utility for consistent raw traffic visibility."""

from __future__ import annotations

from datetime import datetime


def format_serial_log(direction: str, node_id: str, data: bytes) -> str:
    """Format raw serial data with timestamp for logging.

    Matches broker format: [HH:MM:SS.mmm] [direction node_id] decoded_data
    """
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    # Replace non-printable ASCII with replacement character
    decoded = data.decode("ascii", errors="replace").strip()
    # Ensure node_id context is clear even if empty
    context = f"{direction} {node_id}".strip()
    return f"[{ts}] [{context}] {decoded}"
