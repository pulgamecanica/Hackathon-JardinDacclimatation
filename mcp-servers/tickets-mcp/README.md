# tickets-mcp

MCP server exposing **session / ticket / catalog** tools over **stdio**.
Session + ticket tools proxy the Rails API; catalog and pricing tools
read the in-process catalog (`src/catalog.py`) so the agent can quote
and assemble pack offers without a network round-trip.

## Tools

### Session-backed (proxy Rails)

| Tool | Purpose | Mutates? |
|---|---|---|
| `get_session_details` | Fetch a visit session with tickets (simulated or purchased). | no |
| `create_simulated_ticket` | Create a draft ticket (`purchased=false`). Safe during planning. | yes (reversible) |
| `confirm_purchase` | Convert simulated tickets to purchased. | **irreversible** |

### Catalog / pricing (local, deterministic)

| Tool | Purpose | Mutates? |
|---|---|---|
| `list_ticket_catalog` | Return the full catalog (optionally filtered to a category). Resolves bundle prices for a date. | no |
| `quote_ticket` | Price a single catalog item on a given date (weekday vs weekend/holiday). | no |
| `create_pack_offer` | Assemble a named pack from catalog items. Server computes line prices + total from the catalog — the agent cannot invent a price. Does **not** persist; the caller shows the offer to the user, who materializes it via `create_simulated_ticket` if accepted. | no |

All tools are **agnostic**: reading a session returns the same shape whether
its tickets are simulated or purchased. Only `confirm_purchase` crosses the
financial boundary.

## Catalog categories

- `park_entry` — Entrée simple, tarifs par public (adulte, sénior, RSA, …)
- `admission` — Carnet de 10 entrées, Abonnement annuel
- `attraction_unit` — Ticket à l'unité, carnets de 15 / 50
- `attraction_bundle` — Pass Illimité / Tribu / 16h (prix jour dépendant)
- `rental` — Poussettes, fauteuils roulants

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
