"""Scraper for OESW (Österreichisches Siedlungswerk)."""

import re

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class OeswScraper(BaseScraper):
    """Scraper for OESW completed housing projects."""

    @property
    def name(self) -> str:
        """Return the scraper name."""
        return "oesw"

    @property
    def base_url(self) -> str:
        """Return the base URL."""
        return "https://www.oesw.at"

    @property
    def minimum_expected_results(self) -> int:
        """Expect at least 20 projects (lower threshold due to slow website)."""
        return 20

    def scrape(self) -> list[Flat]:
        """Scrape projects from OESW."""
        url = f"{self.base_url}/projekt.html"
        soup = self.fetch_html(url)
        flats = []
        seen_urls = set()

        # Find all project links on the main page
        # Links are in format: /immobilienangebot/projektdetail/mhimmo/anzeigen/Wohnhaus/1020-wien-adambergasse-6.html
        project_links = soup.find_all(
            "a", href=re.compile(r"/immobilienangebot/projektdetail/mhimmo/anzeigen/Wohnhaus/")
        )

        self.logger.info(f"Found {len(project_links)} potential project links")

        # Limit to first 50 projects to avoid long scrape times (website is slow)
        max_projects = 50
        project_links = list(project_links[:max_projects])  # type: ignore[assignment]
        self.logger.info(f"Scraping first {len(project_links)} projects (limited for performance)")

        for i, link in enumerate(project_links, 1):
            href = link.get("href", "")
            if not href or href in seen_urls:
                continue

            seen_urls.add(href)
            full_url = f"{self.base_url}{href}"

            try:
                # Fetch project detail page
                flat = self._scrape_project(full_url)
                if flat:
                    flats.append(flat)
                    if i % 10 == 0:
                        self.logger.info(
                            f"Progress: {i}/{len(project_links)} projects scraped, {len(flats)} successful"
                        )
            except Exception as e:
                self.logger.warning(f"Failed to scrape project {full_url}: {e}")
                continue

        self.logger.info(f"Completed: {len(flats)} projects scraped successfully")
        return flats

    def _scrape_project(self, url: str) -> Flat | None:  # noqa: C901, PLR0912, PLR0915
        """Scrape a single project detail page."""
        try:
            soup = self.fetch_html(url)
        except Exception as e:
            self.logger.debug(f"Failed to fetch {url}: {e}")
            return None

        # Check for error page
        error_msg = soup.find(string=re.compile(r"Oops, an error occurred!"))
        if error_msg:
            self.logger.debug(f"Project page returned error: {url}")
            return None

        # Extract project title
        # Title is in format: "SMART & MORE - Hindernisse überwinden"
        title_tag = soup.find("h1") or soup.find("h2")
        title = title_tag.get_text(strip=True) if title_tag else None

        if not title:
            self.logger.debug(f"No title found for {url}")
            return None

        # Extract address from the page
        # Format: "1100 Wien Absberggasse 40"
        address_link = soup.find("a", href=re.compile(r"maps\.google\.com"))
        location = None
        postal_code = None
        city = None
        street = None

        if address_link:
            address_text = address_link.get_text(strip=True)
            # Parse address: "1100 Wien Absberggasse 40"
            addr_match = re.match(r"(\d{4})\s+(\w+)\s+(.+)", address_text)
            if addr_match:
                postal_code, city, street = addr_match.groups()
                location = f"{postal_code} {city}, {street}"

        # Fallback: extract from URL if address not found
        if not location:
            # URL format: .../1100-wien-absberggasse-40.html
            url_match = re.search(r"/(\d{4})-(\w+)-(.+?)(?:-\d+)?\.html", url)
            if url_match:
                postal_code = url_match.group(1)
                city = url_match.group(2).capitalize()
                street_slug = url_match.group(3)
                # Convert slug to street name (e.g., "absberggasse-40" -> "Absberggasse 40")
                street = street_slug.replace("-", " ").title()
                location = f"{postal_code} {city}, {street}"

        if not location:
            self.logger.debug(f"No location found for {url}")
            return None

        # Generate ID from location + title
        flat_id = self.generate_id(f"{location}-{title}")

        # Extract status
        # Look for "FERTIGGESTELLT" (completed) badge
        _status_tag = soup.find(
            string=re.compile(r"FERTIGGESTELLT|IN BAU|IN PLANUNG", re.IGNORECASE)
        )

        # Extract description
        description_parts = []

        # Get main project description paragraphs
        content_divs = soup.find_all("p")
        for p in content_divs:
            text = p.get_text(strip=True)
            if text and len(text) > 50:  # Only substantial paragraphs  # noqa: PLR2004
                description_parts.append(text)
                if len(description_parts) >= 3:  # Limit to first 3 paragraphs  # noqa: PLR2004
                    break

        description = " ".join(description_parts) if description_parts else title

        # Extract number of units if mentioned
        # Look for patterns like "219 Wohneinheiten" or "93 SMART-Wohnungen"
        units_match = re.search(r"(\d+)\s+(?:Wohneinheiten|Wohnungen)", description)
        units_count = int(units_match.group(1)) if units_match else None

        # Determine markers
        markers = []
        markers.append("completed")  # All listed projects are completed

        description_lower = description.lower()

        # Check for subsidy types
        if "smart" in description_lower or "supergeförd" in description_lower:
            markers.append("subsidized")
        if "geförd" in description_lower:
            markers.append("subsidized")

        # Check for special features
        if "barrierefrei" in description_lower:
            markers.append("accessible")
        if "kindergarten" in description_lower or "spielplatz" in description_lower:
            markers.append("family_friendly")

        # Rental vs ownership - OESW is primarily rental
        markers.append("rental")

        # Use number of units in title if available
        title_with_count = f"{title} ({units_count} Wohnungen)" if units_count else title

        return Flat(
            id=flat_id,
            title=title_with_count,
            url=url,  # type: ignore[arg-type]
            location=location,
            price=None,  # No price info on completed project pages
            size=None,  # Individual unit info not shown
            rooms=None,  # Individual unit info not shown
            description=description[:500],  # Limit description length
            image_url=None,
            markers=markers,
            source=self.name,
        )
