"""Tests for site configuration system."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from wohnung.site_config import (
    MarkerConfig,
    PaginationConfig,
    SelectorMap,
    SiteConfig,
    SiteConfigLoader,
)


class TestSelectorMap:
    """Test CSS selector map."""

    def test_required_selectors(self):
        """Test that required selectors are validated."""
        selectors = SelectorMap(
            listing=".apartment",
            title="h2",
            url="a",
            location=".location",
        )
        assert selectors.listing == ".apartment"
        assert selectors.title == "h2"

    def test_optional_selectors(self):
        """Test optional selectors."""
        selectors = SelectorMap(
            listing=".apartment",
            title="h2",
            url="a",
            location=".location",
            price=".price",
            size=".size",
        )
        assert selectors.price == ".price"
        assert selectors.size == ".size"
        assert selectors.rooms is None


class TestPaginationConfig:
    """Test pagination configuration."""

    def test_disabled_pagination(self):
        """Test disabled pagination."""
        pagination = PaginationConfig(enabled=False)
        assert not pagination.enabled
        assert pagination.max_pages == 5

    def test_url_pattern_pagination(self):
        """Test URL pattern pagination."""
        pagination = PaginationConfig(enabled=True, url_pattern="?page={page}", max_pages=10)
        assert pagination.enabled
        assert pagination.url_pattern == "?page={page}"
        assert pagination.max_pages == 10


class TestMarkerConfig:
    """Test marker configuration."""

    def test_marker_creation(self):
        """Test creating a marker."""
        marker = MarkerConfig(
            name="vormerkung",
            label="Vormerkung möglich",
            patterns=["vormerkung", "vormerken"],
            priority="high",
        )
        assert marker.name == "vormerkung"
        assert marker.label == "Vormerkung möglich"
        assert len(marker.patterns) == 2
        assert marker.priority == "high"

    def test_default_search_fields(self):
        """Test default search_in fields."""
        marker = MarkerConfig(name="test", label="Test", patterns=["test"], priority="low")
        assert marker.search_in == ["title", "description"]


class TestSiteConfig:
    """Test site configuration model."""

    def test_basic_site_config(self):
        """Test creating a basic site config."""
        config = SiteConfig(
            name="test_site",
            display_name="Test Site",
            base_url="https://example.com",
            selectors=SelectorMap(
                listing=".item",
                title="h2",
                url="a",
                location=".loc",
            ),
        )
        assert config.name == "test_site"
        assert config.display_name == "Test Site"
        assert config.enabled is True

    def test_site_with_markers(self):
        """Test site config with markers."""
        config = SiteConfig(
            name="test",
            display_name="Test",
            base_url="https://example.com",
            selectors=SelectorMap(listing=".item", title="h2", url="a", location=".loc"),
            markers=[MarkerConfig(name="new", label="New", patterns=["new"], priority="high")],
        )
        assert len(config.markers) == 1
        assert config.markers[0].name == "new"

    def test_request_settings(self):
        """Test request timeout and rate limit settings."""
        config = SiteConfig(
            name="test",
            display_name="Test",
            base_url="https://example.com",
            selectors=SelectorMap(listing=".item", title="h2", url="a", location=".loc"),
            request_timeout=60,
            rate_limit_delay=2.5,
        )
        assert config.request_timeout == 60
        assert config.rate_limit_delay == 2.5

    def test_invalid_timeout(self):
        """Test that invalid timeouts are rejected."""
        with pytest.raises(ValidationError):
            SiteConfig(
                name="test",
                display_name="Test",
                base_url="https://example.com",
                selectors=SelectorMap(listing=".item", title="h2", url="a", location=".loc"),
                request_timeout=200,  # Too high
            )


class TestSiteConfigLoader:
    """Test site configuration loader."""

    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        loader = SiteConfigLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_site(Path("nonexistent.yaml"))

    def test_load_empty_directory(self):
        """Test loading from empty directory."""
        loader = SiteConfigLoader("nonexistent_dir")
        configs = loader.load_all_sites()
        assert configs == {}

    def test_validate_config(self, tmp_path):
        """Test config validation."""
        # Create a valid config file
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""
name: test
display_name: Test Site
base_url: https://example.com
enabled: true
selectors:
  listing: .item
  title: h2
  url: a
  location: .loc
""")

        loader = SiteConfigLoader()
        is_valid, message = loader.validate_config(config_file)
        assert is_valid
        assert "Valid configuration" in message

    def test_validate_invalid_config(self, tmp_path):
        """Test validating invalid config."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("""
name: test
# Missing required fields
""")

        loader = SiteConfigLoader()
        is_valid, message = loader.validate_config(config_file)
        assert not is_valid
        assert len(message) > 0
