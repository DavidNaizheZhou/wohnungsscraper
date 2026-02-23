"""Tests for OEVW scraper."""

import json
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup

from wohnung.models import Flat
from wohnung.scrapers.oevw import OEVWScraper


@pytest.fixture
def oevw_scraper():
    """Create an OEVW scraper instance."""
    return OEVWScraper()


@pytest.fixture
def sample_projects_json():
    """Sample projects data from OEVW website."""
    return [
        {
            "projectstatus": "planning",
            "heading": "Test Project 1",
            "location": "1220 Wien",
            "legalform": "Miete",
            "latitude": 48.229081,
            "longitude": 16.482518,
            "image": '<img src="/assets/thumb/360x240/project123.webp" alt="Test">',
            "url": "/projekte/test-project-1",
        },
        {
            "projectstatus": "selling",
            "heading": "Test Project 2",
            "location": "1020 Wien",
            "legalform": "Eigentum",
            "latitude": 48.225218,
            "longitude": 16.392956,
            "image": '<img src="/assets/thumb/360x240/project456.webp" alt="Test">',
            "url": "/projekte/test-project-2",
        },
        {
            "projectstatus": None,
            "heading": "Test Project 3",
            "location": "3500 Krems",
            "legalform": None,
            "latitude": 48.413378,
            "longitude": 15.633469,
            "image": "",
            "url": "/projekte/test-project-3",
        },
    ]


@pytest.fixture
def sample_html_with_projects(sample_projects_json):
    """Sample HTML with embedded projects JSON."""
    projects_json = json.dumps(sample_projects_json)
    return f"""
<!DOCTYPE html>
<html>
<head>
    <script>var projects = {projects_json};</script>
</head>
<body>
    <h1>OEVW Projects</h1>
</body>
</html>
"""


class TestOEVWScraper:
    """Test suite for OEVW scraper."""

    def test_scraper_properties(self, oevw_scraper):
        """Test scraper name and base_url properties."""
        assert oevw_scraper.name == "oevw"
        assert oevw_scraper.base_url == "https://www.oevw.at/projekte"

    def test_extract_projects_json_success(self, oevw_scraper, sample_html_with_projects):
        """Test successful extraction of projects JSON from HTML."""
        projects = oevw_scraper._extract_projects_json(sample_html_with_projects)

        assert len(projects) == 3
        assert projects[0]["heading"] == "Test Project 1"
        assert projects[1]["location"] == "1020 Wien"
        assert projects[2]["url"] == "/projekte/test-project-3"

    def test_extract_projects_json_no_projects(self, oevw_scraper):
        """Test extraction when no projects variable is found."""
        html = """
        <!DOCTYPE html>
        <html>
        <body>No projects here</body>
        </html>
        """
        projects = oevw_scraper._extract_projects_json(html)

        assert projects == []

    def test_extract_projects_json_invalid_json(self, oevw_scraper):
        """Test extraction with malformed JSON."""
        html = """
        <script>var projects = [invalid json];</script>
        """
        projects = oevw_scraper._extract_projects_json(html)

        assert projects == []

    def test_extract_image_url_success(self, oevw_scraper):
        """Test successful extraction of image URL from HTML."""
        html = '<img src="/assets/thumb/360x240/project123.webp" alt="Test">'
        url = oevw_scraper._extract_image_url(html)

        assert url == "/assets/thumb/360x240/project123.webp"

    def test_extract_image_url_no_image(self, oevw_scraper):
        """Test extraction when no image is present."""
        html = "<div>No image here</div>"
        url = oevw_scraper._extract_image_url(html)

        assert url is None

    def test_detect_markers_planning(self, oevw_scraper):
        """Test marker detection for planning projects."""
        project = {"projectstatus": "planning"}
        markers = oevw_scraper._detect_markers(project)

        assert "in_planning" in markers

    def test_detect_markers_selling(self, oevw_scraper):
        """Test marker detection for selling projects."""
        project = {"projectstatus": "selling"}
        markers = oevw_scraper._detect_markers(project)

        assert "available_soon" in markers

    def test_detect_markers_no_status(self, oevw_scraper):
        """Test marker detection when no status is provided."""
        project = {"projectstatus": ""}
        markers = oevw_scraper._detect_markers(project)

        assert markers == []

    def test_parse_project_complete(self, oevw_scraper, sample_projects_json):
        """Test parsing a complete project."""
        project = sample_projects_json[0]
        flat = oevw_scraper._parse_project(project)

        assert flat is not None
        assert flat.title == "Test Project 1"
        assert flat.location == "1220 Wien"
        assert str(flat.url) == "https://www.oevw.at/projekte/test-project-1"
        assert flat.description == "Miete"
        assert str(flat.image_url) == "https://www.oevw.at/assets/thumb/360x240/project123.webp"
        assert "in_planning" in flat.markers
        assert flat.source == "oevw"
        assert flat.price is None  # Not available in listing
        assert flat.size is None  # Not available in listing
        assert flat.rooms is None  # Not available in listing

    def test_parse_project_minimal(self, oevw_scraper, sample_projects_json):
        """Test parsing a project with minimal data."""
        project = sample_projects_json[2]
        flat = oevw_scraper._parse_project(project)

        assert flat is not None
        assert flat.title == "Test Project 3"
        assert flat.location == "3500 Krems"
        assert str(flat.url) == "https://www.oevw.at/projekte/test-project-3"
        assert flat.description is None
        assert flat.markers == []

    def test_parse_project_missing_title(self, oevw_scraper):
        """Test parsing fails when title is missing."""
        project = {"url": "/projekte/test", "location": "Wien"}
        flat = oevw_scraper._parse_project(project)

        assert flat is None

    def test_parse_project_missing_url(self, oevw_scraper):
        """Test parsing fails when URL is missing."""
        project = {"heading": "Test", "location": "Wien"}
        flat = oevw_scraper._parse_project(project)

        assert flat is None

    def test_parse_project_exception_handling(self, oevw_scraper):
        """Test that exceptions during parsing are handled gracefully."""
        # Pass invalid data type to trigger exception
        flat = oevw_scraper._parse_project(None)  # type: ignore[arg-type]

        assert flat is None

    @patch.object(OEVWScraper, "fetch_html")
    def test_scrape_success(self, mock_fetch_html, oevw_scraper, sample_html_with_projects):
        """Test successful scraping of projects."""
        mock_fetch_html.return_value = BeautifulSoup(sample_html_with_projects, "html.parser")

        flats = oevw_scraper.scrape()

        assert len(flats) == 3
        assert all(isinstance(flat, Flat) for flat in flats)
        assert flats[0].title == "Test Project 1"
        assert flats[1].title == "Test Project 2"
        assert flats[2].title == "Test Project 3"

    @patch.object(OEVWScraper, "fetch_html")
    def test_scrape_no_projects(self, mock_fetch_html, oevw_scraper):
        """Test scraping when no projects are found."""
        html = "<html><body>No projects</body></html>"
        mock_fetch_html.return_value = BeautifulSoup(html, "html.parser")

        flats = oevw_scraper.scrape()

        assert flats == []

    @patch.object(OEVWScraper, "fetch_html")
    def test_scrape_exception_handling(self, mock_fetch_html, oevw_scraper, capsys):
        """Test that scraping exceptions are handled gracefully."""
        mock_fetch_html.side_effect = Exception("Network error")

        flats = oevw_scraper.scrape()

        assert flats == []
        captured = capsys.readouterr()
        assert "Error scraping OEVW" in captured.out

    def test_generated_id_format(self, oevw_scraper):
        """Test that generated IDs have the correct format."""
        url = "https://www.oevw.at/projekte/test-project"
        flat_id = oevw_scraper.generate_id(url)

        assert flat_id.startswith("oevw-")
        assert len(flat_id) == 21  # "oevw-" + 16 hex chars

    def test_generated_id_consistency(self, oevw_scraper):
        """Test that same URL generates same ID."""
        url = "https://www.oevw.at/projekte/test-project"
        id1 = oevw_scraper.generate_id(url)
        id2 = oevw_scraper.generate_id(url)

        assert id1 == id2

    def test_generated_id_uniqueness(self, oevw_scraper):
        """Test that different URLs generate different IDs."""
        url1 = "https://www.oevw.at/projekte/project-1"
        url2 = "https://www.oevw.at/projekte/project-2"
        id1 = oevw_scraper.generate_id(url1)
        id2 = oevw_scraper.generate_id(url2)

        assert id1 != id2

    @patch.object(OEVWScraper, "fetch_html")
    def test_scrape_filters_invalid_projects(self, mock_fetch_html, oevw_scraper):
        """Test that invalid projects are filtered out during scraping."""
        html = """
        <html><head>
        <script>var projects = [
            {"heading": "Valid", "url": "/projekte/valid"},
            {"heading": "", "url": "/projekte/no-title"},
            {"heading": "No URL"},
            {"heading": "Another Valid", "url": "/projekte/valid-2"}
        ];</script>
        </head></html>
        """
        mock_fetch_html.return_value = BeautifulSoup(html, "html.parser")

        flats = oevw_scraper.scrape()

        # Should only return the 2 valid projects
        assert len(flats) == 2
        assert flats[0].title == "Valid"
        assert flats[1].title == "Another Valid"

    def test_image_url_construction(self, oevw_scraper):
        """Test correct construction of image URLs."""
        project = {
            "heading": "Test",
            "url": "/projekte/test",
            "image": '<img src="/assets/thumb/360x240/test.webp">',
        }
        flat = oevw_scraper._parse_project(project)

        assert flat is not None
        assert str(flat.image_url) == "https://www.oevw.at/assets/thumb/360x240/test.webp"

    def test_url_construction(self, oevw_scraper):
        """Test correct construction of project URLs."""
        project = {
            "heading": "Test Project",
            "url": "/projekte/test-project",
        }
        flat = oevw_scraper._parse_project(project)

        assert flat is not None
        assert str(flat.url) == "https://www.oevw.at/projekte/test-project"

    def test_description_from_legalform(self, oevw_scraper):
        """Test that description is populated from legalform."""
        project = {
            "heading": "Test",
            "url": "/projekte/test",
            "legalform": "Miete, Eigentum",
        }
        flat = oevw_scraper._parse_project(project)

        assert flat is not None
        assert flat.description == "Miete, Eigentum"

    def test_location_defaults_to_unknown(self, oevw_scraper):
        """Test that location defaults to 'Unknown' when missing."""
        project = {
            "heading": "Test",
            "url": "/projekte/test",
        }
        flat = oevw_scraper._parse_project(project)

        assert flat is not None
        assert flat.location == "Unknown"
