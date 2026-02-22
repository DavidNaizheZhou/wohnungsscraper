"""Example scraper implementation."""

from datetime import datetime

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class ExampleScraper(BaseScraper):
    """
    Example scraper template.

    Replace this with actual scraper implementations for real estate sites.
    """

    @property
    def name(self) -> str:
        """Scraper identifier."""
        return "example"

    @property
    def base_url(self) -> str:
        """Base URL for scraping."""
        return "https://example.com/flats"

    def scrape(self) -> list[Flat]:
        """
        Scrape flats from the example site.

        Returns:
            List of Flat objects

        Note:
            This is a template. Replace with actual scraping logic.
        """
        flats: list[Flat] = []

        try:
            soup = self.fetch_html(self.base_url)

            # Example: Replace with actual CSS selectors
            listings = soup.select(".flat-listing")

            for listing in listings:
                # Extract data from HTML elements
                title_elem = listing.select_one(".title")
                url_elem = listing.select_one("a")
                price_elem = listing.select_one(".price")
                size_elem = listing.select_one(".size")
                rooms_elem = listing.select_one(".rooms")
                location_elem = listing.select_one(".location")
                image_elem = listing.select_one("img")

                # Skip if essential fields are missing
                if not title_elem or not url_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url_raw = url_elem.get("href", "")

                # Ensure url is a string (BeautifulSoup can return list)
                url = url_raw if isinstance(url_raw, str) else ""

                # Make URL absolute if needed
                if url and not url.startswith("http"):
                    url = f"https://example.com{url}"

                if not url:
                    continue

                # Get image URL
                image_url_raw = image_elem.get("src") if image_elem else None
                image_url = image_url_raw if isinstance(image_url_raw, str) else None

                # Create Flat object
                flat = Flat(
                    id=self.generate_id(url),
                    title=title,
                    url=url,  # type: ignore[arg-type]
                    price=self.parse_price(price_elem.get_text()) if price_elem else None,
                    size=self.parse_size(size_elem.get_text()) if size_elem else None,
                    rooms=self.parse_rooms(rooms_elem.get_text()) if rooms_elem else None,
                    location=location_elem.get_text(strip=True) if location_elem else "Unknown",
                    description=None,
                    image_url=image_url,  # type: ignore[arg-type]
                    source=self.name,
                    found_at=datetime.now(),
                )

                flats.append(flat)

        except Exception as e:
            print(f"Error scraping {self.name}: {e}")

        return flats
