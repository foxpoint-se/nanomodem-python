"""GUI entry point.

Usage:
    cd take2
    PYTHONPATH=. python -m gui
"""

from __future__ import annotations

import tkinter as tk

from .launcher import launch_mock


def main() -> None:
    root = tk.Tk()
    root.withdraw()  # Hide root window; ControllerWindows are Toplevels

    _controllers = launch_mock(root)

    root.mainloop()


if __name__ == "__main__":
    main()
