#!/usr/bin/env bash
# notify.sh — send a push notification via ntfy.sh
#
# Usage:
#   ./scripts/notify.sh "메시지"
#   ./scripts/notify.sh "메시지" "제목" "우선순위"
#
# Priority values: min | low | default | high | urgent
#
# Required env var:
#   NTFY_TOPIC  — ntfy.sh topic name (e.g. my-project-alerts)
#                 Subscribe at: https://ntfy.sh/<NTFY_TOPIC>
#
# Optional env var:
#   NTFY_SERVER — custom ntfy server URL (default: https://ntfy.sh)

set -euo pipefail

NTFY_SERVER="${NTFY_SERVER:-https://ntfy.sh}"
TOPIC="${NTFY_TOPIC:-}"
MESSAGE="${1:-}"
TITLE="${2:-Notification}"
PRIORITY="${3:-default}"

# Validation
if [[ -z "$TOPIC" ]]; then
  echo "Error: NTFY_TOPIC environment variable is not set." >&2
  echo "  Set it in your shell or .env file:" >&2
  echo "  export NTFY_TOPIC=my-project-alerts" >&2
  exit 1
fi

if [[ -z "$MESSAGE" ]]; then
  echo "Usage: $0 \"message\" [\"title\"] [\"priority\"]" >&2
  exit 1
fi

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${NTFY_SERVER}/${TOPIC}" \
  -H "Title: ${TITLE}" \
  -H "Priority: ${PRIORITY}" \
  -H "Content-Type: text/plain; charset=utf-8" \
  -d "${MESSAGE}")

if [[ "$HTTP_STATUS" == "200" ]]; then
  echo "Notification sent → ${NTFY_SERVER}/${TOPIC}"
else
  echo "Error: ntfy.sh returned HTTP ${HTTP_STATUS}" >&2
  exit 1
fi
