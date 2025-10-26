#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <message> <signature_base64>"
  echo "Example: $0 'hello world' 'MEUCIQDx...'"
  exit 1
fi

MESSAGE="$1"
SIGNATURE_B64="$2"

echo "[VERIFY] Verifying signature..."
echo "[VERIFY] Message: $MESSAGE"
echo "[VERIFY] Signature (base64): ${SIGNATURE_B64:0:50}..."

# Get public key
TOKEN=$(bash scripts/auth_token.sh 2>/dev/null || echo "")
if [[ -z "$TOKEN" ]]; then
  PUBLIC_KEY=$(curl -sf http://localhost:10000/api/payment/public-key | jq -r '.public_key')
else
  PUBLIC_KEY=$(curl -sf -H "Authorization: Bearer $TOKEN" http://localhost:10000/api/payment/public-key | jq -r '.public_key')
fi

# Decode public key
echo "$PUBLIC_KEY" | base64 -d > /tmp/verify_public_key.der

# Convert to PEM
openssl pkey -inform DER -in /tmp/verify_public_key.der -pubin -out /tmp/verify_public_key.pem 2>/dev/null || \
  openssl rsa -inform DER -in /tmp/verify_public_key.der -pubin -out /tmp/verify_public_key.pem 2>/dev/null

# Decode signature
echo "$SIGNATURE_B64" | base64 -d > /tmp/verify_signature.bin

# Create message file
echo -n "$MESSAGE" > /tmp/verify_message.txt

# Verify signature
if openssl dgst -sha256 -verify /tmp/verify_public_key.pem -signature /tmp/verify_signature.bin /tmp/verify_message.txt; then
  echo "[VERIFY] Signature verification PASSED"
  exit 0
else
  echo "[VERIFY] Signature verification FAILED"
  exit 1
fi
