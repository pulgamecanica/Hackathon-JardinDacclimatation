# Pavo — Execution Plan

> Companion document to [`PRESENTATION.md`](./PRESENTATION.md).
> This one is for the people who will actually pay for, run, and maintain it.

---

## 1. Technology stack — separated by service

### 1.1 Web — `services/web`

| Concern              | Choice                                      |
|----------------------|---------------------------------------------|
| Framework            | Next.js **16.2** (App Router, RSC)          |
| UI runtime           | React **19.2**                              |
| Styling              | Tailwind CSS **4** + PostCSS                |
| State (client-side)  | Zustand **5** + `localStorage` persistence  |
| Language             | TypeScript **5**                            |
| Lint                 | ESLint **9** (`eslint-config-next`)         |
| Build target         | Node 20 in container                        |

**What lives here.** Calendar landing page, multi-step visit form, chat view
(SSE streaming), pack-offer cards, magic-link verify page. Session id and party
composition are persisted in `localStorage` so a refresh never loses context.

**Why these choices.**
- App Router + RSC keeps the marketing/landing surfaces fast and crawlable.
- Zustand instead of Redux — the global state is tiny (session, party, tickets).
- Tailwind 4 — design tokens come straight from the Figma export.

---

### 1.2 Rails API — `services/api`

| Concern              | Choice                                                      |
|----------------------|-------------------------------------------------------------|
| Framework            | Rails **8.1** (API mode)                                    |
| DB driver            | `pg` against PostgreSQL **16**                              |
| App server           | Puma + Thruster (HTTP/2 in front of Puma)                   |
| Auth                 | Magic-link email + JWT (`jwt` gem, `bcrypt` for shells)     |
| Serialization        | `jsonapi-serializer`                                        |
| CORS                 | `rack-cors`                                                 |
| Pagination           | Kaminari                                                    |
| Background mail      | Active Job + Action Mailer                                  |
| Deploy               | **Kamal** (already in Gemfile)                              |
| Observability        | `sentry-rails`, `prometheus-client`                         |
| Tests                | RSpec, FactoryBot, Faker, shoulda-matchers                  |
| Security tooling     | Brakeman, bundler-audit                                     |
| Style                | rubocop-rails-omakase                                       |

**What lives here.** Source of truth for users, groups, visit_sessions,
tickets, magic_links, chat_messages. The *one* place where `confirm_purchase!`
flips a ticket from simulated to purchased — that boundary is enforced with
DB-level locks and immutability validations on confirmed tickets.

**Why these choices.**
- Rails 8 ships **Solid Queue / Solid Cache / Solid Cable** — we currently use
  Redis, but the Rails-only queue is a one-config swap if we drop Redis later.
- Kamal makes the production rollout to a single VM literally `kamal deploy`.
- Magic link instead of password = less attack surface, no password reset flow.

---

### 1.3 AI Orchestrator — `services/ai-orchestrator`

| Concern              | Choice                                                                |
|----------------------|-----------------------------------------------------------------------|
| HTTP framework       | FastAPI + Uvicorn                                                     |
| Async task queue     | Celery 5 + Redis broker/backend, **Flower** UI                        |
| Settings             | pydantic-settings, YAML routing config                                |
| Database (analytics) | SQLAlchemy 2 + psycopg3, Alembic migrations                           |
| LLM SDKs             | `openai`, `anthropic`, OpenAI-compatible (vLLM), local stub           |
| Agent framework      | In-house `BaseAgent` (LlamaIndex pinned for future FunctionAgents)    |
| Tool layer           | Official `mcp` SDK, stdio transport                                   |
| Logging              | structlog (JSON-friendly)                                             |
| Metrics              | prometheus-client                                                     |
| Errors               | sentry-sdk                                                            |
| Media                | Pillow (image), stubbed OCR/ASR                                       |
| Tests                | pytest, pytest-asyncio, pytest-cov                                    |

**What lives here.** Multi-agent orchestrator (planner / companion /
concierge / detective), the YAML-driven model router with per-task chains and
per-group $/day cap, the MCP client manager, the media upload + Celery
processing pipeline, and the `ai_usage_logs` table that records every LLM
call (tokens, cost, latency, status).

**Why these choices.**
- FastAPI gives us SSE for streaming chat with very little ceremony.
- Celery + Flower gives us a free monitoring UI on day one.
- We keep our own thin `LLMProvider` abstraction so we can swap SDKs without
  rewriting agents — LlamaIndex is on standby for richer tool workflows.

---

### 1.4 MCP servers — `mcp-servers/*`

| Server              | Stack                       | Data source                   | Mutates? |
|---------------------|-----------------------------|-------------------------------|----------|
| `tickets-mcp`       | Python + `mcp` SDK + httpx  | Rails API + local catalogue   | yes (reversible until `confirm_purchase`) |
| `park-status-mcp`   | Python + `mcp` SDK          | In-memory fixtures            | no       |
| `routing-mcp`       | Python + `mcp` SDK          | Local route graph             | no       |

Each server is its own deployable, with its own Dockerfile, requirements,
README and pytest suite. Stdio transport in dev (child process); HTTP transport
is supported by `MCPServerConfig` for the production split.

---

### 1.5 Infra (compose)

| Component        | Image                       | Role                                  |
|------------------|-----------------------------|---------------------------------------|
| Postgres 16      | `postgres:16-alpine`        | Source of truth + analytics           |
| Redis 7          | `redis:7-alpine`            | Celery broker, Action Cable, cache    |
| MailCatcher      | `sj26/mailcatcher`          | Captures magic-link emails in dev     |
| Flower           | `mher/flower:2.0`           | Celery task observability             |

---

## 2. Time — what was built, and how long the rest takes

### 2.1 Already shipped (this hackathon scaffold)

| Slice                                                | Status | Notes |
|------------------------------------------------------|:------:|-------|
| Compose stack with 8 containers                      |   ✅   | One `docker compose up` |
| Rails API: sessions, tickets, groups, chat, magic links |   ✅   | RSpec covered |
| Magic-link auth + MailCatcher loop                   |   ✅   | No password flow |
| Next.js calendar + visit form + chat view            |   ✅   | French UI from Figma |
| Multi-agent orchestrator (4 agents)                  |   ✅   | Intent routing + persona |
| YAML-driven model router with chain fallback         |   ✅   | OpenAI / Anthropic / vLLM / stub |
| Per-group / per-session daily cap with downgrade     |   ✅   | `ai_usage_logs` + tracker |
| MCP tickets server (catalogue, pricing, packs)       |   ✅   | Server-side pricing |
| MCP park-status server (hours, attractions, events)  |   ✅   | Deterministic jitter |
| Pack offer rendering (clickable cards)               |   ✅   | Last commits on `main` |
| Proactive greeting on form submit                    |   ✅   | `/chat/greet` + Celery |
| Flower dashboard                                     |   ✅   | `:5555` |

### 2.2 Estimated effort to production-ready (one engineer)

| Item                                                     | Effort   |
|----------------------------------------------------------|----------|
| Real SMTP + DKIM/SPF + bounce handling                   | 1 day    |
| JWT rotation + refresh + revoke list                     | 1 day    |
| `/admin/usage` endpoint + Grafana dashboard              | 1–2 days |
| Inline thumbs-up/down feedback (UI + persistence)        | 1 day    |
| Routing-mcp real implementation (currently empty)        | 2–3 days |
| Real ticket catalogue + partner billing integration      | 3–5 days |
| Vision OCR provider wired into `media_ocr` task          | 1 day    |
| ASR provider wired into `media_asr` task                 | 1 day    |
| WCAG 2.1 AA pass on chat UI                              | 2 days   |
| GDPR data-export / data-erasure endpoints                | 2 days   |
| Kamal deploy + TLS + log shipping                        | 1 day    |
| Smoke + load tests in CI                                 | 1 day    |
| **Total to production**                                  | **~3 weeks for one engineer** |

---

## 3. Costs

### 3.1 Infrastructure (per month, one production environment)

Conservative estimate for a **single-park, ~10k chat sessions/month** load.
Assumes a small managed Postgres, Redis, one VM, object storage for media.

| Line item                              | Provider example       | Monthly USD |
|----------------------------------------|------------------------|-------------|
| App VM (4 vCPU / 8 GB) running compose | Hetzner CPX31, Fly.io  | 20 – 40     |
| Managed Postgres (small, 10 GB)        | Neon, Supabase, RDS    | 0 – 25      |
| Managed Redis (small)                  | Upstash, Railway       | 0 – 15      |
| Object storage for media (50 GB)       | R2, B2, S3             | 1 – 5       |
| Transactional email (10k/mo)           | Postmark, Resend       | 10 – 15     |
| Error monitoring                       | Sentry team            | 0 – 26      |
| Domain + TLS                           | Cloudflare             | 0 – 5       |
| **Infra subtotal**                     |                        | **~30 – 130** |

### 3.2 LLM cost — the variable line

The router lets us *prove* the bill instead of guessing. With the YAML chain in
place today (`gpt-4o-mini` for chat/companion/concierge, `gpt-4o` for planning,
Claude Haiku as fallback), ~800 prompt
tokens / 200 completion tokens average**:

| Model usage mix              | Cost / session (USD) | 10k sessions / mo |
|------------------------------|----------------------|-------------------|
| 100% gpt-4o-mini             | ~$0.0011             | **~$11**          |
| 80% mini + 20% gpt-4o        | ~$0.0030             | **~$30**          |
| 100% claude-haiku-4-5        | ~$0.0050             | **~$50**          |
| 100% gpt-4o (worst case)     | ~$0.0120             | **~$120**         |

The **per-group $5/day cap** is a hard ceiling — when reached, the router
downgrades to the cheapest configured fallback (typically `stub-chat` in dev,
`claude-haiku-4-5` in prod). The bill cannot run away.

> **Total ballpark:** ~$60 – $250/month for a small-park production deployment,
> with a single config file (`models.yaml`) controlling where on that range you
> land.

### 3.3 People cost

| Role              | Allocation after launch                  |
|-------------------|------------------------------------------|
| 1 backend / AI    | 0.3 FTE — agent tuning, MCP additions    |
| 1 frontend        | 0.1 FTE — chat UX iteration              |
| 1 ops / on-call   | shared rota — see §4.4                   |
| Park content lead | 0.1 FTE — keep catalogue + events fresh  |

---

## 4. Maintenance

### 4.1 Routine (zero or one engineer)

| Cadence  | Task                                                                     |
|----------|--------------------------------------------------------------------------|
| Daily    | Glance at Flower (queue depth) and Sentry (new errors)                   |
| Daily    | `ai_usage_logs` aggregate: yesterday's spend per group, downgrade rate   |
| Weekly   | Review thumbs-down replies, tune affected agent prompt                   |
| Weekly   | Bump catalogue + events fixtures if calendar changed                     |
| Monthly  | `bundler-audit` + `pip-audit` + `npm audit`                              |
| Monthly  | Re-evaluate `models.yaml` chain against latest model prices              |
| Quarterly| Restore-from-backup drill on Postgres                                    |

### 4.2 What is *not* maintenance you have to do

- **Adding a new model** — YAML edit, redeploy. Zero code change.
- **Switching provider for a single task** — YAML edit. Zero code change.
- **Capping a group of visitors** — change `daily_cap_usd`. Zero code change.
- **Killing a runaway conversation** — already automatic via the cap.
- **Replacing the price list** — edit `tickets-mcp/src/catalog.py` (could be
  promoted to a real DB table in <½ day).

### 4.3 Upgrade paths

| Layer       | Cadence       | Risk    | Notes                                          |
|-------------|---------------|---------|------------------------------------------------|
| Next.js     | yearly major  | low     | App Router stable, RSC mature                  |
| Rails       | yearly minor  | low     | LTS within 8.x line                            |
| FastAPI     | quarterly     | low     | Pinned to `>=`                                 |
| LLM SDKs    | as released   | medium  | Provider abstraction shields agent code        |
| MCP SDK     | as released   | medium  | Tool schemas may need re-validation            |

### 4.4 On-call

The system is small (six containers in a single compose). Reasonable on-call:

- **PagerDuty / Opsgenie** alert on: Postgres unavailable, Redis unavailable,
  Rails 5xx rate, FastAPI 5xx rate, Celery queue depth > N, daily LLM spend
  exceeds 2× moving average.
- Runbook lives in `/docs/runbook.md` (to be written; ~½ day).

### 4.5 Backups

- Postgres: daily logical dump (provider-managed) + 7-day PITR.
- Object storage: built-in versioning.
- Catalogue + park fixtures: in git already.
- Configuration: `.env` in a secret manager, never in git (`.env.example` is).

---

## 5. Scalability

The system is built for **horizontal scale by default**. Nothing critical is
in-process state.

### 5.1 Stateless tiers

| Tier                | Stateless? | How to scale                                   |
|---------------------|:----------:|------------------------------------------------|
| Next.js web         | yes        | Vercel-style or N replicas behind a load balancer |
| Rails API           | yes (sessions in DB) | Puma processes × replicas               |
| FastAPI orchestrator| yes        | N replicas behind a load balancer              |
| Celery workers      | yes        | `--concurrency` × replicas, autoscale on queue |

### 5.2 Stateful tiers

| Tier      | Limit reached at                  | Path forward                                                  |
|-----------|-----------------------------------|---------------------------------------------------------------|
| Postgres  | ~80% CPU on the small instance    | Vertical scale → read replicas → partition `ai_usage_logs` by month |
| Redis     | RAM pressure                      | Vertical scale → cluster mode for Celery broker               |
| Media     | Object storage is unbounded       | Add CDN in front for hot assets                               |

### 5.3 Concurrency profile

- Each chat reply currently makes **1** LLM call + **0–N** MCP tool calls.
- MCP servers are local processes — calls are cheap (microseconds within the
  pod, single-digit ms over HTTP).
- Streaming responses (SSE) means front-end perceived latency is bounded by
  *first token*, not full reply.

### 5.4 Cost-aware scaling

Because every LLM call is logged with cost, scaling triggers can be **money,
not load**:

- Auto-promote heavy users to a more expensive plan when their daily spend
  approaches the cap.
- Auto-downgrade *one* task family (say, `companion`) to a cheaper model when
  the global daily spend exceeds a threshold.
- Spawn a vLLM replica only during opening hours; YAML routes the heavy tasks
  to it during the window, back to OpenAI at night when traffic is low.

### 5.5 Multi-tenant readiness

`Group` already namespaces sessions; `ai_usage_logs.group_id` already
enforces per-tenant accounting. Adding a second park is:

1. Add a `tenant_id` column to `groups` and `visit_sessions` (one migration).
2. Add a tenant-aware MCP catalogue (per-park `tickets-mcp` instance, or one
   server with a `tenant` argument).
3. Per-tenant `daily_cap_usd` overrides loaded from DB instead of YAML.

The framework is there — it's a week of work, not a rewrite.

### 5.6 Failure modes & blast radius

| Failure                          | Effect                                       | Mitigation already in place           |
|----------------------------------|----------------------------------------------|---------------------------------------|
| Preferred LLM provider down      | Router walks chain to the next configured    | `_candidate_chain` in `router.py`     |
| Daily cap exhausted              | Replies served by cheapest fallback          | `cap_exhausted` short-circuit         |
| MCP server crashes               | Affected tools missing from `list_all_tools` | Agents degrade gracefully             |
| Rails down                       | New sessions fail; chat continues for live ones (history is in-memory of the chat stream) | Health check + restart |
| Postgres down                    | Hard outage                                  | Managed instance + PITR               |
| Mail delivery down               | Magic-link login fails                       | Retry via Active Job; multiple SMTP providers possible |

---

## 6. Path to production — a practical 3-week plan

| Week | Focus                                                                 |
|------|-----------------------------------------------------------------------|
| 1    | Real SMTP, JWT hardening, `/admin/usage` + Grafana, real catalogue source |
| 2    | Routing-mcp implementation, vision/ASR providers, thumbs feedback loop |
| 3    | WCAG pass, GDPR endpoints, Kamal deploy, load test, runbook, on-call rota |

After week 3 the system is a normal, boring web service — six containers, one
small VM, one managed DB, one managed Redis, one knob (`models.yaml`) for cost,
and a dashboard that shows you exactly where every euro is going.

---

## 7. The summary number

For a **single park, 10k visitor sessions per month**, at the cost mix our
default `models.yaml` produces today, total run cost is approximately:

```
Infra ........................  $30 – $130 / month
LLM (typical mix) ............  $30 – $50  / month
People (0.4 FTE post-launch) .  variable
─────────────────────────────────────────────────
Run cost / month ............. ~$60 – $180 in pure cloud spend
```

…and the cap means even an adversarial week cannot break that envelope.
