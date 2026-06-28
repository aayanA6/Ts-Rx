#!/usr/bin/env bash
# TS-RX connector agent
# Monitors local services and reports incidents to a TS-RX server
#
# Install:
#   curl -fsSL https://your-tsrx-server/connector/tsrx-agent.sh -o /usr/local/bin/tsrx-agent
#   chmod +x /usr/local/bin/tsrx-agent
#
# Configure: /etc/tsrx-agent.conf
#   TSRX_URL=https://your-tsrx-server
#   TSRX_API_KEY=tsrx_your_key_here
#   SERVICES="http://localhost:3000 http://localhost:8080 tcp://localhost:5432"
#   CHECK_INTERVAL=30
#
# Run as a systemd service:
#   tsrx-agent install
set -euo pipefail

CONFIG_FILE="${TSRX_CONFIG:-/etc/tsrx-agent.conf}"
[[ -f "$CONFIG_FILE" ]] && source "$CONFIG_FILE"

TSRX_URL="${TSRX_URL:?Set TSRX_URL in $CONFIG_FILE}"
TSRX_API_KEY="${TSRX_API_KEY:?Set TSRX_API_KEY in $CONFIG_FILE}"
SERVICES="${SERVICES:-}"
CHECK_INTERVAL="${CHECK_INTERVAL:-30}"
NODE_NAME="${NODE_NAME:-$(hostname)}"

declare -A DOWN_SINCE

check_http() {
  local url="$1"
  local code
  code=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
  [[ "$code" =~ ^(2|3) ]] && echo "UP" || echo "DOWN:HTTP $code"
}

check_tcp() {
  local host="${1##tcp://}"
  local h="${host%%:*}"
  local p="${host##*:}"
  timeout 5 bash -c ">/dev/tcp/$h/$p" 2>/dev/null && echo "UP" || echo "DOWN:connection refused"
}

report_incident() {
  local monitor="$1" status="$2" msg="$3"
  local payload
  payload=$(cat <<EOF
{
  "monitor": "$monitor",
  "status": "$status",
  "msg": "$msg",
  "url": "$monitor",
  "time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "metadata": {"device_or_node": "$NODE_NAME"}
}
EOF
)
  curl -sf -X POST \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "${TSRX_URL}/api/v1/ingest/${TSRX_API_KEY}" >/dev/null 2>&1 || true
}

install_systemd() {
  cat > /etc/tsrx-agent.conf <<CONF
TSRX_URL=https://your-tsrx-server
TSRX_API_KEY=tsrx_your_key_here
SERVICES="http://localhost:3000 http://localhost:8080"
CHECK_INTERVAL=30
NODE_NAME=$(hostname)
CONF

  cat > /etc/systemd/system/tsrx-agent.service <<SVC
[Unit]
Description=TS-RX connector agent
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/tsrx-agent run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVC

  systemctl daemon-reload
  systemctl enable tsrx-agent
  echo "Installed. Edit /etc/tsrx-agent.conf then: systemctl start tsrx-agent"
}

run_loop() {
  echo "[tsrx-agent] Starting — monitoring ${SERVICES:-"(no services configured)"}"
  while true; do
    for svc in $SERVICES; do
      if [[ "$svc" =~ ^tcp:// ]]; then
        result=$(check_tcp "$svc")
      else
        result=$(check_http "$svc")
      fi

      if [[ "$result" == "UP" ]]; then
        if [[ -n "${DOWN_SINCE[$svc]+x}" ]]; then
          report_incident "$svc" "UP" "Service recovered"
          unset "DOWN_SINCE[$svc]"
        fi
      else
        msg="${result#*:}"
        if [[ -z "${DOWN_SINCE[$svc]+x}" ]]; then
          DOWN_SINCE[$svc]=$(date +%s)
          report_incident "$svc" "DOWN" "$msg"
          echo "[tsrx-agent] DOWN: $svc — $msg"
        fi
      fi
    done
    sleep "$CHECK_INTERVAL"
  done
}

case "${1:-run}" in
  run)     run_loop ;;
  install) install_systemd ;;
  *)       echo "Usage: tsrx-agent [run|install]" ;;
esac
