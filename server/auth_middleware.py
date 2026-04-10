"""
Bearer token validation via Scalekit (pattern from mcp-fastapi-auth server.py + auth.py).
https://github.com/alejandro-ao/mcp-fastapi-auth
"""

from __future__ import annotations

import json
import logging

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from .config import settings, validate_auth_settings

logger = logging.getLogger(__name__)

_scalekit_client = None


def _get_client():
    global _scalekit_client
    if _scalekit_client is None:
        validate_auth_settings()
        from scalekit import ScalekitClient

        _scalekit_client = ScalekitClient(
            settings.scalekit_environment_url,
            settings.scalekit_client_id,
            settings.scalekit_client_secret,
        )
    return _scalekit_client


def _is_public_route(request: Request) -> bool:
    path = request.url.path
    if path.startswith("/.well-known/"):
        return True
    if path == "/health":
        return True
    if path == "/" and request.method == "GET":
        return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.auth_enabled:
            return await call_next(request)

        if _is_public_route(request):
            return await call_next(request)

        body = await request.body()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = StarletteRequest(request.scope, receive)

        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=401,
                    detail="Missing or invalid authorization header",
                )

            token = auth_header.split(" ", 1)[1].strip()
            if not token:
                raise HTTPException(status_code=401, detail="Empty bearer token")

            try:
                request_data = json.loads(body.decode("utf-8")) if body else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                request_data = {}

            from scalekit.common.scalekit import TokenValidationOptions

            validation_options = TokenValidationOptions(
                issuer=settings.scalekit_environment_url,
                audience=[settings.scalekit_audience_name],
            )

            is_tool_call = request_data.get("method") == "tools/call"
            if is_tool_call and settings.scalekit_tool_call_scopes:
                validation_options.required_scopes = settings.scalekit_tool_call_scopes

            client = _get_client()
            client.validate_token(token, options=validation_options)

        except HTTPException as e:
            meta = settings.scalekit_resource_metadata_url
            www = (
                f'Bearer realm="OAuth", resource_metadata="{meta}"'
                if meta
                else 'Bearer realm="OAuth"'
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": "unauthorized"
                    if e.status_code == 401
                    else "forbidden",
                    "error_description": e.detail,
                },
                headers={"WWW-Authenticate": www},
            )
        except Exception as e:
            logger.exception("Token validation error")
            meta = settings.scalekit_resource_metadata_url
            www = (
                f'Bearer realm="OAuth", resource_metadata="{meta}"'
                if meta
                else 'Bearer realm="OAuth"'
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "error_description": "Token validation failed",
                },
                headers={"WWW-Authenticate": www},
            )

        return await call_next(request)
