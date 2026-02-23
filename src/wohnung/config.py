"""Configuration management using pydantic-settings."""

import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Email configuration (backward compatible - single account)
    resend_api_key: str | None = Field(None, description="Resend API key for sending emails")
    email_to: str = Field(
        default="test@example.com",
        description="Recipient email (for single account mode)",
    )
    email_from: str = Field(
        default="onboarding@resend.dev",
        description="Sender email (must be verified domain)",
    )

    # Storage
    data_dir: Path = Field(
        default=Path("data"),
        description="Directory to store scraped data",
    )

    # Scraper settings
    request_timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    user_agent: str = Field(
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        description="User agent for HTTP requests",
    )

    @field_validator("email_to")
    @classmethod
    def validate_email_to(cls, v: str) -> str:
        """Validate email_to is not empty."""
        if not v.strip():
            raise ValueError("email_to cannot be empty")
        return v

    @field_validator("data_dir", mode="before")
    @classmethod
    def create_data_dir(cls, v: str | Path) -> Path:
        """Ensure data directory exists."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def email_accounts(self) -> list[tuple[str, str]]:
        """
        Get list of (api_key, email) tuples for sending emails.

        Supports two modes:
        1. Single account: RESEND_API_KEY + EMAIL_TO
        2. Multiple accounts: RESEND_API_KEY_1 + EMAIL_TO_1, RESEND_API_KEY_2 + EMAIL_TO_2, etc.

        Returns:
            List of (api_key, recipient_email) tuples
        """
        accounts = []

        # Check for numbered accounts (RESEND_API_KEY_1, EMAIL_TO_1, etc.)
        i = 1
        while True:
            api_key = os.getenv(f"RESEND_API_KEY_{i}")
            email_to = os.getenv(f"EMAIL_TO_{i}")

            if api_key and email_to:
                accounts.append((api_key, email_to.strip()))
                i += 1
            else:
                break

        # If no numbered accounts, fall back to single account mode
        if not accounts and self.resend_api_key and self.email_to:
            accounts.append((self.resend_api_key, self.email_to.strip()))

        return accounts

    @property
    def email_recipients(self) -> list[str]:
        """Get list of email recipients (for backward compatibility)."""
        return [email for _, email in self.email_accounts]


# Global settings instance
# Note: In tests, environment variables should be mocked
try:
    settings = Settings()  # type: ignore[call-arg]
except Exception:
    # Fallback for when env vars are not set (e.g., during import in tests)
    settings = Settings(email_to="test@example.com")  # type: ignore[call-arg]
