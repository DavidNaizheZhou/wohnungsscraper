"""Main entry point for the scraper."""

import sys
from collections import defaultdict

from wohnung.config import settings
from wohnung.models import Flat
from wohnung.scrapers import deduplicate_flats, get_scrapers, run_all_scrapers
from wohnung.site_storage import SiteStorage


def main(dry_run: bool = False) -> int:
    """
    Main scraping function.

    Args:
        dry_run: If True, don't send emails

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("🚀 Starting flat scraping...")
    print("=" * 60)

    try:
        # Initialize new storage system
        storage = SiteStorage(data_dir=settings.data_dir)

        # Migrate from legacy if exists
        legacy_file = settings.data_dir / "flats.json"
        if legacy_file.exists():
            print("\n📦 Migrating from legacy storage...")
            storage.migrate_from_legacy(legacy_file)
            # Rename legacy file to keep as backup
            legacy_file.rename(settings.data_dir / "flats.json.backup")
            print("   ✅ Migration complete")

        # Run all scrapers
        results = run_all_scrapers()

        # Organize flats by source site
        flats_by_site: dict[str, list[Flat]] = defaultdict(list)
        all_flats = []

        for result in results:
            all_flats.extend(result.flats)
            for flat in result.flats:
                site = flat.source or "unknown"
                flats_by_site[site].append(flat)

        print("\n📊 Summary:")
        print(f"   Total flats found: {len(all_flats)}")

        # Deduplicate
        unique_flats = deduplicate_flats(all_flats)
        print(f"   Unique flats: {len(unique_flats)}")

        # Process each site and track detailed changes
        from wohnung.change_detector import ApartmentChange

        all_changes: list[ApartmentChange] = []

        for site_name, flats in flats_by_site.items():
            # Deduplicate within site
            site_flats = deduplicate_flats(flats)

            # Save and get detailed changes
            changes = storage.save_apartments_with_changes(site_name, site_flats)

            if changes:
                new = [c for c in changes if c.change_type == "new"]
                updated = [c for c in changes if c.change_type == "updated"]
                removed = [c for c in changes if c.change_type == "removed"]

                print(f"\n   📍 {site_name}:")
                msg = f"      New: {len(new)}, "
                msg += f"Updated: {len(updated)}, "
                msg += f"Removed: {len(removed)}"
                print(msg)

                all_changes.extend(changes)

        # Count changes
        new_count = len([c for c in all_changes if c.change_type == "new"])
        updated_count = len([c for c in all_changes if c.change_type == "updated"])
        removed_count = len([c for c in all_changes if c.change_type == "removed"])

        print(f"\n   Total NEW: {new_count}")
        print(f"   Total UPDATED: {updated_count}")
        print(f"   Total REMOVED: {removed_count}")

        # Check scraper health
        unhealthy_scrapers = [r for r in results if r.needs_attention]
        healthy_scrapers = [r for r in results if r.is_healthy]

        print("\n🏥 Scraper Health:")
        print(f"   Healthy: {len(healthy_scrapers)}/{len(results)}")
        if unhealthy_scrapers:
            print(f"   ⚠️  Need attention: {len(unhealthy_scrapers)}")
            for result in unhealthy_scrapers:
                print(f"      - {result.source}: {result.health_status}")

        # Separate changes and results by scraper type
        # Special scrapers (like nordwestbahnhof) have custom email recipients
        scrapers = get_scrapers()  # Get scraper instances to check email_recipients
        special_changes = {}  # source -> changes
        special_results = {}  # source -> result
        regular_changes = []
        regular_results = []

        for scraper_instance in scrapers:
            if scraper_instance.email_recipients is not None:
                # Special scraper with custom email recipients
                source = scraper_instance.name
                source_changes = [c for c in all_changes if c.apartment.source == source]
                source_result = next((r for r in results if r.source == source), None)

                if source_changes or (source_result and source_result.needs_attention):
                    special_changes[source] = source_changes
                    if source_result:
                        special_results[source] = source_result
            else:
                # Regular scraper - goes to consolidated email
                source = scraper_instance.name
                source_changes = [c for c in all_changes if c.apartment.source == source]
                source_result = next((r for r in results if r.source == source), None)

                regular_changes.extend(source_changes)
                if source_result:
                    regular_results.append(source_result)

        # Send consolidated email for regular scrapers
        # Only send if there are actual apartment changes (new or updated)
        regular_new = len([c for c in regular_changes if c.change_type == "new"])
        regular_updated = len([c for c in regular_changes if c.change_type == "updated"])
        regular_unhealthy = [r for r in regular_results if r.needs_attention]

        if regular_new > 0 or regular_updated > 0:
            print("\n📧 Sending consolidated email notification...")
            from wohnung.email import send_consolidated_email

            email_sent = send_consolidated_email(
                changes=regular_changes,
                scraper_results=regular_results,
                dry_run=dry_run,
            )

            if email_sent:
                print("✅ Email sent successfully")
            else:
                print("⚠️  Email sending failed")
        else:
            print("\n✅ No changes detected, no email sent")
            if regular_unhealthy:
                print(
                    f"   Note: {len(regular_unhealthy)} scraper(s) unhealthy but no apartment changes"
                )

        # Send separate emails for special scrapers
        # Only send if there are actual apartment changes
        for source, source_changes in special_changes.items():
            source_result = special_results.get(source)

            # Check if there are any new or updated apartments
            source_new = len([c for c in source_changes if c.change_type == "new"])
            source_updated = len([c for c in source_changes if c.change_type == "updated"])

            if source_new == 0 and source_updated == 0:
                print(f"\n✅ {source}: No changes detected, no email sent")
                continue

            print(f"\n📧 Sending special email for {source}...")
            from wohnung.email import send_scraper_specific_email

            # Get the scraper instance to get custom recipients
            scraper_inst = next((s for s in scrapers if s.name == source), None)
            if not scraper_inst:
                print(f"⚠️  Could not find scraper instance for {source}")
                continue

            # Check if scraper has custom recipients
            if not scraper_inst.email_recipients:
                print(f"⚠️  No email recipients configured for {source}")
                continue

            # Check if we have result for this scraper
            if not source_result:
                print(f"⚠️  No result available for {source}")
                continue

            email_sent = send_scraper_specific_email(
                scraper_name=source,
                changes=source_changes,
                scraper_result=source_result,
                recipients=scraper_inst.email_recipients,
                dry_run=dry_run,
            )

            if email_sent:
                print(f"✅ Email sent to {', '.join(scraper_inst.email_recipients)}")
            else:
                print("⚠️  Email sending failed")

        # Print stats per site
        print("\n📈 Storage stats:")
        for site_name in storage.list_sites():
            stats = storage.get_site_stats(site_name)
            print(f"   {site_name}: {stats['active']} active, " f"{stats['removed']} removed")

        print("\n" + "=" * 60)
        print("✅ Scraping completed successfully")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Check for --dry-run flag
    dry_run = "--dry-run" in sys.argv
    exit_code = main(dry_run=dry_run)
    sys.exit(exit_code)
