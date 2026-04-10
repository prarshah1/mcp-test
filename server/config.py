"""OAuth / Scalekit settings.

Reference clone: temp/mcp-fastapi-auth (same env names as alejandro-ao/mcp-fastapi-auth).
The Scalekit SDK needs SCALEKIT_ENVIRONMENT_URL + SCALEKIT_CLIENT_ID + SCALEKIT_CLIENT_SECRET.
"""

import logging
import os
from functools import cached_property

logger = logging.getLogger("simple-mcp-server")

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
        lines = [
            "Scalekit auth is enabled but the following environment variables are missing or empty:",
            *(f"  - {name}" for name in missing),
            "",
            "Set them in your Databricks App env or in a local .env file (see .env.example).",
            "Required Scalekit values: environment URL, client ID, client secret, audience, metadata URL.",
            "Variables:",
            "  SCALEKIT_ENVIRONMENT_URL — Scalekit environment / issuer URL",
            "  SCALEKIT_CLIENT_ID — OAuth client ID from Scalekit",
            "  SCALEKIT_CLIENT_SECRET — OAuth client secret (paired with client ID)",
            "  SCALEKIT_AUDIENCE_NAME — token audience (resource identifier)",
            "  SCALEKIT_RESOURCE_METADATA_URL — full URL to /.well-known/oauth-protected-resource/mcp",
        ]
        raise RuntimeError("\n".join(lines))


def log_auth_configuration() -> None:
    """
    Explain how Scalekit is configured at startup (mirrors temp/mcp-fastapi-auth flow:
    set environment URL, client id, secret, then audience + metadata URL).
    """
    if not settings.auth_enabled:
        logger.info(
            "Auth is disabled. To require Bearer tokens, set all Scalekit variables "
            "in .env (copy from .env.example) or Databricks App env — start with "
            "SCALEKIT_ENVIRONMENT_URL, SCALEKIT_CLIENT_ID, SCALEKIT_CLIENT_SECRET, "
            "then SCALEKIT_AUDIENCE_NAME and SCALEKIT_RESOURCE_METADATA_URL. "
            "See temp/mcp-fastapi-auth/readme.md for dashboard steps."
        )
        return

    cid = settings.scalekit_client_id
    cid_preview = (cid[:8] + "…") if len(cid) > 8 else cid or "(empty)"
    logger.info(
        "Scalekit auth enabled: token validation will use "
        "SCALEKIT_ENVIRONMENT_URL=%s, SCALEKIT_CLIENT_ID=%s, SCALEKIT_CLIENT_SECRET=********",
        settings.scalekit_environment_url or "(missing — should not happen after validate)",
        cid_preview,
    )
    logger.info(
        "Also using SCALEKIT_AUDIENCE_NAME and SCALEKIT_RESOURCE_METADATA_URL for JWT checks "
        "and WWW-Authenticate (see .env.example)."
    )
