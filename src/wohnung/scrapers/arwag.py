"""ARWAG Holding scraper.

Scrapes projects from https://www.arwag.at/projekte/
"""

import re
from datetime import datetime

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class ArwagScraper(BaseScraper):
    """Scraper for ARWAG housing projects."""

    @property
    def name(self) -> str:
        """Scraper identifier."""
        return "arwag"

    @property
    def base_url(self) -> str:
        """Base URL for scraping."""
        return "https://www.arwag.at/projekte/"

    def scrape(self) -> list[Flat]:
        """Scrape flats from ARWAG projects page.

        Returns:
            List of Flat objects
        """
        flats = []

        try:
            # Fetch residential projects via lazy list API
            api_url = "https://www.arwag.at/projekte/lazylist/load/ResidentialProjectGroups"
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
            print(f"Error scraping ARWAG: {e}")

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
            title_elem = soup.find("h2", class_="app-ObjectGridEntry-headline")
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)

            # Extract link
            link = soup.find("a", class_="app-ObjectGridEntry-Link")
            if not link:
                return None

            url_path = link.get("href", "")  # type: ignore[union-attr]
            if not url_path:
                return None

            # Build full URL
            url = f"https://www.arwag.at{url_path}"

            # Extract type (Miete/Eigentum)
            type_elem = link.find("em")  # type: ignore[union-attr]
            project_type = type_elem.get_text(strip=True) if type_elem else None  # type: ignore[union-attr]

            # Extract location/address
            address_elem = soup.find("p", class_="app-ObjectGridEntry-address")
            location = None
            address = None
            if address_elem:
                text = address_elem.get_text(separator=" ", strip=True)
                # Format: "1030 Wien - Markhofgasse 11"
                parts = text.split("-")
                if parts:
                    location = parts[0].strip()
                if len(parts) > 1:
                    address = parts[1].strip()

            # Extract image URL
            image_url = None
            img = soup.find("img", class_="app-ObjectGridEntry-ImageContainer-image")
            if img:
                # Try data-srcset first (for lazyload), then src
                srcset = img.get("data-srcset", "")  # type: ignore[union-attr]
                if srcset:
                    # Extract first URL from srcset
                    match = re.search(r"(/assets/[^\s]+)", str(srcset))  # type: ignore[arg-type]
                    if match:
                        image_url = f"https://www.arwag.at{match.group(1)}"
                else:
                    src = img.get("src", "")  # type: ignore[union-attr]
                    if src and str(src).startswith("/"):  # type: ignore[union-attr]
                        image_url = f"https://www.arwag.at{src}"
                    elif src and str(src).startswith("http"):  # type: ignore[union-attr]
                        image_url = str(src)  # type: ignore[assignment]

            # Build description
            description_parts = []
            if project_type:
                description_parts.append(project_type)
            if address:
                description_parts.append(address)
            description = ", ".join(description_parts) if description_parts else None

            # Detect markers
            markers = self._detect_markers(project_type or "")

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

    def _detect_markers(self, project_type: str) -> list[str]:
        """Detect markers based on project type.

        Args:
            project_type: Project type text

        Returns:
            List of marker strings
        """
        markers = []

        type_lower = project_type.lower()

        # Check for rental projects
        if "miete" in type_lower:
            markers.append("rental")

        # Check for ownership projects
        if "eigentum" in type_lower or "kauf" in type_lower:
            markers.append("for_sale")

        return markers
