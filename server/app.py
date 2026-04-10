"""FastMCP + FastAPI combined app (streamable HTTP for Databricks MCP Apps).

OAuth metadata shape aligns with github.com/alejandro-ao/mcp-fastapi-auth (see temp/ clone).
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastmcp import FastMCP

from .auth_middleware import AuthMiddleware
from .tools import load_tools

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _oauth_protected_resource_metadata() -> dict:
    """
    OAuth 2.0 Protected Resource Metadata for MCP discovery.

    Same pattern as mcp-fastapi-auth: optional METADATA_JSON_RESPONSE is the full JSON string.
    Otherwise fields are built from env. Aliases match that repo’s .env names:
    SCALEKIT_AUTHORIZATION_SERVERS, SCALEKIT_RESOURCE_IDENTIFIER, SCALEKIT_RESOURCE_DOCS_URL.
    """
    raw = os.environ.get("METADATA_JSON_RESPONSE", "").strip()
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                "METADATA_JSON_RESPONSE must be valid JSON (mcp-fastapi-auth style)"
            ) from e

    auth_servers_raw = (
        os.environ.get("OAUTH_AUTHORIZATION_SERVERS")
        or os.environ.get("SCALEKIT_AUTHORIZATION_SERVERS")
        or "https://spa.scalekit.dev/resources/res_120336297230336514"
    )
    authorization_servers = [s.strip() for s in auth_servers_raw.split(",") if s.strip()]

    resource = os.environ.get("OAUTH_RESOURCE") or os.environ.get(
        "SCALEKIT_RESOURCE_IDENTIFIER",
        "https://mcp-a1-896143009251172.aws.databricksapps.com/mcp/",
    )
    resource_documentation = os.environ.get(
        "OAUTH_RESOURCE_DOCUMENTATION"
    ) or os.environ.get(
        "SCALEKIT_RESOURCE_DOCS_URL",
        "https://mcp-a1-896143009251172.aws.databricksapps.com/mcp/docs",
    )
    scopes_raw = os.environ.get("OAUTH_SCOPES_SUPPORTED", "health:read")
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
    description="Minimal tools for Databricks Apps",
    version="0.1.0",
    lifespan=mcp_app.lifespan,
)


@app.get("/", include_in_schema=False)
async def root():
    # Match Databricks MCP template: serve landing page when static/index.html exists.
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"message": "Simple MCP server is running", "status": "ok"}


@app.get("/health", include_in_schema=False)
async def http_health():
    # HTTP-only liveness; MCP clients can still use the `health` tool.
    return {
        "status": "healthy",
        "message": "Simple MCP server is operational.",
    }


@app.get("/.well-known/oauth-protected-resource/mcp", include_in_schema=False)
async def oauth_protected_resource_mcp():
    """Scalekit (and similar) metadata discovery — HTTP GET, JSON body."""
    return _oauth_protected_resource_metadata()


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
