"""Marker detection for apartment listings."""

import re
from typing import ClassVar

from wohnung.models import Flat
from wohnung.site_config import MarkerConfig


class MarkerDetector:
    """Detects markers in apartment listings."""

    PRIORITY_ORDER: ClassVar[dict[str, int]] = {"high": 0, "medium": 1, "low": 2}

    def __init__(self, markers: list[MarkerConfig]) -> None:
        """Initialize the detector with a list of markers.

        Args:
            markers: List of marker configurations
        """
        self.markers = sorted(markers, key=lambda m: self.PRIORITY_ORDER[m.priority])

    def detect_markers(self, apartment: Flat) -> list[str]:
        """Detect which markers apply to an apartment.

        Searches in configured fields (title/description) for marker patterns.
        Returns markers in priority order (high -> medium -> low).

        Args:
            apartment: The apartment to check

        Returns:
            List of detected marker names
        """
        detected = []

        for marker in self.markers:
            if self._matches_marker(apartment, marker):
                detected.append(marker.name)

        return detected

    def _matches_marker(self, apartment: Flat, marker: MarkerConfig) -> bool:
        """Check if apartment matches any of the marker's patterns.

        Args:
            apartment: The apartment to check
            marker: Marker configuration

        Returns:
            True if any pattern matches in any configured field
        """
        # Collect text from configured fields
        text_parts = []
        if "title" in marker.search_in and apartment.title:
            text_parts.append(apartment.title)
        if "description" in marker.search_in and apartment.description:
            text_parts.append(apartment.description)

        # Combine all text (case-insensitive)
        text_lower = " ".join(text_parts).lower()

        for pattern in marker.patterns:
            pattern_lower = pattern.lower()

            # Check if pattern looks like regex (contains regex special chars)
            is_regex = any(char in pattern for char in r"^$.*+?[]{}()\|")

            if is_regex:
                # Regex matching
                try:
                    if re.search(pattern_lower, text_lower, re.IGNORECASE):
                        return True
                except re.error:
                    # Invalid regex, try exact match as fallback
                    if pattern_lower in text_lower:
                        return True
            # Exact substring matching
            elif pattern_lower in text_lower:
                return True

        return False

    def detect_and_update(self, apartment: Flat) -> Flat:
        """Detect markers and update the apartment's markers field.

        Args:
            apartment: The apartment to update

        Returns:
            The apartment with updated markers field
        """
        apartment.markers = self.detect_markers(apartment)
        return apartment

    def get_marker_label(self, marker_name: str) -> str | None:
        """Get the human-readable label for a marker name.

        Args:
            marker_name: Internal marker identifier

        Returns:
            Human-readable label, or None if marker not found
        """
        for marker in self.markers:
            if marker.name == marker_name:
                return marker.label
        return None

    def get_marker_priority(self, marker_name: str) -> str | None:
        """Get the priority level for a marker name.

        Args:
            marker_name: Internal marker identifier

        Returns:
            Priority level ('low', 'medium', 'high'), or None if marker not found
        """
        for marker in self.markers:
            if marker.name == marker_name:
                return marker.priority
        return None
