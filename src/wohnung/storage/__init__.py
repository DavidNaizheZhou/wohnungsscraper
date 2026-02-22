"""JSON-based storage for tracking seen flats."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from wohnung.config import settings
from wohnung.models import Flat


class JSONStorage:
    """Simple JSON file-based storage for flats."""

    def __init__(self, storage_file: Path | None = None) -> None:
        """
        Initialize storage.

        Args:
            storage_file: Path to JSON storage file. Defaults to data/flats.json
        """
        self.storage_file = storage_file or settings.data_dir / "flats.json"
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Create storage file if it doesn't exist."""
        if not self.storage_file.exists():
            self._write_data({"flats": {}, "last_updated": datetime.now().isoformat()})

    def _read_data(self) -> dict[str, Any]:
        """Read data from storage file."""
        with open(self.storage_file, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data

    def _write_data(self, data: dict[str, Any]) -> None:
        """Write data to storage file."""
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def flat_exists(self, flat_id: str) -> bool:
        """
        Check if a flat has been seen before.

        Args:
            flat_id: Unique flat identifier

        Returns:
            True if flat exists in storage
        """
        data = self._read_data()
        return flat_id in data["flats"]

    def save_flat(self, flat: Flat) -> None:
        """
        Save a flat to storage.

        Args:
            flat: Flat object to save
        """
        data = self._read_data()
        data["flats"][flat.id] = flat.model_dump(mode="json")
        data["last_updated"] = datetime.now().isoformat()
        self._write_data(data)

    def save_flats(self, flats: list[Flat]) -> int:
        """
        Save multiple flats to storage (only new ones).

        Args:
            flats: List of flats to save

        Returns:
            Number of new flats saved
        """
        data = self._read_data()
        saved = 0

        for flat in flats:
            if flat.id not in data["flats"]:
                data["flats"][flat.id] = flat.model_dump(mode="json")
                saved += 1

        if saved > 0:
            data["last_updated"] = datetime.now().isoformat()
            self._write_data(data)

        return saved

    def filter_new_flats(self, flats: list[Flat]) -> list[Flat]:
        """
        Filter out flats that already exist in storage.

        Args:
            flats: List of all flats

        Returns:
            List of only new flats
        """
        return [flat for flat in flats if not self.flat_exists(flat.id)]

    def get_all_flats(self) -> list[Flat]:
        """
        Get all flats from storage.

        Returns:
            List of all stored flats
        """
        data = self._read_data()
        return [Flat(**flat_data) for flat_data in data["flats"].values()]

    def get_stats(self) -> dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with stats about stored flats
        """
        flats = self.get_all_flats()
        sources: dict[str, int] = {}

        for flat in flats:
            sources[flat.source] = sources.get(flat.source, 0) + 1

        return {
            "total_flats": len(flats),
            "by_source": sources,
            "last_updated": self._read_data().get("last_updated"),
        }


__all__ = ["JSONStorage"]
