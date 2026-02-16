from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]  # .../backend/app/core/config.py -> repo root
_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # .../backend


class Settings(BaseSettings):
    """
    App settings.

    NOTE: MVP skeleton only. No secrets management or environment-specific config yet.
    """

    app_name: str = "Telegram Ads Marketplace API (MVP skeleton)"
    environment: str = "local"

    # PostgreSQL
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/admarketplace"

    # Telegram Bot API (production)
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_bot_id: int | None = None
    telegram_webhook_secret: str = ""
    # Updates transport: polling getUpdates (no public backend needed)
    telegram_poll_timeout_sec: int = 25

    # MTProto (Telethon)
    telegram_api_id: int | None = None
    telegram_api_hash: str = ""
    telegram_user_session: str = ""  # StringSession for Telethon

    # Required admin permissions for "startchannel" add-bot link.
    telegram_admin_permissions: str = (
        "change_info+post_messages+edit_messages+delete_messages+"
        "restrict_members+invite_users+pin_messages+promote_members"
    )

    # CORS
    # Comma-separated list of allowed origins for browser requests.
    # Example:
    #   CORS_ORIGINS=http://localhost:5173,https://your-domain.com
    cors_origins: str = ""

    # TON (escrow)
    ton_enabled: bool = True
    ton_network: str = "mainnet"  # testnet | mainnet
    ton_mnemonic: str = ""
    ton_api_url: str = "https://tonapi.io/v2"
    ton_api_key: str = ""
    ton_commission_wallet: str = ""
    vite_api_base_url: str = ""

    # Redis / RQ (background jobs)
    redis_url: str = "redis://localhost:6379/0"
    rq_queue_name: str = "default"
    rq_default_job_timeout_sec: int = 600

    # Single source of truth:
    # - Prefer ONE repo-root env file: `<repo>/.env` (and fallback `<repo>/env` if dotfiles are blocked)
    # - Keep backward compatibility with `<backend>/.env` and `<backend>/env`
    model_config = SettingsConfigDict(
        env_file=(
            _REPO_ROOT / ".env",
            _REPO_ROOT / "env",
            _BACKEND_ROOT / ".env",
            _BACKEND_ROOT / "env",
        ),
        env_file_encoding="utf-8",
        # We use a single shared .env for backend + frontend, so ignore unrelated keys like VITE_*.
        extra="ignore",
    )


settings = Settings()


def get_cors_origins() -> list[str]:
    """
    Parse CORS origins from env.
    Empty => CORS middleware not enabled.
    """

    raw = settings.cors_origins.strip()
    if not raw:
        return []
    return [o.strip() for o in raw.split(",") if o.strip()]

