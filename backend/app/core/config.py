"""Application configuration loaded from environment variables / .env file.

No business constants are defined here except risk thresholds and provider
selection. Do not hardcode thresholds elsewhere — read from settings.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    app_name: str = Field(default="landslide-ner")

    # API
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)
    api_prefix: str = Field(default="/api/v1")

    # Database
    database_url: str = Field(default="sqlite:///./landslide.db")
    spatialite_path: str = Field(default="mod_spatialite")

    # CORS
    cors_allow_origins: str = Field(
        default="http://localhost:8501,http://127.0.0.1:8501"
    )

    # Provider selection
    weather_provider: str = Field(default="mock")
    rainfall_provider: str = Field(default="mock")
    terrain_provider: str = Field(default="mock")
    satellite_provider: str = Field(default="mock")
    landslide_provider: str = Field(default="mock")
    soil_provider: str = Field(default="mock")

    # API keys
    openweather_api_key: str = Field(default="")
    bhuvan_api_key: str = Field(default="")
    sentinel_hub_client_id: str = Field(default="")
    sentinel_hub_client_secret: str = Field(default="")

    # Risk engine thresholds (do not hardcode elsewhere)
    risk_threshold_low: int = Field(default=30, ge=0, le=100)
    risk_threshold_moderate: int = Field(default=60, ge=0, le=100)
    risk_threshold_high: int = Field(default=80, ge=0, le=100)

    # Alerts
    alert_provider: str = Field(default="log")
    sms_provider: str = Field(default="log")
    sms_api_key: str = Field(default="")
    sms_sender_id: str = Field(default="NER-ALERT")

    # i18n
    default_language: str = Field(default="en")
    supported_languages: str = Field(default="en,hi,as")

    @field_validator("risk_threshold_low", "risk_threshold_moderate", "risk_threshold_high")
    @classmethod
    def _validate_threshold_order(cls, v, info):
        # We cannot cross-validate at field-validator scope easily; sanity-check
        # happens in `risk_thresholds()` below.
        return v

    @model_validator(mode="after")
    def _validate_threshold_ordering(self):
        lo, mid, hi = self.risk_threshold_low, self.risk_threshold_moderate, self.risk_threshold_high
        if not (0 <= lo < mid < hi <= 100):
            raise ValueError(
                f"Risk thresholds must be 0 <= low < moderate < high <= 100, "
                f"got low={lo}, moderate={mid}, high={hi}"
            )
        return self

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def languages(self) -> List[str]:
        return [l.strip() for l in self.supported_languages.split(",") if l.strip()]

    def risk_thresholds(self) -> dict:
        """Return the configured risk thresholds after sanity-check ordering.

        The values are 0..100 upper bounds for each class:
            LOW      : score in [0, low)
            MODERATE : score in [low, moderate)
            HIGH     : score in [moderate, high)
            CRITICAL : score in [high, 100]
        """
        lo, mid, hi = self.risk_threshold_low, self.risk_threshold_moderate, self.risk_threshold_high
        if not (0 <= lo < mid < hi <= 100):
            raise ValueError(
                f"Risk thresholds must be 0 <= low < moderate < high <= 100, "
                f"got low={lo}, moderate={mid}, high={hi}"
            )
        return {"low": lo, "moderate": mid, "high": hi}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Use this in app code instead of instantiating Settings directly."""
    return Settings()
