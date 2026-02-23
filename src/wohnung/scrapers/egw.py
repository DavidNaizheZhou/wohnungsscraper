"""Scraper for EGW (Erste gemeinnützige Wohnungsgesellschaft)."""

import json
import re
from typing import Any

import requests  # type: ignore[import-untyped]

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class EgwScraper(BaseScraper):
    """Scraper for EGW projects."""

    @property
    def name(self) -> str:
        """Return the scraper name."""
        return "egw"

    @property
    def base_url(self) -> str:
        """Return the base URL for this scraper."""
        return "https://www.egw.at"

    def get_site_name(self) -> str:
        """Return the site name."""
        return "egw"

    def scrape(self) -> list[Flat]:
        """Scrape all projects from EGW."""
        url = "https://www.egw.at/projekte"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Extract projects JSON from embedded JavaScript
        match = re.search(r"var projects = (\[.*?\]);</script>", response.text, re.DOTALL)
        if not match:
            raise ValueError("Could not find projects data in page")

        projects_json = match.group(1)
        projects: list[dict[str, Any]] = json.loads(projects_json)

        flats = []
        for project in projects:
            flat = self._parse_project(project)
            if flat:
                flats.append(flat)

        return flats

    def _parse_project(self, project: dict[str, Any]) -> Flat | None:
        """Parse a single project into a Flat object."""
        # Extract project URL
        project_url = project.get("url", "")
        if not project_url:
            return None

        full_url = f"https://www.egw.at{project_url}"

        # Extract location (e.g., "2700 Wiener Neustadt" or "1030 Wien")
        location = project.get("location", "")

        # Extract title
        title = project.get("heading", "")

        # Generate ID from URL path
        flat_id = project_url.strip("/").replace("/", "-")

        # Extract status
        _status = project.get("realtylabel", "")

        # Determine markers
        markers = []
        project_status = project.get("projectstatus", "")
        if project_status == "planning":
            markers.append("in_planning")
        elif project_status == "selling":
            markers.append("in_vergabe")

        # Create flat object
        flat = Flat(
            id=flat_id,
            title=title,
            location=location,
            url=full_url,  # type: ignore[arg-type]
            price=None,
            size=None,
            rooms=None,
            description=None,
            image_url=None,
            source=self.name,
            markers=markers,
        )

        return flat
