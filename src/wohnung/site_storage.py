"""Git-optimized per-site storage system."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from wohnung.change_detector import ApartmentChange, ChangeDetector
from wohnung.models import Flat


class ApartmentMetadata(BaseModel):
    """Metadata for tracking apartment state over time."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    apartment_id: str = Field(..., description="Unique apartment identifier")
    status: Literal["active", "removed"] = Field(default="active", description="Current status")
    first_seen: datetime = Field(..., description="When apartment was first discovered")
    last_seen: datetime = Field(..., description="When apartment was last seen")
    last_updated: datetime = Field(..., description="When apartment data was last updated")
    data: dict[str, Any] = Field(..., description="Current apartment data")


class SiteStorageData(BaseModel):
    """Storage format for a single site's data."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    site: str = Field(..., description="Site identifier")
    last_scrape: datetime = Field(..., description="Last successful scrape time")
    apartments: dict[str, ApartmentMetadata] = Field(
        default_factory=dict, description="Apartments keyed by ID"
    )


class SiteStorage:
    """Per-site JSON storage with git-friendly formatting."""

    def __init__(self, data_dir: Path | str = "data"):
        """Initialize site storage.

        Args:
            data_dir: Directory for storing site JSON files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_site_file(self, site_name: str) -> Path:
        """Get the storage file path for a site.

        Args:
            site_name: Site identifier

        Returns:
            Path to site's JSON file
        """
        return self.data_dir / f"{site_name}.json"

    def _read_site_data(self, site_name: str) -> SiteStorageData | None:
        """Read data for a specific site.

        Args:
            site_name: Site identifier

        Returns:
            Site data or None if file doesn't exist
        """
        site_file = self._get_site_file(site_name)
        if not site_file.exists():
            return None

        with open(site_file, encoding="utf-8") as f:
            data = json.load(f)
            # Convert string dates back to datetime
            for apt_id in data.get("apartments", {}):
                apt = data["apartments"][apt_id]
                apt["first_seen"] = datetime.fromisoformat(apt["first_seen"])
                apt["last_seen"] = datetime.fromisoformat(apt["last_seen"])
                apt["last_updated"] = datetime.fromisoformat(apt["last_updated"])
            data["last_scrape"] = datetime.fromisoformat(data["last_scrape"])
            return SiteStorageData(**data)

    def _write_site_data(self, site_data: SiteStorageData) -> None:
        """Write data for a specific site in git-friendly format.

        Args:
            site_data: Site data to write
        """
        site_file = self._get_site_file(site_data.site)

        # Convert to dict with sorted keys for stable diffs
        data_dict: dict[str, Any] = {
            "site": site_data.site,
            "last_scrape": site_data.last_scrape.isoformat(),
            "apartments": {},
        }

        # Sort apartments by ID for stable ordering
        for apt_id in sorted(site_data.apartments.keys()):
            apt = site_data.apartments[apt_id]

            # Serialize apartment data, converting datetimes
            serialized_data = self._serialize_data(apt.data)

            data_dict["apartments"][apt_id] = {
                "apartment_id": apt.apartment_id,
                "status": apt.status,
                "first_seen": apt.first_seen.isoformat(),
                "last_seen": apt.last_seen.isoformat(),
                "last_updated": apt.last_updated.isoformat(),
                "data": serialized_data,
            }

        # Write with stable formatting
        with open(site_file, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")  # Trailing newline for git

    def _serialize_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively serialize data, converting datetimes to ISO format.

        Args:
            data: Data dictionary to serialize

        Returns:
            Serialized data with datetimes as strings
        """
        result: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = self._serialize_data(value)
            elif isinstance(value, list):
                result[key] = [
                    item.isoformat()
                    if isinstance(item, datetime)
                    else self._serialize_data(item)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def get_apartments(self, site_name: str) -> dict[str, ApartmentMetadata]:
        """Get all apartments for a site.

        Args:
            site_name: Site identifier

        Returns:
            Dictionary of apartments by ID
        """
        site_data = self._read_site_data(site_name)
        if site_data is None:
            return {}
        return site_data.apartments

    def get_active_apartments(self, site_name: str) -> dict[str, ApartmentMetadata]:
        """Get all active (not removed) apartments for a site.

        Args:
            site_name: Site identifier

        Returns:
            Dictionary of active apartments by ID
        """
        apartments = self.get_apartments(site_name)
        return {apt_id: apt for apt_id, apt in apartments.items() if apt.status == "active"}

    def get_apartments_with_markers(
        self, site_name: str, marker_names: list[str], active_only: bool = True
    ) -> dict[str, ApartmentMetadata]:
        """Get apartments that have any of the specified markers.

        Args:
            site_name: Site identifier
            marker_names: List of marker names to filter by
            active_only: Only return active apartments (default True)

        Returns:
            Dictionary of apartments by ID that have any of the markers
        """
        apartments = (
            self.get_active_apartments(site_name) if active_only else self.get_apartments(site_name)
        )

        filtered = {}
        for apt_id, apt in apartments.items():
            # Check if apartment has markers field in data
            apt_markers = apt.data.get("markers", [])
            if any(marker in apt_markers for marker in marker_names):
                filtered[apt_id] = apt

        return filtered

    def apartment_exists(self, site_name: str, apartment_id: str) -> bool:
        """Check if an apartment exists in storage.

        Args:
            site_name: Site identifier
            apartment_id: Apartment ID

        Returns:
            True if apartment exists
        """
        apartments = self.get_apartments(site_name)
        return apartment_id in apartments

    def save_apartments(
        self, site_name: str, flats: list[Flat], mark_missing_as_removed: bool = True
    ) -> tuple[list[str], list[str], list[str]]:
        """Save apartments from a scrape, detecting new/updated/removed.

        Args:
            site_name: Site identifier
            flats: List of flats from current scrape
            mark_missing_as_removed: Mark apartments not in current scrape as removed

        Returns:
            Tuple of (new_ids, updated_ids, removed_ids)
        """
        now = datetime.now()
        site_data = self._read_site_data(site_name)

        if site_data is None:
            # First scrape for this site
            site_data = SiteStorageData(site=site_name, last_scrape=now, apartments={})

        current_ids = {flat.id for flat in flats}
        existing_ids = set(site_data.apartments.keys())

        new_ids: list[str] = []
        updated_ids: list[str] = []
        removed_ids: list[str] = []

        # Process current flats
        for flat in flats:
            flat_dict = flat.model_dump(mode="json")

            if flat.id not in existing_ids:
                # New apartment
                site_data.apartments[flat.id] = ApartmentMetadata(
                    apartment_id=flat.id,
                    status="active",
                    first_seen=now,
                    last_seen=now,
                    last_updated=now,
                    data=flat_dict,
                )
                new_ids.append(flat.id)
            else:
                # Existing apartment
                existing = site_data.apartments[flat.id]
                was_removed = existing.status == "removed"
                existing.last_seen = now
                existing.status = "active"  # Mark as active again

                # Check if data changed or if it was reactivated
                if existing.data != flat_dict or was_removed:
                    existing.data = flat_dict
                    existing.last_updated = now
                    updated_ids.append(flat.id)

        # Mark missing apartments as removed
        if mark_missing_as_removed:
            for apt_id in existing_ids - current_ids:
                if site_data.apartments[apt_id].status == "active":
                    site_data.apartments[apt_id].status = "removed"
                    removed_ids.append(apt_id)

        # Update last scrape time
        site_data.last_scrape = now

        # Write to file
        self._write_site_data(site_data)

        return new_ids, updated_ids, removed_ids

    def get_site_stats(self, site_name: str) -> dict[str, Any]:
        """Get statistics for a site.

        Args:
            site_name: Site identifier

        Returns:
            Dictionary with stats
        """
        apartments = self.get_apartments(site_name)
        active = [apt for apt in apartments.values() if apt.status == "active"]
        removed = [apt for apt in apartments.values() if apt.status == "removed"]

        return {
            "total": len(apartments),
            "active": len(active),
            "removed": len(removed),
            "newest": (max(apt.first_seen for apt in active) if active else None),
            "oldest": (min(apt.first_seen for apt in active) if active else None),
        }

    def list_sites(self) -> list[str]:
        """List all sites with stored data.

        Returns:
            List of site names
        """
        return [f.stem for f in self.data_dir.glob("*.json")]

    def migrate_from_legacy(self, legacy_file: Path, default_site: str = "legacy") -> None:
        """Migrate from legacy single-file storage to per-site storage.

        Args:
            legacy_file: Path to old flats.json
            default_site: Site name to use for legacy flats
        """
        if not legacy_file.exists():
            return

        with open(legacy_file, encoding="utf-8") as f:
            legacy_data = json.load(f)

        now = datetime.now()
        flats_by_site: dict[str, list[Flat]] = {}

        # Group flats by source
        for flat_id, flat_data in legacy_data.get("flats", {}).items():
            # Reconstruct Flat object with defaults for missing fields
            flat_data["id"] = flat_id
            if "found_at" in flat_data:
                flat_data["found_at"] = datetime.fromisoformat(flat_data["found_at"])
            else:
                flat_data["found_at"] = now

            # Provide defaults for required fields that might be missing
            flat_data.setdefault("location", "Unknown")

            flat = Flat(**flat_data)
            site = flat.source or default_site

            if site not in flats_by_site:
                flats_by_site[site] = []
            flats_by_site[site].append(flat)

        # Save to per-site files
        for site, flats in flats_by_site.items():
            self.save_apartments(site, flats, mark_missing_as_removed=False)

    def save_apartments_with_changes(
        self,
        site_name: str,
        flats: list[Flat],
        mark_missing_as_removed: bool = True,
        track_history: bool = False,
    ) -> list[ApartmentChange]:
        """Save apartments and return detailed change information.

        Args:
            site_name: Site identifier
            flats: List of flats from current scrape
            mark_missing_as_removed: Mark apartments not in current scrape as removed
            track_history: If True, saves change history to separate file

        Returns:
            List of detected changes with field-level details
        """
        # Get current apartments
        apartments = self.get_apartments(site_name)
        old_apartments = {apt_id: apt.data for apt_id, apt in apartments.items()}

        # Use ChangeDetector to find detailed changes
        detector = ChangeDetector()
        changes = detector.detect_changes(old_apartments, flats)

        # Save apartments using standard method
        self.save_apartments(site_name, flats, mark_missing_as_removed)

        # Optionally save change history
        if track_history and changes:
            self._save_change_history(site_name, changes)

        return changes

    def _save_change_history(self, site_name: str, changes: list[ApartmentChange]) -> None:
        """Save change history to a separate file.

        Args:
            site_name: Site identifier
            changes: List of changes to save
        """
        history_file = self.data_dir / f"{site_name}_history.jsonl"

        # Append changes to JSONL file (one JSON per line)
        with open(history_file, "a", encoding="utf-8") as f:
            for change in changes:
                # Serialize change to JSON
                change_dict = {
                    "change_type": change.change_type,
                    "apartment_id": change.apartment_id,
                    "timestamp": change.timestamp.isoformat(),
                    "changes": change.changes,
                    "apartment_data": change.apartment_data,
                }
                f.write(json.dumps(change_dict, ensure_ascii=False) + "\n")

    def get_change_history(self, site_name: str, limit: int | None = None) -> list[ApartmentChange]:
        """Get change history for a site.

        Args:
            site_name: Site identifier
            limit: Optional limit on number of changes to return (most recent)

        Returns:
            List of historical changes
        """
        history_file = self.data_dir / f"{site_name}_history.jsonl"

        if not history_file.exists():
            return []

        changes: list[ApartmentChange] = []

        with open(history_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                data = json.loads(line)
                # Convert timestamp back to datetime
                data["timestamp"] = datetime.fromisoformat(data["timestamp"])

                changes.append(ApartmentChange(**data))

        # Return most recent first
        changes.reverse()

        if limit:
            changes = changes[:limit]

        return changes
