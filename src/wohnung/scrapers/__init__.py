"""Scraper orchestration and management."""

from wohnung.models import Flat, ScraperResult
from wohnung.scrapers.base import BaseScraper
from wohnung.scrapers.example import ExampleScraper
from wohnung.scrapers.oevw import OEVWScraper

# Register all scrapers here
SCRAPERS: list[type[BaseScraper]] = [
    ExampleScraper,
    OEVWScraper,
    # Add more scrapers as you implement them
]


def get_scrapers() -> list[BaseScraper]:
    """
    Get instances of all registered scrapers.

    Returns:
        List of scraper instances
    """
    return [scraper_class() for scraper_class in SCRAPERS]


def run_all_scrapers() -> list[ScraperResult]:
    """
    Run all registered scrapers and collect results.

    Returns:
        List of ScraperResult objects
    """
    results: list[ScraperResult] = []

    for scraper in get_scrapers():
        print(f"🔍 Running scraper: {scraper.name}")

        try:
            with scraper:
                flats = scraper.scrape()
                print(f"✅ Found {len(flats)} flats from {scraper.name}")

                results.append(
                    ScraperResult(
                        flats=flats,
                        source=scraper.name,
                    )
                )
        except Exception as e:
            error_msg = f"Error running {scraper.name}: {e!s}"
            print(f"❌ {error_msg}")
            results.append(
                ScraperResult(
                    flats=[],
                    source=scraper.name,
                    errors=[error_msg],
                )
            )

    return results


def deduplicate_flats(flats: list[Flat]) -> list[Flat]:
    """
    Remove duplicate flats based on their ID.

    Args:
        flats: List of flats that may contain duplicates

    Returns:
        List of unique flats
    """
    seen_ids: set[str] = set()
    unique_flats: list[Flat] = []

    for flat in flats:
        if flat.id not in seen_ids:
            seen_ids.add(flat.id)
            unique_flats.append(flat)

    return unique_flats


__all__ = ["SCRAPERS", "deduplicate_flats", "get_scrapers", "run_all_scrapers"]
