#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

step() {
  echo -e "${YELLOW}[TEST]${NC} $1"
}

success() {
  echo -e "${GREEN}[PASS]${NC} $1"
}

error() {
  echo -e "${RED}[FAIL]${NC} $1"
}

# Get JWT token
step "Obtaining JWT token from Keycloak..."
TOKEN=$("$ROOT_DIR/scripts/auth_token.sh" 2>/dev/null || echo "")
if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  error "Failed to obtain JWT token"
  exit 1
fi
success "JWT token obtained"

# Check Envoy health
step "Checking Envoy gateway health..."
if curl -sf http://localhost:10000/__ping > /dev/null; then
  success "Envoy gateway is healthy"
else
  error "Envoy gateway health check failed"
  exit 1
fi

# Check Payment Orchestrator health
step "Checking Payment Orchestrator health..."
if curl -sf -H "Authorization: Bearer $TOKEN" http://localhost:10000/api/payment/health > /dev/null; then
  success "Payment Orchestrator is healthy"
else
  error "Payment Orchestrator health check failed"
  exit 1
fi

# Create order
step "Creating order..."
ORDER_PAYLOAD='{"amount":200000,"currency":"VND","items":[]}'
ORDER_RESPONSE=$(curl -sf -X POST http://localhost:8001/orders \
  -H "x-user-id: customer1" \
  -H "Content-Type: application/json" \
  -d "$ORDER_PAYLOAD")
ORDER_ID=$(echo "$ORDER_RESPONSE" | jq -r '.id')
if [[ -z "$ORDER_ID" || "$ORDER_ID" == "null" ]]; then
  error "Failed to create order"
  echo "Response: $ORDER_RESPONSE"
  exit 1
fi
success "Order created: $ORDER_ID"

# Tokenize card
step "Tokenizing card via HSM..."
TOKENIZE_RESPONSE=$(curl -sf -X POST http://localhost:10000/api/payment/tokenize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pan":"4111111111111111","exp_month":12,"exp_year":2030,"cvc":"123"}')
PAYMENT_TOKEN=$(echo "$TOKENIZE_RESPONSE" | jq -r '.token')
if [[ -z "$PAYMENT_TOKEN" || "$PAYMENT_TOKEN" == "null" ]]; then
  error "Failed to tokenize card"
  echo "Response: $TOKENIZE_RESPONSE"
  exit 1
fi
success "Card tokenized: ${PAYMENT_TOKEN:0:30}..."

# Process payment
step "Processing payment with fraud check..."
PAYMENT_RESPONSE=$(curl -sf -X POST http://localhost:10000/api/payments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"payment_token\":\"$PAYMENT_TOKEN\"}")
STATUS=$(echo "$PAYMENT_RESPONSE" | jq -r '.status')
if [[ "$STATUS" != "SUCCESS" ]]; then
  error "Payment failed"
  echo "Response: $PAYMENT_RESPONSE"
  exit 1
fi
success "Payment processed successfully"

# Verify signed receipt
step "Verifying signed receipt..."
SIGNED_RECEIPT=$(echo "$PAYMENT_RESPONSE" | jq -r '.signed_receipt')
if [[ -z "$SIGNED_RECEIPT" || "$SIGNED_RECEIPT" == "null" ]]; then
  error "No signed receipt in response"
  exit 1
fi
success "Signed receipt obtained: ${SIGNED_RECEIPT:0:30}..."

# Wait for reconciliation
step "Waiting for reconciliation worker to process receipt..."
sleep 2

# Check reconciliation entry
step "Verifying reconciliation entry in database..."
RECON_COUNT=$(docker-compose exec -T postgres_db psql -U payment_user -d payment_gateway -t -c "SELECT count(*) FROM reconciliation_receipts WHERE order_id = '$ORDER_ID';" 2>/dev/null | tr -d '[:space:]' || echo "0")
if [[ "$RECON_COUNT" == "0" ]]; then
  error "Reconciliation entry not found in database"
  exit 1
fi
success "Reconciliation entry confirmed in database"

# Dump HSM info
step "Dumping HSM information..."
docker-compose exec -T softhsm softhsm2-util --show-slots 2>/dev/null | head -5

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All integration tests PASSED${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Summary:"
echo "  - Order ID: $ORDER_ID"
echo "  - Payment Token: ${PAYMENT_TOKEN:0:30}..."
echo "  - Signed Receipt: ${SIGNED_RECEIPT:0:30}..."
echo "  - Reconciliation Records: $RECON_COUNT"
