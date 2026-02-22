# Quick Start with uv

## Install uv

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

## Setup Project

```bash
# Clone repository
git clone https://github.com/yourusername/wohnung.git
cd wohnung

# Install all dependencies (creates .venv automatically)
uv sync --all-extras
```

## Development Commands

```bash
# Run scraper
uv run wohnung-scrape

# Run scraper (dry run)
uv run wohnung-scrape --dry-run

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Lint code
uv run ruff check src tests

# Fix linting issues
uv run ruff check --fix src tests

# Format code
uv run black src tests

# Type check
uv run mypy src

# Add new dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Update dependencies
uv sync

# Lock dependencies
uv lock
```

## Why uv?

- ⚡ **10-100x faster** than pip
- 📦 **All-in-one** tool (replaces pip, pip-tools, virtualenv)
- 🔒 **Lockfile support** for reproducible installs
- 🚀 **Written in Rust** - blazing fast
- 🎯 **Drop-in replacement** - works with existing pyproject.toml

## Environment Setup

```bash
# uv automatically creates virtual environment in .venv/
# Activate it (optional, uv run works without activation)
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Or just use uv run for everything
uv run python script.py
uv run pytest
```

## GitHub Actions

The project uses uv in CI/CD:
- Faster dependency installation
- Automatic caching
- Consistent environments
