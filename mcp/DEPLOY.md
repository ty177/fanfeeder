# FanFeeder MCP Server — Railway Deployment

## What this does

An MCP (Model Context Protocol) server that lets LLMs query FanFeeder live.
Users can say things like:

- *"What's the latest news about my teams?"*
- *"Show me Man City highlights"*
- *"Add the Lakers to my digest"*
- *"Remove Barcelona from my FanFeeder"*

The newsletter pipeline (GitHub Actions) is completely unchanged.

## Tools exposed

| Tool | Description |
|---|---|
| `get_my_news(email)` | Latest headlines + YouTube highlights for subscribed teams |
| `get_team_news(team_name)` | News for any team in the catalog |
| `list_my_teams(email)` | Show which teams you're subscribed to |
| `list_available_teams(sport?, search?)` | Browse the full team catalog |
| `add_teams(email, team_names)` | Add teams to your digest |
| `remove_teams(email, team_names)` | Remove teams from your digest |
| `unsubscribe(email)` | Stop all digest emails |

## Deploy to Railway

### 1. Create the Railway service

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select the `ty177/fanfeeder` repo
3. In service settings, set **Root Directory** to `mcp`
4. Railway will detect the `Procfile` and use it automatically

### 2. Set environment variables (optional — defaults work)

In Railway → your service → Variables:

```
FANFEEDER_SITE=https://fanfeeder.fire-exit.com
FORMSPREE_ENDPOINT=https://formspree.io/f/mzdawwjk
MCP_TRANSPORT=sse
```

Railway sets `PORT` automatically.

### 3. Get your service URL

After deploy, Railway gives you a public URL like:
```
https://fanfeeder-mcp-production.up.railway.app
```

### 4. Connect to Claude

**Claude.ai (Projects → Connectors):**
```
https://fanfeeder-mcp-production.up.railway.app/sse
```

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "fanfeeder": {
      "url": "https://fanfeeder-mcp-production.up.railway.app/sse"
    }
  }
}
```

**Claude Code** (add to project's MCP config):
```json
{
  "fanfeeder": {
    "type": "sse",
    "url": "https://fanfeeder-mcp-production.up.railway.app/sse"
  }
}
```

## Local development (stdio mode)

Requires Python 3.10+.

```bash
cd mcp
pip install -r requirements.txt
MCP_TRANSPORT=stdio python server.py
```

Then add to Claude Desktop config:
```json
{
  "mcpServers": {
    "fanfeeder-local": {
      "command": "python",
      "args": ["/path/to/fanfeeder/mcp/server.py"],
      "env": { "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

## Architecture note

- **Reads** (news, team lists, subscriber lookup) hit live external APIs on every call — no stale cache beyond a one-shot teams.json cache per server process.
- **Writes** (add/remove teams) POST to Formspree, which feeds the same GitHub Actions pipeline the web form uses. Digest changes take effect on the next scheduled run (up to 12 hours).
- Subscriber identity uses the same SHA-256 hash index (`subscribers_index.json`) as the manage.html page — no raw email is stored or transmitted outside Formspree.
