"""Wohnberatung Wien scraper.

Scrapes projects from https://wohnungssuche.wohnberatung-wien.at/?page=planungsprojekte-liste
"""

import re
from datetime import datetime
from typing import Any

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class WohnberatungWienScraper(BaseScraper):
    """Scraper for Wohnberatung Wien housing projects."""

    @property
    def name(self) -> str:
        """Scraper identifier."""
        return "wohnberatung-wien"

    @property
    def base_url(self) -> str:
        """Base URL for scraping."""
        return "https://wohnungssuche.wohnberatung-wien.at/?page=planungsprojekte-liste"

    def scrape(self) -> list[Flat]:
        """Scrape flats from Wohnberatung Wien projects page.

        Returns:
            List of Flat objects
        """
        flats = []

        try:
            # Fetch first page to determine total pages
            soup = self.fetch_html(self.base_url)
            max_page = self._extract_max_page(soup)

            # Scrape all pages
            for page_num in range(1, max_page + 1):
                page_url = f"{self.base_url}&p={page_num}"
                page_soup = self.fetch_html(page_url)
                page_flats = self._scrape_page(page_soup)
                flats.extend(page_flats)

        except Exception as e:
            print(f"Error scraping Wohnberatung Wien: {e}")

        return flats

    def _extract_max_page(self, soup: Any) -> int:
        """Extract the maximum page number from pagination.

        Args:
            soup: BeautifulSoup object

        Returns:
            Maximum page number (default: 1)
        """
        try:
            # Find pagination links
            pagination = soup.find("ul", class_="pagination")
            if not pagination:
                return 1

            # Extract all page numbers from links
            page_numbers = []
            for link in pagination.find_all("a"):
                href = link.get("href", "")
                match = re.search(r"p=(\d+)", href)
                if match:
                    page_numbers.append(int(match.group(1)))

            return max(page_numbers) if page_numbers else 1

        except Exception:
            return 1

    def _scrape_page(self, soup: Any) -> list[Flat]:
        """Scrape flats from a single page.

        Args:
            soup: BeautifulSoup object for the page

        Returns:
            List of Flat objects from this page
        """
        flats = []

        try:
            # Find all project listings
            projects = soup.find_all("div", class_="media-wohnung")

            for project in projects:
                flat = self._parse_project(project)
                if flat:
                    flats.append(flat)

        except Exception as e:
            print(f"Error parsing page: {e}")

        return flats

    def _parse_project(self, project: Any) -> Flat | None:  # noqa: C901
        """Parse a project element into a Flat object.

        Args:
            project: BeautifulSoup element for project

        Returns:
            Flat object or None if parsing fails
        """
        try:
            # Extract title and URL
            heading = project.find("h4", class_="media-heading")
            if not heading:
                return None

            link = heading.find("a")
            if not link:
                return None

            title = link.get_text(strip=True)
            url_path = link.get("href", "")
            if not url_path:
                return None

            # Build full URL
            url = f"https://wohnungssuche.wohnberatung-wien.at{url_path}"

            # Extract metadata
            body = project.find("div", class_="media-body")
            if not body:
                return None

            text = body.get_text(separator=" ", strip=True)

            # Extract completion date (Bezugsfertig: YYYY)
            completion_match = re.search(r"Bezugsfertig:\s*(\d{4})", text)
            completion_year = completion_match.group(1) if completion_match else None

            # Extract type (Miete, Eigentum, etc.)
            type_match = re.search(r"(Miete|Eigentum|Vorsorgewohnung)", text)
            housing_type = type_match.group(1) if type_match else None

            # Build description
            description_parts = []
            if completion_year:
                description_parts.append(f"Bezugsfertig: {completion_year}")
            if housing_type:
                description_parts.append(housing_type)
            description = ", ".join(description_parts) if description_parts else None

            # Extract location (first part of title before comma)
            location = title.split(",")[0].strip() if "," in title else title

            # Extract image URL
            image_url = None
            media_left = project.find("div", class_="media-left")
            if media_left:
                img = media_left.find("img")
                if img:
                    image_src = img.get("src", "")
                    if image_src and not image_src.startswith("http"):
                        image_url = f"https://wohnungssuche.wohnberatung-wien.at{image_src}"
                    else:
                        image_url = image_src

            # Detect markers
            markers = self._detect_markers(text, completion_year)

            # Create flat
            flat = Flat(
                id=self.generate_id(url),
                url=url,  # type: ignore[arg-type]
                title=title,
                location=location,
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

    def _detect_markers(self, _text: str, completion_year: str | None) -> list[str]:
        """Detect markers based on project information.

        Args:
            _text: Project text content (unused)
            completion_year: Completion year if available

        Returns:
            List of marker strings
        """
        markers = []

        # Always mark as in_planning since these are all planning projects
        markers.append("in_planning")

        # Check if completion is soon (within next 2 years)
        if completion_year:
            try:
                year = int(completion_year)
                current_year = datetime.now().year
                if year <= current_year + 2:
                    markers.append("available_soon")
            except ValueError:
                pass

        return markers
