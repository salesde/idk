"""Company-wide configuration loaded from .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLMs
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # Research
    tavily_api_key: str = ""

    # TikTok
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_access_token: str = ""

    # YouTube
    youtube_api_key: str = ""
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""

    # Netlify
    netlify_auth_token: str = ""
    netlify_team_id: str = ""

    # Shopify
    shopify_shop_url: str = ""
    shopify_access_token: str = ""

    # Company
    company_name: str = "NexGen AI Corp"
    company_mission: str = "Autonomously generate revenue through AI-powered content and commerce"
    cycle_interval_minutes: int = 60
    min_research_confidence: float = 0.70
    heartbeat_interval: int = 30
    max_cost_per_cycle: float = 2.00

    # Models — gemini-2.0-flash works on free tier; 2.5-pro requires paid billing
    executive_model: str = "gemini-2.0-flash"
    research_model: str = "gemini-2.0-flash"
    worker_model: str = "gemini-2.0-flash"

    # Runtime
    dry_run: bool = Field(default=False, alias="DRY_RUN")
    log_level: str = "INFO"
    log_file: str = "output/company.log"

    @model_validator(mode="after")
    def force_gemini_models(self) -> "Settings":
        """Replace any Claude model with a Gemini equivalent.

        Claude API requires separate paid API credits (different from Claude.ai Pro).
        The system runs 100% on Gemini by default. If the user adds Anthropic credits
        in the future they can manually set a claude-* model here.
        """
        if self.executive_model.startswith("claude"):
            self.executive_model = "gemini-2.0-flash"
        if self.research_model.startswith("claude"):
            self.research_model = "gemini-2.0-flash"
        if self.worker_model.startswith("claude"):
            self.worker_model = "gemini-2.0-flash"
        return self


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
