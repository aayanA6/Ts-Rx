# HackCanada

Self-healing network/service dashboard with a React frontend and a FastAPI analysis backend.

## Repo structure

- `src/`: frontend dashboard (Vite + React + TypeScript)
- `analysis_agent/`: backend incident analysis service (FastAPI + Postgres + Gemini)
- `extension/`: built extension assets

## Frontend (Vite)

```bash
npm install
npm run dev
```

Frontend expects backend API at `/api/*`.
In local dev, Vite proxies `/api` to `http://127.0.0.1:8000`.

## Backend (analysis agent)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
uvicorn analysis_agent.main:app --reload
```

### Core API endpoints

- `POST /api/v1/analysis/jobs`
- `GET /api/v1/analysis/incidents`
- `GET /api/v1/analysis/jobs/{job_id}`
- `GET /api/v1/analysis/jobs/{job_id}/result`
- `GET /api/v1/analysis/jobs/{job_id}/summary`
- `GET /api/v1/analysis/jobs/{job_id}/download`

### Intake JSON format (Uptime Kuma style)

```json
{
  "monitor": "test-service",
  "status": "DOWN",
  "msg": "connection refused",
  "url": "https://example.com",
  "time": "2026-03-07T12:00:00Z"
}
```

Supported statuses for triage: `DOWN/down`, `DEGRADED/degraded`.

Optional teammate-provided extracted logs around the timestamp:

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

- No command execution path is implemented in backend.
- Suggested commands are text-only guidance.
- Code retrieval is read-only and constrained to allowlisted roots.
