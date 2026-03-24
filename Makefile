.PHONY: help test lint format typecheck check

help:
	@echo "Available commands:"
	@echo "  make test      - Run tests using pytest"
	@echo "  make lint      - Check code style and quality using ruff"
	@echo "  make format    - Format code using ruff"
	@echo "  make typecheck - Check types using mypy"
	@echo "  make check     - Run lint, typecheck, and test"

test:
	pytest

lint:
	ruff check src apps

format:
	ruff format src apps

typecheck:
	mypy src apps

check: lint typecheck test
