#!/usr/bin/env bash
set -euo pipefail

REALM=${KEYCLOAK_REALM:-ecommerce}
KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8081}
CLIENT_ID=${KEYCLOAK_CLIENT_ID:-payment-frontend}
USERNAME=${KEYCLOAK_USERNAME:-customer1}
PASSWORD=${KEYCLOAK_PASSWORD:-ChangeMe123!}

curl_opts=(
  -sS
  --retry 5
  --retry-delay 1
  --retry-connrefused
  -X POST
  "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token"
  -d "client_id=$CLIENT_ID"
  -d grant_type=password
  -d "username=$USERNAME"
  -d "password=$PASSWORD"
)

if ! RESPONSE=$(curl "${curl_opts[@]}"); then
  echo "Failed to contact Keycloak at $KEYCLOAK_URL/realms/$REALM. Is the container running?" >&2
  exit 1
fi

if command -v jq >/dev/null 2>&1; then
  TOKEN=$(jq -r '.access_token' <<<"$RESPONSE")
elif command -v python3 >/dev/null 2>&1; then
  TOKEN=$(RESPONSE="$RESPONSE" python3 -c 'import json, os, sys
try:
    data = json.loads(os.environ["RESPONSE"])
    token = data.get("access_token") or ""
except (KeyError, json.JSONDecodeError):
    token = ""
sys.stdout.write(token)')
else
  echo "Neither jq nor python3 is available to parse token response" >&2
  exit 1
fi

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "Failed to obtain token" >&2
  exit 1
fi

echo "$TOKEN"
