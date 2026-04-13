"""FastMCP + FastAPI for Databricks Apps (streamable HTTP MCP).

Google and other logins are configured in the Scalekit dashboard; this process only serves
MCP and validates Bearer tokens (see auth_middleware + scalekit-sdk). Resource URLs must come
from environment variables for your Databricks app host — do not rely on localhost.
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastmcp import FastMCP

from .auth_middleware import AuthMiddleware
from .tools import load_tools

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _oauth_protected_resource_metadata() -> dict:
    """
    OAuth protected-resource metadata (RFC-style) for MCP clients.
    Uses the same env vars as temp/mcp-fastapi-auth / Scalekit — set hosts to your
    Databricks app URL, e.g. https://<id>.aws.databricksapps.com
    """
    raw = os.environ.get("METADATA_JSON_RESPONSE", "").strip()
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError("METADATA_JSON_RESPONSE must be valid JSON") from e

    auth_servers_raw = (
        os.environ.get("OAUTH_AUTHORIZATION_SERVERS")
        or os.environ.get("SCALEKIT_AUTHORIZATION_SERVERS", "")
    ).strip()
    if not auth_servers_raw:
        raise ValueError(
            "Set SCALEKIT_AUTHORIZATION_SERVERS to your Scalekit authorization server URL(s)."
        )

    authorization_servers = [s.strip() for s in auth_servers_raw.split(",") if s.strip()]

    resource = (
        os.environ.get("OAUTH_RESOURCE") or os.environ.get("SCALEKIT_RESOURCE_IDENTIFIER", "")
    ).strip()
    if not resource:
        raise ValueError(
            "Set SCALEKIT_RESOURCE_IDENTIFIER to your MCP resource URL on Databricks "
            "(e.g. https://<app>.aws.databricksapps.com/mcp/)."
        )

    resource_documentation = (
        os.environ.get("OAUTH_RESOURCE_DOCUMENTATION")
        or os.environ.get("SCALEKIT_RESOURCE_DOCS_URL", "")
    ).strip()
    if not resource_documentation:
        resource_documentation = f"{resource.rstrip('/')}/docs"

    scopes_raw = os.environ.get("OAUTH_SCOPES_SUPPORTED", "search:read")
    scopes_supported = [s.strip() for s in scopes_raw.split(",") if s.strip()]

    return {
        "authorization_servers": authorization_servers,
        "bearer_methods_supported": ["header"],
        "resource": resource,
        "resource_documentation": resource_documentation,
        "scopes_supported": scopes_supported,
    }


mcp_server = FastMCP(name="simple-mcp-server")
load_tools(mcp_server)
mcp_app = mcp_server.http_app()

app = FastAPI(
    title="Simple MCP Server",
    description="MCP on Databricks Apps with Scalekit Bearer auth",
    version="0.1.0",
    lifespan=mcp_app.lifespan,
)


@app.get("/", include_in_schema=False)
async def root():
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"service": "mcp", "deployment": "databricks"}


@app.get("/health", include_in_schema=False)
async def http_health():
    return {
        "status": "healthy",
        "message": "MCP server is operational.",
    }


@app.get("/.well-known/oauth-protected-resource/mcp", include_in_schema=False)
async def oauth_protected_resource_mcp():
    """OAuth discovery for MCP clients (authorization_servers → Scalekit, including Google)."""
    try:
        return _oauth_protected_resource_metadata()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


combined_app = FastAPI(
    title="Simple MCP App",
    routes=[*mcp_app.routes, *app.routes],
    lifespan=mcp_app.lifespan,
)

combined_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
combined_app.add_middleware(AuthMiddleware)
