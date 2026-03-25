"""Entry point for the acoustic modem localization system.

Usage:
    Mock mode (demo):   python -m nanomodem
    Real serial:        python -m nanomodem --port /dev/ttyUSB0 --baud 9600 --node-id 001
"""

from __future__ import annotations

import argparse
import logging

from .calculation import Calculation
from .node import AcousticNode
from .transports.mock import MockEther, MockTransport
from .types import Coord

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _create_mock_node(
    node_id: str,
    position: Coord,
    ether: MockEther,
    calc: Calculation,
) -> AcousticNode:
    """Create a node with MockTransport, setting position on both node and transport."""
    transport = MockTransport(node_id, ether)
    transport.position = position
    return AcousticNode(
        node_id=node_id,
        transport=transport,
        calculation=calc,
        position=position,
    )


def run_mock_demo() -> None:
    """Scripted demo: 3 beacons + 1 submerged host, full localization cycle."""

    ether = MockEther(sound_speed=1500.0)
    calc = Calculation()

    # --- Create beacons with known surface positions ---

    beacon_positions = {
        "002": Coord(lat=63.0, lon=10.0),
        "003": Coord(lat=63.001, lon=10.0),
        "004": Coord(lat=63.0005, lon=10.001),
    }

    beacons: dict[str, AcousticNode] = {}
    for nid, pos in beacon_positions.items():
        node = _create_mock_node(nid, pos, ether, calc)
        node.set_depth(0.0)
        node.capabilities.is_broadcasting_own_position = True
        beacons[nid] = node
        logger.info("Beacon %s at (%.4f, %.4f, %.1f)", nid, pos.lat, pos.lon, node.get_depth())

    # --- Create submerged host ---

    actual_pos = Coord(lat=63.0004, lon=10.0003)
    host = _create_mock_node("001", actual_pos, ether, calc)
    host.set_depth(5.0)
    host.capabilities.is_inferring_own_position = True
    logger.info(
        "Host 001 at (%.4f, %.4f, %.1f) — actual position",
        actual_pos.lat,
        actual_pos.lon,
        host.get_depth(),
    )

    # --- Step 1: Beacons broadcast their positions ---

    logger.info("--- Beacons broadcasting positions ---")
    for beacon in beacons.values():
        beacon.broadcast_position()

    for nid, kn in host.get_known_nodes().items():
        logger.info("  Host knows beacon %s at %s", nid, kn.position)

    # --- Step 2: Host ranges to each beacon ---

    logger.info("--- Host ranging to beacons ---")
    for nid in beacon_positions:
        host.request_range(nid)
        kn_opt = host.get_known_nodes().get(nid)
        if kn_opt and kn_opt.last_range is not None:
            logger.info("  Range to %s: %.2fm", nid, kn_opt.last_range)

    # --- Step 3: Position should have been auto-calculated ---

    logger.info("--- Result ---")
    result = host.get_position()
    if result is not None:
        logger.info(
            "  Estimated: (%.6f, %.6f, %.1f)",
            result.lat,
            result.lon,
            host.get_depth(),
        )
        logger.info(
            "  Actual:    (%.6f, %.6f, %.1f)",
            actual_pos.lat,
            actual_pos.lon,
            5.0,
        )
    else:
        logger.warning("  Could not calculate position")


def main() -> None:
    parser = argparse.ArgumentParser(description="Acoustic modem localization system")
    parser.add_argument("--port", type=str, help="Serial port (e.g. /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate")
    parser.add_argument("--node-id", type=str, default="001", help="This node's ID")

    args = parser.parse_args()
    port: str | None = args.port
    baud: int = args.baud
    node_id: str = args.node_id

    if port is not None:
        logger.info("Real serial mode: port=%s, baud=%d, node=%s", port, baud, node_id)
        logger.warning("NanomodemTransport not yet implemented (Step 10)")
    else:
        logger.info("Running mock demo...")
        run_mock_demo()


if __name__ == "__main__":
    main()
