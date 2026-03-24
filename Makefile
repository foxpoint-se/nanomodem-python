.PHONY: help lint format typecheck test

help:
	@echo "Available commands:"
	@echo "  make lint      - Check code style and quality using ruff"
	@echo "  make format    - Format code using ruff"
	@echo "  make typecheck - Check types using mypy"
	@echo "  make test      - Run all code checks and tests using pytest"

lint:
	ruff check src apps

format:
	ruff format src apps

typecheck:
	mypy src apps

test: lint typecheck
	pytest
