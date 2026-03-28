.PHONY: help install clean-env lint format typecheck test verify-dist verify-dist-gui run-bridge run-broker

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies using uv"
	@echo "  make clean-env    - Delete virtual environment"
	@echo "  make lint         - Check code style and quality using ruff"
	@echo "  make format       - Format code using ruff"
	@echo "  make typecheck    - Check types using mypy"
	@echo "  make test         - Run all code checks and tests using pytest"
	@echo "  make verify-dist  - Verify the library is installable and importable"
	@echo "  make run-bridge   - Run the serial bridge scenario (requires socat)"
	@echo "  make run-broker   - Show instructions for running the standalone broker"

install:
	@echo "Installing dependencies with uv..."
	uv sync --all-extras
	@echo "✓ Dependencies installed."

clean-env:
	@if [ -d ".venv" ]; then \
		echo "Removing virtual environment..."; \
		rm -rf .venv; \
		echo "✓ Virtual environment deleted."; \
	else \
		echo "Virtual environment not found (nothing to clean)."; \
	fi

lint:
	uv run ruff check src

format:
	uv run ruff format src

typecheck:
	uv run mypy src

test: lint typecheck
	uv run pytest

verify-dist:
	@echo "Verifying distribution (isolated install)..."
	uv run --no-project --with "." python -c "from nanomodem.node import AcousticNode; print('✅ Distribution verified')"

verify-dist-gui:
	@echo "Verifying GUI distribution (isolated install)..."
	uv run --no-project --with ".[gui]" python -c "from nanomodem.gui.scenarios.mock_4_nodes import main; print('✅ GUI distribution verified')"

run-bridge:
	uv run nanomodem-bridge

run-broker:
	@echo ""
	@echo "Step 1: Create two virtual serial pairs."
	@echo "  Run each command in its own terminal and note the two PTY paths printed:"
	@echo ""
	@echo "    socat -d -d pty,raw,echo=0 pty,raw,echo=0"
	@echo "    socat -d -d pty,raw,echo=0 pty,raw,echo=0"
	@echo ""
	@echo "Step 2: Run the broker (replace PTY paths with the ones from step 1):"
	@echo ""
	@echo "    uv run python scripts/serial_broker.py <A_broker> <A_node> <B_broker> <B_node>"
	@echo ""
	@echo "  Example:"
	@echo "    uv run python scripts/serial_broker.py /dev/pts/2 /dev/pts/3 /dev/pts/4 /dev/pts/5"
	@echo ""
	@echo "Step 3: Connect nodes to their PTYs (A_node and B_node paths from step 1)."
	@echo "  Edit NODE_POSITIONS in scripts/serial_broker.py to set simulated positions."
	@echo ""
