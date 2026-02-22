"""Pytest configuration and fixtures."""

from collections.abc import Generator
from pathlib import Path

import pytest

from wohnung.models import Flat
from wohnung.storage import JSONStorage


@pytest.fixture
def sample_html() -> str:
    """Sample HTML response for scraper tests."""
    return """
    <html>
    <body>
        <div class="flat-listing">
            <h2 class="title">Beautiful 2-Room Apartment</h2>
            <a href="/flat/123">View Details</a>
            <span class="price">€1,200</span>
            <span class="size">65 m²</span>
            <span class="rooms">2 rooms</span>
            <span class="location">Berlin-Mitte</span>
            <img src="https://example.com/image.jpg" alt="flat" />
        </div>
        <div class="flat-listing">
            <h2 class="title">Cozy Studio</h2>
            <a href="/flat/456">View Details</a>
            <span class="price">€850</span>
            <span class="size">35m2</span>
            <span class="rooms">1</span>
            <span class="location">Kreuzberg</span>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_flat() -> Flat:
    """Create a sample Flat object for testing."""
    return Flat(
        id="test-123",
        title="Test Apartment",
        url="https://example.com/flat/123",
        price=1000.0,
        size=50.0,
        rooms=2.0,
        location="Test Location",
        description="A test apartment",
        image_url="https://example.com/image.jpg",
        source="test",
    )


@pytest.fixture
def sample_flats() -> list[Flat]:
    """Create a list of sample Flat objects."""
    return [
        Flat(
            id="test-1",
            title="Flat 1",
            url="https://example.com/1",
            price=1000.0,
            size=50.0,
            rooms=2.0,
            location="Location 1",
            source="test",
        ),
        Flat(
            id="test-2",
            title="Flat 2",
            url="https://example.com/2",
            price=1500.0,
            size=75.0,
            rooms=3.0,
            location="Location 2",
            source="test",
        ),
    ]


@pytest.fixture
def temp_storage(tmp_path: Path) -> Generator[JSONStorage, None, None]:
    """Create a temporary storage for testing."""
    storage_file = tmp_path / "test_flats.json"
    storage = JSONStorage(storage_file=storage_file)
    yield storage
    # Cleanup is automatic with tmp_path


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up mock environment variables."""
    monkeypatch.setenv("EMAIL_TO", "test@example.com")
    monkeypatch.setenv("EMAIL_FROM", "sender@example.com")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")
