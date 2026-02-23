"""Tests for change detection system."""

from datetime import datetime
from pathlib import Path

import pytest

from wohnung.change_detector import (
    ApartmentChange,
    ChangeDetector,
    ChangeDetectorConfig,
)
from wohnung.models import Flat
from wohnung.site_storage import SiteStorage


@pytest.fixture
def sample_flat() -> Flat:
    """Create a sample flat."""
    return Flat(
        id="test-123",
        title="Test Apartment",
        url="https://example.com/test-123",
        price=1000.0,
        rooms=3,
        size=80.0,
        location="Vienna",
        source="test-site",
    )


@pytest.fixture
def sample_flat_data(sample_flat: Flat) -> dict:
    """Get sample flat as dict."""
    return sample_flat.model_dump(mode="json")


@pytest.fixture
def detector() -> ChangeDetector:
    """Create a change detector."""
    return ChangeDetector()


class TestApartmentChange:
    """Tests for ApartmentChange model."""

    def test_create_new_change(self):
        """Test creating a new apartment change."""
        now = datetime.now()
        change = ApartmentChange(
            change_type="new",
            apartment_id="test-123",
            timestamp=now,
            changes={},
            apartment_data={"title": "Test"},
        )

        assert change.change_type == "new"
        assert change.apartment_id == "test-123"
        assert change.timestamp == now
        assert change.changes == {}

    def test_create_updated_change(self):
        """Test creating an updated apartment change."""
        now = datetime.now()
        change = ApartmentChange(
            change_type="updated",
            apartment_id="test-123",
            timestamp=now,
            changes={"price": (1000.0, 1100.0), "title": ("Old", "New")},
            apartment_data={"title": "New", "price": 1100.0},
        )

        assert change.change_type == "updated"
        assert len(change.changes) == 2
        assert change.changes["price"] == (1000.0, 1100.0)
        assert change.changes["title"] == ("Old", "New")

    def test_create_removed_change(self):
        """Test creating a removed apartment change."""
        now = datetime.now()
        change = ApartmentChange(
            change_type="removed",
            apartment_id="test-123",
            timestamp=now,
            changes={},
            apartment_data={"title": "Test"},
        )

        assert change.change_type == "removed"
        assert change.changes == {}

    def test_change_serialization(self):
        """Test that changes can be serialized to JSON."""
        now = datetime.now()
        change = ApartmentChange(
            change_type="new",
            apartment_id="test-123",
            timestamp=now,
            changes={},
            apartment_data={"title": "Test"},
        )

        json_str = change.model_dump_json()
        assert "test-123" in json_str
        assert "new" in json_str


class TestChangeDetectorConfig:
    """Tests for ChangeDetectorConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = ChangeDetectorConfig()

        assert "price" in config.monitored_fields
        assert "title" in config.monitored_fields
        assert "found_at" in config.ignore_fields
        assert "last_updated" in config.ignore_fields

    def test_custom_config(self):
        """Test custom configuration."""
        config = ChangeDetectorConfig(
            monitored_fields=["price", "title"],
            ignore_fields=["description"],
        )

        assert config.monitored_fields == ["price", "title"]
        assert config.ignore_fields == ["description"]


class TestChangeDetector:
    """Tests for ChangeDetector class."""

    def test_detect_new_apartment(self, detector: ChangeDetector, sample_flat: Flat):
        """Test detecting a new apartment."""
        changes = detector.detect_changes({}, [sample_flat])

        assert len(changes) == 1
        assert changes[0].change_type == "new"
        assert changes[0].apartment_id == sample_flat.id

    def test_detect_removed_apartment(self, detector: ChangeDetector, sample_flat_data: dict):
        """Test detecting a removed apartment."""
        old_apartments = {"test-123": sample_flat_data}
        changes = detector.detect_changes(old_apartments, [])

        assert len(changes) == 1
        assert changes[0].change_type == "removed"
        assert changes[0].apartment_id == "test-123"

    def test_detect_no_changes(
        self, detector: ChangeDetector, sample_flat: Flat, sample_flat_data: dict
    ):
        """Test no changes when apartment is unchanged."""
        old_apartments = {"test-123": sample_flat_data}
        changes = detector.detect_changes(old_apartments, [sample_flat])

        # Should have no changes (apartment unchanged)
        assert len(changes) == 0

    def test_detect_price_change(
        self, detector: ChangeDetector, sample_flat: Flat, sample_flat_data: dict
    ):
        """Test detecting a price change."""
        old_apartments = {"test-123": sample_flat_data}

        # Update price
        updated_flat = sample_flat.model_copy(update={"price": 1100.0})
        changes = detector.detect_changes(old_apartments, [updated_flat])

        assert len(changes) == 1
        assert changes[0].change_type == "updated"
        assert "price" in changes[0].changes
        assert changes[0].changes["price"] == (1000.0, 1100.0)

    def test_detect_title_change(
        self, detector: ChangeDetector, sample_flat: Flat, sample_flat_data: dict
    ):
        """Test detecting a title change."""
        old_apartments = {"test-123": sample_flat_data}

        # Update title
        updated_flat = sample_flat.model_copy(update={"title": "New Title"})
        changes = detector.detect_changes(old_apartments, [updated_flat])

        assert len(changes) == 1
        assert changes[0].change_type == "updated"
        assert "title" in changes[0].changes
        assert changes[0].changes["title"] == ("Test Apartment", "New Title")

    def test_detect_multiple_field_changes(
        self, detector: ChangeDetector, sample_flat: Flat, sample_flat_data: dict
    ):
        """Test detecting changes in multiple fields."""
        old_apartments = {"test-123": sample_flat_data}

        # Update multiple fields
        updated_flat = sample_flat.model_copy(update={"price": 1100.0, "size": 90.0, "rooms": 4})
        changes = detector.detect_changes(old_apartments, [updated_flat])

        assert len(changes) == 1
        assert changes[0].change_type == "updated"
        assert len(changes[0].changes) == 3
        assert "price" in changes[0].changes
        assert "size" in changes[0].changes
        assert "rooms" in changes[0].changes

    def test_detect_mixed_changes(self, detector: ChangeDetector, sample_flat: Flat):
        """Test detecting new, updated, and removed apartments together."""
        # Old apartments
        old_flat_data = sample_flat.model_dump(mode="json")
        old_apartments = {
            "test-123": old_flat_data,
            "test-456": {**old_flat_data, "id": "test-456"},
        }

        # New scrape: test-123 updated, test-456 removed, test-789 new
        updated_flat = sample_flat.model_copy(update={"price": 1100.0})
        new_flat = sample_flat.model_copy(update={"id": "test-789"})
        changes = detector.detect_changes(old_apartments, [updated_flat, new_flat])

        assert len(changes) == 3

        change_types = {c.apartment_id: c.change_type for c in changes}
        assert change_types["test-123"] == "updated"
        assert change_types["test-456"] == "removed"
        assert change_types["test-789"] == "new"

    def test_custom_monitored_fields(self, sample_flat: Flat, sample_flat_data: dict):
        """Test custom monitored fields configuration."""
        config = ChangeDetectorConfig(
            monitored_fields=["price"],  # Only monitor price
            ignore_fields=[],
        )
        detector = ChangeDetector(config)

        old_apartments = {"test-123": sample_flat_data}

        # Update both price and title
        updated_flat = sample_flat.model_copy(update={"price": 1100.0, "title": "New Title"})
        changes = detector.detect_changes(old_apartments, [updated_flat])

        # Should only detect price change
        assert len(changes) == 1
        assert len(changes[0].changes) == 1
        assert "price" in changes[0].changes
        assert "title" not in changes[0].changes

    def test_ignore_fields(self, sample_flat: Flat, sample_flat_data: dict):
        """Test that ignored fields are not tracked."""
        # Update found_at timestamp (should be ignored)
        updated_data = {**sample_flat_data}
        updated_data["found_at"] = datetime.now().isoformat()

        old_apartments = {"test-123": sample_flat_data}
        updated_flat = Flat(**updated_data)

        detector = ChangeDetector()
        changes = detector.detect_changes(old_apartments, [updated_flat])

        # Should not detect changes in ignored fields
        assert len(changes) == 0

    def test_get_significant_changes(self, detector: ChangeDetector):
        """Test filtering significant changes."""
        now = datetime.now()
        changes = [
            ApartmentChange(
                change_type="new",
                apartment_id="test-1",
                timestamp=now,
                changes={},
                apartment_data={},
            ),
            ApartmentChange(
                change_type="updated",
                apartment_id="test-2",
                timestamp=now,
                changes={},
                apartment_data={},
            ),
            ApartmentChange(
                change_type="removed",
                apartment_id="test-3",
                timestamp=now,
                changes={},
                apartment_data={},
            ),
        ]

        significant = detector.get_significant_changes(changes)
        assert len(significant) == 2
        assert all(c.change_type in ("new", "updated") for c in significant)

    def test_get_price_changes(self, detector: ChangeDetector):
        """Test filtering price changes."""
        now = datetime.now()
        changes = [
            ApartmentChange(
                change_type="updated",
                apartment_id="test-1",
                timestamp=now,
                changes={"price": (1000, 1100)},
                apartment_data={},
            ),
            ApartmentChange(
                change_type="updated",
                apartment_id="test-2",
                timestamp=now,
                changes={"title": ("Old", "New")},
                apartment_data={},
            ),
        ]

        price_changes = detector.get_price_changes(changes)
        assert len(price_changes) == 1
        assert price_changes[0].apartment_id == "test-1"

    def test_format_change_summary_new(self, detector: ChangeDetector):
        """Test formatting a new apartment change."""
        now = datetime.now()
        change = ApartmentChange(
            change_type="new",
            apartment_id="test-123",
            timestamp=now,
            changes={},
            apartment_data={"title": "Test Apartment"},
        )

        summary = detector.format_change_summary(change)
        assert "NEW:" in summary
        assert "Test Apartment" in summary

    def test_format_change_summary_updated(self, detector: ChangeDetector):
        """Test formatting an updated apartment change."""
        now = datetime.now()
        change = ApartmentChange(
            change_type="updated",
            apartment_id="test-123",
            timestamp=now,
            changes={"price": (1000, 1100), "size": (80, 90)},
            apartment_data={"title": "Test Apartment"},
        )

        summary = detector.format_change_summary(change)
        assert "UPDATED:" in summary
        assert "Test Apartment" in summary
        assert "Price: 1000 → 1100" in summary
        assert "Size: 80 → 90" in summary

    def test_format_change_summary_removed(self, detector: ChangeDetector):
        """Test formatting a removed apartment change."""
        now = datetime.now()
        change = ApartmentChange(
            change_type="removed",
            apartment_id="test-123",
            timestamp=now,
            changes={},
            apartment_data={"title": "Test Apartment"},
        )

        summary = detector.format_change_summary(change)
        assert "REMOVED:" in summary
        assert "Test Apartment" in summary


class TestSiteStorageWithChanges:
    """Tests for SiteStorage integration with change detection."""

    def test_save_apartments_with_changes_new(self, tmp_path: Path, sample_flat: Flat):
        """Test saving new apartments with detailed changes."""
        storage = SiteStorage(data_dir=tmp_path)

        changes = storage.save_apartments_with_changes("test-site", [sample_flat])

        assert len(changes) == 1
        assert changes[0].change_type == "new"
        assert changes[0].apartment_id == sample_flat.id

    def test_save_apartments_with_changes_updated(self, tmp_path: Path, sample_flat: Flat):
        """Test detecting updates with detailed field changes."""
        storage = SiteStorage(data_dir=tmp_path)

        # Save initial version
        storage.save_apartments("test-site", [sample_flat])

        # Update and save again
        updated_flat = sample_flat.model_copy(update={"price": 1100.0})
        changes = storage.save_apartments_with_changes("test-site", [updated_flat])

        assert len(changes) == 1
        assert changes[0].change_type == "updated"
        assert "price" in changes[0].changes
        assert changes[0].changes["price"] == (1000.0, 1100.0)

    def test_save_apartments_with_changes_removed(self, tmp_path: Path, sample_flat: Flat):
        """Test detecting removed apartments."""
        storage = SiteStorage(data_dir=tmp_path)

        # Save initial version
        storage.save_apartments("test-site", [sample_flat])

        # Save without the apartment (removed)
        changes = storage.save_apartments_with_changes("test-site", [])

        assert len(changes) == 1
        assert changes[0].change_type == "removed"
        assert changes[0].apartment_id == sample_flat.id

    def test_change_history_tracking(self, tmp_path: Path, sample_flat: Flat):
        """Test change history tracking."""
        storage = SiteStorage(data_dir=tmp_path)

        # Save with history tracking
        changes = storage.save_apartments_with_changes(
            "test-site", [sample_flat], track_history=True
        )

        assert len(changes) == 1

        # Check history file exists
        history_file = tmp_path / "test-site_history.jsonl"
        assert history_file.exists()

        # Retrieve history
        history = storage.get_change_history("test-site")
        assert len(history) == 1
        assert history[0].change_type == "new"
        assert history[0].apartment_id == sample_flat.id

    def test_change_history_multiple_changes(self, tmp_path: Path, sample_flat: Flat):
        """Test change history with multiple changes."""
        storage = SiteStorage(data_dir=tmp_path)

        # Multiple saves with history
        storage.save_apartments_with_changes("test-site", [sample_flat], track_history=True)

        updated_flat = sample_flat.model_copy(update={"price": 1100.0})
        storage.save_apartments_with_changes("test-site", [updated_flat], track_history=True)

        storage.save_apartments_with_changes("test-site", [], track_history=True)

        # Get full history
        history = storage.get_change_history("test-site")
        assert len(history) == 3

        # Most recent first
        assert history[0].change_type == "removed"
        assert history[1].change_type == "updated"
        assert history[2].change_type == "new"

    def test_change_history_with_limit(self, tmp_path: Path, sample_flat: Flat):
        """Test retrieving limited change history."""
        storage = SiteStorage(data_dir=tmp_path)

        # Create multiple changes
        for i in range(5):
            flat = sample_flat.model_copy(update={"price": 1000.0 + i * 100})
            storage.save_apartments_with_changes("test-site", [flat], track_history=True)

        # Get limited history
        history = storage.get_change_history("test-site", limit=2)
        assert len(history) == 2

    def test_get_change_history_no_file(self, tmp_path: Path):
        """Test getting history when no history file exists."""
        storage = SiteStorage(data_dir=tmp_path)

        history = storage.get_change_history("nonexistent")
        assert history == []
