.PHONY: help install clean-env lint format typecheck test verify-dist verify-dist-demo run-bridge

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies using uv"
	@echo "  make clean-env    - Delete virtual environment"
	@echo "  make lint         - Check code style and quality using ruff"
	@echo "  make format       - Format code using ruff"
	@echo "  make typecheck    - Check types using mypy"
	@echo "  make test         - Run all code checks and tests using pytest"
	@echo "  make verify-dist  - Verify the library is installable and importable"
	@echo "  make verify-dist-demo - Verify the demo scenarios are installable"
	@echo "  make run-bridge   - Run the serial bridge scenario (requires socat)"

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
	uv run ruff format src & uv run ruff check src --fix

typecheck:
	uv run mypy src

test: lint typecheck
	uv run pytest

verify-dist:
	@echo "Verifying distribution (isolated install)..."
	uv run --no-project --with "." python -c "from nanomodem.node import AcousticNode; print('✅ Distribution verified')"

verify-dist-demo:
	@echo "Verifying demo distribution (isolated install)..."
	uv run --no-project --with ".[demo]" python -c "from nanomodem.demo.scenarios.mock_4_nodes import main; print('✅ Demo distribution verified')"

run-bridge:
	uv run nanomodem-bridge
