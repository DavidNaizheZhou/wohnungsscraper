"""Scraper for BWSG (Badener Wohnungsgenossenschaft)."""

import re
from typing import Any

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class BwsgScraper(BaseScraper):
    """Scraper for BWSG subsidized housing."""

    @property
    def name(self) -> str:
        """Return the scraper name."""
        return "bwsg"

    @property
    def base_url(self) -> str:
        """Return the base URL for this scraper."""
        return "https://www.bwsg.at"

    def get_site_name(self) -> str:
        """Return the site name."""
        return "bwsg"

    def scrape(self) -> list[Flat]:
        """Scrape all subsidized housing from BWSG."""
        # URL filtered for subsidized apartments and houses
        url = f"{self.base_url}/immobilien/immobilie-suchen/?_objektart=haus%2Cwohnung&_finanzierung=gefoerdert"

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        flats = []
        # Find all property containers
        property_divs = soup.find_all("div", {"data-objektnummer": True})

        for prop_div in property_divs:
            flat = self._parse_property(prop_div)
            if flat:
                flats.append(flat)

        return flats

    def _parse_property(self, prop_div: Any) -> Flat | None:
        """Parse a single property div into a Flat object."""
        # Get property ID
        property_id = prop_div.get("data-objektnummer", "")
        if not property_id:
            return None

        # Find the link
        link_tag = prop_div.find("a", class_="res_immobiliensuche__immobilien__item")
        if not link_tag:
            return None

        property_url = link_tag.get("href", "")
        if not property_url:
            return None

        # Get title
        title_tag = prop_div.find(
            "h2", class_="res_immobiliensuche__immobilien__item__content__title"
        )
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Get location
        location_tag = prop_div.find(
            "span", class_="res_immobiliensuche__immobilien__item__content__meta__location"
        )
        location = ""
        if location_tag:
            # Extract postal code and city
            icon_tag = location_tag.find("i")
            if icon_tag:
                icon_tag.decompose()  # Remove icon from text
            location_text = location_tag.get_text(strip=True)
            # Clean up and format location (add space after postal code)
            location = re.sub(r"(\d{4})([A-Z])", r"\1 \2", location_text)

        # Get price
        price_tag = prop_div.find(
            "span", class_="res_immobiliensuche__immobilien__item__content__meta__preis"
        )
        price = None
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            price = self.parse_price(price_text)

        # Get image URL
        image_tag = prop_div.find("img")
        image_url = None
        if image_tag:
            image_url = image_tag.get("src", "")

        # Determine markers
        markers = []
        markers.append("subsidized")  # All results are subsidized (gefoerdert filter)

        # Check if it's for sale or rental based on URL patterns or title
        title_lower = title.lower()
        if "kaufen" in title_lower or "eigentum" in title_lower:
            markers.append("for_sale")
        else:
            markers.append("rental")

        # Create flat object
        flat = Flat(
            id=property_id.replace("/", "-"),
            title=title,
            url=property_url,
            price=price,
            location=location,
            size=None,
            rooms=None,
            description=None,
            image_url=image_url if image_url else None,
            source=self.name,
            markers=markers,
        )

        return flat
