#!/bin/bash

# Initialize SoftHSM2 Token for Payment Gateway
# This script creates a token with predefined SO-PIN and User-PIN

set -e

echo "[SoftHSM] Initializing token..."

# Configuration
SLOT=0
LABEL="payment-hsm"
SO_PIN="1234"
USER_PIN="5678"
TOKEN_DIR="/var/lib/softhsm/tokens"

# Ensure token directory exists
mkdir -p "$TOKEN_DIR"
chmod 700 "$TOKEN_DIR"

# Initialize the token
echo "[SoftHSM] Creating token on slot $SLOT with label '$LABEL'..."
softhsm2-util --init-token \
  --slot "$SLOT" \
  --label "$LABEL" \
  --so-pin "$SO_PIN" \
  --pin "$USER_PIN"

echo "[SoftHSM] Token initialized successfully!"

# Display token information
echo "[SoftHSM] Token information:"
softhsm2-util --show-slots

# Generate RSA key pair for signing (2048-bit)
echo "[SoftHSM] Generating RSA key pair for signing..."
pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so \
  --token-label "$LABEL" \
  --pin "$USER_PIN" \
  --keypairgen \
  --key-type rsa:2048 \
  --label "payment-signing-key" \
  --id 01

echo "[SoftHSM] RSA key pair generated successfully!"

# Generate AES key for encryption (256-bit)
echo "[SoftHSM] Generating AES key for encryption..."
pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so \
  --token-label "$LABEL" \
  --pin "$USER_PIN" \
  --keygen \
  --key-type AES:32 \
  --label "payment-encryption-key" \
  --id 02

echo "[SoftHSM] AES key generated successfully!"

# List all objects in the token
echo "[SoftHSM] Objects in token:"
pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so \
  --token-label "$LABEL" \
  --pin "$USER_PIN" \
  --list-objects

echo "[SoftHSM] Initialization complete!"
