"""Email sending functionality."""

from wohnung.config import settings
from wohnung.models import Flat

try:
    from resend import Resend  # type: ignore[import-not-found, attr-defined]

    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    Resend = None  # type: ignore[assignment]


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

    plural = "s" if len(flats) != 1 else ""
    html += f"        <h1>🏠 {len(flats)} New Flat{plural} Found!</h1>\n"

    for flat in flats:
        html += f"""
        <div class="flat">
            {f'<img class="flat-image" src="{flat.image_url}" alt="{flat.title}" />' if flat.image_url else ''}
            <div class="flat-title">{flat.title}</div>
            <div class="flat-details">
"""

        if flat.price:
            html += f'                <span class="flat-detail"><strong>💰 Price:</strong> €{flat.price:.0f}</span>\n'
        if flat.size:
            html += f'                <span class="flat-detail"><strong>📐 Size:</strong> {flat.size}m²</span>\n'
        if flat.rooms:
            html += f'                <span class="flat-detail"><strong>🚪 Rooms:</strong> {flat.rooms}</span>\n'

        html += f"""            </div>
            <div class="flat-detail"><strong>📍 Location:</strong> {flat.location}</div>
            {f'<p style="color: #666; margin-top: 12px;">{flat.description[:200]}...</p>' if flat.description else ''}
            <a class="flat-link" href="{flat.url}" target="_blank">View Listing →</a>
            <div class="meta">
                Source: {flat.source} | Found: {flat.found_at.strftime('%Y-%m-%d %H:%M')}
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

    Args:
        flats: List of flats to send
        dry_run: If True, only print what would be sent

    Returns:
        True if email was sent successfully

    Raises:
        RuntimeError: If Resend is not installed
        ValueError: If no API key is configured
    """
    if len(flats) == 0:
        print("📭 No new flats to send")
        return True

    if dry_run:
        print(f"📧 [DRY RUN] Would send email about {len(flats)} flats to: {settings.email_recipients}")
        return True

    if not RESEND_AVAILABLE or Resend is None:
        raise RuntimeError("Resend package is not installed. Install with: pip install resend")

    if not settings.resend_api_key:
        raise ValueError("RESEND_API_KEY environment variable is not set")

    resend = Resend(api_key=settings.resend_api_key)

    plural = "s" if len(flats) != 1 else ""
    subject = f"🏠 {len(flats)} New Flat{plural} Found!"
    html_content = generate_email_html(flats)

    try:
        params = {
            "from": settings.email_from,
            "to": settings.email_recipients,
            "subject": subject,
            "html": html_content,
        }

        response = resend.emails.send(params)
        print(f"📧 Email sent successfully to {', '.join(settings.email_recipients)}")
        print(f"📨 Email ID: {response.get('id', 'N/A')}")
        return True

    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


__all__ = ["generate_email_html", "send_email"]
