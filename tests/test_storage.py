"""Tests for storage functionality."""

from pathlib import Path

from wohnung.models import Flat
from wohnung.storage import JSONStorage


class TestJSONStorage:
    """Tests for JSONStorage class."""

    def test_storage_initialization(self, tmp_path: Path) -> None:
        """Test storage file is created on initialization."""
        storage_file = tmp_path / "test.json"
        storage = JSONStorage(storage_file=storage_file)

        assert storage_file.exists()
        assert storage.storage_file == storage_file

    def test_save_and_retrieve_flat(self, temp_storage: JSONStorage, sample_flat: Flat) -> None:
        """Test saving and retrieving a single flat."""
        temp_storage.save_flat(sample_flat)

        assert temp_storage.flat_exists(sample_flat.id)

        flats = temp_storage.get_all_flats()
        assert len(flats) == 1
        assert flats[0].id == sample_flat.id
        assert flats[0].title == sample_flat.title

    def test_save_multiple_flats(self, temp_storage: JSONStorage, sample_flats: list[Flat]) -> None:
        """Test saving multiple flats at once."""
        saved = temp_storage.save_flats(sample_flats)

        assert saved == 2
        assert temp_storage.flat_exists("test-1")
        assert temp_storage.flat_exists("test-2")

    def test_save_flats_prevents_duplicates(
        self, temp_storage: JSONStorage, sample_flats: list[Flat]
    ) -> None:
        """Test that saving same flats twice doesn't create duplicates."""
        # Save first time
        saved1 = temp_storage.save_flats(sample_flats)
        assert saved1 == 2

        # Save again
        saved2 = temp_storage.save_flats(sample_flats)
        assert saved2 == 0  # No new flats saved

        # Should still have only 2 flats
        all_flats = temp_storage.get_all_flats()
        assert len(all_flats) == 2

    def test_filter_new_flats(self, temp_storage: JSONStorage, sample_flats: list[Flat]) -> None:
        """Test filtering returns only unseen flats."""
        # Save first flat
        temp_storage.save_flat(sample_flats[0])

        # Filter should only return second flat
        new_flats = temp_storage.filter_new_flats(sample_flats)

        assert len(new_flats) == 1
        assert new_flats[0].id == "test-2"

    def test_flat_exists(self, temp_storage: JSONStorage, sample_flat: Flat) -> None:
        """Test checking flat existence."""
        assert not temp_storage.flat_exists(sample_flat.id)

        temp_storage.save_flat(sample_flat)

        assert temp_storage.flat_exists(sample_flat.id)

    def test_get_stats(self, temp_storage: JSONStorage, sample_flats: list[Flat]) -> None:
        """Test getting storage statistics."""
        temp_storage.save_flats(sample_flats)

        stats = temp_storage.get_stats()

        assert stats["total_flats"] == 2
        assert "test" in stats["by_source"]
        assert stats["by_source"]["test"] == 2
        assert "last_updated" in stats

    def test_get_all_flats_empty(self, temp_storage: JSONStorage) -> None:
        """Test getting flats from empty storage."""
        flats = temp_storage.get_all_flats()
        assert flats == []

    def test_storage_persists_data(self, tmp_path: Path, sample_flat: Flat) -> None:
        """Test that data persists across storage instances."""
        storage_file = tmp_path / "persistent.json"

        # Save with first instance
        storage1 = JSONStorage(storage_file=storage_file)
        storage1.save_flat(sample_flat)

        # Load with second instance
        storage2 = JSONStorage(storage_file=storage_file)
        flats = storage2.get_all_flats()

        assert len(flats) == 1
        assert flats[0].id == sample_flat.id
