"""Uvicorn entry point for the MCP server (Databricks Apps default: port 8000)."""

import argparse

import uvicorn

from server.config import settings, validate_auth_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the simple MCP server")
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)",
    )
    args = parser.parse_args()

    if settings.auth_enabled:
        validate_auth_settings()

    uvicorn.run(
        "server.app:combined_app",
        host="0.0.0.0",
        port=args.port,
    )
