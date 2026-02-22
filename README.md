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

# Install dependencies
uv sync --all-extras

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
uv run wohnung-scrape

# Dry run (no email)
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

## 🧩 Adding New Scrapers

1. Create a new scraper class in `src/wohnung/scrapers/`:

```python
from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper

class ImmoscoutScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "immoscout"
    
    @property
    def base_url(self) -> str:
        return "https://www.immobilienscout24.de/..."
    
    def scrape(self) -> list[Flat]:
        soup = self.fetch_html(self.base_url)
        flats = []
        
        for listing in soup.select(".listing-selector"):
            flat = Flat(
                id=self.generate_id(url),
                title=listing.select_one(".title").text,
                url=listing.select_one("a")["href"],
                price=self.parse_price(listing.select_one(".price").text),
                # ... more fields
                location="...",
                source=self.name,
            )
            flats.append(flat)
        
        return flats
```

2. Register it in `src/wohnung/scrapers/__init__.py`:

```python
from wohnung.scrapers.immoscout import ImmoscoutScraper

SCRAPERS: list[type[BaseScraper]] = [
    ExampleScraper,
    ImmoscoutScraper,  # Add here
]
```

3. Write tests in `tests/test_scrapers.py`:

```python
def test_immoscout_scraper(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://www.immobilienscout24.de/...",
        text=mock_html,
    )
    
    scraper = ImmoscoutScraper()
    flats = scraper.scrape()
    
    assert len(flats) > 0
```

## 🧪 Development

### Run Tests

```bash
# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/test_scrapers.py

# Run with verbose output
uv run pytest -v

# Run only fast tests (skip slow/integration)
uv run pytest -m "not slow"
```

### Code Quality

```bash
# Lint with ruff
uv run ruff check src tests

# Auto-fix issues
uv run ruff check --fix src tests

# Format with black
uv run black src tests

# Type check with mypy
uv run mypy src
```

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
