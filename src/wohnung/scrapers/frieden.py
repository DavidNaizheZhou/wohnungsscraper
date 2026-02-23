"""Scraper for Frieden (frieden.at)."""

import re

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class FriedenScraper(BaseScraper):
    """Scraper for Frieden gemeinnützige housing cooperative."""

    @property
    def name(self) -> str:
        """Return the scraper name."""
        return "frieden"

    @property
    def base_url(self) -> str:
        """Return the base URL."""
        return "https://www.frieden.at/projekte"

    def scrape(self) -> list[Flat]:  # noqa: C901, PLR0912, PLR0915
        """Scrape flats from Frieden."""
        url = self.base_url
        soup = self.fetch_html(url)
        flats = []
        seen_urls = set()

        # Find all project tiles
        tiles = soup.find_all(
            "div", class_=lambda x: x and "ProjectDashboardTile__DashboardTile" in x
        )

        for tile in tiles:
            try:
                # Get the project link
                link_tag = tile.find("a", href=lambda x: x and "/projekte/" in x)
                if not link_tag:
                    continue

                href = link_tag.get("href", "")
                # Remove query parameters
                project_url = href.split("?")[0]
                full_url = f"https://www.frieden.at{project_url}"

                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Get the address/title (contains postal code + location + street)
                address_tag = tile.find("h2", class_=lambda x: x and "Address" in x)
                if not address_tag:
                    continue

                # Get text with <br/> converted to space
                title_text = address_tag.get_text(separator=" ", strip=True)

                # Parse location (postal code + city, may include multiple words)
                location = None
                # Match postal code + city name (which may be multiple words)
                location_match = re.match(r"(\d{4}\s+(?:[^\d\s]+(?:\s+[^\d\s]+)?)+)", title_text)
                if location_match:
                    location = location_match.group(1).strip()

                if not location:
                    location = title_text

                # Get proposal type (Miete, Kauf, etc.)
                proposal_tag = tile.find("div", class_=lambda x: x and "ProjectProposalTypes" in x)
                proposal_type = proposal_tag.get_text(strip=True) if proposal_tag else ""

                # Determine markers
                markers = []
                proposal_lower = proposal_type.lower()

                # Check for rental vs for_sale
                if "miete ohne kaufoption" in proposal_lower:
                    # Rent without purchase option - rental only
                    markers.append("rental")
                elif "miete mit" in proposal_lower and "kaufoption" in proposal_lower:
                    # Rent with purchase option - both rental and for_sale
                    markers.append("rental")
                    markers.append("for_sale")
                elif "miete" in proposal_lower:
                    # General rental
                    markers.append("rental")
                elif "kauf" in proposal_lower:
                    # Purchase only
                    markers.append("for_sale")

                # All Frieden projects are subsidized (gemeinnützige)
                markers.append("subsidized")

                # Mark as neubau (new construction)
                markers.append("neubau")

                # Get info about units
                info_tag = tile.find("div", class_=lambda x: x and "ProjectOtherInfo" in x)
                if info_tag:
                    info_text = info_tag.get_text(strip=True)
                    # Try to extract unit count
                    units_match = re.search(r"Wohnungen:\s*(\d+)\s*/\s*(\d+)", info_text)
                    if units_match:
                        available = int(units_match.group(1))
                        total = int(units_match.group(2))
                        title_text = f"{title_text} ({available}/{total} verfügbar)"

                flat = Flat(
                    id=self.generate_id(full_url),
                    title=title_text,
                    url=full_url,  # type: ignore[arg-type]
                    price=None,  # No pricing shown on listing page
                    size=None,  # Size not shown on listing page
                    rooms=None,  # Rooms not shown on listing page
                    location=location,
                    description=proposal_type,
                    image_url=None,  # Could extract but not critical
                    source=self.name,
                    markers=markers,
                )
                flats.append(flat)

            except Exception as e:
                self.logger.warning(f"Error parsing project tile: {e}")
                continue

        return flats
