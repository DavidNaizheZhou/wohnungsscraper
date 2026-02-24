"""Scraper for NHG - Neue Heimat."""

from bs4 import BeautifulSoup

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class NhgScraper(BaseScraper):
    """Scraper for Neue Heimat projects."""

    @property
    def name(self) -> str:
        """Return the scraper name."""
        return "nhg"

    @property
    def base_url(self) -> str:
        """Return the base URL for this scraper."""
        return "https://www.nhg.at"

    def scrape(self) -> list[Flat]:
        """Scrape flats from NHG project pages.

        Scrapes both "projekte-in-planung" (planning) and "projekte-in-bau" (construction) pages.
        Projects are listed as divs with class "item" and data-url attribute.
        """
        flats = []
        seen_urls = set()

        # Scrape both planning and construction phases
        pages = [("projekte-in-planung", "in_planning"), ("projekte-in-bau", "neubau")]

        for page_slug, marker in pages:
            url = f"{self.base_url}/immobilienangebot/{page_slug}/"

            try:
                response = self.client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Find all project items with data-url
                items = soup.find_all("div", class_="item", attrs={"data-url": True})

                for item in items:
                    project_url = item.get("data-url")

                    # Skip duplicates
                    if project_url in seen_urls:
                        continue
                    seen_urls.add(project_url)

                    # Extract project data
                    title_elem = item.find("h6")
                    location_elem = item.find("p")
                    img_elem = item.find("img")

                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    location = location_elem.get_text(strip=True) if location_elem else None
                    image_url = img_elem.get("src") if img_elem else None

                    # Build full URL
                    full_url = (
                        f"{self.base_url}{project_url}"
                        if project_url.startswith("/")
                        else project_url
                    )

                    # Create flat object
                    flat = self._create_flat(
                        title=title,
                        location=location,
                        url=full_url,
                        image_url=image_url,
                        marker=marker,
                    )

                    if flat:
                        flats.append(flat)

            except Exception as e:
                self.logger.error(f"Error scraping {page_slug}: {e}")
                continue

        return flats

    def _create_flat(
        self, title: str, location: str | None, url: str, image_url: str | None, marker: str
    ) -> Flat | None:
        """Create a Flat object from extracted data."""

        # Generate ID from title and location
        id_base = f"{title}-{location}" if location else title
        flat_id = self.generate_id(id_base)

        # Clean location if it contains duplicate text
        # e.g., "1210 Wien, An der Schanze , 1210 Wien, Simone-Veil-Gasse 11"
        clean_location = location
        if location:
            # Split by comma and deduplicate
            parts = [p.strip() for p in location.split(",")]
            # Keep unique parts while preserving order
            seen = set()
            unique_parts = []
            for part in parts:
                if part and part not in seen:
                    seen.add(part)
                    unique_parts.append(part)
            clean_location = ", ".join(unique_parts)

        # Build full image URL if it's relative
        full_image_url = None
        if image_url:
            if image_url.startswith("/"):
                full_image_url = f"{self.base_url}{image_url}"
            else:
                full_image_url = image_url

        # Set markers based on project phase
        markers = []
        if marker == "in_planning":
            markers.append("in_planning")
        elif marker == "neubau":
            markers.append("neubau")

        # All NHG projects are subsidized/gemeinnützig
        markers.append("subsidized")
        markers.append("for_sale")  # Most are for sale

        return Flat(
            id=flat_id,
            title=title,
            url=url,  # type: ignore[arg-type]
            location=clean_location if clean_location else title,  # type: ignore[arg-type]
            price=None,  # Price not available on listing page
            size=None,
            rooms=None,
            description=None,
            image_url=full_image_url,  # type: ignore[arg-type]
            source=self.name,
            markers=markers,
        )
