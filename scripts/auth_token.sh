#!/usr/bin/env bash
set -euo pipefail

REALM=${KEYCLOAK_REALM:-ecommerce}
KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8081}
CLIENT_ID=${KEYCLOAK_CLIENT_ID:-payment-frontend}
USERNAME=${KEYCLOAK_USERNAME:-customer1}
PASSWORD=${KEYCLOAK_PASSWORD:-ChangeMe123!}

TOKEN=$(curl -s -X POST "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
  -d "client_id=$CLIENT_ID" \
  -d grant_type=password \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD" \
  | jq -r '.access_token')

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "Failed to obtain token" >&2
  exit 1
fi

echo "$TOKEN"
