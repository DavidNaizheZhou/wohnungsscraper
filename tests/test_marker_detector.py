"""Tests for marker detection functionality."""

import pytest
from pydantic import HttpUrl

from wohnung.marker_detector import MarkerDetector
from wohnung.models import Flat
from wohnung.site_config import MarkerConfig


@pytest.fixture
def sample_markers() -> list[MarkerConfig]:
    """Sample marker configurations for testing."""
    return [
        MarkerConfig(
            name="vormerkung_possible",
            label="Vormerkung möglich",
            patterns=["vormerkung möglich", "vormerken"],
            priority="high",
            search_in=["title", "description"],
        ),
        MarkerConfig(
            name="in_planning",
            label="In Planung",
            patterns=["in planung", "bauphase", "baubeginn"],
            priority="medium",
            search_in=["title", "description"],
        ),
        MarkerConfig(
            name="immediate_availability",
            label="Sofort verfügbar",
            patterns=["sofort verfügbar", "ab sofort"],
            priority="high",
            search_in=["title", "description"],
        ),
        MarkerConfig(
            name="subsidized",
            label="Gefördert",
            patterns=["gefördert", "gefördertes", "sozialwohnung"],
            priority="medium",
            search_in=["description"],
        ),
    ]


@pytest.fixture
def sample_flat() -> Flat:
    """Sample apartment for testing."""
    return Flat(
        id="test-123",
        title="Schöne 3-Zimmer Wohnung in Wien",
        url=HttpUrl("https://example.com/flat/123"),
        price=850.0,
        size=75.0,
        rooms=3.0,
        location="1010 Wien",
        description="Moderne Wohnung mit Balkon. Vormerkung möglich ab März 2026.",
        source="test",
    )


class TestMarkerConfig:
    """Tests for MarkerConfig model."""

    def test_marker_config_creation(self) -> None:
        """Test creating a marker configuration."""
        marker = MarkerConfig(
            name="test_marker",
            label="Test Marker",
            patterns=["pattern1", "pattern2"],
            priority="high",
        )

        assert marker.name == "test_marker"
        assert marker.label == "Test Marker"
        assert marker.patterns == ["pattern1", "pattern2"]
        assert marker.priority == "high"
        assert marker.search_in == ["title", "description"]  # default

    def test_marker_config_custom_search_fields(self) -> None:
        """Test marker with custom search fields."""
        marker = MarkerConfig(
            name="title_only",
            label="Title Only",
            patterns=["test"],
            priority="low",
            search_in=["title"],
        )

        assert marker.search_in == ["title"]


class TestMarkerDetector:
    """Tests for MarkerDetector class."""

    def test_detector_initialization(self, sample_markers: list[MarkerConfig]) -> None:
        """Test initializing the detector."""
        detector = MarkerDetector(sample_markers)
        assert len(detector.markers) == 4

        # Check priority sorting (high should come first)
        assert detector.markers[0].priority == "high"
        assert detector.markers[-1].priority == "medium"

    def test_detect_marker_in_description(self, sample_markers: list[MarkerConfig]) -> None:
        """Test detecting marker in German description text."""
        detector = MarkerDetector(sample_markers)

        flat = Flat(
            id="test-1",
            title="Wohnung in Wien",
            url=HttpUrl("https://example.com/1"),
            location="Wien",
            description="Moderne Wohnung. Vormerkung möglich ab sofort.",
            source="test",
        )

        detected = detector.detect_markers(flat)
        assert "vormerkung_possible" in detected

    def test_detect_marker_in_title(self, sample_markers: list[MarkerConfig]) -> None:
        """Test detecting marker in title."""
        detector = MarkerDetector(sample_markers)

        flat = Flat(
            id="test-2",
            title="Wohnung - Sofort verfügbar!",
            url=HttpUrl("https://example.com/2"),
            location="Wien",
            source="test",
        )

        detected = detector.detect_markers(flat)
        assert "immediate_availability" in detected

    def test_case_insensitive_matching(self, sample_markers: list[MarkerConfig]) -> None:
        """Test that matching is case-insensitive."""
        detector = MarkerDetector(sample_markers)

        # Uppercase in title
        flat1 = Flat(
            id="test-3",
            title="VORMERKUNG MÖGLICH - Neue Wohnung",
            url=HttpUrl("https://example.com/3"),
            location="Wien",
            source="test",
        )

        detected1 = detector.detect_markers(flat1)
        assert "vormerkung_possible" in detected1

        # Mixed case in description
        flat2 = Flat(
            id="test-4",
            title="Wohnung",
            url=HttpUrl("https://example.com/4"),
            location="Wien",
            description="VoRmErKuNg MöGlIcH",
            source="test",
        )

        detected2 = detector.detect_markers(flat2)
        assert "vormerkung_possible" in detected2

    def test_multiple_markers_detected(self, sample_markers: list[MarkerConfig]) -> None:
        """Test detecting multiple markers in one apartment."""
        detector = MarkerDetector(sample_markers)

        flat = Flat(
            id="test-5",
            title="Neubauwohnung - Sofort verfügbar",
            url=HttpUrl("https://example.com/5"),
            location="Wien",
            description="Geförderte Wohnung in Bauphase. Vormerkung möglich.",
            source="test",
        )

        detected = detector.detect_markers(flat)
        assert "vormerkung_possible" in detected
        assert "in_planning" in detected
        assert "immediate_availability" in detected
        assert "subsidized" in detected
        assert len(detected) == 4

    def test_no_markers_detected(self, sample_markers: list[MarkerConfig]) -> None:
        """Test when no markers match."""
        detector = MarkerDetector(sample_markers)

        flat = Flat(
            id="test-6",
            title="Standard Wohnung",
            url=HttpUrl("https://example.com/6"),
            location="Wien",
            description="Schöne Wohnung mit Balkon.",
            source="test",
        )

        detected = detector.detect_markers(flat)
        assert len(detected) == 0

    def test_priority_ordering(self) -> None:
        """Test that markers are returned in priority order."""
        markers = [
            MarkerConfig(
                name="low_marker",
                label="Low",
                patterns=["low"],
                priority="low",
            ),
            MarkerConfig(
                name="high_marker",
                label="High",
                patterns=["high"],
                priority="high",
            ),
            MarkerConfig(
                name="medium_marker",
                label="Medium",
                patterns=["medium"],
                priority="medium",
            ),
        ]

        detector = MarkerDetector(markers)

        flat = Flat(
            id="test-7",
            title="low high medium",
            url=HttpUrl("https://example.com/7"),
            location="Wien",
            source="test",
        )

        detected = detector.detect_markers(flat)
        # Should be in priority order: high, medium, low
        assert detected == ["high_marker", "medium_marker", "low_marker"]

    def test_multiple_patterns_per_marker(self) -> None:
        """Test marker with multiple alternative patterns."""
        markers = [
            MarkerConfig(
                name="availability",
                label="Available",
                patterns=["ab sofort", "sofort verfügbar", "verfügbar"],
                priority="high",
            ),
        ]

        detector = MarkerDetector(markers)

        # Test first pattern
        flat1 = Flat(
            id="test-8",
            title="Wohnung ab sofort",
            url=HttpUrl("https://example.com/8"),
            location="Wien",
            source="test",
        )
        assert "availability" in detector.detect_markers(flat1)

        # Test second pattern
        flat2 = Flat(
            id="test-9",
            title="Sofort verfügbar",
            url=HttpUrl("https://example.com/9"),
            location="Wien",
            source="test",
        )
        assert "availability" in detector.detect_markers(flat2)

        # Test third pattern
        flat3 = Flat(
            id="test-10",
            title="Jetzt verfügbar",
            url=HttpUrl("https://example.com/10"),
            location="Wien",
            source="test",
        )
        assert "availability" in detector.detect_markers(flat3)

    def test_regex_pattern_detection(self) -> None:
        """Test detection with regex patterns."""
        markers = [
            MarkerConfig(
                name="room_count",
                label="3+ Rooms",
                patterns=[r"\b[3-9]\s*zimmer", r"\b[3-9]-zimmer"],
                priority="medium",
            ),
        ]

        detector = MarkerDetector(markers)

        # Should match
        flat1 = Flat(
            id="test-11",
            title="Schöne 3 Zimmer Wohnung",
            url=HttpUrl("https://example.com/11"),
            location="Wien",
            source="test",
        )
        assert "room_count" in detector.detect_markers(flat1)

        # Should match
        flat2 = Flat(
            id="test-12",
            title="5-Zimmer Maisonette",
            url=HttpUrl("https://example.com/12"),
            location="Wien",
            source="test",
        )
        assert "room_count" in detector.detect_markers(flat2)

        # Should not match (2 rooms)
        flat3 = Flat(
            id="test-13",
            title="Gemütliche 2 Zimmer Wohnung",
            url=HttpUrl("https://example.com/13"),
            location="Wien",
            source="test",
        )
        assert "room_count" not in detector.detect_markers(flat3)

    def test_search_in_title_only(self) -> None:
        """Test marker that only searches in title."""
        markers = [
            MarkerConfig(
                name="title_marker",
                label="Title Marker",
                patterns=["special"],
                priority="high",
                search_in=["title"],
            ),
        ]

        detector = MarkerDetector(markers)

        # In title - should match
        flat1 = Flat(
            id="test-14",
            title="Special apartment",
            url=HttpUrl("https://example.com/14"),
            location="Wien",
            description="Regular description",
            source="test",
        )
        assert "title_marker" in detector.detect_markers(flat1)

        # Only in description - should NOT match
        flat2 = Flat(
            id="test-15",
            title="Regular apartment",
            url=HttpUrl("https://example.com/15"),
            location="Wien",
            description="This is special",
            source="test",
        )
        assert "title_marker" not in detector.detect_markers(flat2)

    def test_search_in_description_only(self) -> None:
        """Test marker that only searches in description."""
        markers = [
            MarkerConfig(
                name="desc_marker",
                label="Description Marker",
                patterns=["keyword"],
                priority="low",
                search_in=["description"],
            ),
        ]

        detector = MarkerDetector(markers)

        # In description - should match
        flat1 = Flat(
            id="test-16",
            title="Regular apartment",
            url=HttpUrl("https://example.com/16"),
            location="Wien",
            description="Contains keyword here",
            source="test",
        )
        assert "desc_marker" in detector.detect_markers(flat1)

        # Only in title - should NOT match
        flat2 = Flat(
            id="test-17",
            title="Apartment with keyword",
            url=HttpUrl("https://example.com/17"),
            location="Wien",
            description="Regular description",
            source="test",
        )
        assert "desc_marker" not in detector.detect_markers(flat2)

    def test_detect_and_update(self, sample_markers: list[MarkerConfig]) -> None:
        """Test detect_and_update method."""
        detector = MarkerDetector(sample_markers)

        flat = Flat(
            id="test-18",
            title="Wohnung - Sofort verfügbar",
            url=HttpUrl("https://example.com/18"),
            location="Wien",
            description="Vormerkung möglich.",
            source="test",
        )

        assert flat.markers == []  # Initially empty

        updated_flat = detector.detect_and_update(flat)

        assert len(updated_flat.markers) > 0
        assert "vormerkung_possible" in updated_flat.markers
        assert "immediate_availability" in updated_flat.markers

    def test_get_marker_label(self, sample_markers: list[MarkerConfig]) -> None:
        """Test getting marker label by name."""
        detector = MarkerDetector(sample_markers)

        label = detector.get_marker_label("vormerkung_possible")
        assert label == "Vormerkung möglich"

        label = detector.get_marker_label("in_planning")
        assert label == "In Planung"

        # Non-existent marker
        label = detector.get_marker_label("non_existent")
        assert label is None

    def test_get_marker_priority(self, sample_markers: list[MarkerConfig]) -> None:
        """Test getting marker priority by name."""
        detector = MarkerDetector(sample_markers)

        priority = detector.get_marker_priority("vormerkung_possible")
        assert priority == "high"

        priority = detector.get_marker_priority("in_planning")
        assert priority == "medium"

        # Non-existent marker
        priority = detector.get_marker_priority("non_existent")
        assert priority is None

    def test_german_special_characters(self) -> None:
        """Test handling of German special characters (umlauts)."""
        markers = [
            MarkerConfig(
                name="furnished",
                label="Möbliert",
                patterns=["möbliert", "möblierte", "eingerichtet"],
                priority="medium",
            ),
        ]

        detector = MarkerDetector(markers)

        flat = Flat(
            id="test-19",
            title="Schöne möblierte Wohnung",
            url=HttpUrl("https://example.com/19"),
            location="Wien",
            source="test",
        )

        detected = detector.detect_markers(flat)
        assert "furnished" in detected

    def test_empty_title_and_description(self, sample_markers: list[MarkerConfig]) -> None:
        """Test marker detection with missing title/description."""
        detector = MarkerDetector(sample_markers)

        flat = Flat(
            id="test-20",
            title="Title only, no description",
            url=HttpUrl("https://example.com/20"),
            location="Wien",
            description=None,
            source="test",
        )

        # Should not crash, returns empty list
        detected = detector.detect_markers(flat)
        assert isinstance(detected, list)

    def test_invalid_regex_pattern_fallback(self) -> None:
        """Test that invalid regex patterns fall back to exact match."""
        markers = [
            MarkerConfig(
                name="bad_regex",
                label="Bad Regex",
                patterns=["test(unclosed", "valid"],
                priority="low",
            ),
        ]

        detector = MarkerDetector(markers)

        # Should still match valid pattern
        flat = Flat(
            id="test-21",
            title="This is valid test",
            url=HttpUrl("https://example.com/21"),
            location="Wien",
            source="test",
        )

        detected = detector.detect_markers(flat)
        assert "bad_regex" in detected  # Matches "valid" pattern


class TestMarkerIntegration:
    """Integration tests for marker functionality."""

    def test_flat_model_has_markers_field(self) -> None:
        """Test that Flat model includes markers field."""
        flat = Flat(
            id="test-100",
            title="Test",
            url=HttpUrl("https://example.com/100"),
            location="Wien",
            source="test",
        )

        assert hasattr(flat, "markers")
        assert isinstance(flat.markers, list)
        assert len(flat.markers) == 0  # default empty

    def test_flat_model_with_markers(self) -> None:
        """Test creating Flat with markers."""
        flat = Flat(
            id="test-101",
            title="Test",
            url=HttpUrl("https://example.com/101"),
            location="Wien",
            source="test",
            markers=["marker1", "marker2"],
        )

        assert flat.markers == ["marker1", "marker2"]

    def test_full_workflow_german_text(self) -> None:
        """Test complete workflow with German text examples."""
        # Configure markers
        markers = [
            MarkerConfig(
                name="vormerkung",
                label="Vormerkung möglich",
                patterns=["vormerkung", "vormerken"],
                priority="high",
            ),
            MarkerConfig(
                name="neubau",
                label="Neubau",
                patterns=["neubau", "erstbezug", "neubauprojekt"],
                priority="medium",
            ),
            MarkerConfig(
                name="befristet",
                label="Befristete Vermietung",
                patterns=["befristet", "zeitlich begrenzt"],
                priority="low",
            ),
        ]

        detector = MarkerDetector(markers)

        # Sample German apartment listings
        flats = [
            Flat(
                id="wien-1",
                title="Neubauwohnung in zentraler Lage - Vormerkung möglich!",
                url=HttpUrl("https://example.com/wien-1"),
                location="1010 Wien",
                description="Moderne 3-Zimmer-Wohnung im Erstbezug.",
                source="test",
            ),
            Flat(
                id="wien-2",
                title="2-Zimmer Wohnung zu vermieten",
                url=HttpUrl("https://example.com/wien-2"),
                location="1020 Wien",
                description="Schöne Altbauwohnung, befristet für 2 Jahre.",
                source="test",
            ),
            Flat(
                id="wien-3",
                title="Geräumige Familienwohnung",
                url=HttpUrl("https://example.com/wien-3"),
                location="1030 Wien",
                description=(
                    "4-Zimmer in ruhiger Lage. Teil eines Neubauprojekts. "
                    "Vormerken jetzt möglich!"
                ),
                source="test",
            ),
        ]

        # Detect markers
        for flat in flats:
            detector.detect_and_update(flat)

        # Check results
        assert "vormerkung" in flats[0].markers
        assert "neubau" in flats[0].markers
        assert "befristet" not in flats[0].markers

        assert "vormerkung" not in flats[1].markers
        assert "befristet" in flats[1].markers

        assert "vormerkung" in flats[2].markers
        assert "neubau" in flats[2].markers
