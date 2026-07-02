# TS-RX — Ship-by-Friday Plan

**Today:** Wednesday, July 1, 2026  
**Target:** Running production instance, end of Friday July 4, 2026  
**Time budget:** ~3 days (Wed afternoon, Thu, Fri)

> Items marked **(YOU)** require action from you specifically — API key, provisioning, DNS, etc. They're blocking by nature and can't be done by AI or automated away.

---

## Status snapshot (what's already done)

- [x] Full backend (FastAPI + Postgres + Redis + Gemini AI)
- [x] Full frontend (React + TypeScript + Tailwind)
- [x] JWT auth with rate limiting and startup enforcement
- [x] CORS fixed (was broken by spec)
- [x] Incident → AI analysis → proposed fix → resolve flow
- [x] `ProposedFixView` now returns `markdown`, `destructiveActions`, `targetNode`, `detectedAt`
- [x] IncidentCard shows real data (no hardcoded IPs/versions)
- [x] ReviewModal wired to resolve endpoint
- [x] Dead code removed; .gitignore fixed
- [x] Docker Compose prod stack + Tailscale variant
- [x] Connector agent (`connector/tsrx-agent.sh`)
- [x] Pushed to GitHub at `aayanA6/Ts-Rx` (4 commits ahead before today)

---

## Wednesday, July 1 — Fix blockers, get keys, decide infra (~2–3 hrs)

### Code fixes (30 min, blocking)

- [ ] **Fix `.env.example`** — two wrong values that will trip up anyone following SETUP.md:
  - `GEMINI_MODEL=gemini-1.5-flash` → should be `gemini-2.5-flash` (matches `config.py` default)
  - `VITE_API_BASE_URL=http://127.0.0.1:8000` → should be empty; comment explaining when to set it
  - Add `JWT_SECRET=` with a `# openssl rand -hex 64` comment
  - Add `APP_URL=http://localhost:5173` with a note to set to real URL in prod
  - Add `CORS_ORIGINS=` (blank, with comment)

- [ ] **Fix `ALLOWED_READ_ROOTS` for Docker deployments** — default is `src,services,config`. In the Docker container `/app/src` contains the frontend JS build output — Gemini reads JS bundle files as "code context", which is irrelevant noise. Either change the default to empty (`""`) or add a `DEPLOYMENT_CONTEXT_ROOTS` env override. For now: document it in SETUP.md (done). Low priority for functionality — AI still works, just wastes some context tokens.

### **(YOU)** Get a Gemini API key (5 min, blocking)

1. Go to **https://aistudio.google.com/app/apikey**
2. Create a key, copy it — starts with `AIza...`
3. Verify it works: `curl "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY"` should return a list of models

### **(YOU)** Decide where to run production (15–30 min, blocking)

Pick **one** of:

**A) Tailscale homelab machine** (recommended for this project)
- Requires: a machine on your Tailscale network, Docker installed, always-on
- No domain, no TLS certs needed
- App is only accessible to devices on your Tailnet
- URL will be something like `http://100.x.y.z` or `http://hostname.your-tailnet.ts.net`

**B) VPS with a domain** (publicly accessible)
- Requires: VPS (DigitalOcean/Hetzner/etc., ~$6/mo), domain, DNS pointed at VPS
- Need to provision TLS certs (certbot) before nginx starts

---

## Thursday, July 3 — Deploy, verify E2E, wire first monitor (~4–6 hrs)

### **(YOU)** Provision and prep the server (30–60 min)

For Tailscale path:
```bash
# On the machine:
# 1. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER  # then re-login

# 2. Clone the repo
git clone https://github.com/aayanA6/Ts-Rx.git && cd Ts-Rx

# 3. Create .env (see SETUP.md §9 for all vars)
cat > .env <<EOF
GEMINI_API_KEY=AIza...
JWT_SECRET=$(openssl rand -hex 64)
POSTGRES_PASSWORD=$(openssl rand -hex 16)
APP_URL=http://$(tailscale ip -4)
ENVIRONMENT=production
EOF
```

For VPS path — also:
```bash
# Point your domain's A record at the VPS IP first (TTL 60 for fast propagation)
# Then get certs:
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com
mkdir -p certs
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem certs/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem certs/
sudo chmod 644 certs/*.pem
```

### Start the stack (30 min)

```bash
# Tailscale path:
docker compose -f docker-compose.yml -f docker-compose.tailscale.yml --profile tailscale up -d --build

# VPS+TLS path:
docker compose --profile prod up -d --build
```

Check logs:
```bash
docker compose logs -f backend   # look for "Worker started", no startup errors
docker compose logs backend | grep -i "JWT\|CORS\|startup"
```

### First-run checklist (30 min)

- [ ] `curl http://<server>/health` → `{"status":"ok"}`
- [ ] Open the UI in browser → see login screen
- [ ] Register an account
- [ ] Go to Settings → create an API key → copy it
- [ ] Send a test incident via curl (see SETUP.md §7 Option C)
- [ ] Wait ~15–30s → check Doctor tab → should see incident with AI analysis
- [ ] Click "Review Suggestions" → verify the modal opens with real content
- [ ] Click "Mark Resolved" → incident disappears from the list (or stays if "Show resolved" is on)

### Wire up first real service (30–45 min)

- [ ] Pick one service you actually want to monitor (Plex, Home Assistant, Postgres, etc.)
- [ ] Install connector agent on the host running that service (see SETUP.md §7)
- [ ] Edit `/etc/tsrx-agent.conf` with real URL, API key, service URL, NODE_NAME
- [ ] `sudo systemctl start tsrx-agent && sudo systemctl status tsrx-agent`
- [ ] Verify: stop the service → wait ≤30s → incident appears in dashboard
- [ ] Restart the service → incident auto-resolves

---

## Friday, July 4 — Polish, harden, optional extras (~2–4 hrs)

*Note: US Independence Day — adjust if needed. Treat as a buffer day.*

### Hardening (1 hr, blocking for production)

- [ ] **Cert renewal** (VPS path only): set up cron for certbot renewal + nginx reload
- [ ] **Firewall**: ensure only port 80/443 (or 80 for Tailscale) is open; port 8000 should NOT be public (it's behind nginx in prod, but verify)
- [ ] **Postgres backup**: set up a cron for `pg_dump` if you care about incident history persisting
  ```bash
  # Example cron: daily at 2am
  0 2 * * * docker compose exec -T postgres pg_dump -U tsrx tsrx | gzip > /backup/tsrx-$(date +%F).sql.gz
  ```
- [ ] **Log rotation**: Docker logs can grow unbounded; configure `--log-driver json-file` with max-size if not already set

### Nice-to-have (2–3 hrs, not blocking)

- [ ] **Chrome extension** — if you use tailscale.com/admin regularly:
  - Run `npm run build` (builds to `dist/`)
  - Load `extension/` as unpacked extension in Chrome
  - Verify "Doctor" tab appears on tailscale.com/admin

- [ ] **Notifications** — configure Discord/Slack webhook or SMTP in Settings tab:
  - Discord: Server settings → Integrations → Webhooks → New webhook → Copy URL → paste in TS-RX Settings
  - Slack: Create Incoming Webhook app → copy URL → paste in TS-RX Settings

- [ ] **Add more monitored services** — repeat the connector agent install on each host

- [ ] **Uptime Kuma integration** — if you run Uptime Kuma, point a webhook at `https://your-server/api/v1/ingest/<API_KEY>`

---

## Known limitations to be aware of (not blocking but should know)

| Issue | File | Impact | Fix effort |
|-------|------|--------|------------|
| `ALLOWED_READ_ROOTS` in Docker reads frontend JS build, not homelab code | `config.py:29` | AI gets irrelevant code context | Set `ALLOWED_READ_ROOTS=` (empty) in production `.env` — 2 min |
| `create_all` doesn't apply `ALTER TABLE` | `main.py` `on_startup` | Future schema changes require manual DDL or DB recreate | Low until schema changes |
| Rate limiter is in-process only | `limiter.py` | Multi-worker deployments share nothing (default is 1 worker so fine) | Replace with Redis-backed slowapi when scaling |
| Extension hardcodes `API_BASE = 'http://127.0.0.1:8000'` | `extension/content.js:1` | Extension only works with local backend | Change hardcoded value to your server URL; rebuild extension |
| `apiBase` URL param passed to iframe is ignored | `src/App.tsx` | Extension's `apiBase=` param has no effect; API base is baked in at build time | Not needed for single-server deployments |
| SMTP notifications untested | `analysis_agent/notifier.py` | Email notifications may silently fail | Test with a real SMTP provider |
| No automated tests for auth/routes | `tests/` | Regressions possible | Add pytest suite — medium effort |
| Connector script uses Linux `date` format | `connector/tsrx-agent.sh:51` | Won't work on macOS hosts | Add BSD `date` fallback if monitoring macOS |
| WebSocket reconnect has no exponential backoff | `src/components/Dashboard.tsx:61` | Rapid reconnect storm if backend is down | Add jitter/backoff — 15 min |

---

## Summary: what YOU need to do vs what's code

| Task | Who | When |
|------|-----|-------|
| Get Gemini API key | **YOU** | Wed (today) |
| Pick and provision a server | **YOU** | Wed/Thu |
| Set up DNS (VPS path) | **YOU** | Thu |
| Get TLS certs (VPS path) | **YOU** | Thu |
| Set `JWT_SECRET`, `POSTGRES_PASSWORD`, `APP_URL` in `.env` | **YOU** | Thu |
| Fix `.env.example` errors | Code | Wed |
| Start Docker stack | Automate / you | Thu |
| Register account + generate API key | **YOU** (in UI) | Thu |
| Install connector on first service | **YOU** | Thu |
| Set up cert renewal cron | **YOU** | Fri |
| Configure notifications (optional) | **YOU** (in UI) | Fri |
| Add more monitors | **YOU** | Fri+ |
