# Plume — Jardin d'Acclimatation Companion

AI visit-planning companion for the Jardin d'Acclimatation. Users land on a calendar, pick a date and party composition, and immediately get contextual help from an agentic chatbot: closures for that date, events, suggested routes, and (optionally) ticket purchase.

## Architecture

| Service | Stack | Purpose |
|---|---|---|
| `services/web` | Next.js 14 (App Router) + Zustand | Calendar entry, chat UI, session state (localStorage) |
| `services/api` | Rails 8 API + Postgres + Redis | Visit sessions, tickets, groups, chat history, magic-link auth |
| `services/ai-orchestrator` | FastAPI + Celery + SQLAlchemy + structlog | Multi-provider LLM routing, usage caps, agents, MCP client, media |
| `mcp-servers/tickets-mcp` | Python MCP SDK | Ticket + session tools (calls Rails API) |
| `mcp-servers/routing-mcp` | Python MCP SDK | Route optimization |
| `mcp-servers/park-status-mcp` | Python MCP SDK | Closures, events for a given date |

## Core design principle: agnostic features

All chatbot features work the same whether a user's tickets are **simulated** (`purchased=false`) or **purchased** (`purchased=true`). A user who only filled out the calendar form (no tickets yet) gets the same planning quality as one who has paid. `purchased` is a financial state, not a feature gate. The only irreversible operation is `confirm_purchase`.

## Quick start (dev)

```bash
cp .env.example .env
docker compose -f docker/docker-compose.dev.yml up --build
```

- Web: http://localhost:3000
- Rails API: http://localhost:3001
- AI Orchestrator: http://localhost:8000
- Flower (Celery): http://localhost:5555

## Tests

```bash
# Rails
(cd services/api && bundle exec rspec)
# Python (AI orchestrator)
(cd services/ai-orchestrator && pytest)
# Next.js
(cd services/web && npm test)
```

## Project status

Scaffold + core logic. Production concerns deliberately out of scope for this hackathon build: Terraform, Kubernetes, Grafana dashboards, real vLLM deployment. The dev compose file uses a stub LLM client so the stack runs without a GPU.
