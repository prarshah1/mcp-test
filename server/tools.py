"""MCP tools: health, add, subtract, get_my_name, ping."""

import os


def load_tools(mcp_server):
    """Register all tools on the FastMCP instance."""

    @mcp_server.tool
    def health() -> dict:
        """
        Check that the MCP server is running.

        Returns:
            dict with status and message for monitoring or AI Playground tests.
        """
        return {
            "status": "healthy",
            "message": "Simple MCP server is operational.",
        }

    @mcp_server.tool
    def add(a: float, b: float) -> dict:
        """
        Add two numbers.

        Args:
            a: First summand.
            b: Second summand.

        Returns:
            dict with the sum under key "result".
        """
        return {"result": a + b}

    @mcp_server.tool
    def subtract(a: float, b: float) -> dict:
        """
        Subtract the second number from the first.

        Args:
            a: Minuend.
            b: Subtrahend.

        Returns:
            dict with the difference under key "result".
        """
        return {"result": a - b}

    @mcp_server.tool
    def get_my_name() -> dict:
        """
        Return the configured display name for this server.

        Set the environment variable MY_NAME in the Databricks App configuration
        to customize the returned name.

        Returns:
            dict with "name" and whether it was set via MY_NAME.
        """
        name = os.environ.get("MY_NAME", "").strip()
        if not name:
            return {
                "name": None,
                "configured": False,
                "hint": "Set MY_NAME in the app's environment variables.",
            }
        return {"name": name, "configured": True}

    @mcp_server.tool
    def ping() -> dict:
        """
        Lightweight liveness check with a short fixed response.

        Returns:
            dict with ok=True and a pong message.
        """
        return {"ok": True, "message": "pong"}
