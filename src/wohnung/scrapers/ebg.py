"""Scraper for EBG Wohnen (Gemeinnützige Ein- und Mehrfamilienhäuser Baugenossenschaft)."""

import re

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class EbgScraper(BaseScraper):
    """Scraper for EBG Wohnen projects in planning."""

    @property
    def name(self) -> str:
        """Return the scraper name."""
        return "ebg"

    @property
    def base_url(self) -> str:
        """Return the base URL."""
        return "https://www.ebg-wohnen.at"

    def scrape(self) -> list[Flat]:
        """Scrape projects from EBG in-planning page."""
        url = f"{self.base_url}/in-planung/projekte"
        soup = self.fetch_html(url)
        flats = []
        seen_urls = set()

        # Find all project links - they point to /in-planung/projekte/detail/{id}
        project_links = soup.find_all("a", href=re.compile(r"/in-planung/projekte/detail/\d+"))

        self.logger.info(f"Found {len(project_links)} project links")

        for link in project_links:
            href = link.get("href", "")
            if not href or href in seen_urls:
                continue

            seen_urls.add(href)
            full_url = f"{self.base_url}{href}" if href.startswith("/") else href

            try:
                # Get project title from link text
                title = link.get_text(strip=True)

                # Skip if title is just "MIETE" or empty
                if not title or title.upper() == "MIETE":
                    # Try to find title in parent element
                    parent = link.parent
                    if parent:
                        # Look for heading or title in parent
                        title_elem = parent.find(["h2", "h3", "h4", "h5", "h6"])
                        if title_elem:
                            title = title_elem.get_text(strip=True)

                if not title or title.upper() == "MIETE":
                    self.logger.debug(f"Skipping link without proper title: {href}")
                    continue

                # Fetch project detail page for full information
                flat = self._scrape_project(full_url, title)
                if flat:
                    flats.append(flat)
            except Exception as e:
                self.logger.warning(f"Failed to scrape project {full_url}: {e}")
                continue

        return flats

    def _scrape_project(self, url: str, fallback_title: str | None = None) -> Flat | None:  # noqa: C901, PLR0912, PLR0915
        """Scrape a single project detail page."""
        try:
            soup = self.fetch_html(url)
        except Exception as e:
            self.logger.debug(f"Failed to fetch {url}: {e}")
            return None

        location: str = ""  # Initialize location
        title: str = ""  # Initialize title

        # Extract project title - usually in an h3
        title_tag = soup.find(
            ["h3", "h2", "h1"],
            string=lambda x: x
            and len(x.strip()) > 3  # noqa: PLR2004
            and x.strip().upper() not in ["BESCHREIBUNG", "LAGEPLAN", "VORMERKUNG", "ARCHITEKTUR"],
        )
        if title_tag:
            title = title_tag.get_text(strip=True)

            # Extract location from the same parent div as the title
            # Format is typically: Title | Location Line 1 | Location Line 2
            parent = title_tag.parent
            if parent:
                # Get text with separator
                parent_text = parent.get_text(separator="|", strip=True)
                # Split by separator and get parts after title
                parts = [p.strip() for p in parent_text.split("|")]
                # Filter out empty parts and the title itself
                parts = [p for p in parts if p and p != title]
                # Location is typically in the first 1-2 parts after title
                # Join first 2 parts as location (postal code + street)
                location = " ".join(parts[:2]) if parts else ""
            else:
                location = ""
        else:
            title = fallback_title or ""
            location = ""

        if not title:
            self.logger.debug(f"No title found for {url}")
            return None

        # If no location found yet, try regex on description area only
        if not location:
            # Look for location in main content area (skip navigation)
            main_content = soup.find(["main", "article"]) or soup
            content_text = main_content.get_text()

            # Look for Austrian postal code patterns
            location_match = re.search(
                r"(\d{4}\s+[\w\s-]+(?:\s+[\w\s\.-]+){1,3})", content_text[200:1000]
            )
            if location_match:
                location = location_match.group(1).strip()
                # Clean up potential garbage
                location = re.sub(r"\s+", " ", location)
                # Limit length
                if len(location) > 100:  # noqa: PLR2004
                    location = location[:100]

        if not location:
            # Final fallback: use title
            location = title

        # Extract description from the BESCHREIBUNG section
        description_parts = []
        description_section = soup.find(string=re.compile(r"BESCHREIBUNG"))
        if description_section:
            # Get the parent and find following paragraphs
            parent = description_section.find_parent()
            if parent:
                # Find all paragraphs in the parent's next siblings
                for sibling in parent.find_next_siblings(["p", "div"]):
                    text = sibling.get_text(strip=True)
                    if text and len(text) > 20:  # noqa: PLR2004
                        description_parts.append(text)
                        if len(description_parts) >= 3:  # noqa: PLR2004
                            break

        if not description_parts:
            # Fallback: get first few substantial paragraphs
            paragraphs = soup.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50:  # noqa: PLR2004
                    description_parts.append(text)
                    if len(description_parts) >= 2:  # noqa: PLR2004
                        break

        description = " ".join(description_parts) if description_parts else title

        # Extract number of units if mentioned
        # Look for patterns like "136 Wohnungen" or "100 Wohnungen"
        units_match = re.search(r"(\d+)\s+(?:Wohnungen|Wohneinheiten)", description)
        units_count = int(units_match.group(1)) if units_match else None

        # Extract move-in date if mentioned
        # Look for "Geplanter Bezug: 3. Quartal 2028"
        move_in_match = re.search(
            r"(?:Geplanter Bezug|Bezug|Fertigstellung):\s*([^.]+)", description
        )
        move_in_date = move_in_match.group(1).strip() if move_in_match else None

        # Generate ID
        flat_id = self.generate_id(f"{title}-{location}")

        # Determine markers
        markers = []
        markers.append("in_planning")  # All projects are in planning phase
        markers.append("rental")  # All are marked as "MIETE"

        description_lower = description.lower()

        # Check for subsidy
        if "geförd" in description_lower:
            markers.append("subsidized")
        elif "freifinanziert" in description_lower:
            markers.append("free_financed")

        # Check for registration availability
        if "vormerkung" in description_lower:
            markers.append("vormerkung_possible")

        # Check for special features
        if "barrierefrei" in description_lower:
            markers.append("accessible")
        if "kindergarten" in description_lower or "spielplatz" in description_lower:
            markers.append("family_friendly")
        if "nachhaltig" in description_lower or "energieeffizient" in description_lower:
            markers.append("sustainable")

        # Build enhanced title with unit count
        enhanced_title = f"{title} ({units_count} Wohnungen)" if units_count else title

        # Add move-in date to description if available
        description = (
            f"Geplanter Bezug: {move_in_date}. {description[:400]}"
            if move_in_date
            else description[:500]
        )

        return Flat(
            id=flat_id,
            title=enhanced_title,
            url=url,  # type: ignore[arg-type]
            location=location or "Wien",  # type: ignore[arg-type]
            price=None,  # Not specified on project pages
            size=None,  # Not specified on project pages
            rooms=None,  # Not specified on project pages
            description=description,
            image_url=None,
            markers=markers,
            source=self.name,
        )
