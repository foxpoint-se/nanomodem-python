.PHONY: help install clean-env lint format typecheck test verify-dist verify-dist-demo run-bridge

help:
	@echo "Available commands:"
	@echo "  make install      - Install workspace dependencies using uv"
	@echo "  make clean-env    - Delete virtual environment"
	@echo "  make lint         - Check code style and quality using ruff"
	@echo "  make format       - Format code using ruff"
	@echo "  make typecheck    - Check types using mypy"
	@echo "  make test         - Run all code checks and tests using pytest"
	@echo "  make verify-dist  - Verify the library is installable and importable"
	@echo "  make verify-dist-demo - Verify the demo package is installable"
	@echo "  make run-bridge   - Run the serial bridge scenario (requires socat)"
	@echo "  make run-controller - Run a single controller (mock or serial)"

install:
	@echo "Installing workspace dependencies with uv..."
	uv sync --all-groups
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
	uv run ruff check packages

format:
	uv run ruff format packages & uv run ruff check packages --fix

typecheck:
	uv run mypy packages/nanomodem/src packages/nanomodem-demo/src packages/nanomodem-cli/src

test: lint typecheck
	uv run pytest

verify-dist:
	@echo "Verifying library distribution (isolated install)..."
	uv run --no-project --directory packages/nanomodem --with . python -c "from nanomodem import PositioningNode; from nanomodem.core.transports import InMemoryTransport; print('✅ Library distribution verified')"

verify-dist-demo:
	# Tests demo wheel can import lib from sibling path (workspace dev check)
	# For production install validation, test: pip install from git subdirectories
	@echo "Verifying demo distribution (isolated install)..."
	UV_NO_CACHE=1 uv run --no-project --directory packages/nanomodem-demo --with . --with ../nanomodem python -c "from nanomodem_demo.scenarios.mock_4_nodes import main; print('✅ Demo distribution verified')"

run-bridge:
	uv run nanomodem-bridge

run-controller:
	@if [ -z "$(ID)" ]; then \
		echo "Usage: make run-controller ID=001 [PORT=/dev/ttyUSB0]"; \
		exit 1; \
	fi
	@if [ -z "$(PORT)" ]; then \
		uv run nanomodem-controller $(ID); \
	else \
		uv run nanomodem-controller $(ID) --port $(PORT); \
	fi
