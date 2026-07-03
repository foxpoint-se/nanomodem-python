"""CLI input validation."""

from __future__ import annotations

import argparse
import sys

from nanomodem.constants import validate_sound_speed


def _exit_on_invalid_node_id(value: str, label: str) -> None:
    if len(value) != 3 or not value.isdigit():
        print(
            f"Error: {label} must be a 3-digit numeric string (e.g. '001'), got '{value}'.",
            file=sys.stderr,
        )
        sys.exit(1)
    numeric = int(value)
    if numeric < 1 or numeric > 255:
        print(f"Error: {label} must represent 1-255, got {numeric}.", file=sys.stderr)
        sys.exit(1)


def validate_one_shot_args(args: argparse.Namespace) -> None:
    """Validate one-shot CLI args; exit 1 with a message on failure."""
    if not args.node_id:
        print("Error: --node-id is required for one-shot commands.", file=sys.stderr)
        sys.exit(1)
    if not args.serial and not args.in_memory:
        print("Error: A transport (--serial or --in-memory) must be specified for one-shot commands.", file=sys.stderr)
        sys.exit(1)

    _exit_on_invalid_node_id(args.node_id, "--node-id")

    try:
        validate_sound_speed(args.sound_speed)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.command == "ping":
        _exit_on_invalid_node_id(args.target_id, "ping target_id")
