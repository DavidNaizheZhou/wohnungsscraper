# Pre-commit Git Hooks

This project can use pre-commit hooks to ensure code quality before commits.

## Setup

```bash
# Install pre-commit (if not already installed)
uv add --dev pre-commit

# Install the git hooks
uv run pre-commit install
```

## Manual Run

```bash
# Run on all files
uv run pre-commit run --all-files

# Run on staged files only
uv run pre-commit run
```

## .pre-commit-config.yaml

Create this file in the project root:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.2
    hooks:
      # Run the linter
      - id: ruff
        args: [--fix]
      # Run the formatter
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.19.1
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, pydantic-settings, httpx, beautifulsoup4, types-beautifulsoup4]
        args: [--strict, --ignore-missing-imports]
        files: ^src/
        exclude: ^tests/

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: check-toml
```
