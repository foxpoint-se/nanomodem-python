"""Tests for nanomodem package import behavior."""

from __future__ import annotations

import subprocess
import sys


def test__should_not_import_positioning_when_importing_core_only() -> None:
    script = (
        "import nanomodem.core\n"
        "import sys\n"
        "print('nanomodem.positioning' in sys.modules)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "False"


def test__should_resolve_positioning_exports_lazily() -> None:
    script = (
        "import nanomodem\n"
        "import sys\n"
        "assert 'nanomodem.positioning' not in sys.modules\n"
        "node = nanomodem.PositioningNode\n"
        "assert 'nanomodem.positioning' in sys.modules\n"
        "print(node.__name__)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "PositioningNode"
