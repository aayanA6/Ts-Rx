# TS-RX Setup Guide

AI-powered incident triage for homelab/Tailscale services. This guide takes you from zero to a running instance.

---

## Prerequisites

| Tool | Why | Min version |
|------|-----|-------------|
| Docker + Docker Compose | Runs the full stack (Postgres, Redis, backend, nginx) | Docker 24+ |
| Node.js + npm | Frontend dev server / build | Node 20+ |
| Python 3.11+ | Local backend dev (not needed for Docker path) | 3.11 |
| Git | Clone the repo | any |
| curl / bash | Connector agent, testing | any |

Optional:
- A Linux VPS or homelab machine with a public/Tailscale IP (for production deployment)
- A domain name (for TLS path) OR a Tailscale account (for Tailscale path — no domain needed)
- Chrome (for the browser extension)

---

## 1. Get a Gemini API key

The backend requires `GEMINI_API_KEY` to run AI analysis. Without it the app boots but every incident falls back to keyword heuristics.

1. Go to **https://aistudio.google.com/app/apikey**
2. Click **Create API key** → select any Google Cloud project (or create one)
3. Copy the key — it starts with `AIza...`
4. Keep it handy for the `.env` step below

The project uses `gemini-2.5-flash` by default (fast, cheap, good at structured JSON output). Free-tier API access is sufficient for low-volume homelab use.

---

## 2. Clone the repo

```bash
git clone https://github.com/aayanA6/Ts-Rx.git
cd Ts-Rx
```

---

## 3. Local development (no Docker)

Use this path to iterate on code. Requires Postgres and Redis running locally (Docker is the easiest way to get just those).

### 3a. Start Postgres and Redis

```bash
docker compose up postgres redis
```

This starts Postgres on port 5432 and Redis on 6379. Data persists in named Docker volumes.

### 3b. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env
```

Edit `.env` — the **required** fields:

```env
GEMINI_API_KEY=AIza...             # your key from step 1
JWT_SECRET=                        # generate: openssl rand -hex 64
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/analysis_agent
```

Leave `VITE_API_BASE_URL` **empty** in `.env` for local dev — Vite's proxy handles `/api`, `/auth`, `/ws` to port 8000. Only set it if you're running the frontend in extension/embedded mode pointing at a remote backend.

Start the backend:

```bash
uvicorn analysis_agent.main:app --reload
```

The backend is at **http://localhost:8000**. On first start it creates all database tables automatically.

### 3c. Frontend

```bash
npm install
npm run dev
```

The frontend is at **http://localhost:5173**. API calls proxy to port 8000 automatically.

---

## 4. Production deployment

Two options:

- **Option A — nginx with TLS** — for a VPS with a domain name (Let's Encrypt)
- **Option B — Tailscale** — for a homelab machine; Tailscale handles encryption, no domain needed

### 4a. Required environment variables

Create a `.env` file on the server (never commit this):

```env
# Required
GEMINI_API_KEY=AIza...                    # from step 1
JWT_SECRET=<64-char random hex>           # openssl rand -hex 64
POSTGRES_PASSWORD=<strong password>       # pick something strong

# Set to your public URL (used for CORS and notification links)
APP_URL=https://your-domain.com           # Option A
# APP_URL=http://100.x.y.z               # Option B (your Tailscale IP or MagicDNS name)

# Optional notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=noreply@your-domain.com
```

### Option A — nginx + TLS (domain required)

1. **Get TLS certificates** (on the server):
   ```bash
   # Using certbot + standalone (stop nginx first if running)
   sudo certbot certonly --standalone -d your-domain.com
   # Certs go to /etc/letsencrypt/live/your-domain.com/
   ```

2. **Mount certs into the project**:
   ```bash
   mkdir -p certs
   sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem certs/
   sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem certs/
   sudo chmod 644 certs/*.pem
   ```
   The `nginx/nginx.conf` expects `./certs/fullchain.pem` and `./certs/privkey.pem`.

3. **Build and start everything**:
   ```bash
   docker compose --profile prod up -d --build
   ```
   This starts: postgres → redis → backend → frontend → nginx (with TLS).

4. **Set up cert renewal** (cron):
   ```bash
   # Add to crontab -e
   0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/your-domain.com/*.pem /path/to/Ts-Rx/certs/ && docker compose -f /path/to/Ts-Rx/docker-compose.yml exec nginx nginx -s reload
   ```

### Option B — Tailscale (no domain, no certs)

Best for homelab where you're on your own Tailscale network. Tailscale handles encryption between devices — no TLS certs needed.

1. **Install Tailscale** on the server if not already: https://tailscale.com/download
2. **Find your Tailscale IP**: `tailscale ip -4` (e.g. `100.x.y.z`) or use MagicDNS hostname
3. **Build and start with the Tailscale profile**:
   ```bash
   docker compose \
     -f docker-compose.yml \
     -f docker-compose.tailscale.yml \
     --profile tailscale up -d --build
   ```
   This uses `nginx/nginx-tailscale.conf` (HTTP only on port 80). Tailscale encrypts in transit.

4. Set `APP_URL=http://100.x.y.z` (or `http://hostname.your-tailnet.ts.net`) in `.env`.

---

## 5. First run: create an account

1. Open the app URL (http://localhost:5173 for dev, or your server URL)
2. You'll see the login screen — click **Register**
3. Enter an email and password (min 8 chars) — this is only stored in your own Postgres
4. You're now logged in

> **Note:** There is no email verification. The first registered account is just as privileged as any other. This is a single-user or small-team tool — there's no admin/user role distinction.

---

## 6. Generate an API key

The connector agent and Uptime Kuma use an **API key** (not JWT) to send incident webhooks.

1. Go to **Settings** tab → scroll to **API Keys**
2. Click **New Key** and give it a label (e.g. "homelab-connector")
3. Copy the key — it is shown **once only** (starts with `tsrx_...`)
4. This key goes into your connector config or Uptime Kuma webhook URL

---

## 7. Wire up a monitor

### Option A — connector agent (recommended for homelab)

The connector checks HTTP endpoints and TCP ports on a loop and reports incidents.

**On each host you want to monitor:**

```bash
# Download
curl -fsSL https://raw.githubusercontent.com/aayanA6/Ts-Rx/main/connector/tsrx-agent.sh \
  -o /usr/local/bin/tsrx-agent
chmod +x /usr/local/bin/tsrx-agent

# Install (creates /etc/tsrx-agent.conf and a systemd service)
sudo tsrx-agent install
```

Edit `/etc/tsrx-agent.conf`:

```bash
TSRX_URL=https://your-domain.com        # or http://100.x.y.z for Tailscale
TSRX_API_KEY=tsrx_your_key_here         # from step 6
SERVICES="http://localhost:3000 http://localhost:8080 tcp://localhost:5432"
CHECK_INTERVAL=30                        # seconds between checks
NODE_NAME=my-server                      # friendly name sent with incidents
```

```bash
sudo systemctl start tsrx-agent
sudo systemctl status tsrx-agent
```

### Option B — Uptime Kuma

Point any Uptime Kuma webhook at:
```
POST https://your-domain.com/api/v1/ingest/<API_KEY>
```
Uptime Kuma's heartbeat format is supported natively.

### Option C — custom webhook (curl test)

```bash
# Simulate a DOWN incident
curl -X POST https://your-domain.com/api/v1/ingest/<API_KEY> \
  -H "Content-Type: application/json" \
  -d '{
    "monitor": "My Service",
    "status": "DOWN",
    "msg": "Connection refused on port 8080",
    "url": "http://localhost:8080",
    "time": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "metadata": {"device_or_node": "my-server", "service_type": "http"}
  }'

# Wait 10-30s for AI analysis, then check the Doctor tab

# Resolve it
curl -X POST https://your-domain.com/api/v1/ingest/<API_KEY> \
  -H "Content-Type: application/json" \
  -d '{"monitor": "My Service", "status": "UP", "msg": "Recovered", "url": "", "time": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}'
```

---

## 8. Chrome extension (optional)

The extension adds a "Doctor" tab directly inside **tailscale.com/admin**, loading TS-RX in an iframe.

> **Limitation:** The extension always connects to `http://127.0.0.1:8000`. It only works when the backend is running locally on the same machine as your browser.

1. Build the extension bundle (the extension uses the already-built `dist/`):
   ```bash
   npm run build
   ```

2. Open `chrome://extensions` → enable **Developer mode** → **Load unpacked** → select the `extension/` folder

3. Navigate to **https://tailscale.com/admin** — a "Doctor" tab appears in the nav

---

## 9. Environment variable reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Google AI Studio key. Get at aistudio.google.com |
| `JWT_SECRET` | Yes (prod) | insecure default | Random 64-char hex. `openssl rand -hex 64` |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://postgres:postgres@localhost:5432/analysis_agent` | Postgres DSN |
| `POSTGRES_PASSWORD` | Prod | `changeme` | Password for the Docker Compose postgres service |
| `APP_URL` | Prod | `http://localhost:5173` | Public URL of the app. Used for CORS + notification links |
| `CORS_ORIGINS` | No | — | Extra CORS origins beyond APP_URL, comma-separated |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model name |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis DSN. WebSocket live updates require Redis |
| `ENVIRONMENT` | No | `dev` | Set to `production` to enforce JWT_SECRET |
| `SMTP_HOST` | No | — | SMTP server for email notifications |
| `SMTP_PORT` | No | 587 | — |
| `SMTP_USER` | No | — | — |
| `SMTP_PASS` | No | — | — |
| `ALLOWED_READ_ROOTS` | No | `src,services,config` | Comma-separated dirs Gemini can read for code context |
| `WORKER_ENABLED` | No | `true` | Set to `false` to disable background AI analysis |
| `VITE_API_BASE_URL` | No | `""` (uses Vite proxy) | Only set for extension / embedded mode with remote backend |

---

## 10. Verifying everything works

```bash
# Backend health
curl http://localhost:8000/health
# → {"status":"ok"}

# Send a test incident and check the Doctor tab in the browser
# (see step 7, Option C above)
```

Check the backend logs for `[worker]` messages — these show when AI analysis starts and completes.
