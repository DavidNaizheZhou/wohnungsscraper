"""Tests for scraper functionality."""

import pytest
from pytest_httpx import HTTPXMock

from wohnung.models import Flat
from wohnung.scrapers import deduplicate_flats
from wohnung.scrapers.example import ExampleScraper


class TestBaseScraper:
    """Tests for BaseScraper class."""

    def test_generate_id(self) -> None:
        """Test ID generation is consistent and unique."""
        scraper = ExampleScraper()

        id1 = scraper.generate_id("https://example.com/flat/123")
        id2 = scraper.generate_id("https://example.com/flat/123")
        id3 = scraper.generate_id("https://example.com/flat/456")

        # Same URL should generate same ID
        assert id1 == id2
        # Different URLs should generate different IDs
        assert id1 != id3
        # ID should contain scraper name
        assert id1.startswith("example-")

    @pytest.mark.parametrize(
        "price_str,expected",
        [
            ("€1,200", 1200.0),
            ("1200 EUR", 1200.0),
            ("$1,500.50", 1500.50),
            ("1200", 1200.0),
            ("EUR 1.200,50", 1200.50),
            ("no price here", None),
            ("", None),
        ],
    )
    def test_parse_price(self, price_str: str, expected: float | None) -> None:
        """Test price parsing from various formats."""
        scraper = ExampleScraper()
        result = scraper.parse_price(price_str)
        assert result == expected

    @pytest.mark.parametrize(
        "size_str,expected",
        [
            ("65 m²", 65.0),
            ("65m²", 65.0),
            ("65 m2", 65.0),
            ("65.5 sqm", 65.5),
            ("65,5 m²", 65.5),
            ("no size", None),
            ("", None),
        ],
    )
    def test_parse_size(self, size_str: str, expected: float | None) -> None:
        """Test size parsing from various formats."""
        scraper = ExampleScraper()
        result = scraper.parse_size(size_str)
        assert result == expected

    @pytest.mark.parametrize(
        "rooms_str,expected",
        [
            ("2 rooms", 2.0),
            ("2.5", 2.5),
            ("2,5 Zimmer", 2.5),
            ("Studio", None),
            ("", None),
        ],
    )
    def test_parse_rooms(self, rooms_str: str, expected: float | None) -> None:
        """Test rooms parsing from various formats."""
        scraper = ExampleScraper()
        result = scraper.parse_rooms(rooms_str)
        assert result == expected

    def test_context_manager(self) -> None:
        """Test scraper can be used as context manager."""
        with ExampleScraper() as scraper:
            assert scraper.client is not None
        # Client should be closed after context

    def test_fetch_html(self, httpx_mock: HTTPXMock, sample_html: str) -> None:
        """Test fetching and parsing HTML."""
        httpx_mock.add_response(
            url="https://example.com/test",
            text=sample_html,
        )

        scraper = ExampleScraper()
        soup = scraper.fetch_html("https://example.com/test")

        assert soup is not None
        listings = soup.select(".flat-listing")
        assert len(listings) == 2


class TestExampleScraper:
    """Tests for ExampleScraper."""

    def test_scraper_properties(self) -> None:
        """Test scraper has required properties."""
        scraper = ExampleScraper()
        assert scraper.name == "example"
        assert scraper.base_url == "https://example.com/flats"

    def test_scrape_success(self, httpx_mock: HTTPXMock, sample_html: str) -> None:
        """Test successful scraping with mocked response."""
        httpx_mock.add_response(
            url="https://example.com/flats",
            text=sample_html,
        )

        scraper = ExampleScraper()
        flats = scraper.scrape()

        assert len(flats) == 2

        # Check first flat
        flat1 = flats[0]
        assert flat1.title == "Beautiful 2-Room Apartment"
        assert flat1.price == 1200.0
        assert flat1.size == 65.0
        assert flat1.rooms == 2.0
        assert flat1.location == "Berlin-Mitte"
        assert flat1.source == "example"

        # Check second flat
        flat2 = flats[1]
        assert flat2.title == "Cozy Studio"
        assert flat2.price == 850.0

    def test_scrape_http_error(self, httpx_mock: HTTPXMock) -> None:
        """Test scraper handles HTTP errors gracefully."""
        httpx_mock.add_response(
            url="https://example.com/flats",
            status_code=404,
        )

        scraper = ExampleScraper()
        flats = scraper.scrape()

        # Should return empty list on error
        assert flats == []

    def test_scrape_invalid_html(self, httpx_mock: HTTPXMock) -> None:
        """Test scraper handles malformed HTML."""
        httpx_mock.add_response(
            url="https://example.com/flats",
            text="<html><body>No listings here</body></html>",
        )

        scraper = ExampleScraper()
        flats = scraper.scrape()

        assert flats == []


class TestScraperOrchestration:
    """Tests for scraper orchestration functions."""

    def test_deduplicate_flats(self, sample_flats: list[Flat]) -> None:
        """Test deduplication removes duplicates."""
        # Create list with duplicates
        flats_with_dupes = sample_flats + [sample_flats[0]]  # Add duplicate

        result = deduplicate_flats(flats_with_dupes)

        assert len(result) == 2
        assert result[0].id == "test-1"
        assert result[1].id == "test-2"

    def test_deduplicate_empty_list(self) -> None:
        """Test deduplication handles empty list."""
        result = deduplicate_flats([])
        assert result == []
