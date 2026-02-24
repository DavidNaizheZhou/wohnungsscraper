"""Scraper for Sozialbau AG housing projects.

Scrapes projects from https://angebote.sozialbau.at/sobitvX/htmlprospect/home.xhtml
This site uses JSF (JavaServer Faces) technology requiring ViewState handling.
"""

import re
from datetime import datetime
from typing import ClassVar

from bs4 import BeautifulSoup

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class SozialbauScraper(BaseScraper):
    """Scraper for Sozialbau AG housing projects."""

    # Category IDs for different project statuses
    CATEGORIES: ClassVar[dict[str, str]] = {
        "in_bau": "menuform:j_idt23",  # In Bau (under construction)
        "in_planung": "menuform:j_idt24",  # In Planung (in planning)
        "sofort_verfugbar": "menuform:j_idt25",  # Sofort verfügbar (immediately available)
    }

    @property
    def name(self) -> str:
        """Scraper identifier."""
        return "sozialbau"

    @property
    def base_url(self) -> str:
        """Base URL for scraping."""
        return "https://angebote.sozialbau.at/sobitvX/htmlprospect/home.xhtml"

    @property
    def email_recipients(self) -> list[str]:
        """Send notifications to dana.kreuz."""
        return ["dana.kreuz@posteo.at"]

    def scrape(self) -> list[Flat]:
        """Scrape flats from Sozialbau projects page.

        This site uses JSF (JavaServer Faces) which requires:
        1. GET request to obtain ViewState and session cookie
        2. POST request with ViewState to load listings

        Returns:
            List of Flat objects
        """
        all_flats: list[Flat] = []

        try:
            # Step 1: GET the page to obtain ViewState and session cookie
            response = self.client.get(self.base_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            viewstate_input = soup.find("input", {"name": "javax.faces.ViewState"})

            if not viewstate_input:
                self.logger.error("Could not find ViewState in initial page")
                return all_flats

            viewstate = viewstate_input.get("value", "")  # type: ignore[union-attr]
            self.logger.debug(f"Obtained ViewState: {viewstate[:50]}...")

            # Step 2: Fetch from all categories
            for category_name, source_id in self.CATEGORIES.items():
                self.logger.debug(f"Fetching {category_name} listings...")

                payload = {
                    "javax.faces.partial.ajax": "true",
                    "javax.faces.source": source_id,
                    "javax.faces.partial.execute": "@all",
                    "javax.faces.partial.render": "f1:ajax-main",
                    source_id: source_id,
                    "menuform": "menuform",
                    "javax.faces.ViewState": viewstate,
                }

                response2 = self.client.post(self.base_url, data=payload)
                response2.raise_for_status()

                # Parse the response
                flats = self._parse_ajax_response(response2.text, category_name)
                all_flats.extend(flats)

                self.logger.debug(f"Found {len(flats)} flats in {category_name}")

            self.logger.info(f"Found {len(all_flats)} total flats from Sozialbau")

        except Exception as e:
            self.logger.error(f"Error scraping Sozialbau: {e}", exc_info=True)

        return all_flats

    def _parse_ajax_response(self, ajax_response: str, category: str) -> list[Flat]:
        """Parse the AJAX response containing listings.

        Args:
            ajax_response: AJAX response text (XML format)
            category: Category name (in_bau, in_planung, sofort_verfugbar)

        Returns:
            List of Flat objects
        """
        flats = []

        try:
            # Parse as XML to find the update elements
            soup_xml = BeautifulSoup(ajax_response, "xml")
            updates = soup_xml.find_all("update")

            for update in updates:
                update_id = update.get("id", "")

                # We're interested in the main content update
                if update_id != "f1:ajax-main":
                    continue

                content = update.get_text()

                # Parse the HTML content
                soup_html = BeautifulSoup(content, "html.parser")

                # Check if this is table-based (In Bau, In Planung) or card-based (Sofort verfügbar)
                table = soup_html.find("table")

                if table:
                    # Table structure (In Bau, In Planung)
                    rows = table.find_all("tr")  # type: ignore[union-attr]
                    for row in rows[1:]:  # Skip header
                        flat = self._parse_table_row(row, category)
                        if flat:
                            flats.append(flat)
                else:
                    # Card structure (Sofort verfügbar)
                    cards = soup_html.find_all(
                        "div", class_=lambda x: x and "card" in str(x) and "p-0" in str(x)
                    )
                    for card in cards:
                        flat = self._parse_card_item(card, category)
                        if flat:
                            flats.append(flat)

        except Exception as e:
            self.logger.error(f"Error parsing AJAX response for {category}: {e}", exc_info=True)

        return flats

    def _parse_table_row(self, row: BeautifulSoup, category: str) -> Flat | None:  # noqa: C901 912
        """Parse a table row into a Flat object.

        Table structure:
        - Cell 0: Type (Miete/Eigentum)
        - Cell 1: Address (with link)
        - Cell 2: Number of apartments
        - Cell 3: Available date
        - Cell 4: Number of reservations
        - Cell 5: Map link
        - Cell 6: Vormerken button

        Args:
            row: BeautifulSoup tr element
            category: Category name (in_bau, in_planung, sofort_verfugbar)

        Returns:
            Flat object or None if parsing fails
        """
        try:
            cells = row.find_all(["td", "th"])  # type: ignore[union-attr]
            min_cells = 6
            if len(cells) < min_cells:
                return None

            # Cell 0: Type (Miete/Eigentum)
            property_type = cells[0].get_text(strip=True)

            # Cell 1: Address (with link to details)
            address_cell = cells[1]
            address = address_cell.get_text(strip=True)

            # Extract link (may be # for AJAX trigger)
            # The ID of the link is important for detail fetching
            link = address_cell.find("a")
            link_id = link.get("id", "") if link else ""

            # For now, use the base URL as the property URL
            # In a real implementation, you might need to trigger the detail view
            url = f"{self.base_url}#property-{link_id}" if link_id else self.base_url

            # Cell 2: Number of apartments
            num_apartments = cells[2].get_text(strip=True)

            # Cell 3: Available date
            available_date = cells[3].get_text(strip=True)

            # Cell 4: Number of reservations
            reservations = cells[4].get_text(strip=True)

            # Extract location from address (usually starts with postal code)
            location = self._extract_location(address)

            # Clean address for title (remove duplicate postal code prefix if present)
            # Pattern: "1210 Wien1210 Wien, ..." -> "1210 Wien, ..."
            clean_address = re.sub(r"^(\d{4}\s+\w+)\1,?\s*", r"\1, ", address)

            # Create title from address and number of apartments
            title = f"{clean_address} ({num_apartments} Wohnungen)"

            # Build description
            description_parts = []
            if property_type:
                description_parts.append(property_type)
            if available_date:
                description_parts.append(f"Bezug: {available_date}")
            if reservations:
                description_parts.append(f"Vormerkungen: {reservations}")

            description = " · ".join(description_parts) if description_parts else None

            # Determine markers based on category and type
            markers = []
            if category == "in_bau":
                markers.append("under_construction")
            elif category == "in_planung":
                markers.append("in_planning")
            elif category == "sofort_verfugbar":
                markers.append("available_now")

            if "Miete" in property_type:
                markers.append("rental")
            elif "Eigentum" in property_type:
                markers.append("for_sale")

            # Create Flat object
            flat = Flat(
                id=self.generate_id(url),
                url=url,  # type: ignore[arg-type]
                title=title,
                location=location,
                description=description,
                image_url=None,  # No images in table view
                markers=markers,
                source=self.name,
                found_at=datetime.now(),
                price=None,  # Not shown in table
                size=None,  # Not shown in table
                rooms=None,  # Not shown in table
            )

            return flat

        except Exception as e:
            self.logger.debug(f"Could not parse table row: {e}")
            return None

    def _parse_card_item(self, card: BeautifulSoup, category: str) -> Flat | None:  # noqa: C901, PLR0912, PLR0915
        """Parse a card div into a Flat object (for Sofort verfügbar).

        Card structure:
        - Image in card-image div
        - Details in card-body div
          - Title with size (m²), rooms, and price
          - Address in span.flat-address

        Args:
            card: BeautifulSoup div element with class 'card'
            category: Category name (should be sofort_verfugbar)

        Returns:
            Flat object or None if parsing fails
        """
        try:
            # Find the card body with details
            card_body = card.find("div", class_="card-body")  # type: ignore[call-arg]
            if not card_body:
                return None

            # Find the title (contains size, rooms, price)
            title_elem = card_body.find("h4", class_="card-title")  # type: ignore[union-attr, call-arg]
            if not title_elem:
                return None

            # Extract size (e.g., "95 m²")
            size = None
            size_text = title_elem.find("span", class_="text-nowrap")  # type: ignore[union-attr, call-arg]
            if size_text:
                size_str = size_text.get_text(strip=True)  # type: ignore[union-attr]
                size = self.parse_size(size_str)

            # Extract rooms (e.g., "4 Zimmer")
            rooms = None
            spans = title_elem.find_all("span", class_="text-nowrap")  # type: ignore[union-attr]
            for span in spans:
                text = span.get_text(strip=True)
                if "Zimmer" in text:
                    rooms = self.parse_rooms(text)
                    break

            # Extract price from the right side
            price = None
            price_div = title_elem.find("div", class_="text-right")  # type: ignore[union-attr, call-arg]
            if price_div:
                price_text = price_div.get_text(strip=True)  # type: ignore[union-attr]
                price = self.parse_price(price_text)

            # Extract address
            address = ""
            address_span = card_body.find("span", class_="flat-address")  # type: ignore[call-arg]
            if address_span:
                strong = address_span.find("strong")  # type: ignore[union-attr]
                if strong:
                    address = strong.get_text(strip=True)  # type: ignore[union-attr]

            if not address:
                return None

            # Extract location from address
            location = self._extract_location(address)

            # Extract image URL
            image_url = None
            img = card.find("img")
            if img:
                image_url = img.get("src", "")  # type: ignore[union-attr]
                # Remove pfdrid_c parameter if present
                if image_url and "?pfdrid_c=" in image_url:  # type: ignore[operator]
                    image_url = image_url.split("?pfdrid_c=")[0]  # type: ignore[union-attr]

            # Find the link for generating proper URL
            link = card.find("a", href="#")
            link_id = link.get("id", "") if link else ""  # type: ignore[union-attr]
            url = f"{self.base_url}#property-{link_id}" if link_id else self.base_url

            # Build title
            title_parts = []
            if size:
                title_parts.append(f"{size:.0f}m²")
            if rooms:
                title_parts.append(f"{rooms:.0f} Zimmer")
            title_parts.append(address)
            title = " - ".join(title_parts)

            # Build description
            description_parts = []
            if price:
                description_parts.append(f"Miete: €{price:.2f}")
            description = " · ".join(description_parts) if description_parts else None

            # Determine markers
            markers = []
            if category == "sofort_verfugbar":
                markers.append("available_now")

            # Assume rental for immediately available properties
            markers.append("rental")

            # Check for subsidized housing indicators in address/description
            # (Sozialbau typically offers subsidized housing)
            markers.append("subsidized")

            # Create Flat object
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
                price=price,
                size=size,
                rooms=rooms,
            )

            return flat

        except Exception as e:
            self.logger.debug(f"Could not parse card item: {e}")
            return None

    def _extract_location(self, address: str) -> str:
        """Extract location (postal code + city) from address string.

        Args:
            address: Full address string

        Returns:
            Location string (e.g., "1210 Wien")
        """
        # Look for first occurrence of pattern like "1210 Wien"
        match = re.search(r"(\d{4}\s+Wien)", address)
        if match:
            return match.group(1)

        # Try other city names
        match = re.search(r"(\d{4}\s+\w+)", address)
        if match:
            return match.group(1)

        # If no match, try to find just "Wien"
        if "Wien" in address:
            return "Wien"

        return address.split(",")[0] if "," in address else address[:50]
