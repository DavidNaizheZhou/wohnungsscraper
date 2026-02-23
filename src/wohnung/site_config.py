"""Site configuration models for declarative scraper definitions."""

from pathlib import Path
from typing import ClassVar, Literal

import yaml
from pydantic import BaseModel, Field, HttpUrl


class SelectorMap(BaseModel):
    """CSS selectors for extracting apartment data."""

    listing: str = Field(..., description="Selector for individual listing containers")
    title: str = Field(..., description="Selector for apartment title")
    url: str = Field(..., description="Selector for apartment link (href)")
    price: str | None = Field(None, description="Selector for price")
    size: str | None = Field(None, description="Selector for size")
    rooms: str | None = Field(None, description="Selector for number of rooms")
    location: str = Field(..., description="Selector for location/address")
    description: str | None = Field(None, description="Selector for description text")
    image: str | None = Field(None, description="Selector for main image")


class PaginationConfig(BaseModel):
    """Pagination configuration for multi-page listings."""

    enabled: bool = Field(default=False, description="Whether pagination is enabled")
    next_selector: str | None = Field(None, description="Selector for next page link")
    max_pages: int = Field(default=5, description="Maximum pages to scrape")
    url_pattern: str | None = Field(
        None, description="URL pattern with {page} placeholder, e.g., '?page={page}'"
    )


class MarkerConfig(BaseModel):
    """Configuration for detecting special markers/keywords."""

    name: str = Field(..., description="Internal identifier for the marker")
    label: str = Field(..., description="Display label for the marker")
    patterns: list[str] = Field(..., description="List of patterns to match (case-insensitive)")
    priority: Literal["low", "medium", "high"] = Field(
        default="medium", description="Priority level for highlighting"
    )
    search_in: list[Literal["title", "description"]] = Field(
        default=["title", "description"], description="Fields to search for patterns"
    )


class SiteConfig(BaseModel):
    """Declarative configuration for apartment listing sites."""

    name: str = Field(..., description="Unique site identifier (lowercase, no spaces)")
    display_name: str = Field(..., description="Human-readable site name")
    base_url: HttpUrl = Field(..., description="Starting URL for scraping")
    enabled: bool = Field(default=True, description="Whether this site is active")

    selectors: SelectorMap = Field(..., description="CSS selector mappings")
    pagination: PaginationConfig | None = Field(None, description="Pagination configuration")
    markers: list[MarkerConfig] = Field(
        default_factory=list, description="Special markers to detect"
    )

    request_timeout: int = Field(default=30, description="Request timeout in seconds", ge=5, le=120)
    rate_limit_delay: float = Field(
        default=1.0,
        description="Delay between requests in seconds",
        ge=0.1,
        le=10.0,
    )

    class Config:
        """Pydantic config."""

        json_schema_extra: ClassVar[dict[str, object]] = {
            "example": {
                "name": "example_site",
                "display_name": "Example Site",
                "base_url": "https://example.com/apartments",
                "enabled": True,
                "selectors": {
                    "listing": ".apartment-card",
                    "title": "h2.title",
                    "url": "a.apartment-link",
                    "price": ".price",
                    "location": ".location",
                },
            }
        }


class SiteConfigLoader:
    """Loads and manages site configurations."""

    def __init__(self, config_dir: Path | str = "sites"):
        """Initialize the config loader.

        Args:
            config_dir: Directory containing YAML site config files
        """
        self.config_dir = Path(config_dir)

    def load_site(self, config_path: Path) -> SiteConfig:
        """Load a single site configuration from YAML.

        Args:
            config_path: Path to YAML config file

        Returns:
            Validated SiteConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            data = yaml.safe_load(f)

        try:
            return SiteConfig(**data)
        except Exception as e:
            raise ValueError(f"Invalid config in {config_path}: {e}") from e

    def load_all_sites(self) -> dict[str, SiteConfig]:
        """Load all site configurations from the config directory.

        Returns:
            Dictionary mapping site names to their configurations

        Raises:
            ValueError: If duplicate site names are found
        """
        if not self.config_dir.exists():
            return {}

        configs: dict[str, SiteConfig] = {}
        config_files = list(self.config_dir.glob("*.yaml")) + list(self.config_dir.glob("*.yml"))

        for config_file in config_files:
            try:
                config = self.load_site(config_file)

                if config.name in configs:
                    raise ValueError(f"Duplicate site name '{config.name}' found in {config_file}")

                configs[config.name] = config
            except Exception as e:
                # Log error but continue loading other configs
                print(f"Warning: Failed to load {config_file}: {e}")

        return configs

    def get_enabled_sites(self) -> dict[str, SiteConfig]:
        """Get only enabled site configurations.

        Returns:
            Dictionary of enabled site configurations
        """
        all_sites = self.load_all_sites()
        return {name: config for name, config in all_sites.items() if config.enabled}

    def validate_config(self, config_path: Path) -> tuple[bool, str]:
        """Validate a site configuration file.

        Args:
            config_path: Path to YAML config file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            config = self.load_site(config_path)
            # Additional validation checks
            if not config.selectors.listing:
                return False, "Missing required selector: listing"
            if not config.selectors.title:
                return False, "Missing required selector: title"
            if not config.selectors.url:
                return False, "Missing required selector: url"
            if not config.selectors.location:
                return False, "Missing required selector: location"

            return True, f"✓ Valid configuration for '{config.display_name}'"
        except Exception as e:
            return False, str(e)
