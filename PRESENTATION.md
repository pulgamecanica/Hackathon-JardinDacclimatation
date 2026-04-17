# Pavo — AI Companion for the Jardin d'Acclimatation

> *Un compagnon de visite, pas un chatbot de plus.*
> Hackathon submission — `pulgamecanica/HackathonJardinDAcclimatation`

---

## 1. The pitch in one paragraph

Visitors land on a calendar, pick a date and who's coming (adults, petits, enfants,
ados), and a French-speaking AI companion named **Pavo** is *already* up to speed
when the chat opens. From the first message it can plan a route, check what's
closed on that day, simulate ticket bundles, and propose family activities — all
without forcing a purchase. Tickets are *first-class but optional*: the bot helps
identically whether they are **simulated** for planning or **purchased** for real.

---

## 2. What the visitor experiences

```
   ┌─────────────────┐      ┌──────────────────┐      ┌──────────────────────┐
   │  Calendar +     │ ───▶ │  Pavo greets you │ ───▶ │  4 specialised modes │
   │  party form     │      │  in French, knows│      │  (planner, compagnon,│
   │  (no signup)    │      │  date + group    │      │  conciergerie,       │
   └─────────────────┘      └──────────────────┘      │  découverte)         │
                                                      └──────────────────────┘
```

- **One landing page.** Date + visitor counts + email. Magic-link auth means *no
  password*, ever.
- **Proactive greeting.** As soon as the form is submitted the orchestrator fires
  `/chat/greet`; the user sees a warm welcome that already cites their date and
  party — no "How can I help you?" cold start.
- **Quick-reply chips** under every reply, tailored to the active mode.
- **Clickable pack cards** when the conciergerie suggests ticket bundles —
  prices come from the catalogue, never invented by the LLM.
- **All tickets are reversible** until the visitor explicitly clicks
  *Confirmer l'achat*. That single irreversible boundary is enforced in Rails.

---

## 3. Architecture at a glance

| Service                       | Stack                                 | Role                                                              |
|-------------------------------|---------------------------------------|-------------------------------------------------------------------|
| `services/web`                | Next.js 14 (App Router) + Zustand     | Calendar, chat UI, session in localStorage                        |
| `services/api`                | Rails 8 API + Postgres + Redis        | Visit sessions, tickets, groups, chat history, magic-link auth    |
| `services/ai-orchestrator`    | FastAPI + Celery + SQLAlchemy         | Multi-provider LLM router, agents, MCP client, usage logging      |
| `mcp-servers/tickets-mcp`     | Python MCP SDK (stdio)                | Catalogue, pricing, simulated tickets, pack offers                |
| `mcp-servers/park-status-mcp` | Python MCP SDK (stdio)                | Park hours, attractions, live status, events for a date           |
| `mcp-servers/routing-mcp`     | Python MCP SDK (stdio)                | Route optimisation between attractions                            |

Wired with `docker-compose.yml`: Postgres, Redis, Rails, FastAPI, Celery worker,
Celery beat, **Flower** (task observability) and **MailCatcher** (magic-link
testing). One `docker compose up` and the whole stack runs without a GPU.

```
              ┌──────────────────────────┐
              │  Next.js (web)           │
              └──────────┬───────────────┘
                         │ JSON / SSE
              ┌──────────▼───────────────┐        magic-link email
              │  Rails 8 API             ├──▶ MailCatcher / SMTP
              └──────────┬───────────────┘
                         │ HTTP (/chat, /chat/greet)
              ┌──────────▼───────────────┐
              │  AI Orchestrator         │── Celery ──▶ Flower UI
              │  (FastAPI + LlamaIndex)  │
              └──────────┬───────────────┘
                         │ MCP (stdio)
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   tickets-mcp     park-status-mcp    routing-mcp
```

---

## 4. The four agents

Pavo is a **multi-agent orchestrator**, not a single prompt. A fast keyword
classifier (with an LLM fallback) routes each user message to the right
specialist — every agent has its own system prompt, its own MCP fact block, and
its own quick-reply chips.

| Intent       | Agent              | Mission                                                 |
|--------------|--------------------|---------------------------------------------------------|
| `planner`    | PlanningAgent      | Build a 3–5 step itinerary for the date + party         |
| `companion`  | CompanionAgent     | Practical Q&A in the park (toilets, ages, horaires)     |
| `concierge`  | ConciergeAgent     | Ticket simulation, pack offers, confirmation flow       |
| `detective`  | DiscoveryAgent     | Games, badges, secrets — playful family discovery       |

All four agents share the **`SessionContext`** (date, party, tickets, history,
preferences, group, processed media). None of them branches on
`ticket.purchased` — the agnostic-features rule is enforced architecturally.

---

## 5. Why this design wins (the *advantages*)

### 5.1 Agnostic features — no purchase wall

Simulated and purchased tickets are interchangeable for planning, routing, and
recommendations. A curious visitor gets the *same* quality of help as a paying
one. Conversion follows trust, not extortion.

### 5.2 Model-agnostic, YAML-routed LLM layer

`app/config/models.yaml` declares providers (OpenAI, Anthropic, vLLM,
local stub) and assigns a **chain of models per task**. Want to swap GPT-4o for
Claude Haiku for the companion mode? Edit one line — no code change, no rebuild.

```yaml
tasks:
  planning:    [gpt-4o,      claude-opus-4-6,  claude-haiku-4-5, stub-chat]
  concierge:   [gpt-4o-mini, claude-haiku-4-5, stub-chat]
  companion:   [gpt-4o-mini, claude-haiku-4-5, stub-chat]
```

If the preferred provider isn't configured, isn't available, or returns an empty
reply, the router walks down the chain automatically.

### 5.3 Hard usage budget per group / per session

Every LLM call is wrapped by `Router.call(...)` which writes an `ai_usage_logs`
row (provider, model, task, prompt_tokens, completion_tokens, **cost_usd**,
latency_ms, status). When today's spend hits the configured cap (default
`$5/day`), the router **downgrades** rather than failing — the user sees a reply
served by the cheapest fallback, the operator sees the downgrade in the logs.

### 5.4 MCP — tools that lie can't lie here

Prices, opening hours, attractions and events come from MCP servers, not from
the LLM's imagination. The Concierge agent literally cannot quote a price the
catalogue doesn't know — `create_pack_offer` re-prices server-side.

### 5.5 Determinism where it matters

`park-status-mcp` seeds wait-time jitter from `(attraction_id, date)`. Replans
return identical numbers. Maintenance windows are pre-declared so tests can
assert them.

### 5.6 Hackathon-ready dev loop

`docker compose up` boots the whole stack with a stub LLM, a fake SMTP server
(MailCatcher at :1080), and Flower at :5555. No GPU, no API keys, no cloud
account required to demo the full flow.

### 5.7 Test coverage where it would hurt to break

- Rails: RSpec
- AI orchestrator: pytest
- MCP tickets: pytest with `httpx.MockTransport` (no live API needed)
- MCP park-status: pytest covering fixtures, weekend logic, jitter, handlers
- Web: `npm test`

---

## 6. Possibilities for the future

Most of these are *small* additions because the architecture is already shaped
for them.

### 6.1 Observability & monitoring of AI usage

- **Live cost dashboard.** `ai_usage_logs` already records cost, latency, status
  per call. A `/admin/usage` endpoint is stubbed; wiring it to **Grafana** (with
  Postgres as the data source) gives a per-group spend chart in an afternoon.
- **Flower** is already in the compose file — Celery task latency, queue depth,
  worker health are one click away.
- **Per-task latency histograms** (planner vs. companion vs. concierge) by
  grouping `ai_usage_logs.task_type, model`.
- **Downgrade alerts.** A scheduled Celery beat job that pings Slack when
  `status=fallback` exceeds a threshold for the day.
- **OpenTelemetry traces** through the agent → router → MCP call chain.

### 6.2 Measuring satisfaction

- **Inline thumbs up/down** on every assistant reply, persisted in
  `chat_messages.metadata` (the migration `20260416120000_add_metadata_to_chat_messages`
  is already applied).
- **End-of-visit survey** triggered by Celery beat the evening of the visit
  date.
- **Conversion funnel.** Simulated → confirmed ticket conversion is a one-line
  query on the existing schema (`tickets.purchased` flips at confirmation).
- **Drop-off analysis.** `chat_messages` keep ordered history per session;
  trivial to compute "messages until first booking" or "abandoned plans".
- **CSAT correlated with model.** Join `chat_messages.metadata.feedback` with
  `ai_usage_logs.model` to find which model actually delights visitors.

### 6.3 Easy integrations

The agent layer is **tool-agnostic** by construction (MCP), and the LLM layer is
**provider-agnostic** by construction (YAML). New capabilities are *new MCP
servers*, never agent rewrites.

| Integration              | What to add                                                  | Touch points                |
|--------------------------|--------------------------------------------------------------|-----------------------------|
| Real ticketing backend   | Swap `tickets-mcp` Rails proxy for the partner API           | One MCP server              |
| Weather-aware planning   | New `weather-mcp` exposing `forecast(date)`                  | Register in `MCPClientManager` |
| Multilingual visitors    | Per-task model swap to a multilingual model in `models.yaml` | YAML only                   |
| Loyalty / pass holders   | New scope on `Group`, expose via session context             | Rails + SessionContext      |
| Mobile push reminders    | Celery beat job using existing session/group data            | Orchestrator only           |
| Voice interface          | `/media/upload` already accepts audio; wire ASR provider     | `media_asr` task in YAML    |
| Image of a map / sign    | `/media/upload` accepts images; wire vision provider         | `media_ocr` task in YAML    |

### 6.4 Scaling out

- **Read-only MCP servers can be HTTP-transport** instead of stdio, deployed
  independently and shared across replicas. The `MCPServerConfig` already
  models that transport.
- **Stateless FastAPI**. Horizontal scale is just replicas behind a load
  balancer — sessions live in Postgres, not in memory.
- **Celery worker autoscaling** for media processing + async chat.
- **Per-group budgets** make multi-tenant SaaS possible without a single line of
  pricing-tier code.

### 6.5 Real-deployment polish (deliberately *out of scope* for the hackathon)

- Terraform / Kubernetes manifests
- Real vLLM GPU runtime (the OpenAI-compatible endpoint is already wired)
- Production SMTP, JWT rotation, rate-limit tier per group
- WCAG audit on the chat UI
- GDPR data-export / data-erasure endpoints (the data is already namespaced by
  user → session → tickets/messages, so the migration is mechanical)

---

## 7. The single most important architectural decision

> **The LLM never holds a fact. It holds a personality.**

Prices come from the catalogue. Hours come from `park-status-mcp`. Wait times
come from a deterministic seed. The agent's job is to *talk like Pavo* — warm,
French, concise, helpful — about facts the system gives it. That is why we can
swap models without anyone noticing, why we can cap costs without breaking the
product, and why a mistake in the LLM can never sell a visitor a ticket that
doesn't exist.

---

## 8. Try it

```bash
cp .env.example .env
docker compose up --build

# Web         http://localhost:3000
# Rails API   http://localhost:3001
# AI service  http://localhost:8000   (FastAPI docs at /docs)
# Flower      http://localhost:5555
# MailCatcher http://localhost:1080   (catches magic-link emails)
```

Pick a date, fill the party, check your inbox in MailCatcher, click the magic
link — and start chatting with Pavo.
