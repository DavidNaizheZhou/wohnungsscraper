# 🏠 Wohnung Scraper

[![Tests](https://github.com/yourusername/wohnung/workflows/Tests/badge.svg)](https://github.com/yourusername/wohnung/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Automated flat/apartment scraping with email notifications. Runs on GitHub Actions - completely free!

## ✨ Features

- 🔍 **Extensible scraper architecture** - Easy to add new sources
- 📧 **Email notifications** - Get notified about new flats instantly
- 💾 **JSON storage** - Simple, git-friendly flat tracking
- ⏰ **Scheduled runs** - Automatic scraping every 4 hours via GitHub Actions
- 🧪 **Comprehensive tests** - 90%+ test coverage with pytest
- 🛠️ **Modern Python tooling** - Ruff, Black, MyPy, Pydantic
- 📦 **Best practices** - Clean architecture with src-layout

## 🚀 Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/wohnung.git
cd wohnung

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and setup dev environment
uv run wohnung install

# This creates a virtual environment automatically in .venv/
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

Get your Resend API key from [resend.com](https://resend.com) (free tier includes 100 emails/day).

### 3. Run Locally

```bash
# Run scraper
uv run wohnung scrape

# Dry run (no email)
uv run wohnung scrape --dry-run

# Or use the legacy command
uv run wohnung-scrape --dry-run
```

### 4. Set Up GitHub Actions

1. Fork this repository
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Add these secrets:
   - `EMAIL_TO`: Your email address(es)
   - `EMAIL_FROM`: Sender email (use your verified domain)
   - `RESEND_API_KEY`: Your Resend API key

The scraper will now run automatically every 4 hours!

### 5. Project Board (Optional)

Set up GitHub CLI for easy issue/backlog management:

```bash
# Install GitHub CLI (choose your OS)
# macOS
brew install gh

# Linux (Debian/Ubuntu)
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install gh

# Windows
winget install GitHub.cli

# Authenticate
gh auth login

# Verify setup
uv run wohnung board setup-check
```

## 📁 Project Structure

```
wohnung/
├── .github/
│   └── workflows/          # GitHub Actions workflows
│       ├── scrape.yml      # Scheduled scraping
│       └── test.yml        # CI/CD tests
├── src/
│   └── wohnung/
│       ├── __init__.py
│       ├── config.py       # Settings with pydantic-settings
│       ├── models.py       # Data models (Flat, ScraperResult)
│       ├── main.py         # Main entry point
│       ├── scrapers/       # Scraper implementations
│       │   ├── base.py     # Abstract base scraper
│       │   ├── example.py  # Example scraper
│       │   └── __init__.py # Scraper orchestration
│       ├── storage/        # Data persistence
│       │   └── __init__.py # JSON storage
│       └── email/          # Email notifications
│           └── __init__.py # Email sending
├── tests/                  # Comprehensive test suite
│   ├── conftest.py         # Pytest fixtures
│   ├── test_models.py
│   ├── test_scrapers.py    # Tests with mocked HTTP
│   └── test_storage.py
├── pyproject.toml          # Project config & dependencies
├── .env.example            # Environment template
└── README.md
```

## 🌐 Site Management

The scraper uses YAML-based site configurations for easy extensibility. Add new sites without writing code!

### Quick Start: Adding a New Site

```bash
# 1. Generate a template
uv run wohnung site new immoscout24 --url "https://www.immobilienscout24.de/..."

# 2. Edit the configuration
vim sites/immoscout24.yaml

# 3. Validate your config
uv run wohnung site validate sites/immoscout24.yaml

# 4. Test scraping (dry-run)
uv run wohnung site test immoscout24 --max-pages 1

# 5. Enable the site
# Set enabled: true in sites/immoscout24.yaml

# 6. Run the scraper
uv run wohnung scrape
```

### Site Configuration Structure

```yaml
name: immoscout24
display_name: "ImmobilienScout24"
base_url: "https://www.immobilienscout24.de/..."
enabled: true

selectors:
  listing: "article.result-list-entry"  # Container for each apartment
  title: "h5.title"                     # Apartment title
  url: "a.link"                         # Link to detail page
  location: "div.address"               # Location
  price: "dd.price"                     # Monthly rent (optional)
  size: "dd.size"                       # Size in m² (optional)
  rooms: "dd.rooms"                     # Number of rooms (optional)
  description: "p.description"          # Description (optional)
  image: "img.main-image"               # Main image (optional)

# Optional: Pagination
pagination:
  enabled: true
  max_pages: 5
  url_pattern: "?page={page}"  # or use next_selector

# Optional: Markers for special keywords
markers:
  - name: vormerkung_possible
    label: "Vormerkung möglich"
    patterns: ["vormerkung möglich", "vormerken"]
    priority: high
    search_in: [title, description]

request_timeout: 30
rate_limit_delay: 1.0
```

### Site Commands

```bash
# List all configured sites
uv run wohnung site list

# View site details
uv run wohnung site info immoscout24

# Test marker detection
uv run wohnung site test-markers oevw --limit 20

# Validate configuration
uv run wohnung site validate sites/mysite.yaml
```

### Example Configurations

The project includes ready-to-use examples:

- **[immoscout24.yaml.example](sites/immoscout24.yaml.example)** - ImmobilienScout24
- **[wg-gesucht.yaml.example](sites/wg-gesucht.yaml.example)** - WG-Gesucht.de
- **[ebay-kleinanzeigen.yaml.example](sites/ebay-kleinanzeigen.yaml.example)** - eBay Kleinanzeigen
- **[immowelt.yaml.example](sites/immowelt.yaml.example)** - Immowelt
- **[willhaben.yaml.example](sites/willhaben.yaml.example)** - Willhaben.at (Austria)

Copy any example, adjust selectors for your needs, and you're ready to go!

### Detailed Guide

For a comprehensive step-by-step guide, see **[docs/adding-sites.md]( docs/adding-sites.md)**:

- How to inspect websites and find selectors
- Selector reference and CSS tips
- Marker configuration guide
- Pagination setup
- Troubleshooting common issues
- Best practices

## 🧪 Development

The project includes a comprehensive Typer CLI for all development tasks:

```bash
# Show all available commands
uv run wohnung --help
uv run wohnung info

# Setup and installation
uv run wohnung install              # Install deps + pre-commit hooks
uv run wohnung install --skip-hooks # Skip pre-commit installation

# Testing
uv run wohnung test                 # Run tests with coverage
uv run wohnung test --no-coverage   # Fast tests without coverage
uv run wohnung test -v              # Verbose output
uv run wohnung test -x              # Stop on first failure

# Code quality
uv run wohnung lint                 # Check linting
uv run wohnung lint --fix           # Auto-fix issues
uv run wohnung lint --complexity    # Show complexity only
uv run wohnung format               # Format code
uv run wohnung format --check       # Check formatting only
uv run wohnung type-check           # Run mypy
uv run wohnung pre-commit           # Run pre-commit hooks
uv run wohnung check                # Run all checks (lint + format + type)
uv run wohnung all                  # Run checks + tests

# Scraping
uv run wohnung scrape               # Run scraper
uv run wohnung scrape --dry-run     # Test without emails

# Project board & issue management (requires gh CLI)
uv run wohnung board setup-check    # Check if gh is installed
uv run wohnung board templates      # Show available templates
uv run wohnung board create "Title" # Create basic issue
uv run wohnung board create "Bug title" -t bug           # Bug report
uv run wohnung board create "Feature title" -t feature   # Feature request
uv run wohnung board create "Site name" -t scraper       # Scraper task
uv run wohnung board list           # List open issues
uv run wohnung board list --state closed  # List closed issues
uv run wohnung board view 42        # View issue #42
uv run wohnung board view 42 -w     # Open issue #42 in browser

# Maintenance
uv run wohnung clean                # Clean cache and artifacts
```

## 📋 Project Management with GitHub Boards

With GitHub Pro (free for public repos), you can use the board commands to manage your backlog:

### Quick Start

```bash
# 1. Check setup
uv run wohnung board setup-check

# 2. Create issues from templates
uv run wohnung board create "Immoscout24 scraper" -t scraper
uv run wohnung board create "Email styling broken" -t bug
uv run wohnung board create "Add price alerts" -t feature

# 3. List and view
uv run wohnung board list
uv run wohnung board view 1
```

### Issue Templates

The CLI includes ready-to-use templates:

- **`bug`** - Bug reports with reproduction steps
- **`feature`** - Feature requests with motivation/solution
- **`scraper`** - Scraper implementation tasks with checklist

Each template:
- Pre-fills structured content
- Adds appropriate labels
- Creates actionable checklist items

### Link to GitHub Projects

1. Create a Project board on GitHub (Settings → Projects)
2. Enable workflow automation
3. Link your repository
4. Issues created via CLI will automatically appear in your board!

### Enable Shell Completion (Optional)

```bash
# Bash
uv run wohnung --install-completion bash

# Zsh
uv run wohnung --install-completion zsh

# Fish
uv run wohnung --install-completion fish
```

### Legacy Makefile Commands (Deprecated)

The CLI replaces the old Makefile. If you prefer make-style commands, these are still available:
- `make install` → `wohnung install`
- `make test` → `wohnung test`
### Legacy Makefile Commands (Deprecated)

The CLI replaces the old Makefile. If you prefer make-style commands, these are still available:
- `make install` → `wohnung install`
- `make test` → `wohnung test`
- `make lint` / `make lint-fix` → `wohnung lint [--fix]`
- `make check` → `wohnung check`

### Testing with Mocked HTTP

The project uses `pytest-httpx` to mock HTTP requests:

```python
def test_scraper(httpx_mock: HTTPXMock):
    # Mock HTTP response
    httpx_mock.add_response(
        url="https://example.com/flats",
        text="<html>...</html>",
        status_code=200,
    )

    scraper = ExampleScraper()
    flats = scraper.scrape()

    assert len(flats) > 0
```

This way you can test scraper logic without making real HTTP requests!

## 📊 GitHub Actions Workflows

### Scraping Workflow (`scrape.yml`)

- **Schedule**: Every 4 hours (customize with cron syntax)
- **Manual trigger**: Click "Run workflow" in Actions tab
- **Artifacts**: Saves `data/` directory for 30 days

### Test Workflow (`test.yml`)

- Runs on push to main
- Tests across Python 3.11, 3.12, 3.13
- Includes: linting, formatting, type checking, tests
- Uploads coverage to Codecov

## ⚙️ Configuration

All configuration is done via environment variables (see `.env.example`):

| Variable | Required | Description |
|----------|----------|-------------|
| `EMAIL_TO` | Yes | Comma-separated recipient emails |
| `EMAIL_FROM` | Yes | Sender email (verified domain) |
| `RESEND_API_KEY` | Yes | Resend API key |
| `DATA_DIR` | No | Data directory (default: `./data`) |
| `REQUEST_TIMEOUT` | No | HTTP timeout in seconds (default: 30) |
| `USER_AGENT` | No | Custom user agent string |

## 🎓 Design Patterns & Best Practices

This project demonstrates:

- **Strategy Pattern**: Pluggable scrapers via `BaseScraper`
- **Repository Pattern**: `JSONStorage` abstracts data access
- **Dependency Injection**: Settings via `pydantic-settings`
- **Factory Pattern**: `get_scrapers()` creates scraper instances
- **Context Manager Protocol**: Automatic resource cleanup
- **Modern Python Packaging**: src-layout, pyproject.toml
- **Type Safety**: Full type hints with MyPy strict mode
- **Test-Driven Development**: Comprehensive test coverage

## 📝 Testing Strategy

### Why pytest for scrapers?

✅ **Mocking HTTP requests** - Test scraper logic without hitting real sites
✅ **Fixtures** - Reusable test data and setup
✅ **Parametrized tests** - Test multiple scenarios easily
✅ **Coverage reporting** - Ensure all code is tested
✅ **Fast execution** - No network calls = fast tests

### Test Structure

- **Unit tests**: Individual components (models, parsing functions)
- **Integration tests**: Scraper workflows with mocked HTTP
- **Fixtures**: Reusable test data in `conftest.py`
- **Mocking**: `pytest-httpx` for HTTP, `monkeypatch` for env vars

## 🔒 Privacy & Data

- All data stored locally in `data/` directory
- No external database required
- Git-friendly JSON format
- Scraped data not committed to repo (in `.gitignore`)

## 📜 License

MIT License - see LICENSE file

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Run linting: `ruff check src tests`
6. Submit a pull request

## 💡 Tips

- **Respect robots.txt** and rate limits
- **Test scrapers locally** before deploying
- **Monitor GitHub Actions** for failures
- **Update scrapers** when sites change their HTML
- **Use descriptive commit messages** for git history

## 🐛 Troubleshooting

**Tests failing?**
```bash
uv sync --all-extras  # Ensure dev dependencies installed
```

**GitHub Actions not running?**
- Check your secrets are set correctly
- Verify cron schedule syntax
- Look at Actions logs for details

**No emails received?**
- Verify Resend API key is valid
- Check sender domain is verified
- Look for errors in console output

## 🚀 Next Steps

- [ ] Add more scraper implementations
- [ ] Set up email templates
- [ ] Add database support (PostgreSQL, SQLite)
- [ ] Create web dashboard
- [ ] Add Telegram/Discord notifications
- [ ] Implement search filters

---

Made with ❤️ and Python
