"""Change detection system for apartment tracking."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from wohnung.models import Flat


class ApartmentChange(BaseModel):
    """Represents a detected change in an apartment."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    change_type: Literal["new", "updated", "removed"] = Field(..., description="Type of change")
    apartment_id: str = Field(..., description="Apartment identifier")
    timestamp: datetime = Field(..., description="When change was detected")
    changes: dict[str, tuple[Any, Any]] = Field(
        default_factory=dict,
        description="Field changes: field -> (old_value, new_value)",
    )
    apartment_data: dict[str, Any] = Field(..., description="Current apartment data snapshot")

    @property
    def apartment(self) -> Flat:
        """Convert apartment_data to Flat object."""
        return Flat(**self.apartment_data)

    @property
    def changed_fields(self) -> list[str]:
        """List of field names that changed."""
        return list(self.changes.keys())


class ChangeDetectorConfig(BaseModel):
    """Configuration for change detection."""

    monitored_fields: list[str] = Field(
        default=[
            "price",
            "title",
            "size",
            "rooms",
            "location",
            "description",
        ],
        description="Fields to monitor for changes",
    )
    ignore_fields: list[str] = Field(
        default=["found_at", "last_updated"],
        description="Fields to ignore when detecting changes",
    )


class ChangeDetector:
    """Detects changes between apartment states."""

    def __init__(self, config: ChangeDetectorConfig | None = None):
        """Initialize change detector.

        Args:
            config: Optional configuration for change detection
        """
        self.config = config or ChangeDetectorConfig()

    def detect_changes(
        self,
        old_apartments: dict[str, dict[str, Any]],
        new_apartments: list[Flat],
    ) -> list[ApartmentChange]:
        """Detect changes between old and new apartment states.

        Args:
            old_apartments: Previously stored apartments {id: apartment_data}
            new_apartments: Newly scraped apartments

        Returns:
            List of detected changes
        """
        changes: list[ApartmentChange] = []
        now = datetime.now()

        # Convert new apartments to dict by ID
        new_by_id = {flat.id: flat for flat in new_apartments}
        old_ids = set(old_apartments.keys())
        new_ids = set(new_by_id.keys())

        # Detect new apartments
        for apt_id in new_ids - old_ids:
            flat = new_by_id[apt_id]
            changes.append(
                ApartmentChange(
                    change_type="new",
                    apartment_id=apt_id,
                    timestamp=now,
                    changes={},
                    apartment_data=flat.model_dump(mode="json"),
                )
            )

        # Detect updated apartments
        for apt_id in old_ids & new_ids:
            old_data = old_apartments[apt_id]
            new_flat = new_by_id[apt_id]
            new_data = new_flat.model_dump(mode="json")

            field_changes = self._compare_fields(old_data, new_data)

            if field_changes:
                changes.append(
                    ApartmentChange(
                        change_type="updated",
                        apartment_id=apt_id,
                        timestamp=now,
                        changes=field_changes,
                        apartment_data=new_data,
                    )
                )

        # Detect removed apartments
        for apt_id in old_ids - new_ids:
            old_data = old_apartments[apt_id]
            changes.append(
                ApartmentChange(
                    change_type="removed",
                    apartment_id=apt_id,
                    timestamp=now,
                    changes={},
                    apartment_data=old_data,
                )
            )

        return changes

    def _compare_fields(
        self, old_data: dict[str, Any], new_data: dict[str, Any]
    ) -> dict[str, tuple[Any, Any]]:
        """Compare fields between old and new data.

        Args:
            old_data: Old apartment data
            new_data: New apartment data

        Returns:
            Dictionary of changed fields with (old, new) values
        """
        changes: dict[str, tuple[Any, Any]] = {}

        # Check monitored fields
        for field in self.config.monitored_fields:
            if field in self.config.ignore_fields:
                continue

            old_value = old_data.get(field)
            new_value = new_data.get(field)

            # Only report if values are different
            if old_value != new_value:
                changes[field] = (old_value, new_value)

        return changes

    def get_significant_changes(self, changes: list[ApartmentChange]) -> list[ApartmentChange]:
        """Filter to only significant changes (new and updated).

        Args:
            changes: List of all changes

        Returns:
            List of significant changes (excludes removals)
        """
        return [c for c in changes if c.change_type in ("new", "updated")]

    def get_price_changes(self, changes: list[ApartmentChange]) -> list[ApartmentChange]:
        """Filter to only apartments with price changes.

        Args:
            changes: List of all changes

        Returns:
            List of changes with price modifications
        """
        return [c for c in changes if c.change_type == "updated" and "price" in c.changes]

    def format_change_summary(self, change: ApartmentChange) -> str:
        """Format a human-readable change summary.

        Args:
            change: Apartment change to format

        Returns:
            Formatted change summary
        """
        if change.change_type == "new":
            return f"NEW: {change.apartment_data.get('title', 'Unknown')}"

        if change.change_type == "removed":
            return f"REMOVED: {change.apartment_data.get('title', 'Unknown')}"

        # Updated - show what changed
        parts = [f"UPDATED: {change.apartment_data.get('title', 'Unknown')}"]

        for field, (old, new) in change.changes.items():
            if field == "price":
                parts.append(f"  Price: {old} → {new}")
            elif field == "title":
                parts.append("  Title changed")
            elif field == "size":
                parts.append(f"  Size: {old} → {new}")
            elif field == "rooms":
                parts.append(f"  Rooms: {old} → {new}")
            else:
                parts.append(f"  {field.title()}: {old} → {new}")

        return "\n".join(parts)
