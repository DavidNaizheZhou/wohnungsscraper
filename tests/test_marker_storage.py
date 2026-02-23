"""Tests for marker filtering in storage."""

import pytest
from pydantic import HttpUrl

from wohnung.models import Flat
from wohnung.site_storage import SiteStorage


@pytest.fixture
def temp_storage(tmp_path):
    """Create a temporary storage directory."""
    return SiteStorage(tmp_path)


@pytest.fixture
def sample_flats_with_markers():
    """Sample flats with various markers."""
    return [
        Flat(
            id="flat-1",
            title="Wohnung mit Vormerkung",
            url=HttpUrl("https://example.com/1"),
            location="Wien",
            source="test",
            markers=["vormerkung_possible", "neubau"],
        ),
        Flat(
            id="flat-2",
            title="Sofort verfügbare Wohnung",
            url=HttpUrl("https://example.com/2"),
            location="Wien",
            source="test",
            markers=["immediate_availability"],
        ),
        Flat(
            id="flat-3",
            title="Standard Wohnung",
            url=HttpUrl("https://example.com/3"),
            location="Wien",
            source="test",
            markers=[],  # No markers
        ),
        Flat(
            id="flat-4",
            title="Geförderte Neubauwohnung",
            url=HttpUrl("https://example.com/4"),
            location="Wien",
            source="test",
            markers=["subsidized", "neubau"],
        ),
    ]


class TestMarkerFiltering:
    """Tests for marker filtering in storage."""

    def test_get_apartments_with_single_marker(
        self, temp_storage: SiteStorage, sample_flats_with_markers: list[Flat]
    ) -> None:
        """Test filtering apartments by a single marker."""
        # Save flats
        temp_storage.save_apartments("test_site", sample_flats_with_markers)

        # Filter by vormerkung_possible
        filtered = temp_storage.get_apartments_with_markers("test_site", ["vormerkung_possible"])

        assert len(filtered) == 1
        assert "flat-1" in filtered
        assert filtered["flat-1"].data["markers"] == ["vormerkung_possible", "neubau"]

    def test_get_apartments_with_multiple_markers(
        self, temp_storage: SiteStorage, sample_flats_with_markers: list[Flat]
    ) -> None:
        """Test filtering apartments by multiple markers (OR logic)."""
        # Save flats
        temp_storage.save_apartments("test_site", sample_flats_with_markers)

        # Filter by vormerkung_possible OR immediate_availability
        filtered = temp_storage.get_apartments_with_markers(
            "test_site", ["vormerkung_possible", "immediate_availability"]
        )

        assert len(filtered) == 2
        assert "flat-1" in filtered  # Has vormerkung_possible
        assert "flat-2" in filtered  # Has immediate_availability
        assert "flat-3" not in filtered  # Has no markers
        assert "flat-4" not in filtered  # Has different markers

    def test_get_apartments_with_common_marker(
        self, temp_storage: SiteStorage, sample_flats_with_markers: list[Flat]
    ) -> None:
        """Test filtering by a marker that appears in multiple apartments."""
        # Save flats
        temp_storage.save_apartments("test_site", sample_flats_with_markers)

        # Filter by neubau (appears in flat-1 and flat-4)
        filtered = temp_storage.get_apartments_with_markers("test_site", ["neubau"])

        assert len(filtered) == 2
        assert "flat-1" in filtered
        assert "flat-4" in filtered

    def test_get_apartments_with_nonexistent_marker(
        self, temp_storage: SiteStorage, sample_flats_with_markers: list[Flat]
    ) -> None:
        """Test filtering by a marker that doesn't exist."""
        # Save flats
        temp_storage.save_apartments("test_site", sample_flats_with_markers)

        # Filter by non-existent marker
        filtered = temp_storage.get_apartments_with_markers("test_site", ["non_existent_marker"])

        assert len(filtered) == 0

    def test_active_only_filtering(
        self, temp_storage: SiteStorage, sample_flats_with_markers: list[Flat]
    ) -> None:
        """Test that active_only parameter works correctly."""
        # Save initial flats
        temp_storage.save_apartments("test_site", sample_flats_with_markers)

        # Remove some flats (simulate them being gone)
        temp_storage.save_apartments(
            "test_site",
            [sample_flats_with_markers[0], sample_flats_with_markers[2]],
            mark_missing_as_removed=True,
        )

        # Filter with active_only=True (default)
        active_filtered = temp_storage.get_apartments_with_markers(
            "test_site", ["neubau"], active_only=True
        )

        # Only flat-1 should be returned (flat-4 was removed)
        assert len(active_filtered) == 1
        assert "flat-1" in active_filtered

        # Filter with active_only=False
        all_filtered = temp_storage.get_apartments_with_markers(
            "test_site", ["neubau"], active_only=False
        )

        # Both flat-1 and flat-4 should be returned
        assert len(all_filtered) == 2
        assert "flat-1" in all_filtered
        assert "flat-4" in all_filtered

    def test_empty_marker_list(
        self, temp_storage: SiteStorage, sample_flats_with_markers: list[Flat]
    ) -> None:
        """Test filtering with an empty marker list."""
        # Save flats
        temp_storage.save_apartments("test_site", sample_flats_with_markers)

        # Filter with empty marker list
        filtered = temp_storage.get_apartments_with_markers("test_site", [])

        # Should return no apartments
        assert len(filtered) == 0

    def test_filtering_nonexistent_site(self, temp_storage: SiteStorage) -> None:
        """Test filtering on a site that doesn't exist."""
        # Filter on non-existent site
        filtered = temp_storage.get_apartments_with_markers("nonexistent_site", ["some_marker"])

        # Should return empty dict
        assert len(filtered) == 0
        assert isinstance(filtered, dict)

    def test_apartments_without_markers_field(self, temp_storage: SiteStorage) -> None:
        """Test filtering when some apartments don't have markers field."""
        # Create flats without markers field in data
        flats = [
            Flat(
                id="old-flat-1",
                title="Old apartment",
                url=HttpUrl("https://example.com/old1"),
                location="Wien",
                source="test",
                # markers field exists in model but may not be in stored data
            ),
            Flat(
                id="new-flat-1",
                title="New apartment",
                url=HttpUrl("https://example.com/new1"),
                location="Wien",
                source="test",
                markers=["special"],
            ),
        ]

        # Save flats
        temp_storage.save_apartments("test_site", flats)

        # Filter by marker
        filtered = temp_storage.get_apartments_with_markers("test_site", ["special"])

        # Should find the one with markers
        assert len(filtered) == 1
        assert "new-flat-1" in filtered
