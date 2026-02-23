"""Email sending functionality."""

from collections import defaultdict

from wohnung.change_detector import ApartmentChange
from wohnung.config import settings
from wohnung.models import Flat

try:
    import resend  # type: ignore[import-untyped]

    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    resend = None  # type: ignore[assignment]


def generate_email_html(flats: list[Flat]) -> str:
    """
    Generate HTML email content for new flats.

    Args:
        flats: List of flats to include in email

    Returns:
        HTML string
    """
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
               line-height: 1.6; color: #333; background: #f5f5f5; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: white;
                     border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; margin-bottom: 30px; }
        .flat { border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;
                margin-bottom: 20px; transition: transform 0.2s; }
        .flat:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .flat-title { font-size: 20px; font-weight: 600; margin-bottom: 12px; color: #2c3e50; }
        .flat-details { display: flex; gap: 20px; margin-bottom: 12px; flex-wrap: wrap; }
        .flat-detail { color: #666; font-size: 14px; }
        .flat-detail strong { color: #2c3e50; }
        .flat-link { display: inline-block; background: #3498db; color: white !important;
                     padding: 12px 24px; text-decoration: none; border-radius: 6px;
                     margin-top: 12px; font-weight: 500; }
        .flat-link:hover { background: #2980b9; }
        .flat-image { max-width: 100%; height: auto; border-radius: 6px; margin-bottom: 12px; }
        .meta { font-size: 12px; color: #999; margin-top: 12px; padding-top: 12px;
                border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
"""

    plural = "en" if len(flats) != 1 else "e"
    html += f"        <h1>🏠 {len(flats)} Neu{plural} Wohnung{plural} gefunden!</h1>\n"

    for flat in flats:
        markers_html = ""
        if flat.markers:
            markers_html = '<div style="margin-bottom: 12px;">'
            for marker in flat.markers:
                markers_html += f'<span class="badge" style="background: #16a085; color: white; display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-right: 8px;">🏷️ {marker}</span>'
            markers_html += "</div>"

        html += f"""
        <div class="flat">
            {f'<img class="flat-image" src="{flat.image_url}" alt="{flat.title}" />' if flat.image_url else ''}
            <div class="flat-title">{flat.title}</div>
            {markers_html}
            <div class="flat-details">
"""

        if flat.price:
            html += f'                <span class="flat-detail"><strong>💰 Preis:</strong> €{flat.price:.0f}</span>\n'
        if flat.size:
            html += f'                <span class="flat-detail"><strong>📐 Größe:</strong> {flat.size}m²</span>\n'
        if flat.rooms:
            html += f'                <span class="flat-detail"><strong>🚪 Zimmer:</strong> {flat.rooms}</span>\n'

        html += f"""            </div>
            <div class="flat-detail"><strong>📍 Standort:</strong> {flat.location}</div>
            {f'<p style="color: #666; margin-top: 12px;">{flat.description[:200]}...</p>' if flat.description else ''}
            <a class="flat-link" href="{flat.url}" target="_blank">Anzeige ansehen →</a>
            <div class="meta">
                Quelle: {flat.source} | Gefunden: {flat.found_at.strftime('%d.%m.%Y %H:%M')}
            </div>
        </div>
"""

    html += """    </div>
</body>
</html>
"""
    return html


def send_email(flats: list[Flat], dry_run: bool = False) -> bool:
    """
    Send email notification for new flats.

    Supports multiple Resend accounts:
    - Single account: RESEND_API_KEY + EMAIL_TO
    - Multiple accounts: RESEND_API_KEY_1 + EMAIL_TO_1, RESEND_API_KEY_2 + EMAIL_TO_2, etc.

    Args:
        flats: List of flats to send
        dry_run: If True, only print what would be sent

    Returns:
        True if all emails were sent successfully

    Raises:
        RuntimeError: If Resend is not installed
        ValueError: If no API key is configured
    """
    if len(flats) == 0:
        print("📭 No new flats to send")
        return True

    accounts = settings.email_accounts
    if not accounts:
        raise ValueError(
            "No email accounts configured. Set RESEND_API_KEY + EMAIL_TO or numbered pairs."
        )

    if dry_run:
        print(
            f"📧 [DRY RUN] Would send email about {len(flats)} flats to: {settings.email_recipients}"
        )
        return True

    if not RESEND_AVAILABLE or resend is None:
        raise RuntimeError("Resend package is not installed. Install with: pip install resend")

    plural = "s" if len(flats) != 1 else ""
    subject = f"🏠 {len(flats)} Neu{plural} Wohnung{plural} gefunden!"
    html_content = generate_email_html(flats)

    all_success = True

    # Send email from each account to its registered email
    for api_key, recipient_email in accounts:
        try:
            # Set API key for this account
            resend.api_key = api_key

            params = {
                "from": settings.email_from,
                "to": [recipient_email],
                "subject": subject,
                "html": html_content,
            }

            response = resend.Emails.send(params)
            print(f"📧 Email sent to {recipient_email}")
            print(f"   Email ID: {response.get('id', 'N/A')}")

        except Exception as e:
            print(f"❌ Error sending email to {recipient_email}: {e}")
            all_success = False

    return all_success


__all__ = [
    "generate_changes_email_html",
    "generate_email_html",
    "preview_changes_email",
    "send_changes_email",
    "send_email",
]


def _get_html_styles() -> str:
    """Get CSS styles for email templates."""
    return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
            margin: 0;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
        }
        .summary {
            background: #ecf0f1;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 25px;
            font-size: 14px;
        }
        .summary-item {
            display: inline-block;
            margin-right: 20px;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }
        .badge-new {
            background: #2ecc71;
            color: white;
        }
        .badge-updated {
            background: #3498db;
            color: white;
        }
        .badge-removed {
            background: #95a5a6;
            color: white;
        }
        .badge-price-drop {
            background: #e74c3c;
            color: white;
        }
        .badge-price-up {
            background: #f39c12;
            color: white;
        }
        .badge-marker-high {
            background: #9b59b6;
            color: white;
        }
        .badge-marker-medium {
            background: #16a085;
            color: white;
        }
        .badge-marker-low {
            background: #7f8c8d;
            color: white;
        }
        .flat {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            transition: transform 0.2s;
            background: white;
        }
        .flat:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .flat-header {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
        }
        .flat-title {
            font-size: 20px;
            font-weight: 600;
            color: #2c3e50;
            flex: 1;
        }
        .flat-details {
            display: flex;
            gap: 20px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }
        .flat-detail {
            color: #666;
            font-size: 14px;
        }
        .flat-detail strong {
            color: #2c3e50;
        }
        .change-highlight {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 12px;
            margin: 12px 0;
            border-radius: 4px;
        }
        .change-item {
            margin: 6px 0;
            font-size: 14px;
        }
        .change-arrow {
            color: #666;
            font-weight: bold;
            margin: 0 8px;
        }
        .old-value {
            text-decoration: line-through;
            color: #999;
        }
        .new-value {
            color: #27ae60;
            font-weight: 600;
        }
        .flat-link {
            display: inline-block;
            background: #3498db;
            color: white !important;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 6px;
            margin-top: 12px;
            font-weight: 500;
        }
        .flat-link:hover {
            background: #2980b9;
        }
        .flat-image {
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            margin-bottom: 12px;
        }
        .meta {
            font-size: 12px;
            color: #999;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #eee;
        }
        .site-section {
            margin-bottom: 30px;
        }
        .site-header {
            background: #34495e;
            color: white;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 15px;
            font-weight: 600;
        }
    """


def _format_price_change(old_price: float, new_price: float) -> str:
    """Format price change with indicator."""
    if new_price < old_price:
        diff = old_price - new_price
        percentage = (diff / old_price) * 100
        return f'<span class="badge badge-price-drop">💰 Price Drop: -{percentage:.1f}%</span>'
    if new_price > old_price:
        diff = new_price - old_price
        percentage = (diff / old_price) * 100
        return f'<span class="badge badge-price-up">📈 Price Up: +{percentage:.1f}%</span>'
    return ""


def _render_change_highlight(change: ApartmentChange) -> str:
    """Render change highlights for an updated apartment."""
    if not change.changes:
        return ""

    html = '        <div class="change-highlight">\n'
    html += "            <strong>📝 Was hat sich geändert:</strong>\n"

    for field, (old_val, new_val) in change.changes.items():
        if field == "price":
            html += '            <div class="change-item">'
            html += f'💰 Preis: <span class="old-value">€{old_val:.0f}</span>'
            html += '<span class="change-arrow">→</span>'
            html += f'<span class="new-value">€{new_val:.0f}</span>'
            html += "</div>\n"
        elif field == "size":
            html += '            <div class="change-item">'
            html += f'📐 Größe: <span class="old-value">{old_val}m²</span>'
            html += '<span class="change-arrow">→</span>'
            html += f'<span class="new-value">{new_val}m²</span>'
            html += "</div>\n"
        elif field == "rooms":
            html += '            <div class="change-item">'
            html += f'🚪 Zimmer: <span class="old-value">{old_val}</span>'
            html += '<span class="change-arrow">→</span>'
            html += f'<span class="new-value">{new_val}</span>'
            html += "</div>\n"
        elif field == "title":
            html += '            <div class="change-item">📝 Titel wurde aktualisiert</div>\n'
        elif field == "description":
            html += (
                '            <div class="change-item">📄 Beschreibung wurde aktualisiert</div>\n'
            )
        else:
            html += f'            <div class="change-item">{field.title()}: '
            html += f'<span class="old-value">{old_val}</span>'
            html += '<span class="change-arrow">→</span>'
            html += f'<span class="new-value">{new_val}</span>'
            html += "</div>\n"

    html += "        </div>\n"
    return html


def _render_apartment_card(  # noqa: C901, PLR0912
    change: ApartmentChange, show_changes: bool = True
) -> str:
    """Render an apartment card with optional change highlights."""
    data = change.apartment_data
    html = '        <div class="flat">\n'

    # Header with badges
    html += '            <div class="flat-header">\n'
    if change.change_type == "new":
        html += '                <span class="badge badge-new">🆕 NEW</span>\n'
    elif change.change_type == "updated":
        html += '                <span class="badge badge-updated">📝 UPDATED</span>\n'
        # Add price change indicator
        if "price" in change.changes:
            old_price, new_price = change.changes["price"]
            html += f"                {_format_price_change(old_price, new_price)}\n"

    # Add marker badges if present
    markers = data.get("markers", [])
    if markers:
        for marker in markers:
            # Use medium priority styling by default
            html += f'                <span class="badge badge-marker-medium">🏷️ {marker}</span>\n'

    html += "            </div>\n"

    # Image
    if data.get("image_url"):
        html += f'            <img class="flat-image" src="{data["image_url"]}" alt="{data.get("title", "Apartment")}" />\n'

    # Title
    html += f'            <div class="flat-title">{data.get("title", "Unknown")}</div>\n'

    # Change highlights (for updates)
    if show_changes and change.change_type == "updated":
        html += _render_change_highlight(change)

    # Details
    html += '            <div class="flat-details">\n'
    if data.get("price"):
        html += f'                <span class="flat-detail"><strong>💰 Preis:</strong> €{data["price"]:.0f}</span>\n'
    if data.get("size"):
        html += f'                <span class="flat-detail"><strong>📐 Größe:</strong> {data["size"]}m²</span>\n'
    if data.get("rooms"):
        html += f'                <span class="flat-detail"><strong>🚪 Zimmer:</strong> {data["rooms"]}</span>\n'
    html += "            </div>\n"

    if data.get("location"):
        html += f'            <div class="flat-detail"><strong>📍 Standort:</strong> {data["location"]}</div>\n'

    # Description
    if data.get("description"):
        desc = data["description"][:200]
        html += f'            <p style="color: #666; margin-top: 12px;">{desc}...</p>\n'

    # Link
    if data.get("url"):
        html += f'            <a class="flat-link" href="{data["url"]}" target="_blank">Anzeige ansehen →</a>\n'

    # Meta
    source = data.get("source", "Unbekannt")
    timestamp = change.timestamp.strftime("%d.%m.%Y %H:%M")
    html += '            <div class="meta">\n'
    html += f"                Quelle: {source} | Erkannt: {timestamp}\n"
    html += "            </div>\n"

    html += "        </div>\n"
    return html


def generate_changes_email_html(  # noqa: C901, PLR0912
    changes: list[ApartmentChange],
    group_by_site: bool = True,
    include_removed: bool = False,
) -> str:
    """Generate HTML email content for apartment changes.

    Args:
        changes: List of apartment changes
        group_by_site: Whether to group apartments by site
        include_removed: Whether to include removed apartments

    Returns:
        HTML string
    """
    # Filter changes
    if not include_removed:
        changes = [c for c in changes if c.change_type != "removed"]

    new_changes = [c for c in changes if c.change_type == "new"]
    updated_changes = [c for c in changes if c.change_type == "updated"]
    removed_changes = [c for c in changes if c.change_type == "removed"]

    # Start HTML
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>"""
    html += _get_html_styles()
    html += """
    </style>
</head>
<body>
    <div class="container">
"""

    # Title
    total = len(new_changes) + len(updated_changes)
    html += f"        <h1>🏠 {total} Wohnungs-Update{'s' if total != 1 else ''}</h1>\n"

    # Summary
    html += '        <div class="summary">\n'
    if new_changes:
        html += f'            <span class="summary-item">🆕 <strong>{len(new_changes)}</strong> Neu</span>\n'
    if updated_changes:
        html += f'            <span class="summary-item">📝 <strong>{len(updated_changes)}</strong> Aktualisiert</span>\n'
    if removed_changes and include_removed:
        html += f'            <span class="summary-item">🗑️ <strong>{len(removed_changes)}</strong> Entfernt</span>\n'
    html += "        </div>\n"

    if group_by_site:
        # Group by site
        changes_by_site: dict[str, list[ApartmentChange]] = defaultdict(list)
        for change in changes:
            site = change.apartment_data.get("source", "Unknown")
            changes_by_site[site].append(change)

        # Render each site
        for site, site_changes in sorted(changes_by_site.items()):
            site_new = [c for c in site_changes if c.change_type == "new"]
            site_updated = [c for c in site_changes if c.change_type == "updated"]

            html += '        <div class="site-section">\n'
            html += f'            <div class="site-header">📍 {site}</div>\n'

            # New apartments
            if site_new:
                html += "            <h2>🆕 Neue Wohnungen</h2>\n"
                for change in site_new:
                    html += _render_apartment_card(change, show_changes=False)

            # Updated apartments
            if site_updated:
                html += "            <h2>📝 Aktualisierte Wohnungen</h2>\n"
                for change in site_updated:
                    html += _render_apartment_card(change, show_changes=True)

            html += "        </div>\n"
    else:
        # Render without grouping
        if new_changes:
            html += "        <h2>🆕 Neue Wohnungen</h2>\n"
            for change in new_changes:
                html += _render_apartment_card(change, show_changes=False)

        if updated_changes:
            html += "        <h2>📝 Aktualisierte Wohnungen</h2>\n"
            for change in updated_changes:
                html += _render_apartment_card(change, show_changes=True)

    # Footer
    html += """    </div>
</body>
</html>
"""
    return html


def send_changes_email(
    changes: list[ApartmentChange],
    dry_run: bool = False,
    group_by_site: bool = True,
    include_removed: bool = False,
) -> bool:
    """Send email notification for apartment changes.

    Supports multiple Resend accounts:
    - Single account: RESEND_API_KEY + EMAIL_TO
    - Multiple accounts: RESEND_API_KEY_1 + EMAIL_TO_1, RESEND_API_KEY_2 + EMAIL_TO_2, etc.

    Args:
        changes: List of apartment changes
        dry_run: If True, only print what would be sent
        group_by_site: Whether to group apartments by site
        include_removed: Whether to include removed apartments

    Returns:
        True if all emails were sent successfully

    Raises:
        RuntimeError: If Resend is not installed
        ValueError: If no API key is configured
    """
    # Filter significant changes
    significant = [c for c in changes if c.change_type in ("new", "updated")]

    if not significant:
        print("📭 No significant changes to notify about")
        return True

    new_count = len([c for c in significant if c.change_type == "new"])
    updated_count = len([c for c in significant if c.change_type == "updated"])

    accounts = settings.email_accounts
    if not accounts:
        raise ValueError(
            "No email accounts configured. Set RESEND_API_KEY + EMAIL_TO or numbered pairs."
        )

    if dry_run:
        print(
            f"📧 [DRY RUN] Would send email about {new_count} new and {updated_count} updated apartments"
        )
        print(f"    Recipients: {settings.email_recipients}")
        return True

    if not RESEND_AVAILABLE or resend is None:
        raise RuntimeError("Resend package is not installed. Install with: pip install resend")

    # Generate subject
    parts = []
    if new_count:
        parts.append(f"{new_count} neue")
    if updated_count:
        parts.append(f"{updated_count} aktualisierte")

    subject = f"🏠 {' und '.join(parts).capitalize()} Wohnung{'en' if len(significant) > 1 else ''}"

    # Generate HTML
    html_content = generate_changes_email_html(
        changes, group_by_site=group_by_site, include_removed=include_removed
    )

    all_success = True

    # Send email from each account to its registered email
    for api_key, recipient_email in accounts:
        try:
            # Set API key for this account
            resend.api_key = api_key

            params = {
                "from": settings.email_from,
                "to": [recipient_email],
                "subject": subject,
                "html": html_content,
            }

            response = resend.Emails.send(params)
            print(f"📧 Email sent to {recipient_email}")
            print(f"   Email ID: {response.get('id', 'N/A')}")

        except Exception as e:
            print(f"❌ Error sending email to {recipient_email}: {e}")
            all_success = False

    return all_success


def preview_changes_email(
    changes: list[ApartmentChange],
    output_file: str = "email_preview.html",
    group_by_site: bool = True,
) -> str:
    """Generate and save email preview to a file.

    Args:
        changes: List of apartment changes
        output_file: Path to save HTML file
        group_by_site: Whether to group apartments by site

    Returns:
        Path to generated HTML file
    """
    html = generate_changes_email_html(changes, group_by_site=group_by_site)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"📄 Email preview saved to: {output_file}")
    return output_file
