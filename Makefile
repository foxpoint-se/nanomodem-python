.PHONY: help install clean-env lint format typecheck test verify-dist

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies using uv"
	@echo "  make clean-env    - Delete virtual environment"
	@echo "  make lint         - Check code style and quality using ruff"
	@echo "  make format       - Format code using ruff"
	@echo "  make typecheck    - Check types using mypy"
	@echo "  make test         - Run all code checks and tests using pytest"
	@echo "  make verify-dist  - Verify the library is installable and importable"

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
