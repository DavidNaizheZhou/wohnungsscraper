"""Base scraper class and protocols."""

import hashlib
import logging
import re
from abc import ABC, abstractmethod

import httpx
from bs4 import BeautifulSoup

from wohnung.config import settings
from wohnung.models import Flat


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    def __init__(self) -> None:
        """Initialize the scraper."""
        self.client = httpx.Client(
            timeout=settings.request_timeout,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        )
        self.logger = self._get_logger()

    def _get_logger(self) -> logging.Logger:
        """Get logger for this scraper."""
        return logging.getLogger(f"wohnung.scrapers.{self.name}")

    @property
    def minimum_expected_results(self) -> int:
        """Minimum number of results expected from a healthy scraper.

        Override this in subclasses to set a reasonable threshold.
        Default is 1 (at least one result expected).
        """
        return 1

    @property
    def email_recipients(self) -> list[str] | None:
        """Custom email recipients for this scraper.

        Override this in subclasses to send notifications to specific recipients.
        Returns None to use default recipients (all configured accounts).
        Returns list of email addresses for custom recipients.
        """
        return None

    def check_health(self, results: list[Flat]) -> tuple[str, list[str]]:
        """Check if scraping results are healthy.

        Args:
            results: List of scraped flats

        Returns:
            Tuple of (health_status, warnings)
            health_status: "healthy", "unhealthy", or "failed"
            warnings: List of warning messages
        """
        warnings = []

        # No results at all
        if len(results) == 0:
            return "unhealthy", ["No results found - scraper may need updating"]

        # Below minimum threshold
        if len(results) < self.minimum_expected_results:
            warnings.append(
                f"Only {len(results)} result(s) found, expected at least {self.minimum_expected_results}"
            )
            return "unhealthy", warnings

        # Check for suspicious patterns
        if len(results) == 1:
            warnings.append("Only 1 result found - unusually low")

        return "healthy", warnings

    @property
    @abstractmethod
    def name(self) -> str:
        """Scraper name identifier."""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the scraping target."""
        ...

    @abstractmethod
    def scrape(self) -> list[Flat]:
        """
        Scrape flats from the source.

        Returns:
            List of Flat objects found.
        """
        ...

    def generate_id(self, url: str) -> str:
        """
        Generate a unique ID for a flat based on source and URL.

        Args:
            url: The flat's URL

        Returns:
            Unique identifier string
        """
        hash_input = f"{self.name}:{url}"
        return f"{self.name}-{hashlib.md5(hash_input.encode()).hexdigest()[:16]}"

    def parse_price(self, price_str: str) -> float | None:
        """
        Parse price string to float.

        Args:
            price_str: String containing price information

        Returns:
            Price as float or None if parsing fails
        """
        # Remove common currency symbols and whitespace
        cleaned = re.sub(r"[€$£\s]", "", price_str)

        # Check if it looks like European format (1.200,50) or US format (1,200.50)
        # If there's a comma after the last period, or last comma is followed by 2 digits, it's likely decimal
        if re.search(r",\d{2}$", cleaned):  # European: 1.200,50
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:  # US format: 1,200.50 or simple: 1200
            cleaned = cleaned.replace(",", "")

        match = re.search(r"\d+\.?\d*", cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    def parse_size(self, size_str: str) -> float | None:
        """
        Parse size string to float (square meters).

        Args:
            size_str: String containing size information

        Returns:
            Size in square meters or None if parsing fails
        """
        # Extract number before m², m2, or sqm
        cleaned = size_str.replace(",", ".")
        match = re.search(r"(\d+\.?\d*)\s*(?:m²|m2|sqm)", cleaned, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def parse_rooms(self, rooms_str: str) -> float | None:
        """
        Parse rooms string to float.

        Args:
            rooms_str: String containing room information

        Returns:
            Number of rooms or None if parsing fails
        """
        cleaned = rooms_str.replace(",", ".")
        match = re.search(r"(\d+\.?\d*)", cleaned)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def fetch_html(self, url: str) -> BeautifulSoup:
        """
        Fetch and parse HTML from a URL.

        Args:
            url: URL to fetch

        Returns:
            BeautifulSoup object

        Raises:
            httpx.HTTPError: If request fails
        """
        response = self.client.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def __enter__(self) -> "BaseScraper":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - cleanup resources."""
        self.client.close()

    def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        self.client.close()
