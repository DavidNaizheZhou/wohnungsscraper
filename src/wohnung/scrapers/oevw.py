"""OEVW (Österreichische Volkswohnungsbauvereinigung) scraper.

Scrapes projects from https://www.oevw.at/projekte
"""

import json
import re
from datetime import datetime
from typing import Any

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class OEVWScraper(BaseScraper):
    """Scraper for OEVW housing projects."""

    @property
    def name(self) -> str:
        """Scraper identifier."""
        return "oevw"

    @property
    def base_url(self) -> str:
        """Base URL for scraping."""
        return "https://www.oevw.at/projekte"

    def scrape(self) -> list[Flat]:
        """Scrape flats from OEVW projects page.

        Returns:
            List of Flat objects
        """
        flats = []

        try:
            soup = self.fetch_html(self.base_url)
            html = str(soup)

            # Extract projects JSON from JavaScript variable
            projects = self._extract_projects_json(html)

            # Convert projects to flats
            for project in projects:
                flat = self._parse_project(project)
                if flat:
                    flats.append(flat)
        except Exception as e:
            print(f"Error scraping OEVW: {e}")

        return flats

    def _extract_projects_json(self, html: str) -> list[dict[str, Any]]:
        """Extract projects array from JavaScript variable in HTML.

        Args:
            html: HTML content

        Returns:
            List of project dictionaries
        """
        # Find the JavaScript variable declaration
        # Pattern: var projects = [...];
        pattern = r"var\s+projects\s*=\s*(\[.*?\]);"
        match = re.search(pattern, html, re.DOTALL)

        if not match:
            return []

        json_str = match.group(1)

        try:
            projects = json.loads(json_str)
            return projects if isinstance(projects, list) else []
        except json.JSONDecodeError:
            return []

    def _parse_project(self, project: dict[str, Any]) -> Flat | None:
        """Parse a project dictionary into a Flat object.

        Args:
            project: Project data dictionary

        Returns:
            Flat object or None if parsing fails
        """
        try:
            # Extract basic info
            title = project.get("heading", "")
            if not title:
                return None

            # Extract URL
            url_path = project.get("url", "")
            if not url_path:
                return None

            # Build full URL
            url = f"https://www.oevw.at{url_path}"

            # Extract location
            location = project.get("location", "Unknown")

            # Extract legal form (rent/ownership)
            legalform = project.get("legalform") or ""

            # Extract image URL from HTML string
            image_html = project.get("image", "")
            image_url = self._extract_image_url(image_html)
            if image_url and not image_url.startswith("http"):
                image_url = f"https://www.oevw.at{image_url}"

            # Detect markers based on project status
            markers = self._detect_markers(project)

            # Create flat
            flat = Flat(
                id=self.generate_id(url),
                url=url,  # type: ignore[arg-type]
                title=title,
                location=location,
                description=legalform if legalform else None,
                image_url=image_url,  # type: ignore[arg-type]
                markers=markers,
                source=self.name,
                found_at=datetime.now(),
                # Price, size, rooms not available in listing
                price=None,
                size=None,
                rooms=None,
            )

            return flat

        except Exception:
            return None

    def _extract_image_url(self, image_html: str) -> str | None:
        """Extract image URL from HTML img tag.

        Args:
            image_html: HTML string containing img tag

        Returns:
            Image URL or None
        """
        # Pattern: <img src="/assets/thumb/..." ...>
        pattern = r'<img\s+src="([^"]+)"'
        match = re.search(pattern, image_html)

        if match:
            return match.group(1)

        return None

    def _detect_markers(self, project: dict[str, Any]) -> list[str]:
        """Detect markers for a project based on status.

        Args:
            project: Project data dictionary

        Returns:
            List of marker names
        """
        markers = []

        # Check project status
        status = project.get("projectstatus", "")

        if status == "planning":
            markers.append("in_planning")
        elif status == "selling":
            markers.append("available_soon")

        return markers
