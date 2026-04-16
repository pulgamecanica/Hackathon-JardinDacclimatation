# tickets-mcp

MCP server exposing ticket + session tools over **stdio**. All tools are
backed by the Rails API (`services/api`) — this server is a thin,
agent-friendly facade that keeps tool schemas stable even as the HTTP
contract evolves.

## Tools

| Tool | Purpose | Mutates? |
|---|---|---|
| `get_session_details` | Fetch a visit session with tickets (simulated or purchased). | no |
| `create_simulated_ticket` | Create a draft ticket (`purchased=false`). Safe to call during planning. | yes (but reversible) |
| `confirm_purchase` | Convert simulated tickets to purchased. | **irreversible** |

All tools are **agnostic**: reading a session returns the same shape whether
its tickets are simulated or purchased. Only `confirm_purchase` crosses the
financial boundary.

## Environment

| Var | Default | Notes |
|---|---|---|
| `RAILS_API_URL` | `http://api:3000` | Base URL for the Rails API |
| `INTERNAL_API_KEY` | _(empty)_ | Sent as `Authorization: Bearer ...` |

## Run

```bash
pip install -r requirements.txt
python -m src.server          # stdio transport
```

The AI orchestrator launches this server as a child process via the MCP
stdio manager; you normally don't run it by hand.

## Tests

```bash
PYTHONPATH=. pytest
```

Unit tests cover the Rails client using `httpx.MockTransport` — no live API
required. Tests assert the correct HTTP method, path, auth header, and
payload shape for every tool.
