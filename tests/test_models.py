"""Tests for models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from wohnung.models import Flat, ScraperResult


class TestFlat:
    """Tests for Flat model."""

    def test_flat_creation(self) -> None:
        """Test creating a valid Flat."""
        flat = Flat(
            id="test-123",
            title="Test Flat",
            url="https://example.com/flat/123",
            location="Test City",
            source="test",
        )

        assert flat.id == "test-123"
        assert flat.title == "Test Flat"
        assert str(flat.url) == "https://example.com/flat/123"
        assert flat.location == "Test City"
        assert flat.source == "test"

    def test_flat_with_optional_fields(self) -> None:
        """Test Flat with all optional fields."""
        flat = Flat(
            id="test-123",
            title="Luxury Apartment",
            url="https://example.com/flat/123",
            price=1500.0,
            size=75.5,
            rooms=3.0,
            location="Downtown",
            description="A beautiful apartment",
            image_url="https://example.com/image.jpg",
            source="test",
        )

        assert flat.price == 1500.0
        assert flat.size == 75.5
        assert flat.rooms == 3.0
        assert flat.description == "A beautiful apartment"
        assert str(flat.image_url) == "https://example.com/image.jpg"

    def test_flat_invalid_url(self) -> None:
        """Test Flat validation fails with invalid URL."""
        with pytest.raises(ValidationError):
            Flat(
                id="test-123",
                title="Test",
                url="not-a-valid-url",  # type: ignore
                location="Test",
                source="test",
            )

    def test_flat_missing_required_fields(self) -> None:
        """Test Flat validation fails when required fields are missing."""
        with pytest.raises(ValidationError):
            Flat(id="test-123")  # type: ignore

    def test_flat_json_serialization(self, sample_flat: Flat) -> None:
        """Test Flat can be serialized to JSON."""
        json_data = sample_flat.model_dump(mode="json")

        assert json_data["id"] == "test-123"
        assert json_data["title"] == "Test Apartment"
        assert isinstance(json_data["url"], str)
        assert isinstance(json_data["found_at"], str)  # ISO format

    def test_flat_found_at_default(self) -> None:
        """Test found_at field has default value."""
        flat = Flat(
            id="test",
            title="Test",
            url="https://example.com",
            location="Test",
            source="test",
        )

        assert isinstance(flat.found_at, datetime)
        # Should be recent (within last minute)
        assert (datetime.now() - flat.found_at).total_seconds() < 60


class TestScraperResult:
    """Tests for ScraperResult model."""

    def test_scraper_result_creation(self) -> None:
        """Test creating a ScraperResult."""
        result = ScraperResult(
            flats=[],
            source="test",
        )

        assert result.source == "test"
        assert result.flats == []
        assert result.errors == []
        assert isinstance(result.scraped_at, datetime)

    def test_scraper_result_with_flats(self, sample_flats: list[Flat]) -> None:
        """Test ScraperResult with flats."""
        result = ScraperResult(
            flats=sample_flats,
            source="test",
        )

        assert len(result.flats) == 2
        assert result.flats[0].id == "test-1"

    def test_scraper_result_with_errors(self) -> None:
        """Test ScraperResult with errors."""
        result = ScraperResult(
            flats=[],
            source="test",
            errors=["Error 1", "Error 2"],
        )

        assert len(result.errors) == 2
        assert not result.success

    def test_scraper_result_success_property(self) -> None:
        """Test success property."""
        # No errors = success
        result1 = ScraperResult(flats=[], source="test")
        assert result1.success

        # With errors = not success
        result2 = ScraperResult(flats=[], source="test", errors=["Error"])
        assert not result2.success
