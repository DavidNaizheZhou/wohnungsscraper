"""Tests for git-optimized site storage."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from wohnung.models import Flat
from wohnung.site_storage import ApartmentMetadata, SiteStorage, SiteStorageData


@pytest.fixture
def temp_storage(tmp_path: Path) -> SiteStorage:
    """Create temporary storage."""
    return SiteStorage(data_dir=tmp_path)


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


class TestApartmentMetadata:
    """Tests for ApartmentMetadata model."""

    def test_create_metadata(self):
        """Test creating apartment metadata."""
        now = datetime.now()
        metadata = ApartmentMetadata(
            apartment_id="test-123",
            status="active",
            first_seen=now,
            last_seen=now,
            last_updated=now,
            data={"title": "Test"},
        )

        assert metadata.apartment_id == "test-123"
        assert metadata.status == "active"
        assert metadata.first_seen == now
        assert metadata.data == {"title": "Test"}

    def test_metadata_serialization(self):
        """Test metadata can be serialized to JSON."""
        now = datetime.now()
        metadata = ApartmentMetadata(
            apartment_id="test-123",
            status="active",
            first_seen=now,
            last_seen=now,
            last_updated=now,
            data={"title": "Test"},
        )

        # Should serialize without errors
        json_str = metadata.model_dump_json()
        assert "test-123" in json_str


class TestSiteStorageData:
    """Tests for SiteStorageData model."""

    def test_create_site_data(self):
        """Test creating site storage data."""
        now = datetime.now()
        data = SiteStorageData(site="test-site", last_scrape=now, apartments={})

        assert data.site == "test-site"
        assert data.last_scrape == now
        assert data.apartments == {}

    def test_site_data_with_apartments(self):
        """Test site data with apartments."""
        now = datetime.now()
        metadata = ApartmentMetadata(
            apartment_id="test-123",
            status="active",
            first_seen=now,
            last_seen=now,
            last_updated=now,
            data={},
        )

        data = SiteStorageData(site="test-site", last_scrape=now, apartments={"test-123": metadata})

        assert len(data.apartments) == 1
        assert "test-123" in data.apartments


class TestSiteStorage:
    """Tests for SiteStorage class."""

    def test_initialization(self, tmp_path: Path):
        """Test storage initialization."""
        storage = SiteStorage(data_dir=tmp_path / "test")
        assert storage.data_dir == tmp_path / "test"
        assert storage.data_dir.exists()

    def test_get_site_file(self, temp_storage: SiteStorage):
        """Test getting site file path."""
        path = temp_storage._get_site_file("test-site")
        assert path.name == "test-site.json"
        assert path.parent == temp_storage.data_dir

    def test_save_and_read_apartments(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test saving and reading apartments."""
        new, updated, removed = temp_storage.save_apartments("test-site", [sample_flat])

        assert len(new) == 1
        assert new[0] == sample_flat.id
        assert len(updated) == 0
        assert len(removed) == 0

        apartments = temp_storage.get_apartments("test-site")
        assert len(apartments) == 1
        assert sample_flat.id in apartments
        assert apartments[sample_flat.id].status == "active"

    def test_apartment_exists(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test checking apartment existence."""
        assert not temp_storage.apartment_exists("test-site", sample_flat.id)

        temp_storage.save_apartments("test-site", [sample_flat])

        assert temp_storage.apartment_exists("test-site", sample_flat.id)
        assert not temp_storage.apartment_exists("test-site", "nonexistent")

    def test_update_detection(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test detecting updated apartments."""
        # Save initial version
        temp_storage.save_apartments("test-site", [sample_flat])

        # Update price
        updated_flat = sample_flat.model_copy(update={"price": 1100.0})
        new, updated, removed = temp_storage.save_apartments("test-site", [updated_flat])

        assert len(new) == 0
        assert len(updated) == 1
        assert updated[0] == sample_flat.id
        assert len(removed) == 0

        # Verify data was updated
        apartments = temp_storage.get_apartments("test-site")
        assert apartments[sample_flat.id].data["price"] == 1100.0

    def test_no_update_when_unchanged(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test no update detected when data unchanged."""
        temp_storage.save_apartments("test-site", [sample_flat])

        # Save same data again
        new, updated, removed = temp_storage.save_apartments("test-site", [sample_flat])

        assert len(new) == 0
        assert len(updated) == 0
        assert len(removed) == 0

    def test_removal_detection(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test detecting removed apartments."""
        # Save apartment
        temp_storage.save_apartments("test-site", [sample_flat])

        # Scrape without the apartment
        new, updated, removed = temp_storage.save_apartments("test-site", [])

        assert len(new) == 0
        assert len(updated) == 0
        assert len(removed) == 1
        assert removed[0] == sample_flat.id

        # Check it's marked as removed
        apartments = temp_storage.get_apartments("test-site")
        assert apartments[sample_flat.id].status == "removed"

    def test_no_removal_when_disabled(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test no removal when mark_missing_as_removed is False."""
        temp_storage.save_apartments("test-site", [sample_flat])

        _new, _updated, removed = temp_storage.save_apartments(
            "test-site", [], mark_missing_as_removed=False
        )

        assert len(removed) == 0

        # Should still be marked as active
        apartments = temp_storage.get_apartments("test-site")
        assert apartments[sample_flat.id].status == "active"

    def test_reactivation_of_removed(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test apartment gets reactivated when it reappears."""
        # Save, remove, then save again
        temp_storage.save_apartments("test-site", [sample_flat])
        temp_storage.save_apartments("test-site", [])
        new, updated, _removed = temp_storage.save_apartments("test-site", [sample_flat])

        # Should not be new, but updated (reactivated)
        assert len(new) == 0
        assert len(updated) == 1

        apartments = temp_storage.get_apartments("test-site")
        assert apartments[sample_flat.id].status == "active"

    def test_get_active_apartments(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test getting only active apartments."""
        flat2 = sample_flat.model_copy(update={"id": "test-456"})

        # Save both
        temp_storage.save_apartments("test-site", [sample_flat, flat2])

        # Remove one
        temp_storage.save_apartments("test-site", [sample_flat])

        active = temp_storage.get_active_apartments("test-site")
        assert len(active) == 1
        assert sample_flat.id in active
        assert flat2.id not in active

    def test_get_site_stats(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test getting site statistics."""
        flat2 = sample_flat.model_copy(update={"id": "test-456"})

        temp_storage.save_apartments("test-site", [sample_flat, flat2])
        temp_storage.save_apartments("test-site", [sample_flat])

        stats = temp_storage.get_site_stats("test-site")
        assert stats["total"] == 2
        assert stats["active"] == 1
        assert stats["removed"] == 1
        assert stats["newest"] is not None
        assert stats["oldest"] is not None

    def test_list_sites(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test listing all sites."""
        assert temp_storage.list_sites() == []

        temp_storage.save_apartments("site1", [sample_flat])
        temp_storage.save_apartments("site2", [sample_flat])

        sites = temp_storage.list_sites()
        assert len(sites) == 2
        assert "site1" in sites
        assert "site2" in sites

    def test_multiple_apartments(self, temp_storage: SiteStorage):
        """Test handling multiple apartments."""
        flats = [
            Flat(
                id=f"test-{i}",
                title=f"Apartment {i}",
                url=f"https://example.com/{i}",
                price=1000.0 + i * 100,
                location="Vienna",
                source="test-site",
            )
            for i in range(5)
        ]

        new, _, _ = temp_storage.save_apartments("test-site", flats)
        assert len(new) == 5

        apartments = temp_storage.get_apartments("test-site")
        assert len(apartments) == 5

    def test_git_friendly_format(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test that output is git-friendly (sorted, formatted)."""
        temp_storage.save_apartments("test-site", [sample_flat])

        site_file = temp_storage._get_site_file("test-site")
        content = site_file.read_text()

        # Check for proper JSON formatting
        data = json.loads(content)
        assert "site" in data
        assert "apartments" in data
        assert "last_scrape" in data

        # Check trailing newline
        assert content.endswith("\n")

        # Check it's valid JSON
        json.loads(content)

    def test_empty_site_data(self, temp_storage: SiteStorage):
        """Test handling non-existent site."""
        apartments = temp_storage.get_apartments("nonexistent")
        assert apartments == {}

        active = temp_storage.get_active_apartments("nonexistent")
        assert active == {}

        assert not temp_storage.apartment_exists("nonexistent", "test-123")

    def test_migrate_from_legacy(self, temp_storage: SiteStorage, tmp_path: Path):
        """Test migration from legacy storage format."""
        # Create legacy file
        legacy_file = tmp_path / "flats.json"
        legacy_data = {
            "flats": {
                "test-123": {
                    "title": "Test Apartment",
                    "url": "https://example.com/test",
                    "price": 1000.0,
                    "source": "legacy-site",
                    "found_at": datetime.now().isoformat(),
                },
                "test-456": {
                    "title": "Another Apartment",
                    "url": "https://example.com/test2",
                    "price": 1200.0,
                    "source": "another-site",
                    "found_at": datetime.now().isoformat(),
                },
            },
            "last_updated": datetime.now().isoformat(),
        }

        with open(legacy_file, "w") as f:
            json.dump(legacy_data, f)

        # Migrate
        temp_storage.migrate_from_legacy(legacy_file)

        # Check migration worked
        sites = temp_storage.list_sites()
        assert "legacy-site" in sites
        assert "another-site" in sites

        legacy_apartments = temp_storage.get_apartments("legacy-site")
        assert "test-123" in legacy_apartments

        another_apartments = temp_storage.get_apartments("another-site")
        assert "test-456" in another_apartments

    def test_timestamps_preserved(self, temp_storage: SiteStorage, sample_flat: Flat):
        """Test that timestamps are properly preserved."""
        temp_storage.save_apartments("test-site", [sample_flat])

        apartments = temp_storage.get_apartments("test-site")
        apt = apartments[sample_flat.id]

        assert isinstance(apt.first_seen, datetime)
        assert isinstance(apt.last_seen, datetime)
        assert isinstance(apt.last_updated, datetime)
        assert apt.first_seen == apt.last_seen == apt.last_updated
