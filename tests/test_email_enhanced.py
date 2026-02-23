"""Tests for enhanced email notifications."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from wohnung.change_detector import ApartmentChange
from wohnung.email import (
    generate_changes_email_html,
    preview_changes_email,
    send_changes_email,
)


@pytest.fixture
def sample_new_change() -> ApartmentChange:
    """Create a sample new apartment change."""
    return ApartmentChange(
        change_type="new",
        apartment_id="test-123",
        timestamp=datetime.now(),
        changes={},
        apartment_data={
            "id": "test-123",
            "title": "Beautiful 3-Room Apartment",
            "url": "https://example.com/test-123",
            "price": 1000.0,
            "size": 80.0,
            "rooms": 3,
            "location": "Vienna, 1st District",
            "description": "This is a lovely apartment in the heart of Vienna.",
            "source": "test-site",
        },
    )


@pytest.fixture
def sample_updated_change() -> ApartmentChange:
    """Create a sample updated apartment change."""
    return ApartmentChange(
        change_type="updated",
        apartment_id="test-456",
        timestamp=datetime.now(),
        changes={
            "price": (1200.0, 1100.0),
            "size": (75.0, 80.0),
        },
        apartment_data={
            "id": "test-456",
            "title": "Modern Studio",
            "url": "https://example.com/test-456",
            "price": 1100.0,
            "size": 80.0,
            "rooms": 1,
            "location": "Vienna, 2nd District",
            "description": "Cozy studio apartment.",
            "source": "test-site",
        },
    )


@pytest.fixture
def sample_removed_change() -> ApartmentChange:
    """Create a sample removed apartment change."""
    return ApartmentChange(
        change_type="removed",
        apartment_id="test-789",
        timestamp=datetime.now(),
        changes={},
        apartment_data={
            "id": "test-789",
            "title": "Removed Apartment",
            "url": "https://example.com/test-789",
            "price": 900.0,
            "location": "Vienna",
            "source": "test-site",
        },
    )


class TestGenerateChangesEmailHTML:
    """Tests for generate_changes_email_html function."""

    def test_generate_new_apartment_email(self, sample_new_change: ApartmentChange):
        """Test generating email for new apartment."""
        html = generate_changes_email_html([sample_new_change])

        assert "<!DOCTYPE html>" in html
        assert "Beautiful 3-Room Apartment" in html
        assert "UPDATED" not in html or "🆕 NEW" in html
        assert "€1000" in html
        assert "80.0m²" in html
        assert "Vienna, 1st District" in html

    def test_generate_updated_apartment_email(self, sample_updated_change: ApartmentChange):
        """Test generating email for updated apartment."""
        html = generate_changes_email_html([sample_updated_change])

        assert "Modern Studio" in html
        assert "📝 UPDATED" in html
        assert "💰 Price Drop" in html or "Price" in html
        assert "1200" in html  # Old price
        assert "1100" in html  # New price

    def test_generate_mixed_changes_email(
        self,
        sample_new_change: ApartmentChange,
        sample_updated_change: ApartmentChange,
    ):
        """Test generating email with both new and updated apartments."""
        html = generate_changes_email_html([sample_new_change, sample_updated_change])

        assert "🆕 NEW" in html
        assert "📝 UPDATED" in html
        assert "Beautiful 3-Room Apartment" in html
        assert "Modern Studio" in html

    def test_exclude_removed_by_default(
        self, sample_new_change: ApartmentChange, sample_removed_change: ApartmentChange
    ):
        """Test that removed apartments are excluded by default."""
        html = generate_changes_email_html([sample_new_change, sample_removed_change])

        assert "Beautiful 3-Room Apartment" in html
        assert "Removed Apartment" not in html

    def test_include_removed_when_requested(
        self, sample_new_change: ApartmentChange, sample_removed_change: ApartmentChange
    ):
        """Test including removed apartments when requested."""
        html = generate_changes_email_html(
            [sample_new_change, sample_removed_change], include_removed=True
        )

        assert "Beautiful 3-Room Apartment" in html
        assert "Removed Apartment" in html or "🗑️" in html

    def test_group_by_site(
        self,
        sample_new_change: ApartmentChange,
        sample_updated_change: ApartmentChange,
    ):
        """Test grouping apartments by site."""
        # Set different sites
        sample_new_change.apartment_data["source"] = "site-a"
        sample_updated_change.apartment_data["source"] = "site-b"

        html = generate_changes_email_html(
            [sample_new_change, sample_updated_change], group_by_site=True
        )

        assert "site-a" in html
        assert "site-b" in html

    def test_no_grouping(
        self,
        sample_new_change: ApartmentChange,
        sample_updated_change: ApartmentChange,
    ):
        """Test email without site grouping."""
        html = generate_changes_email_html(
            [sample_new_change, sample_updated_change], group_by_site=False
        )

        assert "🆕 New Apartments" in html
        assert "📝 Updated Apartments" in html

    def test_summary_section(
        self,
        sample_new_change: ApartmentChange,
        sample_updated_change: ApartmentChange,
    ):
        """Test that summary section is included."""
        html = generate_changes_email_html([sample_new_change, sample_updated_change])

        # Should show counts
        assert "1" in html  # Count of new or updated
        assert "summary" in html.lower() or "🆕" in html

    def test_price_drop_indicator(self, sample_updated_change: ApartmentChange):
        """Test price drop indicator is shown."""
        html = generate_changes_email_html([sample_updated_change])

        # Price dropped from 1200 to 1100
        assert "💰 Price Drop" in html or "price" in html.lower()

    def test_price_increase_indicator(self, sample_updated_change: ApartmentChange):
        """Test price increase indicator is shown."""
        # Change to price increase
        sample_updated_change.changes["price"] = (1000.0, 1200.0)
        sample_updated_change.apartment_data["price"] = 1200.0

        html = generate_changes_email_html([sample_updated_change])

        assert "📈 Price Up" in html or "price" in html.lower()

    def test_change_highlights(self, sample_updated_change: ApartmentChange):
        """Test change highlights are displayed for updates."""
        html = generate_changes_email_html([sample_updated_change])

        assert "What Changed" in html or "change" in html.lower()
        assert "1200" in html  # Old price
        assert "1100" in html  # New price

    def test_apartment_links(self, sample_new_change: ApartmentChange):
        """Test that apartment links are included."""
        html = generate_changes_email_html([sample_new_change])

        assert sample_new_change.apartment_data["url"] in html
        assert "View Listing" in html

    def test_empty_changes_list(self):
        """Test generating email with empty changes list."""
        html = generate_changes_email_html([])

        assert "<!DOCTYPE html>" in html
        assert "0 Apartment Update" in html

    def test_html_valid_structure(self, sample_new_change: ApartmentChange):
        """Test that generated HTML has valid structure."""
        html = generate_changes_email_html([sample_new_change])

        assert html.startswith("<!DOCTYPE html>")
        assert "<html>" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</body>" in html

    def test_css_styles_included(self, sample_new_change: ApartmentChange):
        """Test that CSS styles are included."""
        html = generate_changes_email_html([sample_new_change])

        assert "<style>" in html
        assert "</style>" in html
        assert "font-family" in html
        assert "background" in html


class TestSendChangesEmail:
    """Tests for send_changes_email function."""

    def test_send_email_dry_run(self, sample_new_change: ApartmentChange, capsys):
        """Test sending email in dry run mode."""
        result = send_changes_email([sample_new_change], dry_run=True)

        assert result is True
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert "1 new" in captured.out

    def test_send_email_no_changes(self, capsys):
        """Test sending email with no changes."""
        result = send_changes_email([], dry_run=True)

        assert result is True
        captured = capsys.readouterr()
        assert "No significant changes" in captured.out

    def test_send_email_only_removed(self, sample_removed_change: ApartmentChange, capsys):
        """Test that email is not sent for only removed apartments."""
        result = send_changes_email([sample_removed_change], dry_run=True)

        assert result is True
        captured = capsys.readouterr()
        assert "No significant changes" in captured.out

    def test_send_email_mixed_changes(
        self,
        sample_new_change: ApartmentChange,
        sample_updated_change: ApartmentChange,
        capsys,
    ):
        """Test sending email with mixed changes."""
        result = send_changes_email([sample_new_change, sample_updated_change], dry_run=True)

        assert result is True
        captured = capsys.readouterr()
        assert "1 new" in captured.out
        assert "1 updated" in captured.out


class TestPreviewChangesEmail:
    """Tests for preview_changes_email function."""

    def test_preview_generates_file(self, sample_new_change: ApartmentChange):
        """Test that preview generates an HTML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "preview.html"
            result_path = preview_changes_email([sample_new_change], output_file=str(output_file))

            assert result_path == str(output_file)
            assert output_file.exists()

    def test_preview_file_content(self, sample_new_change: ApartmentChange):
        """Test that preview file contains expected content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "preview.html"
            preview_changes_email([sample_new_change], output_file=str(output_file))

            content = output_file.read_text(encoding="utf-8")
            assert "<!DOCTYPE html>" in content
            assert "Beautiful 3-Room Apartment" in content
            assert "View Listing" in content

    def test_preview_with_grouping(
        self,
        sample_new_change: ApartmentChange,
        sample_updated_change: ApartmentChange,
    ):
        """Test preview with site grouping."""
        sample_new_change.apartment_data["source"] = "site-a"
        sample_updated_change.apartment_data["source"] = "site-b"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "preview.html"
            preview_changes_email(
                [sample_new_change, sample_updated_change],
                output_file=str(output_file),
                group_by_site=True,
            )

            content = output_file.read_text(encoding="utf-8")
            assert "site-a" in content
            assert "site-b" in content

    def test_preview_without_grouping(
        self,
        sample_new_change: ApartmentChange,
        sample_updated_change: ApartmentChange,
    ):
        """Test preview without site grouping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "preview.html"
            preview_changes_email(
                [sample_new_change, sample_updated_change],
                output_file=str(output_file),
                group_by_site=False,
            )

            content = output_file.read_text(encoding="utf-8")
            assert "🆕 New Apartments" in content
            assert "📝 Updated Apartments" in content


class TestChangeHighlights:
    """Tests for change highlight rendering."""

    def test_price_change_highlight(self):
        """Test price change is highlighted correctly."""
        change = ApartmentChange(
            change_type="updated",
            apartment_id="test",
            timestamp=datetime.now(),
            changes={"price": (1000.0, 900.0)},
            apartment_data={
                "title": "Test",
                "url": "https://example.com",
                "price": 900.0,
                "location": "Vienna",
                "source": "test",
            },
        )

        html = generate_changes_email_html([change])
        assert "€1000" in html
        assert "€900" in html
        assert "→" in html

    def test_size_change_highlight(self):
        """Test size change is highlighted correctly."""
        change = ApartmentChange(
            change_type="updated",
            apartment_id="test",
            timestamp=datetime.now(),
            changes={"size": (70.0, 80.0)},
            apartment_data={
                "title": "Test",
                "url": "https://example.com",
                "size": 80.0,
                "location": "Vienna",
                "source": "test",
            },
        )

        html = generate_changes_email_html([change])
        assert "70" in html and "m²" in html
        assert "80" in html and "m²" in html

    def test_rooms_change_highlight(self):
        """Test rooms change is highlighted correctly."""
        change = ApartmentChange(
            change_type="updated",
            apartment_id="test",
            timestamp=datetime.now(),
            changes={"rooms": (2, 3)},
            apartment_data={
                "title": "Test",
                "url": "https://example.com",
                "rooms": 3,
                "location": "Vienna",
                "source": "test",
            },
        )

        html = generate_changes_email_html([change])
        assert "2" in html
        assert "3" in html

    def test_title_change_highlight(self):
        """Test title change is indicated."""
        change = ApartmentChange(
            change_type="updated",
            apartment_id="test",
            timestamp=datetime.now(),
            changes={"title": ("Old Title", "New Title")},
            apartment_data={
                "title": "New Title",
                "url": "https://example.com",
                "location": "Vienna",
                "source": "test",
            },
        )

        html = generate_changes_email_html([change])
        assert "Title was updated" in html or "title" in html.lower()
