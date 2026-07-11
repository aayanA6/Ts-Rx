from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ts-rx"
    environment: str = "dev"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/analysis_agent"
    redis_url: str = "redis://localhost:6379"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_sec: int = 20
    gemini_retries: int = 2

    worker_enabled: bool = True
    worker_poll_interval_sec: float = 1.5

    max_log_snippets: int = 150
    max_log_line_chars: int = 600
    max_context_files: int = 8
    max_context_excerpt_chars: int = 1600

    allowed_read_roots: str = "src,services,config"
    project_root: Path = Field(default_factory=Path.cwd)

    # Auth
    jwt_secret: str = "change-me-in-production-use-a-long-random-string"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # SMTP notifications (optional)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = "noreply@tsrx.app"

    # ntfy.sh notifications (optional) — override for a self-hosted ntfy server
    ntfy_base_url: str = "https://ntfy.sh"

    # App URL for notification links and CORS allow-list
    app_url: str = "http://localhost:5173"
    # Extra CORS origins beyond app_url (comma-separated, e.g. "https://tailscale.com")
    cors_origins: str = ""

    # Tailscale API (OAuth client credentials — for tailnet device listing)
    tailscale_oauth_client_id: str | None = None
    tailscale_oauth_client_secret: str | None = None
    tailscale_tailnet: str = "-"  # "-" = the tailnet the OAuth client belongs to

    @property
    def read_roots(self) -> list[Path]:
        roots: list[Path] = []
        for entry in self.allowed_read_roots.split(","):
            part = entry.strip()
            if not part:
                continue
            roots.append((self.project_root / part).resolve())
        return roots


@lru_cache
def get_settings() -> Settings:
    return Settings()
