# Makefile for common development tasks

.PHONY: help install test lint format type-check check all clean

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies with uv
	uv sync --all-extras
	uv run pre-commit install

test:  ## Run tests with coverage
	uv run pytest --cov --cov-report=term-missing

test-fast:  ## Run tests without coverage
	uv run pytest -x

lint:  ## Run ruff linter (includes complexity checks)
	uv run ruff check src tests

lint-fix:  ## Run ruff linter and auto-fix issues
	uv run ruff check --fix src tests

format:  ## Format code with black
	uv run black src tests

format-check:  ## Check code formatting without changes
	uv run black --check src tests

type-check:  ## Run mypy type checker
	uv run mypy src

complexity:  ## Check code complexity with detailed report
	@echo "Checking code complexity (max: 10)..."
	uv run ruff check --select C90 src tests

pre-commit:  ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

check: lint format-check type-check  ## Run all checks (lint, format, type)
	@echo "✅ All checks passed!"

all: check test  ## Run all checks and tests

clean:  ## Clean up cache and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:  ## Run the scraper
	uv run wohnung-scrape

run-dry:  ## Run the scraper in dry-run mode (no emails)
	uv run wohnung-scrape --dry-run

watch:  ## Run tests in watch mode
	uv run pytest-watch

.DEFAULT_GOAL := help
