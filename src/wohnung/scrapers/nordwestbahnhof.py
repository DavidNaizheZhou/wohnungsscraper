"""Scraper for GBStern Nordwestbahnhof construction projects.

This is a special monitoring scraper that tracks:
- Entwicklungsstufe (development stages)
- Bauplatz → Bauträger mappings
- Changes in subsidized housing projects

This scraper has special email notification requirements.
"""

import re

from wohnung.models import Flat
from wohnung.scrapers.base import BaseScraper


class NordwestbahnhofScraper(BaseScraper):
    """Scraper for Nordwestbahnhof development area monitoring."""

    @property
    def name(self) -> str:
        """Return the scraper name."""
        return "nordwestbahnhof"

    @property
    def base_url(self) -> str:
        """Return the base URL."""
        return "https://www.gbstern.at/themen-projekte/stadtteilmanagement-in-neubaugebieten/stadtteilmanagement-nordwestbahnhof/bauprojekte/"

    @property
    def minimum_expected_results(self) -> int:
        """Expect at least 3 projects (Entwicklungsstufe I has 3 subsidized projects)."""
        return 3

    def scrape(self) -> list[Flat]:
        """Scrape Nordwestbahnhof construction project assignments.

        Extracts:
        - Entwicklungsstufe (development stage)
        - Bauplatz (construction site/plot) numbers
        - Bauträger (developer) assignments
        """
        url = self.base_url
        soup = self.fetch_html(url)
        flats = []

        # Find all Entwicklungsstufe sections
        entwicklungsstufe_headers = soup.find_all(string=re.compile(r"Entwicklungsstufe\s+[IVX]+"))

        self.logger.info(f"Found {len(entwicklungsstufe_headers)} development stage(s)")

        for header in entwicklungsstufe_headers:
            # Extract stage number (e.g., "Entwicklungsstufe I")
            stage_match = re.search(r"Entwicklungsstufe\s+([IVX]+)", header)
            if not stage_match:
                continue

            stage = stage_match.group(0)  # Full text like "Entwicklungsstufe I"
            stage_num = stage_match.group(1)  # Just "I", "II", etc.

            self.logger.info(f"Processing {stage}")

            # Find the section header's parent to get the content
            header_elem = header.find_parent()
            if not header_elem:
                continue

            # Get all text in this section (until next major header)
            section_content = []
            current = header_elem
            while current:
                current = current.find_next_sibling()
                if not current:
                    break
                # Stop at next h2 (new major section)
                if current.name == "h2":
                    break
                text = current.get_text(separator=" ", strip=True)
                if text:
                    section_content.append(text)

            section_text = " ".join(section_content)

            # Extract Bauplatz → Bauträger mappings
            # Pattern: "Bauplatz 4: (Baufeld 12) Bauträger: Familienwohnbau"
            # or just "• Bauplatz 4: ... Bauträger: Name"
            bauplatz_pattern = r"Bauplatz\s+(\d+)[:\s]+(?:\(Baufeld\s+\d+\))?\s*Bauträger:\s*([^•\n]+?)(?:\s+Planung:|$|•)"

            matches = re.findall(bauplatz_pattern, section_text, re.IGNORECASE)

            self.logger.info(f"Found {len(matches)} Bauplatz assignments in {stage}")

            for bauplatz_num, bautraeger_raw in matches:
                # Clean up bauträger name
                bautraeger = bautraeger_raw.strip()
                # Remove trailing "Planung:" if present
                bautraeger = re.sub(r"\s+Planung:.*$", "", bautraeger)

                # Create a "flat" entry for this assignment
                flat = self._create_assignment(
                    stage=stage,
                    stage_num=stage_num,
                    bauplatz=bauplatz_num,
                    bautraeger=bautraeger,
                    section_text=section_text,
                )

                if flat:
                    flats.append(flat)

        return flats

    def _create_assignment(
        self, stage: str, stage_num: str, bauplatz: str, bautraeger: str, section_text: str
    ) -> Flat | None:
        """Create a Flat object representing a Bauplatz assignment."""

        # Generate ID from stage and bauplatz
        flat_id = self.generate_id(f"{stage}-bauplatz-{bauplatz}-{bautraeger}")

        # Build title
        title = f"{stage} - Bauplatz {bauplatz}: {bautraeger}"

        # Build URL (always the same page)
        url = self.base_url

        # Location is Nordwestbahnhof, Vienna
        location = "Wien - Nordwestbahnhof"

        # Extract additional info about the project
        description_parts = [f"{stage}: Bauplatz {bauplatz} wurde an {bautraeger} vergeben."]

        # Try to find Baufeld info
        baufeld_match = re.search(rf"Bauplatz\s+{bauplatz}[:\s]+\(Baufeld\s+(\d+)\)", section_text)
        if baufeld_match:
            baufeld = baufeld_match.group(1)
            description_parts.append(f"Baufeld: {baufeld}")

        # Try to find planning/architecture info
        planning_match = re.search(
            rf"Bauplatz\s+{bauplatz}[^•]+?Planung:\s*([^•\n]+)", section_text, re.IGNORECASE
        )
        if planning_match:
            planning = planning_match.group(1).strip()[:200]  # Limit length
            description_parts.append(f"Planung: {planning}")

        description = " ".join(description_parts)

        # Determine markers
        markers = []
        markers.append(f"stufe_{stage_num.lower()}")  # e.g., "stufe_i"
        markers.append("nordwestbahnhof")

        # Check project type
        section_lower = section_text.lower()
        if "geförd" in section_lower:
            markers.append("subsidized")
        if "freifinanziert" in section_lower:
            markers.append("free_financed")
        if "gemeindebau" in section_lower:
            markers.append("gemeindebau")

        return Flat(
            id=flat_id,
            title=title,
            url=url,  # type: ignore[arg-type]
            location=location,
            price=None,
            size=None,
            rooms=None,
            description=description,
            image_url=None,
            markers=markers,
            source=self.name,
        )
