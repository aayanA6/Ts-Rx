# Ts-Rx

**Self-healing incident triage for Tailscale networks.** When a service on your tailnet goes down, Ts-Rx figures out why and tells you what to do about it — before you've even opened a terminal.

Built at HackCanada 2026.

---

## The problem

If you're self-hosting more than a couple of services on a Tailscale network, you already know the drill: something goes down, your monitor pings you, and then you're SSH'd into three machines cross-referencing logs to figure out what actually broke. Uptime monitors tell you *that* something failed. They don't tell you *why*, and they definitely don't tell you what to do next.

## What Ts-Rx does

Ts-Rx sits on top of your existing monitoring (built for Uptime Kuma-style webhooks) and turns a raw "DOWN" alert into an actual diagnosis:

- **Per-service AI agents** — each monitored service gets its own dedicated agent that pulls in telemetry and log context to investigate incidents independently, so diagnoses don't get diluted across unrelated services.
- **Root-cause analysis, not just alerts** — incidents are analyzed against log snippets and metadata to produce a real hypothesis for what broke, not just a red status dot.
- **A "Doctor" tab inside Tailscale itself** — recovery suggestions and health status show up directly in the Tailscale interface via a browser extension, so you're not tab-switching between your monitor and your dashboard mid-incident.
- **Incident memory** — every investigation (successful diagnosis or fallback check) is written to that service's own notes file, so the next time it breaks for a similar reason, the agent starts from history instead of a blank slate.
- **Read-only by design** — Ts-Rx diagnoses and suggests. It does not execute commands. See [Safety constraints](#safety-constraints).

## Architecture

```
                 ┌─────────────────────┐
  Uptime Kuma /  │                     │
  monitor webhook├──▶  analysis_agent  │  FastAPI + Postgres
  (DOWN/DEGRADED)│   (backend)         │  Gemini-powered root-cause analysis
                 └─────────┬───────────┘
                           │
                 ┌─────────▼───────────┐
                 │   src/ (frontend)   │  Vite + React + TypeScript
                 │   dashboard         │
                 └─────────┬───────────┘
                           │
                 ┌─────────▼───────────┐
                 │   extension/        │  "Doctor" tab injected into
                 │                     │  the Tailscale interface
                 └─────────────────────┘
```

## Tech stack

**Frontend:** Vite, React, TypeScript
**Backend:** FastAPI, Postgres, Gemini
**Extension:** Browser extension injecting into the Tailscale UI

## Getting started

### Frontend

```bash
npm install
npm run dev
```

The frontend expects the backend API at `/api/*`. In local dev, Vite proxies `/api` to `http://127.0.0.1:8000`.

### Backend (analysis agent)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
uvicorn analysis_agent.main:app --reload
```

## API

| Endpoint | Description |
|---|---|
| `POST /api/v1/analysis/jobs` | Submit a new incident for analysis |
| `GET /api/v1/analysis/incidents` | List tracked incidents |
| `GET /api/v1/analysis/jobs/{job_id}` | Check job status |
| `GET /api/v1/analysis/jobs/{job_id}/result` | Get the full analysis result |
| `GET /api/v1/analysis/jobs/{job_id}/summary` | Get a short summary of the result |
| `GET /api/v1/analysis/jobs/{job_id}/download` | Download the result |

### Intake format (Uptime Kuma–style webhook)

Supported statuses for triage: `DOWN` / `down`, `DEGRADED` / `degraded`.

```json
{
  "monitor": "test-service",
  "status": "DOWN",
  "msg": "connection refused",
  "url": "https://example.com",
  "time": "2026-03-07T12:00:00Z"
}
```

Optionally, include log context pulled from around the timestamp for better diagnosis:

```json
{
  "monitor": "test-service",
  "status": "DOWN",
  "msg": "connection refused",
  "url": "https://example.com",
  "time": "2026-03-07T12:00:00Z",
  "log_snippets": [
    {
      "timestamp": "2026-03-07T11:59:50Z",
      "source": "service.log",
      "line": "dial tcp 10.0.0.12:443: connect: connection refused"
    }
  ],
  "metadata": {
    "device_or_node": "mac-mini-1"
  }
}
```

## Incident diagnosis: agentic per-service specialists

Each incident is diagnosed by a two-tier agent system, not a single generic Gemini call:

- `analysis_agent/orchestrator.py` — the main agent. Watches every incident regardless of
  service, and deploys (or reuses) a specialist for that exact service.
- `analysis_agent/specialist.py` — one agent per service. Builds the diagnosis prompt and
  injects that service's own incident history into it, so recurring failures get recognized
  instead of re-diagnosed from scratch each time.
- `analysis_agent/service_kb.py` — after every diagnosis (successful or fallback), appends an
  entry to that service's knowledge base at `data/service_kb/<service>.md` (gitignored, one
  markdown file per service).

If the Gemini call fails, the orchestrator falls back to `analysis_agent/fallback.py`'s
deterministic report — the knowledge base still gets an entry either way, so failures are
tracked too.

See `test/agentic-demo.html` for a self-contained walkthrough of a live run across 3 services
(open it directly in a browser — no server needed).

## Safety constraints

- No command execution path is implemented in the backend.
- Suggested commands are text-only guidance — nothing runs automatically.
- Code retrieval is read-only and constrained to allowlisted roots.

## Repo structure

- `src/` — frontend dashboard (Vite + React + TypeScript)
- `analysis_agent/` — backend incident analysis service (FastAPI + Postgres + Gemini)
- `extension/` — built extension assets (Tailscale "Doctor" tab)

## License

MIT — see [LICENSE](LICENSE).
