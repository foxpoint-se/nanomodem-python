"""Text-only mock localization demo (no GUI).

Usage:
    python -m nanomodem_demo.scenarios.text_mock_demo
"""

from __future__ import annotations

import argparse
import logging

from nanomodem.constants import SOUND_SPEED_WATER_M_S
from nanomodem.core.transports import InMemoryBus
from nanomodem.positioning import PositioningNode
from nanomodem.types import Coord

from nanomodem_demo.node_builder import build_in_memory_node

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _create_mock_node(
    node_id: str,
    position: Coord,
    bus: InMemoryBus,
    sound_speed: float,
) -> PositioningNode:
    """Create a node with InMemoryTransport, setting position on both node and transport."""
    return build_in_memory_node(node_id, bus, position=position, sound_speed=sound_speed)


def run_mock_demo(sound_speed: float = SOUND_SPEED_WATER_M_S) -> None:
    """Scripted demo: 3 beacons + 1 submerged host, full localization cycle."""

    bus = InMemoryBus(sound_speed=sound_speed)

    beacon_positions = {
        "002": Coord(lat=63.0, lon=10.0),
        "003": Coord(lat=63.001, lon=10.0),
        "004": Coord(lat=63.0005, lon=10.001),
    }

    beacons: dict[str, PositioningNode] = {}
    for nid, pos in beacon_positions.items():
        node = _create_mock_node(nid, pos, bus, sound_speed)
        node.set_depth(0.0)
        node.capabilities.is_broadcasting_own_position = True
        beacons[nid] = node
        logger.info("Beacon %s at (%.4f, %.4f, %.1f)", nid, pos.lat, pos.lon, node.get_depth())

    actual_pos = Coord(lat=63.0004, lon=10.0003)
    host = _create_mock_node("001", actual_pos, bus, sound_speed)
    host.set_depth(5.0)
    host.capabilities.is_inferring_own_position = True
    logger.info(
        "Host 001 at (%.4f, %.4f, %.1f) — actual position",
        actual_pos.lat,
        actual_pos.lon,
        host.get_depth(),
    )

    logger.info("--- Beacons broadcasting positions ---")
    for beacon in beacons.values():
        beacon.broadcast_position()

    for nid, kn in host.get_known_nodes().items():
        logger.info("  Host knows beacon %s at %s", nid, kn.position)

    logger.info("--- Host ranging to beacons ---")
    for nid in beacon_positions:
        host.request_range(nid)
        kn_opt = host.get_known_nodes().get(nid)
        if kn_opt and kn_opt.last_range is not None:
            logger.info("  Range to %s: %.2fm", nid, kn_opt.last_range)

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
    parser.add_argument(
        "--sound-speed",
        type=float,
        default=SOUND_SPEED_WATER_M_S,
        help="Speed of sound in m/s for ranging (default: 1500 water; use 340 for air bench)",
    )

    args = parser.parse_args()
    port: str | None = args.port

    if port is not None:
        logger.info("Real serial mode: port=%s, baud=%d, node=%s", port, args.baud, args.node_id)
        logger.warning("SerialWireTransport demo not yet implemented (Step 10)")
    else:
        logger.info("Running mock demo (sound_speed=%.0f m/s)...", args.sound_speed)
        run_mock_demo(sound_speed=args.sound_speed)


if __name__ == "__main__":
    main()
