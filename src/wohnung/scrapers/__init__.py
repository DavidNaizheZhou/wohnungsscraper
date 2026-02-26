"""Scraper orchestration and management."""

import traceback
from datetime import datetime
from pathlib import Path

from wohnung.models import Flat, ScraperResult
from wohnung.scrapers.arwag import ArwagScraper
from wohnung.scrapers.athome import AthomeScraper
from wohnung.scrapers.base import BaseScraper
from wohnung.scrapers.bwsg import BwsgScraper
from wohnung.scrapers.ebg import EbgScraper
from wohnung.scrapers.egw import EgwScraper
from wohnung.scrapers.familienwohnbau import FamilienwohnbauScraper
from wohnung.scrapers.frieden import FriedenScraper
from wohnung.scrapers.migra import MigraScraper
from wohnung.scrapers.mischek import MischekScraper
from wohnung.scrapers.nhg import NhgScraper
from wohnung.scrapers.nordwestbahnhof import NordwestbahnhofScraper
from wohnung.scrapers.oesw import OeswScraper
from wohnung.scrapers.oevw import OEVWScraper
from wohnung.scrapers.sozialbau import SozialbauScraper
from wohnung.scrapers.wohnberatung_wien import WohnberatungWienScraper

# Register all scrapers here
SCRAPERS: list[type[BaseScraper]] = [
    OEVWScraper,
    WohnberatungWienScraper,
    MigraScraper,
    ArwagScraper,
    EgwScraper,
    BwsgScraper,
    AthomeScraper,
    MischekScraper,
    NhgScraper,
    FamilienwohnbauScraper,
    FriedenScraper,
    OeswScraper,
    EbgScraper,
    NordwestbahnhofScraper,
    # SozialbauScraper,  # Disabled: scraper not working properly
    # Add more scrapers as you implement them
]


def get_scrapers() -> list[BaseScraper]:
    """
    Get instances of all registered scrapers.

    Returns:
        List of scraper instances
    """
    return [scraper_class() for scraper_class in SCRAPERS]


def _write_scraper_log(
    log_dir: Path,
    name: str,
    started_at: datetime,
    flats: list[Flat],
    health_status: str,
    warnings: list[str],
    errors: list[str],
) -> None:
    """Write/overwrite a per-scraper log file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    finished_at = datetime.now()
    duration = (finished_at - started_at).total_seconds()

    lines: list[str] = [
        f"scraper:    {name}",
        f"started:    {started_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"finished:   {finished_at.strftime('%Y-%m-%d %H:%M:%S')} ({duration:.1f}s)",
        f"status:     {health_status.upper()}",
        f"results:    {len(flats)} Wohnungen gefunden",
    ]

    if warnings:
        lines.append("")
        lines.append("warnings:")
        for w in warnings:
            lines.append(f"  - {w}")

    if errors:
        lines.append("")
        lines.append("errors:")
        for e in errors:
            lines.append(f"  - {e}")

    if flats:
        lines.append("")
        lines.append("flats:")
        for flat in flats:
            location = f" | {flat.location}" if flat.location else ""
            price = f" | {flat.price}" if flat.price else ""
            lines.append(f"  [{flat.id}] {flat.title}{location}{price}")
            lines.append(f"    {flat.url}")

    log_file = log_dir / f"{name}.log"
    log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_all_scrapers() -> list[ScraperResult]:
    """
    Run all registered scrapers and collect results.

    Returns:
        List of ScraperResult objects with health status
    """
    from wohnung.config import settings

    results: list[ScraperResult] = []

    for scraper in get_scrapers():
        print(f"🔍 Running scraper: {scraper.name}")
        started_at = datetime.now()

        try:
            with scraper:
                flats = scraper.scrape()

                # Check health of results
                health_status, warnings = scraper.check_health(flats)

                # Print status with appropriate emoji
                if health_status == "healthy":
                    print(f"✅ Found {len(flats)} flats from {scraper.name}")
                elif health_status == "unhealthy":
                    print(f"⚠️  Found {len(flats)} flats from {scraper.name} (needs attention)")
                    for warning in warnings:
                        print(f"    ⚠️  {warning}")
                else:
                    print(f"❌ Scraper {scraper.name} failed")

                _write_scraper_log(
                    log_dir=settings.log_dir,
                    name=scraper.name,
                    started_at=started_at,
                    flats=flats,
                    health_status=health_status,
                    warnings=warnings,
                    errors=[],
                )

                results.append(
                    ScraperResult(
                        flats=flats,
                        source=scraper.name,
                        health_status=health_status,
                        warnings=warnings,
                    )
                )
        except Exception as e:
            error_msg = f"Error running {scraper.name}: {e!s}"
            tb = traceback.format_exc()
            print(f"❌ {error_msg}")

            _write_scraper_log(
                log_dir=settings.log_dir,
                name=scraper.name,
                started_at=started_at,
                flats=[],
                health_status="failed",
                warnings=[],
                errors=[error_msg, tb],
            )

            results.append(
                ScraperResult(
                    flats=[],
                    source=scraper.name,
                    errors=[error_msg],
                    health_status="failed",
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
