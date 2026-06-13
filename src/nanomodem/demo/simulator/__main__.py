"""CLI entry point for the God View Simulator."""

from __future__ import annotations

import argparse
import logging
import tkinter as tk

from nanomodem.demo.simulator.app import launch_simulator


def main() -> None:
    parser = argparse.ArgumentParser(description="God View Simulator for acoustic network")
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind metadata server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5555,
        help="Port for metadata server (default: 5555)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(message)s",
    )

    print("=== God View Simulator ===")
    print(f"  Metadata server: {args.host}:{args.port}")
    print("\nWaiting for controllers to connect...")
    print("\nController examples:")
    print("  Network mode:  nanomodem-controller 001 --network 127.0.0.1:5555")
    print("  Serial mode:   socat -d -d pty,raw,echo=0 pty,raw,echo=0")
    print("                 nanomodem-controller 001 --port /dev/pts/4 --world 127.0.0.1:5555 --world-port /dev/pts/5")
    print()

    root = tk.Tk()
    root.withdraw()

    _simulator = launch_simulator(root, host=args.host, port=args.port)

    root.mainloop()


if __name__ == "__main__":
    main()
