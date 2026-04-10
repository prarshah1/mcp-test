"""OAuth / Scalekit settings (see https://github.com/alejandro-ao/mcp-fastapi-auth)."""

import os
from functools import cached_property

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _truthy(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


class Settings:
    """Loaded at import; override via environment (Databricks App env, .env locally)."""

    @cached_property
    def auth_enabled(self) -> bool:
        explicit = os.environ.get("AUTH_ENABLED")
        if explicit is not None:
            return _truthy(explicit, False)
        # If Scalekit client credentials exist, default to requiring auth
        return bool(
            os.environ.get("SCALEKIT_CLIENT_ID") and os.environ.get("SCALEKIT_CLIENT_SECRET")
        )

    @property
    def scalekit_environment_url(self) -> str:
        return os.environ.get("SCALEKIT_ENVIRONMENT_URL", "").rstrip("/")

    @property
    def scalekit_client_id(self) -> str:
        return os.environ.get("SCALEKIT_CLIENT_ID", "")

    @property
    def scalekit_client_secret(self) -> str:
        return os.environ.get("SCALEKIT_CLIENT_SECRET", "")

    @property
    def scalekit_audience_name(self) -> str:
        return os.environ.get("SCALEKIT_AUDIENCE_NAME", "")

    @property
    def scalekit_resource_metadata_url(self) -> str:
        """
        Full URL to this app's protected-resource metadata document (WWW-Authenticate).
        e.g. https://<app>/.well-known/oauth-protected-resource/mcp
        """
        return os.environ.get("SCALEKIT_RESOURCE_METADATA_URL", "").strip()

    @property
    def scalekit_tool_call_scopes(self) -> list[str]:
        raw = os.environ.get("SCALEKIT_TOOL_CALL_SCOPES", "health:read")
        return [s.strip() for s in raw.split(",") if s.strip()]


settings = Settings()


def validate_auth_settings() -> None:
    if not settings.auth_enabled:
        return
    missing = []
    if not settings.scalekit_environment_url:
        missing.append("SCALEKIT_ENVIRONMENT_URL")
    if not settings.scalekit_client_id:
        missing.append("SCALEKIT_CLIENT_ID")
    if not settings.scalekit_client_secret:
        missing.append("SCALEKIT_CLIENT_SECRET")
    if not settings.scalekit_audience_name:
        missing.append("SCALEKIT_AUDIENCE_NAME")
    if not settings.scalekit_resource_metadata_url:
        missing.append("SCALEKIT_RESOURCE_METADATA_URL")
    if missing:
        raise RuntimeError(
            "AUTH_ENABLED requires Scalekit settings: " + ", ".join(missing)
        )
