"""FastMCP + FastAPI combined app (streamable HTTP for Databricks MCP Apps)."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastmcp import FastMCP

from .tools import load_tools

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

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


combined_app = FastAPI(
    title="Simple MCP App",
    routes=[*mcp_app.routes, *app.routes],
    lifespan=mcp_app.lifespan,
)
