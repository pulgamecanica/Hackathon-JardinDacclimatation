# park-status-mcp

MCP server exposing **read-only park operational data** over **stdio**.
All data is served from an in-memory fixture module (`src/fixtures.py`)
— no database, no network round-trips.

## Tools

| Tool | Purpose |
|---|---|
| `get_park_hours` | Opening / closing / last-entry times for a date (weekend and holiday hours are extended). |
| `list_attractions` | All attractions with zone, min height, min age, thrill level, avg wait, wheelchair access. Optional zone filter. |
| `get_attraction_status` | Live status (open/maintenance) + deterministic current-wait estimate for a (attraction, date). |
| `list_events` | Shows / ateliers / parades programmed on a date; weekend-only events are excluded on weekdays. |

All tools are **read-only**. The agent can call them repeatedly while
planning a visit without mutating state.

## Determinism

Current wait times are pseudo-random but seeded by `(attraction_id, date)`.
Two calls with the same arguments always return the same number — this
matters because the orchestrator may refetch facts when replanning.

Maintenance windows are pre-declared in `_MAINTENANCE` so tests can
assert them.

## Environment

None. The server has no config.

## Run

```bash
pip install -r requirements.txt
python -m src.server          # stdio transport
```

## Tests

```bash
PYTHONPATH=. pytest
```

Covers fixture shape, weekend/holiday logic, park hours, attraction
filtering, deterministic wait jitter, maintenance windows, event
scheduling, and every MCP handler.
