"""Apartment search and filtering functionality."""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from wohnung.models import Flat
from wohnung.site_storage import SiteStorage


class ApartmentQuery(BaseModel):
    """Query model for filtering apartments."""

    sites: list[str] | None = Field(None, description="Filter by specific sites")
    price_min: float | None = Field(None, description="Minimum price")
    price_max: float | None = Field(None, description="Maximum price")
    size_min: float | None = Field(None, description="Minimum size in m²")
    size_max: float | None = Field(None, description="Maximum size in m²")
    rooms_min: float | None = Field(None, description="Minimum number of rooms")
    rooms_max: float | None = Field(None, description="Maximum number of rooms")
    markers: list[str] | None = Field(None, description="Filter by markers")
    location_contains: str | None = Field(None, description="Location substring match")
    new_since: datetime | None = Field(None, description="Only apartments found after this date")
    active_only: bool = Field(True, description="Only show active apartments")
    sort_by: Literal["price", "size", "rooms", "date"] | None = Field(
        None, description="Sort results by field"
    )
    sort_desc: bool = Field(False, description="Sort in descending order")
    limit: int | None = Field(None, description="Maximum number of results")


class ApartmentSearcher:
    """Search and filter apartments from storage."""

    def __init__(self, storage: SiteStorage):
        """Initialize searcher with storage.

        Args:
            storage: Site storage instance
        """
        self.storage = storage

    def search(self, query: ApartmentQuery) -> list[Flat]:
        """Search apartments matching query criteria.

        Args:
            query: Query with filter criteria

        Returns:
            List of matching apartments
        """
        results: list[Flat] = []

        # Determine which sites to search
        sites_to_search = query.sites if query.sites else self.storage.list_sites()

        for site in sites_to_search:
            apartments = (
                self.storage.get_active_apartments(site)
                if query.active_only
                else self.storage.get_apartments(site)
            )

            for apt_id, metadata in apartments.items():
                flat = Flat.model_validate(metadata.data)

                # Apply filters
                if not self._matches_filters(flat, metadata, query):
                    continue

                results.append(flat)

        # Sort results
        if query.sort_by:
            results = self._sort_results(results, query.sort_by, query.sort_desc)

        # Apply limit
        if query.limit and query.limit > 0:
            results = results[: query.limit]

        return results

    def _matches_filters(
        self, flat: Flat, metadata: "object", query: ApartmentQuery
    ) -> bool:
        """Check if apartment matches all filter criteria.

        Args:
            flat: Apartment data
            metadata: Apartment metadata
            query: Query filters

        Returns:
            True if apartment matches all filters
        """
        # Price filter
        if query.price_min is not None and (flat.price is None or flat.price < query.price_min):
            return False
        if query.price_max is not None and (flat.price is None or flat.price > query.price_max):
            return False

        # Size filter
        if query.size_min is not None and (flat.size is None or flat.size < query.size_min):
            return False
        if query.size_max is not None and (flat.size is None or flat.size > query.size_max):
            return False

        # Rooms filter
        if query.rooms_min is not None and (flat.rooms is None or flat.rooms < query.rooms_min):
            return False
        if query.rooms_max is not None and (flat.rooms is None or flat.rooms > query.rooms_max):
            return False

        # Location filter
        if query.location_contains and (
            not flat.location or query.location_contains.lower() not in flat.location.lower()
        ):
            return False

        # Markers filter
        if query.markers:
            flat_markers = set(flat.markers if flat.markers else [])
            required_markers = set(query.markers)
            if not flat_markers.intersection(required_markers):
                return False

        # Date filter
        if query.new_since and hasattr(metadata, "first_seen"):
            metadata_dict = metadata if isinstance(metadata, dict) else metadata.__dict__
            first_seen = metadata_dict.get("first_seen")
            if first_seen and first_seen < query.new_since:
                return False

        return True

    def _sort_results(
        self, results: list[Flat], sort_by: str, descending: bool = False
    ) -> list[Flat]:
        """Sort results by specified field.

        Args:
            results: List of apartments
            sort_by: Field to sort by
            descending: Sort in descending order

        Returns:
            Sorted list of apartments
        """
        if sort_by == "price":
            results.sort(key=lambda x: x.price if x.price else float("inf"), reverse=descending)
        elif sort_by == "size":
            results.sort(key=lambda x: x.size if x.size else 0, reverse=descending)
        elif sort_by == "rooms":
            results.sort(key=lambda x: x.rooms if x.rooms else 0, reverse=descending)
        elif sort_by == "date":
            results.sort(
                key=lambda x: x.found_at if x.found_at else datetime.min, reverse=descending
            )

        return results

    def export_json(self, apartments: list[Flat], output_path: Path) -> None:
        """Export apartments to JSON file.

        Args:
            apartments: List of apartments to export
            output_path: Output file path
        """
        data = [apt.model_dump(mode="json") for apt in apartments]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def export_csv(self, apartments: list[Flat], output_path: Path) -> None:
        """Export apartments to CSV file.

        Args:
            apartments: List of apartments to export
            output_path: Output file path
        """
        if not apartments:
            # Create empty CSV with headers
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "title", "price", "size", "rooms", "location", "url", "source"])
                writer.writeheader()
            return

        fieldnames = list(apartments[0].model_dump().keys())
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for apt in apartments:
                writer.writerow(apt.model_dump())


def parse_relative_time(time_str: str) -> datetime:
    """Parse relative time strings like '2 days ago', 'last week'.

    Args:
        time_str: Relative time string

    Returns:
        Datetime object

    Raises:
        ValueError: If time string cannot be parsed
    """
    time_str = time_str.lower().strip()
    now = datetime.now()

    # Handle "X days/hours/weeks ago"
    if "ago" in time_str:
        parts = time_str.replace("ago", "").strip().split()
        if len(parts) != 2:
            raise ValueError(f"Cannot parse time string: {time_str}")

        value_str, unit = parts
        try:
            value = int(value_str)
        except ValueError as e:
            raise ValueError(f"Invalid number in time string: {value_str}") from e

        if "day" in unit:
            return now - timedelta(days=value)
        elif "hour" in unit:
            return now - timedelta(hours=value)
        elif "week" in unit:
            return now - timedelta(weeks=value)
        elif "month" in unit:
            return now - timedelta(days=value * 30)
        else:
            raise ValueError(f"Unknown time unit: {unit}")

    # Handle "last X"
    if time_str.startswith("last "):
        unit = time_str.replace("last ", "")
        if "day" in unit:
            return now - timedelta(days=1)
        elif "week" in unit:
            return now - timedelta(weeks=1)
        elif "month" in unit:
            return now - timedelta(days=30)
        else:
            raise ValueError(f"Unknown time period: {unit}")

    # Handle "today" and "yesterday"
    if time_str == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_str == "yesterday":
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    raise ValueError(f"Cannot parse time string: {time_str}")
