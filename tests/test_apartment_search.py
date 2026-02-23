"""Tests for apartment search and filtering."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from wohnung.apartment_search import ApartmentQuery, ApartmentSearcher, parse_relative_time
from wohnung.models import Flat
from wohnung.site_storage import SiteStorage


@pytest.fixture
def temp_storage(tmp_path: Path) -> SiteStorage:
    """Create temporary storage with test data."""
    storage = SiteStorage(data_dir=tmp_path)

    # Add test apartments
    apartments = [
        Flat(
            id="apt-1",
            title="Cheap Studio",
            url="https://example.com/1",
            price=800.0,
            size=30.0,
            rooms=1.0,
            location="Vienna",
            source="test-site",
            markers=["cheap"],
        ),
        Flat(
            id="apt-2",
            title="Nice 2-Room",
            url="https://example.com/2",
            price=1200.0,
            size=60.0,
            rooms=2.0,
            location="Vienna Inner City",
            source="test-site",
            markers=["vormerkung_possible"],
        ),
        Flat(
            id="apt-3",
            title="Luxury Penthouse",
            url="https://example.com/3",
            price=2500.0,
            size=120.0,
            rooms=4.0,
            location="München",
            source="another-site",
            markers=["luxury", "balcony"],
        ),
        Flat(
            id="apt-4",
            title="Student Flat",
            url="https://example.com/4",
            price=600.0,
            size=25.0,
            rooms=1.0,
            location="Berlin",
            source="test-site",
            markers=["cheap", "student"],
        ),
    ]

    storage.save_apartments("test-site", apartments[:2] + [apartments[3]])
    storage.save_apartments("another-site", [apartments[2]])

    return storage


@pytest.fixture
def searcher(temp_storage: SiteStorage) -> ApartmentSearcher:
    """Create searcher with test storage."""
    return ApartmentSearcher(temp_storage)


class TestApartmentQuery:
    """Tests for ApartmentQuery model."""

    def test_create_empty_query(self):
        """Test creating query with no filters."""
        query = ApartmentQuery()
        assert query.sites is None
        assert query.price_min is None
        assert query.active_only is True

    def test_create_query_with_filters(self):
        """Test creating query with various filters."""
        query = ApartmentQuery(
            sites=["test-site"],
            price_min=500.0,
            price_max=1500.0,
            size_min=40.0,
            rooms_min=2.0,
            markers=["vormerkung_possible"],
            location_contains="Vienna",
        )

        assert query.sites == ["test-site"]
        assert query.price_min == 500.0
        assert query.price_max == 1500.0
        assert query.size_min == 40.0
        assert query.rooms_min == 2.0
        assert query.markers == ["vormerkung_possible"]
        assert query.location_contains == "Vienna"


class TestApartmentSearcher:
    """Tests for ApartmentSearcher class."""

    def test_search_all_apartments(self, searcher: ApartmentSearcher):
        """Test searching without filters returns all apartments."""
        query = ApartmentQuery()
        results = searcher.search(query)

        assert len(results) == 4
        assert all(isinstance(apt, Flat) for apt in results)

    def test_filter_by_site(self, searcher: ApartmentSearcher):
        """Test filtering by site."""
        query = ApartmentQuery(sites=["test-site"])
        results = searcher.search(query)

        assert len(results) == 3
        assert all(apt.source == "test-site" for apt in results)

    def test_filter_by_price_range(self, searcher: ApartmentSearcher):
        """Test filtering by price range."""
        query = ApartmentQuery(price_min=700.0, price_max=1300.0)
        results = searcher.search(query)

        assert len(results) == 2
        assert all(700.0 <= apt.price <= 1300.0 for apt in results if apt.price)

    def test_filter_by_min_price_only(self, searcher: ApartmentSearcher):
        """Test filtering by minimum price."""
        query = ApartmentQuery(price_min=1000.0)
        results = searcher.search(query)

        assert len(results) == 2
        assert all(apt.price >= 1000.0 for apt in results if apt.price)

    def test_filter_by_max_price_only(self, searcher: ApartmentSearcher):
        """Test filtering by maximum price."""
        query = ApartmentQuery(price_max=1000.0)
        results = searcher.search(query)

        assert len(results) == 2
        assert all(apt.price <= 1000.0 for apt in results if apt.price)

    def test_filter_by_size_range(self, searcher: ApartmentSearcher):
        """Test filtering by size range."""
        query = ApartmentQuery(size_min=50.0, size_max=100.0)
        results = searcher.search(query)

        assert len(results) == 1
        assert all(50.0 <= apt.size <= 100.0 for apt in results if apt.size)

    def test_filter_by_rooms(self, searcher: ApartmentSearcher):
        """Test filtering by room count."""
        query = ApartmentQuery(rooms_min=2.0)
        results = searcher.search(query)

        assert len(results) == 2
        assert all(apt.rooms >= 2.0 for apt in results if apt.rooms)

    def test_filter_by_location(self, searcher: ApartmentSearcher):
        """Test filtering by location substring."""
        query = ApartmentQuery(location_contains="Vienna")
        results = searcher.search(query)

        assert len(results) == 2
        assert all("vienna" in apt.location.lower() for apt in results if apt.location)

    def test_filter_by_location_case_insensitive(self, searcher: ApartmentSearcher):
        """Test location filter is case-insensitive."""
        query = ApartmentQuery(location_contains="VIENNA")
        results = searcher.search(query)

        assert len(results) == 2

    def test_filter_by_marker(self, searcher: ApartmentSearcher):
        """Test filtering by marker."""
        query = ApartmentQuery(markers=["cheap"])
        results = searcher.search(query)

        assert len(results) == 2
        assert all("cheap" in apt.markers for apt in results if apt.markers)

    def test_filter_by_multiple_markers(self, searcher: ApartmentSearcher):
        """Test filtering by multiple markers (OR logic)."""
        query = ApartmentQuery(markers=["luxury", "vormerkung_possible"])
        results = searcher.search(query)

        # Should match apartments with either luxury OR vormerkung_possible
        assert len(results) == 2

    def test_combine_multiple_filters(self, searcher: ApartmentSearcher):
        """Test combining multiple filters (AND logic)."""
        query = ApartmentQuery(
            price_min=500.0,
            price_max=900.0,
            location_contains="Vienna",
            rooms_min=1.0,
        )
        results = searcher.search(query)

        assert len(results) == 1
        assert results[0].id == "apt-1"

    def test_sort_by_price_ascending(self, searcher: ApartmentSearcher):
        """Test sorting by price ascending."""
        query = ApartmentQuery(sort_by="price", sort_desc=False)
        results = searcher.search(query)

        prices = [apt.price for apt in results if apt.price]
        assert prices == sorted(prices)
        assert results[0].price == 600.0

    def test_sort_by_price_descending(self, searcher: ApartmentSearcher):
        """Test sorting by price descending."""
        query = ApartmentQuery(sort_by="price", sort_desc=True)
        results = searcher.search(query)

        prices = [apt.price for apt in results if apt.price]
        assert prices == sorted(prices, reverse=True)
        assert results[0].price == 2500.0

    def test_sort_by_size(self, searcher: ApartmentSearcher):
        """Test sorting by size."""
        query = ApartmentQuery(sort_by="size", sort_desc=True)
        results = searcher.search(query)

        sizes = [apt.size for apt in results if apt.size]
        assert sizes == sorted(sizes, reverse=True)

    def test_sort_by_rooms(self, searcher: ApartmentSearcher):
        """Test sorting by room count."""
        query = ApartmentQuery(sort_by="rooms", sort_desc=False)
        results = searcher.search(query)

        rooms = [apt.rooms for apt in results if apt.rooms]
        assert rooms == sorted(rooms)

    def test_limit_results(self, searcher: ApartmentSearcher):
        """Test limiting number of results."""
        query = ApartmentQuery(limit=2)
        results = searcher.search(query)

        assert len(results) == 2

    def test_limit_with_sorting(self, searcher: ApartmentSearcher):
        """Test limit applies after sorting."""
        query = ApartmentQuery(sort_by="price", sort_desc=False, limit=2)
        results = searcher.search(query)

        assert len(results) == 2
        assert results[0].price == 600.0
        assert results[1].price == 800.0

    def test_no_results(self, searcher: ApartmentSearcher):
        """Test search with no matching results."""
        query = ApartmentQuery(price_min=10000.0)
        results = searcher.search(query)

        assert len(results) == 0

    def test_filter_apartments_with_null_values(self, temp_storage: SiteStorage):
        """Test filtering apartments with missing fields."""
        # Add apartment with missing fields
        apt_no_price = Flat(
            id="apt-5",
            title="No Price Flat",
            url="https://example.com/5",
            location="Berlin",
            source="test-site",
        )
        temp_storage.save_apartments("test-site", [apt_no_price])

        searcher = ApartmentSearcher(temp_storage)

        # Should exclude apartments without price when filtering by price
        query = ApartmentQuery(price_min=500.0)
        results = searcher.search(query)

        assert all(apt.price is not None for apt in results)
        assert apt_no_price.id not in [apt.id for apt in results]


class TestExport:
    """Tests for export functionality."""

    def test_export_json(self, searcher: ApartmentSearcher, tmp_path: Path):
        """Test exporting apartments to JSON."""
        output_file = tmp_path / "apartments.json"
        query = ApartmentQuery()
        results = searcher.search(query)

        searcher.export_json(results, output_file)

        assert output_file.exists()

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == len(results)
        assert all("title" in apt for apt in data)
        assert all("url" in apt for apt in data)

    def test_export_json_empty(self, searcher: ApartmentSearcher, tmp_path: Path):
        """Test exporting empty results to JSON."""
        output_file = tmp_path / "empty.json"
        query = ApartmentQuery(price_min=99999.0)
        results = searcher.search(query)

        searcher.export_json(results, output_file)

        assert output_file.exists()

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data == []

    def test_export_csv(self, searcher: ApartmentSearcher, tmp_path: Path):
        """Test exporting apartments to CSV."""
        output_file = tmp_path / "apartments.csv"
        query = ApartmentQuery()
        results = searcher.search(query)

        searcher.export_csv(results, output_file)

        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # Check headers
        assert "title" in lines[0]
        assert "url" in lines[0]
        assert "price" in lines[0]

        # Check data rows
        assert len(lines) == len(results) + 1  # +1 for header

    def test_export_csv_empty(self, searcher: ApartmentSearcher, tmp_path: Path):
        """Test exporting empty results to CSV."""
        output_file = tmp_path / "empty.csv"
        query = ApartmentQuery(price_min=99999.0)
        results = searcher.search(query)

        searcher.export_csv(results, output_file)

        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # Should have headers only
        assert len(lines) == 1


class TestParseRelativeTime:
    """Tests for relative time parsing."""

    def test_parse_days_ago(self):
        """Test parsing 'X days ago'."""
        result = parse_relative_time("2 days ago")
        expected = datetime.now() - timedelta(days=2)

        # Allow 1 second tolerance
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_hours_ago(self):
        """Test parsing 'X hours ago'."""
        result = parse_relative_time("5 hours ago")
        expected = datetime.now() - timedelta(hours=5)

        assert abs((result - expected).total_seconds()) < 1

    def test_parse_weeks_ago(self):
        """Test parsing 'X weeks ago'."""
        result = parse_relative_time("1 week ago")
        expected = datetime.now() - timedelta(weeks=1)

        assert abs((result - expected).total_seconds()) < 1

    def test_parse_months_ago(self):
        """Test parsing 'X months ago'."""
        result = parse_relative_time("2 months ago")
        expected = datetime.now() - timedelta(days=60)

        assert abs((result - expected).total_seconds()) < 1

    def test_parse_last_day(self):
        """Test parsing 'last day'."""
        result = parse_relative_time("last day")
        expected = datetime.now() - timedelta(days=1)

        assert abs((result - expected).total_seconds()) < 1

    def test_parse_last_week(self):
        """Test parsing 'last week'."""
        result = parse_relative_time("last week")
        expected = datetime.now() - timedelta(weeks=1)

        assert abs((result - expected).total_seconds()) < 1

    def test_parse_today(self):
        """Test parsing 'today'."""
        result = parse_relative_time("today")
        expected = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        assert result.date() == expected.date()
        assert result.hour == 0
        assert result.minute == 0

    def test_parse_yesterday(self):
        """Test parsing 'yesterday'."""
        result = parse_relative_time("yesterday")
        expected = (datetime.now() - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        assert result.date() == expected.date()

    def test_parse_case_insensitive(self):
        """Test parsing is case-insensitive."""
        result1 = parse_relative_time("2 Days Ago")
        result2 = parse_relative_time("2 days ago")

        assert abs((result1 - result2).total_seconds()) < 1

    def test_parse_invalid_string(self):
        """Test parsing invalid time string raises error."""
        with pytest.raises(ValueError):
            parse_relative_time("invalid time")

    def test_parse_invalid_unit(self):
        """Test parsing invalid time unit raises error."""
        with pytest.raises(ValueError):
            parse_relative_time("2 fortnights ago")

    def test_parse_invalid_number(self):
        """Test parsing invalid number raises error."""
        with pytest.raises(ValueError):
            parse_relative_time("many days ago")


class TestIntegration:
    """Integration tests for search functionality."""

    def test_full_search_workflow(self, temp_storage: SiteStorage):
        """Test complete search workflow."""
        searcher = ApartmentSearcher(temp_storage)

        # Build complex query
        query = ApartmentQuery(
            sites=["test-site"],
            price_min=500.0,
            price_max=1000.0,
            size_min=25.0,
            sort_by="price",
            sort_desc=False,
            limit=10,
        )

        # Execute search
        results = searcher.search(query)

        # Verify results
        assert len(results) > 0
        assert all(apt.source == "test-site" for apt in results)
        assert all(500.0 <= apt.price <= 1000.0 for apt in results if apt.price)
        assert all(apt.size >= 25.0 for apt in results if apt.size)

        # Verify sorting
        prices = [apt.price for apt in results if apt.price]
        assert prices == sorted(prices)

    def test_search_and_export(self, temp_storage: SiteStorage, tmp_path: Path):
        """Test searching and exporting results."""
        searcher = ApartmentSearcher(temp_storage)
        output_file = tmp_path / "results.json"

        # Search
        query = ApartmentQuery(location_contains="Vienna")
        results = searcher.search(query)

        # Export
        searcher.export_json(results, output_file)

        # Verify
        assert output_file.exists()

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == len(results)
        assert all("vienna" in apt["location"].lower() for apt in data)
