"""GUI Controller entry point.

Usage:
    python -m apps.gui_controller
"""

from __future__ import annotations


def main() -> None:
    print("\nNanomodem GUI Controller")
    print("========================\n")
    print("Available scenarios:")
    print("  python -m apps.gui_controller.scenarios.mock_4_nodes")
    print("  python -m apps.gui_controller.scenarios.single_node <node_id>\n")
    print("Example:")
    print("  python -m apps.gui_controller.scenarios.single_node 001\n")


if __name__ == "__main__":
    main()
