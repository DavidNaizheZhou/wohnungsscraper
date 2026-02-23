"""Main entry point for the scraper."""

import sys
from collections import defaultdict

from wohnung.config import settings
from wohnung.email import send_changes_email
from wohnung.models import Flat
from wohnung.scrapers import deduplicate_flats, run_all_scrapers
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

        # Send enhanced email for changes
        if new_count > 0 or updated_count > 0:
            print("\n📧 Sending enhanced email notification...")
            email_sent = send_changes_email(all_changes, dry_run=dry_run, group_by_site=True)

            if email_sent:
                print("✅ Email sent successfully")
            else:
                print("⚠️  Email sending failed")
        else:
            print("\n✅ No new or updated apartments found")

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
