"""Data models for the scraper."""

from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, Field, HttpUrl


class Flat(BaseModel):
    """Represents a flat/apartment listing."""

    id: str = Field(..., description="Unique identifier for the flat")
    title: str = Field(..., description="Title/name of the listing")
    url: HttpUrl = Field(..., description="URL to the listing")
    price: float | None = Field(None, description="Monthly rent in EUR")
    size: float | None = Field(None, description="Size in square meters")
    rooms: float | None = Field(None, description="Number of rooms")
    location: str = Field(..., description="Location/address")
    description: str | None = Field(None, description="Full description")
    image_url: HttpUrl | None = Field(None, description="Main image URL")
    source: str = Field(..., description="Source scraper name")
    markers: list[str] = Field(
        default_factory=list, description="Detected markers (e.g., 'vormerkung_possible')"
    )
    found_at: datetime = Field(default_factory=datetime.now, description="When the flat was found")

    class Config:
        """Pydantic config."""

        json_encoders: ClassVar[dict[type, object]] = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v),
        }


class ScraperResult(BaseModel):
    """Result from a scraper execution."""

    flats: list[Flat] = Field(default_factory=list, description="List of flats found")
    source: str = Field(..., description="Scraper name")
    scraped_at: datetime = Field(default_factory=datetime.now, description="When scraping occurred")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    warnings: list[str] = Field(default_factory=list, description="Non-critical issues")
    health_status: str = Field(
        default="unknown", description="Health status: healthy, unhealthy, failed"
    )

    @property
    def success(self) -> bool:
        """Whether the scraping was successful."""
        return len(self.errors) == 0

    @property
    def is_healthy(self) -> bool:
        """Whether the scraper is healthy (has results and no errors)."""
        return self.health_status == "healthy"

    @property
    def needs_attention(self) -> bool:
        """Whether the scraper needs attention (unhealthy or failed)."""
        return self.health_status in ("unhealthy", "failed")
