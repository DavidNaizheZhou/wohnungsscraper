"""Scraper for Mischek real estate projects."""

import re

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class MischekScraper(BaseScraper):
    """Scraper for Mischek projects."""

    @property
    def name(self) -> str:
        """Return the scraper name."""
        return "mischek"

    @property
    def base_url(self) -> str:
        """Return the base URL for this scraper."""
        return "https://www.mischek.at"

    def scrape(self) -> list[Flat]:
        """Scrape flats from Mischek projects page.

        The data is embedded in Next.js __next_f script tags as escaped JSON.
        We extract project information including name, address, price, and details.
        """
        url = f"{self.base_url}/de/projekte"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        flats = []
        seen_ids = set()  # Track IDs to avoid duplicates

        # Find all script tags containing Next.js data
        scripts = soup.find_all("script")

        for script in scripts:
            if not script.string or "__next_f" not in script.string:
                continue

            content = script.string

            # Look for project data with escaped quotes (Next.js format)
            # The pattern matches: \\"name\\":\\"ProjectName\\",...\\"address\\":[\\"Street\\",\\"PostalCode City\\"]
            pattern = (
                r'\\"name\\":\\"([^\\]+)\\",\\"accentColor\\":\\"([^\\]+)\\",\\"badges\\":\[([^\]]+)\],\\"address\\":\[\\"([^\\]+)\\",\\"([^\\]+)\\"\],\\"price\\":\\"([^\\]*)\\",'
                r'\\"availability\\":\\"([^\\]+)\\",\\"estatesCount\\":\\"([^\\]+)\\",\\"roomsRange\\":\\"([^\\]+)\\",\\"floorSpaceRange\\":\\"([^\\]+)\\"'
            )

            matches = re.findall(pattern, content)

            for match in matches:
                (
                    name,
                    accent_color,
                    badges,
                    street,
                    postal_city,
                    price,
                    availability,
                    estates_count,
                    rooms_range,
                    floor_space_range,
                ) = match

                # Skip if not a real project (filter out UI elements)
                if name in ["Custom", "Home"]:
                    continue

                # Parse badges - they come as escaped quoted strings
                # e.g., \\"living\\",\\"subsidised\\"
                badges_clean = badges.replace('\\"', "").replace('"', "")
                badges_list = [b.strip() for b in badges_clean.split(",")]

                # Create flat object
                flat = self._create_flat(
                    name=name,
                    street=street,
                    postal_city=postal_city,
                    price=price,
                    badges=badges_list,
                    estates_count=estates_count,
                    rooms_range=rooms_range,
                    floor_space_range=floor_space_range,
                    _availability=availability,
                )

                if flat and flat.id not in seen_ids:
                    seen_ids.add(flat.id)
                    flats.append(flat)

        return flats

    def _create_flat(
        self,
        name: str,
        street: str,
        postal_city: str,
        price: str,
        badges: list[str],
        estates_count: str,
        rooms_range: str,
        floor_space_range: str,
        _availability: str,
    ) -> Flat | None:
        """Create a Flat object from extracted data."""

        # Generate ID from name
        flat_id = self.generate_id(f"{name}-{postal_city}")

        # Build URL
        # Convert name to slug (lowercase, replace spaces with hyphens, handle special chars)
        slug = name.lower()
        slug = slug.replace("ü", "ue").replace("ö", "oe").replace("ä", "ae").replace("ß", "ss")
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        url = f"{self.base_url}/de/projekte/{slug}"

        # Build location string
        location = f"{street}, {postal_city}"

        # Determine markers from badges
        markers = set()
        markers.add("neubau")  # All Mischek projects are new construction

        for badge in badges:
            badge_lower = badge.lower()
            if badge_lower == "living":
                markers.add("for_sale")
            elif badge_lower == "commercial":
                # Commercial properties - could add a commercial marker if needed
                pass
            elif "subsid" in badge_lower:  # Matches both "subsidised" and "subsidized"
                markers.add("subsidized")
            elif "privately-financed" in badge_lower or "privately" in badge_lower:
                markers.add("for_sale")
            elif "rental" in badge_lower or badge_lower == "rent":
                markers.add("rental")

        # Parse size range (e.g., "38-115 m²")
        size = None
        size_match = re.search(r"(\d+)-(\d+)\s*m", floor_space_range)
        if size_match:
            # Use average of range
            min_size = float(size_match.group(1))
            max_size = float(size_match.group(2))
            size = (min_size + max_size) / 2

        # Parse rooms range (e.g., "1-4 Zimmer")
        rooms = None
        rooms_match = re.search(r"(\d+)-(\d+)\s*Zimmer", rooms_range)
        if rooms_match:
            # Use average of range
            min_rooms = float(rooms_match.group(1))
            max_rooms = float(rooms_match.group(2))
            rooms = (min_rooms + max_rooms) / 2

        # For image, we'll use a placeholder since extracting from the complex JSON is difficult
        # The actual scraper would need to parse the image URLs from the data
        image_url = None

        return Flat(
            id=flat_id,
            title=f"{name} - {estates_count}",
            url=url,  # type: ignore[arg-type]
            location=location,
            price=self.parse_price(price) if price else None,
            size=size,
            rooms=rooms,
            description=None,
            image_url=image_url,
            source=self.name,
            markers=list(markers),
        )
