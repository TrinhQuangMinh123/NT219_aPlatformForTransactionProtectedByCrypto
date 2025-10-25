# Infrastructure Scaffolding Guide

## Overview
This docker-compose setup defines a complete microservices architecture for the secure payment gateway PoC.

## Services

### Core Infrastructure
- **postgres_db**: PostgreSQL database for all services
- **rabbitmq**: Message queue for async processing
- **softhsm**: Hardware Security Module (SoftHSM2) for key management
- **keycloak**: Identity provider (OIDC) for issuing JWTs
- **envoy**: API gateway enforcing authZ/authN and proxying traffic to backend services

### Application Services
- **order_service**: Order management (port 8001)
- **payment_orchestrator**: Payment processing (port 8002)
- **fraud_engine**: Fraud detection (port 8003)
- **reconciliation_worker**: Settlement reconciliation

### Frontend
- **frontend**: React.js checkout interface (port 3000)

## Quick Start

### 1. Clone and Setup
\`\`\`bash
git clone <repo>
cd secure-payment-gateway
cp .env.example .env
\`\`\`

### 2. Build and Start
\`\`\`bash
docker-compose up -d
\`\`\`

### 3. Verify Services
\`\`\`bash
# Check all services are running
docker-compose ps

# View logs
docker-compose logs -f

# Check SoftHSM token
docker-compose exec softhsm softhsm2-util --show-slots
\`\`\`

### 4. Access Services
- Frontend: http://localhost:3000
- Envoy Gateway: http://localhost:10000
- Keycloak Console: http://localhost:8081 (admin/admin)
- RabbitMQ Management: http://localhost:15672 (guest/guest)
- PostgreSQL: localhost:5432

### 5. Obtain Tokens
Keycloak automatically imports the `ecommerce` realm with a sample user.

- Realm: `ecommerce`
- Client: `payment-frontend` (public)
- Sample user: `customer1` / `ChangeMe123!`

Use the Keycloak UI to obtain an access token (or run `curl` / Postman), then call the Envoy endpoints (e.g. `POST http://localhost:10000/api/payment/tokenize`) with the `Authorization: Bearer <token>` header.

## Stage 1: Automated Testing & Verification

### Running the Full Integration Test

Execute the complete end-to-end payment flow test:

\`\`\`bash
make test
\`\`\`

This will:
1. Start all services
2. Obtain JWT token from Keycloak
3. Create an order
4. Tokenize a card via HSM
5. Process payment with fraud check
6. Verify signed receipt
7. Confirm reconciliation entry in database

Expected output: "All integration tests PASSED"

### Health Check

Verify all services are healthy:

\`\`\`bash
make health
\`\`\`

Expected output: All services show ✓

### Viewing Service Logs

View logs from specific services:

\`\`\`bash
# Payment Orchestrator (tokenization, payment processing, signing)
make logs-payment

# Fraud Engine (fraud scoring decisions)
make logs-fraud

# Reconciliation Worker (receipt processing)
make logs-worker

# Order Service
make logs-order

# Envoy Gateway (API routing, JWT validation)
make logs-envoy

# Keycloak (authentication)
make logs-keycloak

# SoftHSM (HSM operations)
make logs-hsm

# All services
make logs-all
\`\`\`

### HSM Cryptographic Operations

#### Dump HSM Information

View HSM slots, objects, and retrieve the public key:

\`\`\`bash
make dump-hsm
\`\`\`

This will:
1. Display SoftHSM slots and initialized tokens
2. Retrieve the RSA public key from Payment Orchestrator
3. Decode and display the public key in both base64 and PEM formats
4. Save the public key to `/tmp/public_key.pem` for verification

#### Verify Signatures

Verify a signed receipt using the public key:

\`\`\`bash
# Get a signature from a payment response
SIGNATURE="<base64_encoded_signature_from_payment_response>"
MESSAGE='{"order_id":"...","amount":200000,...}'

make verify-sig MESSAGE="$MESSAGE" SIGNATURE="$SIGNATURE"
\`\`\`

Expected output: "Signature verification PASSED"

### Manual Payment Flow (Step-by-Step)

#### Step 1: Obtain JWT Token

\`\`\`bash
TOKEN=$(make token)
echo $TOKEN
\`\`\`

#### Step 2: Create Order

\`\`\`bash
ORDER_RESPONSE=$(curl -X POST http://localhost:8001/orders \
  -H "x-user-id: customer1" \
  -H "Content-Type: application/json" \
  -d '{"amount":200000,"currency":"VND","items":[]}')

ORDER_ID=$(echo $ORDER_RESPONSE | jq -r '.id')
echo "Order ID: $ORDER_ID"
\`\`\`

#### Step 3: Tokenize Card (HSM Encryption)

\`\`\`bash
TOKENIZE_RESPONSE=$(curl -X POST http://localhost:10000/api/payment/tokenize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pan":"4111111111111111","exp_month":12,"exp_year":2030,"cvc":"123"}')

PAYMENT_TOKEN=$(echo $TOKENIZE_RESPONSE | jq -r '.token')
echo "Payment Token: $PAYMENT_TOKEN"
\`\`\`

#### Step 4: Process Payment (Fraud Check + PSP + Signing)

\`\`\`bash
PAYMENT_RESPONSE=$(curl -X POST http://localhost:10000/api/payments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"payment_token\":\"$PAYMENT_TOKEN\"}")

echo $PAYMENT_RESPONSE | jq .
\`\`\`

Expected response:
\`\`\`json
{
  "status": "SUCCESS",
  "signed_receipt": "MEUCIQDx...",
  "receipt": {
    "order_id": "...",
    "amount": 200000,
    "currency": "VND",
    "timestamp": "2024-...",
    "status": "SUCCESS",
    "psp_reference": "pi_mock_...",
    "last4": "1111"
  }
}
\`\`\`

#### Step 5: Verify Reconciliation Entry

\`\`\`bash
docker-compose exec -T postgres_db psql -U payment_user -d payment_gateway -c \
  "SELECT order_id, status, signature FROM reconciliation_receipts WHERE order_id = '$ORDER_ID';"
\`\`\`

### Debugging & Troubleshooting

#### View Detailed Logs for a Service

\`\`\`bash
make debug-logs SERVICE=payment
make debug-logs SERVICE=fraud
make debug-logs SERVICE=reconciliation
\`\`\`

#### Check Database State

\`\`\`bash
# View payment intents
docker-compose exec -T postgres_db psql -U payment_user -d payment_gateway -c \
  "SELECT id, order_id, status, created_at FROM payment_intents LIMIT 10;"

# View used tokens (replay prevention)
docker-compose exec -T postgres_db psql -U payment_user -d payment_gateway -c \
  "SELECT order_id, created_at FROM used_payment_tokens LIMIT 10;"

# View reconciliation receipts
docker-compose exec -T postgres_db psql -U payment_user -d payment_gateway -c \
  "SELECT order_id, status, processed_at FROM reconciliation_receipts LIMIT 10;"
\`\`\`

#### Check RabbitMQ Queue

\`\`\`bash
docker-compose exec -T rabbitmq rabbitmq-diagnostics queues
\`\`\`

#### Inspect HSM Slots

\`\`\`bash
docker-compose exec -T softhsm softhsm2-util --show-slots
\`\`\`

## Reconciliation Storage

- Reconciliation worker now persists every signed receipt to PostgreSQL (`reconciliation_receipts` table) together with its signature, status, PSP reference, and raw payload. Duplicate signatures are ignored to avoid double counting.
- A `reconciliation_reports` table is scaffolded for future summary exports (daily/weekly reports). Populate it from a periodic job once report generation logic is ready.

## SoftHSM Configuration

### Token Details
- **Slot**: 0
- **Label**: payment-hsm
- **SO-PIN**: 1234
- **User-PIN**: 5678

### Generated Keys
- **RSA Key**: payment-signing-key (ID: 01) - for signing receipts
- **AES Key**: payment-encryption-key (ID: 02) - for token encryption

### Accessing HSM from Services
\`\`\`python
import os
from PyKCS11 import PyKCS11

lib = PyKCS11.PyKCS11Lib()
lib.load(os.getenv('SOFTHSM_MODULE'))
slot = lib.getSlotList()[0]
session = lib.openSession(slot)
session.login(os.getenv('SOFTHSM_USER_PIN'))
\`\`\`

## Environment Variables

See `.env.example` for all available variables. Key ones:
- `DB_PASSWORD`: PostgreSQL password
- `STRIPE_SECRET_KEY`: Stripe API key (sandbox)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD`: bootstrap credentials for Keycloak admin console
- `ENVOY_LOG_LEVEL`: log level for Envoy proxy

## Volumes

- **postgres_data**: PostgreSQL data persistence
- **rabbitmq_data**: RabbitMQ data persistence
- **softhsm_tokens**: SoftHSM token storage

## Network

All services communicate via the `payment_network` bridge network.

## Troubleshooting

### SoftHSM not initializing
\`\`\`bash
docker-compose logs softhsm
docker-compose exec softhsm softhsm2-util --show-slots
\`\`\`

### Database connection issues
\`\`\`bash
docker-compose exec postgres_db psql -U payment_user -d payment_gateway
\`\`\`

### RabbitMQ issues
\`\`\`bash
docker-compose exec rabbitmq rabbitmq-diagnostics ping
\`\`\`

### Services not communicating
\`\`\`bash
# Check network
docker network ls
docker network inspect payment_network

# Test connectivity
docker-compose exec payment_orchestrator curl -sf http://order_service:8000/health
\`\`\`

### Keycloak token issues
\`\`\`bash
# Check Keycloak logs
make logs-keycloak

# Verify realm import
curl -sf http://localhost:8081/realms/ecommerce
\`\`\`

## Security Notes

- Change all default passwords in `.env` for production
- Use proper secrets management (Vault, AWS Secrets Manager)
- Enable FIPS mode in softhsm2.conf for production
- Rotate keys regularly
- Monitor HSM access logs
- Review Envoy access logs for suspicious patterns
- Implement rate limiting on sensitive endpoints
