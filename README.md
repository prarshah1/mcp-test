# Simple MCP server (Databricks Apps + Scalekit)

Model Context Protocol (MCP) server using **FastMCP** (streamable HTTP), deployed as a **Databricks App**. **Scalekit** validates Bearer tokens; configure **Google** (and other providers) in the [Scalekit dashboard](https://docs.scalekit.com/guides/integrations/social-connections/google), not in this repository.

## Prerequisites

- **Python 3.11+**
- **uv** (recommended for Databricks; see `requirements.txt` and `app.yaml`)
- A **Databricks** workspace with Apps enabled (for production deployment)
- A **Scalekit** account and MCP/resource configuration aligned with your Databricks app URL

## Configure environment

1. Copy the example file and edit values:

   ```bash
   cp .env.example .env
   ```

2. Set at least:

   | Variable | Purpose |
   |----------|---------|
   | `SCALEKIT_ENVIRONMENT_URL` | Scalekit issuer / environment base URL |
   | `SCALEKIT_CLIENT_ID` | OAuth client id from Scalekit |
   | `SCALEKIT_CLIENT_SECRET` | OAuth client secret |
   | `SCALEKIT_AUDIENCE_NAME` | JWT audience (usually your MCP resource URL) |
   | `SCALEKIT_RESOURCE_METADATA_URL` | Full URL to metadata on **your** app host (see below) |
   | `SCALEKIT_AUTHORIZATION_SERVERS` | Comma-separated Scalekit authorization server URL(s) |
   | `SCALEKIT_RESOURCE_IDENTIFIER` | MCP resource id, e.g. `https://<app>.aws.databricksapps.com/mcp/` |

3. **Metadata URL on Databricks** — must use your real app host (no `localhost`):

   ```text
   https://<your-app-id>.aws.databricksapps.com/.well-known/oauth-protected-resource/mcp
   ```

   Do **not** insert `/mcp/` before `/.well-known/`; the path is `/.well-known/...` on the app origin.

4. Optional: `METADATA_JSON_RESPONSE` — if set, must be valid JSON and overrides the built metadata document.

5. **Auth toggle:** If `SCALEKIT_CLIENT_ID` and `SCALEKIT_CLIENT_SECRET` are set, auth defaults to **on**. Set `AUTH_ENABLED=false` only for development if you need to call `/mcp` without a Bearer token.

## Run locally (development)

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
simple-mcp-server --port 8000
```

The process listens on `0.0.0.0:8000`. Open:

- `http://127.0.0.1:8000/` — landing page (if `static/index.html` exists)
- `http://127.0.0.1:8000/health` — HTTP health check
- `http://127.0.0.1:8000/.well-known/oauth-protected-resource/mcp` — OAuth protected-resource metadata

**MCP endpoint:** `POST` (and streamable HTTP as configured) to `http://127.0.0.1:8000/mcp` with appropriate headers. If Scalekit auth is enabled, send:

```http
Authorization: Bearer <access_token>
```

Tokens are obtained through your OAuth client and Scalekit (including Google after you enable it for the workspace).

## Deploy on Databricks Apps

This repo is intended to run as a **Databricks App** (not only on your laptop). Official overview: [Host custom MCP servers using Databricks apps](https://docs.databricks.com/gcp/generative-ai/mcp/custom-mcp).

1. **App name** — use the `mcp-` prefix (e.g. `mcp-my-server`) so the workspace recognizes it as an MCP app.

2. **Layout** — root should include at least:

   - `app.yaml` — runs `uv run simple-mcp-server` (see file)
   - `requirements.txt` — includes `uv`
   - `pyproject.toml` — dependencies and script entry `simple-mcp-server`

3. **Authenticate** to your workspace (OAuth / CLI as in Databricks docs).

4. **Sync and deploy** (adjust app name and paths to match your workspace):

   ```bash
   databricks auth login --host https://<your-workspace-host>
   DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
   databricks sync . "/Workspace/Users/$DATABRICKS_USERNAME/mcp-my-server"
   databricks apps deploy mcp-my-server --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/mcp-my-server"
   ```

5. **Environment variables** — in the Databricks App configuration, set the same variables as in `.env` (especially all `SCALEKIT_*` fields and the Databricks-hosted metadata URL).

6. **MCP URL** after deploy:

   ```text
   https://<app-host>/mcp
   ```

   Discovery metadata:

   ```text
   https://<app-host>/.well-known/oauth-protected-resource/mcp
   ```

## Security notes

- **Do not commit** real `.env` files or secrets to git. Use Databricks secrets / app environment for production.
- **`/mcp`** is protected by middleware when auth is enabled: requests without a valid Bearer token receive `401` and a JSON error body.
- **Google login** is configured in **Scalekit**; this service only **validates** tokens for your MCP resource.

## Reference

- Example patterns: [alejandro-ao/mcp-fastapi-auth](https://github.com/alejandro-ao/mcp-fastapi-auth) (clone under `temp/` for comparison if present)
- Step-by-step walkthrough (OAuth 2.1 + Scalekit, remote MCP): [Tutorial: Auth for Remote MCP Servers](https://www.youtube.com/watch?v=gl6U8s3zStI) (Alejandro AO on YouTube)
- Databricks MCP: [Custom MCP on Databricks Apps](https://docs.databricks.com/gcp/generative-ai/mcp/custom-mcp)
