"""FastMCP + FastAPI combined app (streamable HTTP for Databricks MCP Apps)."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastmcp import FastMCP

from .tools import load_tools

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _oauth_protected_resource_metadata() -> dict:
    """
    OAuth 2.0 Protected Resource Metadata (RFC 9728-style) for Scalekit / MCP clients.

    Override via env (comma-separated lists where noted):
    - OAUTH_AUTHORIZATION_SERVERS: authorization server URLs
    - OAUTH_RESOURCE: protected resource identifier (MCP base URL, usually with trailing /)
    - OAUTH_RESOURCE_DOCUMENTATION: human-readable docs URL
    - OAUTH_SCOPES_SUPPORTED: scope names
    """
    auth_servers_raw = os.environ.get(
        "OAUTH_AUTHORIZATION_SERVERS",
        "https://spa.scalekit.dev/resources/res_120336297230336514",
    )
    authorization_servers = [s.strip() for s in auth_servers_raw.split(",") if s.strip()]

    resource = os.environ.get(
        "OAUTH_RESOURCE",
        "https://mcp-a1-896143009251172.aws.databricksapps.com/mcp/",
    )
    resource_documentation = os.environ.get(
        "OAUTH_RESOURCE_DOCUMENTATION",
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
