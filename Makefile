.PHONY: help install clean-env lint format typecheck test

help:
	@echo "Available commands:"
	@echo "  make install   - Create/update virtual environment and install dependencies"
	@echo "  make clean-env - Delete virtual environment"
	@echo "  make lint      - Check code style and quality using ruff"
	@echo "  make format    - Format code using ruff"
	@echo "  make typecheck - Check types using mypy"
	@echo "  make test      - Run all code checks and tests using pytest"

install:
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@echo "Installing dependencies..."
	@. .venv/bin/activate && pip install -q -e ".[dev]"
	@echo ""
	@echo "✓ Dependencies installed. To activate the virtual environment, run:"
	@echo "  source .venv/bin/activate"

clean-env:
	@if [ -d ".venv" ]; then \
		echo "Removing virtual environment..."; \
		rm -rf .venv; \
		echo "✓ Virtual environment deleted."; \
	else \
		echo "Virtual environment not found (nothing to clean)."; \
	fi

lint:
	ruff check src apps

format:
	ruff format src apps

typecheck:
	mypy src apps

test: lint typecheck
	pytest
