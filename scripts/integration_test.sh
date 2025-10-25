#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

TOKEN=$("$ROOT_DIR/scripts/auth_token.sh")
HEADER=("Authorization: Bearer $TOKEN")

step() {
  echo "[TEST] $1"
}

check() {
  local cmd="$1"
  step "$cmd"
  eval "$cmd"
}

check "curl -sf http://localhost:10000/__ping"
check "curl -sf -H \"${HEADER[*]}\" http://localhost:10000/api/payment/health"

ORDER_PAYLOAD='{"amount":200000,"currency":"VND","items":[]}'
ORDER_RESPONSE=$(curl -sf -X POST http://localhost:8001/orders \
  -H "x-user-id: customer1" \
  -H "Content-Type: application/json" \
  -d "$ORDER_PAYLOAD")
ORDER_ID=$(echo "$ORDER_RESPONSE" | jq -r '.id')
if [[ -z "$ORDER_ID" || "$ORDER_ID" == "null" ]]; then
  echo "Failed to create order" >&2
  exit 1
fi

echo "[TEST] Order created: $ORDER_ID"

TOKENIZE_RESPONSE=$(curl -sf -X POST http://localhost:10000/api/payment/tokenize \
  -H "${HEADER[0]}" \
  -H "Content-Type: application/json" \
  -d '{"pan":"4111111111111111","exp_month":12,"exp_year":2030,"cvc":"123"}')
PAYMENT_TOKEN=$(echo "$TOKENIZE_RESPONSE" | jq -r '.token')
if [[ -z "$PAYMENT_TOKEN" || "$PAYMENT_TOKEN" == "null" ]]; then
  echo "Failed to tokenize" >&2
  exit 1
fi

echo "[TEST] Token obtained"

PAYMENT_RESPONSE=$(curl -sf -X POST http://localhost:10000/api/payments \
  -H "${HEADER[0]}" \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"payment_token\":\"$PAYMENT_TOKEN\"}")
STATUS=$(echo "$PAYMENT_RESPONSE" | jq -r '.status')
if [[ "$STATUS" != "SUCCESS" ]]; then
  echo "Payment failed: $PAYMENT_RESPONSE" >&2
  exit 1
fi

echo "[TEST] Payment succeeded"

RECON_COUNT=$(docker-compose exec -T postgres_db psql -U payment_user -d payment_gateway -t -c "SELECT count(*) FROM reconciliation_receipts WHERE order_id = '$ORDER_ID';" | tr -d '[:space:]')
if [[ "$RECON_COUNT" == "0" ]]; then
  echo "Reconciliation entry not found" >&2
  exit 1
fi

echo "[TEST] Reconciliation entry confirmed"

echo "All tests passed."
