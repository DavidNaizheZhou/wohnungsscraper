"""Scraper for at home Immobilien (athome.at)."""

import re
from typing import Any

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class AthomeScraper(BaseScraper):
    """Scraper for at home Immobilien projects."""

    @property
    def name(self) -> str:
        """Return the scraper name."""
        return "athome"

    @property
    def base_url(self) -> str:
        """Return the base URL for this scraper."""
        return "https://athome.at"

    def get_site_name(self) -> str:
        """Return the site name."""
        return "athome"

    def scrape(self) -> list[Flat]:
        """Scrape all projects from at home."""
        url = f"{self.base_url}/projekte/"

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        flats = []
        # Find all project grid items
        project_items = soup.find_all("a", class_="project-grid-item")

        for item in project_items:
            flat = self._parse_project(item)
            if flat:
                flats.append(flat)

        return flats

    def _parse_project(self, item: Any) -> Flat | None:
        """Parse a single project item into a Flat object."""
        # Get project URL
        project_url = item.get("href", "")
        if not project_url or "coming-soon" in project_url:
            return None

        # Generate ID from URL
        flat_id = project_url.split("/projekt/")[-1].strip("/")
        if not flat_id:
            return None

        # Get title
        title_elem = item.find("div", class_="project-grid-item-title")
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Get address/location
        address_elem = item.find("div", class_="project-grid-item-address")
        location = address_elem.get_text(strip=True) if address_elem else ""

        # Get type (Eigentum, Mietkauf, etc.)
        subline_elem = item.find("div", class_="project-grid-item-subline")
        property_type = subline_elem.get_text(strip=True) if subline_elem else ""

        # Get image URL from style attribute
        image_elem = item.find("div", class_="project-grid-item-image")
        image_url = None
        if image_elem and image_elem.get("style"):
            style = image_elem.get("style", "")
            match = re.search(r"url\(([^)]+)\)", style)
            if match:
                image_url = match.group(1).strip()

        # Determine markers based on type
        markers = []

        # Check property type
        property_type_lower = property_type.lower()
        if "eigentum" in property_type_lower:
            markers.append("for_sale")
        if "mietkauf" in property_type_lower or "miete" in property_type_lower:
            markers.append("rental")
            markers.append("rent_to_own")

        # Check if active or completed project by checking grid settings
        # (This would require checking parent container, but we'll mark all as active for now)
        markers.append("neubau")

        # Create flat object
        flat = Flat(
            id=flat_id,
            title=title,
            url=project_url,
            location=location,
            price=None,
            size=None,
            rooms=None,
            description=None,
            image_url=image_url if image_url else None,  # type: ignore[arg-type]
            source=self.name,
            markers=markers,
        )

        return flat
