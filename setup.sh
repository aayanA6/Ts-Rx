#!/usr/bin/env bash
# TS-RX one-shot VPS setup script
# Usage: curl -fsSL https://your-repo/setup.sh | bash
# Or:    bash setup.sh
set -euo pipefail

REPO_URL="${TSRX_REPO:-https://github.com/Shay350/HackCanada-frontend}"
INSTALL_DIR="${TSRX_DIR:-/opt/tsrx}"

log() { echo -e "\033[1;34m[tsrx]\033[0m $*"; }
die() { echo -e "\033[1;31m[error]\033[0m $*" >&2; exit 1; }

# ── 1. Check OS ───────────────────────────────────────────────────────────────
[[ "$(id -u)" -eq 0 ]] || die "Run as root (sudo bash setup.sh)"
[[ -f /etc/debian_version ]] || die "This script targets Debian/Ubuntu"

# ── 2. Install Docker ─────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  log "Installing Docker..."
  curl -fsSL https://get.docker.com | bash
  systemctl enable docker --now
fi

if ! docker compose version &>/dev/null; then
  log "Installing Docker Compose plugin..."
  DOCKER_CONFIG=${DOCKER_CONFIG:-/usr/local/lib/docker}
  mkdir -p "$DOCKER_CONFIG/cli-plugins"
  curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
    -o "$DOCKER_CONFIG/cli-plugins/docker-compose"
  chmod +x "$DOCKER_CONFIG/cli-plugins/docker-compose"
fi

# ── 3. Clone repo ─────────────────────────────────────────────────────────────
log "Cloning TS-RX to $INSTALL_DIR..."
if [[ -d "$INSTALL_DIR" ]]; then
  git -C "$INSTALL_DIR" pull
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# ── 4. Generate .env ──────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  log "Creating .env from example..."
  cp .env.production.example .env

  # Auto-generate secrets
  JWT_SECRET=$(openssl rand -hex 64)
  POSTGRES_PASSWORD=$(openssl rand -hex 24)
  sed -i "s|change_me_generate_with_openssl_rand_hex_64|$JWT_SECRET|" .env
  sed -i "s|change_me_strong_password|$POSTGRES_PASSWORD|" .env

  log "Generated JWT_SECRET and POSTGRES_PASSWORD"
  log ""
  log "  ⚠️  Edit /opt/tsrx/.env and set:"
  log "     GEMINI_API_KEY=<your key>"
  log "     APP_URL=https://your-domain.com"
  log ""
  read -rp "  Press Enter after editing .env to continue (or Ctrl+C to exit now)..."
fi

# ── 5. Start services ─────────────────────────────────────────────────────────
log "Building and starting TS-RX..."
docker compose pull postgres redis
docker compose build backend frontend
docker compose up -d postgres redis backend frontend

log ""
log "✅ TS-RX is running!"
log "   Backend:  http://$(hostname -I | awk '{print $1}'):8000/health"
log ""
log "Add nginx reverse proxy (pick one):"
log "  Tailscale (no TLS needed — Tailscale encrypts for you):"
log "    docker compose -f docker-compose.yml -f docker-compose.tailscale.yml --profile tailscale up -d nginx"
log "  HTTPS with your own TLS certs (place fullchain.pem + privkey.pem in ./certs/):"
log "    docker compose --profile prod up -d nginx"
log ""
log "View logs: docker compose logs -f"
