"""Scraper for Familienwohnbau."""

import re

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class FamilienwohnbauScraper(BaseScraper):
    """Scraper for Familienwohnbau projects."""

    @property
    def name(self) -> str:
        """Return the scraper name."""
        return "familienwohnbau"

    @property
    def base_url(self) -> str:
        """Return the base URL for this scraper."""
        return "https://familienwohnbau.at"

    def scrape(self) -> list[Flat]:  # noqa: C901, PLR0912
        """Scrape flats from Familienwohnbau projects page.

        Scrapes the main projects page which shows various property offerings
        including rentals, sales, commercial spaces, and more.
        """
        flats = []

        # Main projects page
        url = f"{self.base_url}/de/projekte"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find all links to /de/objekt/
            project_links = soup.find_all("a", href=lambda x: x and "/de/objekt/" in x)

            for link in project_links:
                href = link.get("href", "")

                # Build full URL
                full_url = f"{self.base_url}{href}" if href.startswith("/") else href

                # Find image for metadata
                img = link.find("img")
                img_alt = img.get("alt", "") if img else ""
                img_src = img.get("src", "") if img else None

                # Get text content
                text = link.get_text(strip=True, separator=" ")

                # Extract location and title from alt text or text
                # Format is usually: "Location KEYWORD" or just "Location"
                title = img_alt if img_alt else text.split("Ab €")[0].strip()

                # Extract price if available
                price_match = re.search(r"Ab\s*€\s*([\d.,]+)", text)
                price = None
                if price_match:
                    price_str = price_match.group(1).replace(".", "").replace(",", ".")
                    # Use contextlib.suppress instead of try-except-pass
                    from contextlib import suppress

                    with suppress(ValueError):
                        price = float(price_str)

                # Extract number of units
                units_match = re.search(r"Anzahl der Einheiten:\s*(\d+)", text)
                units_count = units_match.group(1) if units_match else None

                # Parse location from title
                # Format: "1210 Wien, Street" or "Location"
                location = None
                # Try to extract full location including street
                # Pattern: "1210 Wien, Street Name 123"
                location_match = re.match(
                    r"^(\d{4}\s+[^,]+,\s*[^A-Z][^(]*?)(?:\s+[A-Z]{3,}|\s*\(|$)", title
                )
                if location_match:
                    location = location_match.group(1).strip()
                elif re.match(r"^\d{4}\s+", title):
                    # Just has postal code + city
                    location_match = re.match(r"^(\d{4}\s+[^,]+)", title)
                    if location_match:
                        location = location_match.group(1).strip()

                # Determine markers based on title/text
                markers = []
                title_lower = title.lower()

                if "miete" in title_lower or "rental" in title_lower:
                    markers.append("rental")
                elif any(word in title_lower for word in ["eigentum", "verkauf", "kauf"]):
                    markers.append("for_sale")

                if "genossenschaft" in title_lower or "gewerbe" in title_lower:
                    # Gemeinnützige or commercial
                    markers.append("subsidized")

                if "neubau" in title_lower or "neu" in title_lower:
                    markers.append("neubau")

                # Skip if it's just parking/garages
                if (
                    "garage" in title_lower
                    or "stellplatz" in title_lower
                    or "abstellplatz" in title_lower
                ):
                    continue

                # Create flat object
                flat = self._create_flat(
                    title=title,
                    url=full_url,
                    location=location,
                    price=price,
                    image_url=img_src,
                    markers=markers,
                    units_count=units_count,
                )

                if flat:
                    flats.append(flat)

        except Exception as e:
            print(f"Error scraping Familienwohnbau: {e}")

        return flats

    def _create_flat(
        self,
        title: str,
        url: str,
        location: str | None,
        price: float | None,
        image_url: str | None,
        markers: list[str],
        units_count: str | None,
    ) -> Flat | None:
        """Create a Flat object from extracted data."""

        # Generate ID from URL
        # Extract the slug from the URL
        slug_match = re.search(r"/de/objekt/([^?]+)", url)
        if slug_match:
            slug = slug_match.group(1)
            flat_id = self.generate_id(slug)
        else:
            flat_id = self.generate_id(title)

        # Add unit count to title if available
        display_title = title
        if units_count:
            display_title = f"{title} ({units_count} Einheiten)"

        # Default to subsidized for this gemeinnützige organization
        if not markers:
            markers = ["subsidized"]
        elif "subsidized" not in markers:
            markers.append("subsidized")

        return Flat(
            id=flat_id,
            title=display_title,
            url=url,  # type: ignore[arg-type]
            location=location or title,  # Fall back to title if no location parsed
            price=price,
            size=None,  # Not available on listing page
            rooms=None,
            description=None,
            image_url=image_url,  # type: ignore[arg-type]
            source=self.name,
            markers=markers,
        )
