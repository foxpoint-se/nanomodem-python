"""CLI entry point for nanomodem."""

from __future__ import annotations

import argparse
import sys

from nanomodem.constants import SOUND_SPEED_WATER_M_S
from nanomodem.core.codecs import RawPayloadCodec
from nanomodem.core.driver import NanomodemV3Driver
from nanomodem.core.modem_node import ModemNode
from nanomodem.core.protocols import WireTransport
from nanomodem.core.transports.in_memory import InMemoryBus, InMemoryTransport
from nanomodem.core.transports.serial_wire import SerialWireTransport

from .one_shot import execute_ping, execute_status
from .startup import verify_modem_id_at_startup
from .validation import validate_one_shot_args


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nanomodem",
        description="Command-line interface for nanomodem acoustic modems.",
    )
    parser.add_argument("-n", "--node-id", type=str, help="Node ID (e.g. '001')")

    transport_group = parser.add_mutually_exclusive_group()
    transport_group.add_argument("-s", "--serial", type=str, help="Serial port path (e.g. /dev/ttyUSB0)")
    transport_group.add_argument(
        "-m",
        "--in-memory",
        action="store_true",
        help="In-memory bus (one node per run; peer ping needs REPL, not one-shot)",
    )

    parser.add_argument("--baud", type=int, default=9600, help="Serial baud rate (default: 9600)")
    parser.add_argument(
        "--sound-speed",
        type=float,
        default=SOUND_SPEED_WATER_M_S,
        help=f"Speed of sound in m/s (default: {SOUND_SPEED_WATER_M_S})",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.add_parser("status", help="Query modem ID and voltage")
    ping_parser = subparsers.add_parser("ping", help="Range to target node ID")
    ping_parser.add_argument("target_id", type=str, help="Target node ID (e.g. '002')")
    return parser


def _create_transport(args: argparse.Namespace) -> WireTransport:
    if args.serial:
        return SerialWireTransport(port=args.serial, driver=NanomodemV3Driver(), baud=args.baud)
    if args.in_memory:
        bus = InMemoryBus(sound_speed=args.sound_speed)
        return InMemoryTransport(node_id=args.node_id, bus=bus)
    print("Error: A transport (--serial or --in-memory) must be specified for one-shot commands.", file=sys.stderr)
    sys.exit(1)


def _run_one_shot(args: argparse.Namespace) -> int:
    validate_one_shot_args(args)
    transport = _create_transport(args)
    node = ModemNode(node_id=args.node_id, transport=transport, codec=RawPayloadCodec())

    transport.start()
    try:
        verify_modem_id_at_startup(node)
        if args.command == "status":
            return execute_status(node)
        if args.command == "ping":
            return execute_ping(node, args.target_id, args.sound_speed)
        print(f"Error: Unknown command '{args.command}'", file=sys.stderr)
        return 1
    finally:
        transport.stop()


def _run_repl_placeholder(args: argparse.Namespace) -> int:
    if args.node_id or args.serial or args.in_memory:
        print("REPL mode with initial configuration is not yet implemented.")
    else:
        print("REPL mode is not yet implemented.")
    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command:
        sys.exit(_run_one_shot(args))
    sys.exit(_run_repl_placeholder(args))


if __name__ == "__main__":
    main()
