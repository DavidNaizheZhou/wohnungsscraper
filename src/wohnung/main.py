"""Main entry point for the scraper."""

import sys

from wohnung.email import send_email
from wohnung.scrapers import deduplicate_flats, run_all_scrapers
from wohnung.storage import JSONStorage


def main(dry_run: bool = False, storage_file: str | None = None) -> int:
    """
    Main scraping function.

    Args:
        dry_run: If True, don't send emails
        storage_file: Optional custom path to storage file

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("🚀 Starting flat scraping...")
    print("=" * 60)

    try:
        # Initialize storage
        storage = JSONStorage(storage_file=storage_file)  # type: ignore

        # Run all scrapers
        results = run_all_scrapers()

        # Collect all flats
        all_flats = []
        for result in results:
            all_flats.extend(result.flats)

        print("\n📊 Summary:")
        print(f"   Total flats found: {len(all_flats)}")

        # Deduplicate
        unique_flats = deduplicate_flats(all_flats)
        print(f"   Unique flats: {len(unique_flats)}")

        # Filter new flats
        new_flats = storage.filter_new_flats(unique_flats)
        print(f"   New flats: {len(new_flats)}")

        # Save new flats
        if new_flats:
            saved = storage.save_flats(new_flats)
            print(f"   Saved to storage: {saved}")

            # Send email notification
            print("\n📧 Sending email notification...")
            email_sent = send_email(new_flats, dry_run=dry_run)

            if email_sent:
                print("✅ Email sent successfully")
            else:
                print("⚠️  Email sending failed")
        else:
            print("\n✅ No new flats found")

        # Print stats
        stats = storage.get_stats()
        print("\n📈 Storage stats:")
        print(f"   Total flats in storage: {stats['total_flats']}")
        print(f"   By source: {stats['by_source']}")

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
