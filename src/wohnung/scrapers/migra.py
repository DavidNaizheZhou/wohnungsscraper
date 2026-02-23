"""Migra Immobilien scraper.

Scrapes projects from https://www.migra.at/neubauprojekte/
"""

import re
from datetime import datetime

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class MigraScraper(BaseScraper):
    """Scraper for Migra housing projects."""

    @property
    def name(self) -> str:
        """Scraper identifier."""
        return "migra"

    @property
    def base_url(self) -> str:
        """Base URL for scraping."""
        return "https://www.migra.at/neubauprojekte/"

    def scrape(self) -> list[Flat]:
        """Scrape flats from Migra projects page.

        Returns:
            List of Flat objects
        """
        flats = []

        try:
            # Fetch residential projects via lazy list API
            api_url = "https://www.migra.at/neubauprojekte/lazylist/load/ResidentialProjects"
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()

            data = response.json()
            projects = data.get("list", [])

            # Parse each project
            for project in projects:
                flat = self._parse_project(project)
                if flat:
                    flats.append(flat)

        except Exception as e:
            print(f"Error scraping Migra: {e}")

        return flats

    def _parse_project(self, project: dict[str, str]) -> Flat | None:  # noqa: C901, PLR0912
        """Parse a project dictionary into a Flat object.

        Args:
            project: Project data dictionary with 'id' and 'view' (HTML)

        Returns:
            Flat object or None if parsing fails
        """
        try:
            _project_id = project.get("id")
            html = project.get("view", "")

            if not html:
                return None

            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title_elem = soup.find("h2", class_="project__title")
            if not title_elem:
                return None

            link = title_elem.find("a")
            if not link:
                return None

            title = link.get_text(strip=True).strip('"')  # type: ignore[union-attr]
            url_path = link.get("href", "")  # type: ignore[union-attr]
            if not url_path:
                return None

            # Build full URL
            url = f"https://www.migra.at{url_path}"

            # Extract subtitle (type/description)
            subtitle_elem = soup.find("h3", attrs={"role": "doc-subtitle"})
            subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else None

            # Extract location
            location_elem = soup.find("p")
            location = None
            address = None
            if location_elem:
                text = location_elem.get_text(separator=" ", strip=True)
                # Format: "1220 Wien • Attemsgasse 34"
                parts = text.split("•")
                if parts:
                    location = parts[0].strip()
                if len(parts) > 1:
                    address = parts[1].strip()

            # Extract image URL
            image_url = None
            img = soup.find("img", class_="project__img")
            if img:
                # Try data-srcset first (for lazyload), then src
                srcset = img.get("data-srcset", "")  # type: ignore[union-attr]
                if srcset:
                    # Extract first URL from srcset
                    match = re.search(r"(/assets/[^\s]+)", str(srcset))  # type: ignore[arg-type]
                    if match:
                        image_url = f"https://www.migra.at{match.group(1)}"
                else:
                    src = img.get("src", "")  # type: ignore[union-attr]
                    if src and str(src).startswith("/"):  # type: ignore[union-attr]
                        image_url = f"https://www.migra.at{src}"
                    elif src and str(src).startswith("http"):  # type: ignore[union-attr]
                        image_url = str(src)  # type: ignore[assignment]

            # Build description
            description_parts = []
            if subtitle:
                description_parts.append(subtitle)
            if address:
                description_parts.append(address)
            description = ", ".join(description_parts) if description_parts else None

            # Detect markers
            markers = self._detect_markers(subtitle or "")

            # Create flat
            flat = Flat(
                id=self.generate_id(url),
                url=url,  # type: ignore[arg-type]
                title=title,
                location=location or title,
                description=description,
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

        except Exception as e:
            print(f"Error parsing project: {e}")
            return None

    def _detect_markers(self, subtitle: str) -> list[str]:
        """Detect markers based on project subtitle.

        Args:
            subtitle: Project subtitle/type text

        Returns:
            List of marker strings
        """
        markers = []

        subtitle_lower = subtitle.lower()

        # Check for rental projects
        if "miete" in subtitle_lower:
            markers.append("rental")

        # Check for ownership projects
        if "eigentum" in subtitle_lower or "kauf" in subtitle_lower:
            markers.append("for_sale")

        # Check for subsidized housing
        if "gefördert" in subtitle_lower or "förderung" in subtitle_lower:
            markers.append("subsidized")

        # Check for smart apartments
        if "smart" in subtitle_lower:
            markers.append("smart")

        return markers
