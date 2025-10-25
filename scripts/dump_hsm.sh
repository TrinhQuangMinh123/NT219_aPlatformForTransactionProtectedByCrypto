#!/usr/bin/env bash
set -euo pipefail

echo "[HSM] Dumping SoftHSM slots and objects..."
docker-compose exec -T softhsm softhsm2-util --show-slots

echo ""
echo "[HSM] Retrieving public key from Payment Orchestrator..."
TOKEN=$(bash scripts/auth_token.sh 2>/dev/null || echo "")
if [[ -z "$TOKEN" ]]; then
  echo "[HSM] Warning: Could not obtain JWT token, using unauthenticated request"
  PUBLIC_KEY=$(curl -sf http://localhost:10000/api/payment/public-key | jq -r '.public_key')
else
  PUBLIC_KEY=$(curl -sf -H "Authorization: Bearer $TOKEN" http://localhost:10000/api/payment/public-key | jq -r '.public_key')
fi

echo "[HSM] Public key (base64):"
echo "$PUBLIC_KEY"

echo ""
echo "[HSM] Decoding public key to DER format..."
echo "$PUBLIC_KEY" | base64 -d > /tmp/public_key.der

echo "[HSM] Public key saved to /tmp/public_key.der"
echo "[HSM] Public key size: $(stat -f%z /tmp/public_key.der 2>/dev/null || stat -c%s /tmp/public_key.der) bytes"

echo ""
echo "[HSM] Converting DER to PEM format..."
openssl pkey -inform DER -in /tmp/public_key.der -pubin -out /tmp/public_key.pem 2>/dev/null || \
  openssl rsa -inform DER -in /tmp/public_key.der -pubin -out /tmp/public_key.pem 2>/dev/null || \
  echo "[HSM] Warning: Could not convert to PEM (openssl may not be available)"

if [[ -f /tmp/public_key.pem ]]; then
  echo "[HSM] Public key (PEM format):"
  cat /tmp/public_key.pem
fi
