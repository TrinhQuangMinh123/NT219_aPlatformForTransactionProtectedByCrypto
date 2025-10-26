# Stage 1 Completion Checklist

This checklist verifies that all Stage 1 requirements have been met for the Secure Payment Gateway PoC.

## Infrastructure Setup

- [ ] **Docker Compose Services Running**
  ```bash
  make up
  make ps
  ```
  Expected: All services show "Up" status

- [ ] **Health Checks Passing**
  ```bash
  make health
  ```
  Expected: All services report healthy

- [ ] **PostgreSQL Data Persistence**
  ```bash
  docker volume ls | grep postgres_data
  ```
  Expected: Volume exists and persists data

- [ ] **SoftHSM Token Initialization**
  ```bash
  docker-compose exec -T softhsm softhsm2-util --show-slots
  ```
  Expected: Slot 0 shows "Initialized" with label "payment-hsm"

- [ ] **Keycloak Realm Reachable**
  ```bash
  curl -sf http://localhost:8081/realms/master/.well-known/openid-configuration
  ```
  Expected: JSON document containing realm metadata

- [ ] **make health Outputs All ✓**
  ```bash
  make health
  ```
  Expected: Every line reports ✓

- [ ] **Envoy Gateway Running on Port 10000**
  ```bash
  curl -sf http://localhost:10000/__ping
  ```
  Expected: "ok" response

## Authentication & Authorization

- [ ] **JWT Token Generation**
  ```bash
  make -s token
  ```
  Expected: Valid JWT token printed to stdout

- [ ] **Envoy JWT Validation**
  ```bash
  TOKEN=$(make -s token)
  curl -s -o - -w '%{http_code}\n' \
    -H "Authorization: Bearer $TOKEN" \
    http://localhost:10000/api/payment/health
  ```
  Expected: JSON payload with status `ok` and trailing `200`

- [ ] **Unauthorized Request Rejection**
  ```bash
  curl -s -o - -w '%{http_code}\n' \
    -X POST \
    http://localhost:10000/api/payment/tokenize
  ```
  Expected: Empty body (or error JSON) with trailing `401`

## Payment Flow (End-to-End)

- [ ] **Order Creation**
  ```bash
  curl -X POST http://localhost:8001/orders \
    -H "x-user-id: customer1" \
    -H "Content-Type: application/json" \
    -d '{"amount":200000,"currency":"VND","items":[]}'
  ```
  Expected: Order ID returned

- [ ] **Card Tokenization (HSM)**
  ```bash
  TOKEN=$(make -s token)
  curl -X POST http://localhost:10000/api/payment/tokenize \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"pan":"4242424242424242","exp_month":12,"exp_year":2030,"cvc":"123"}'
  ```
  Expected: Token starting with "hsm:v1:" returned

- [ ] **Fraud Check (Rule-Based)**
  ```bash
  curl -X POST http://localhost:8003/score \
    -H "Content-Type: application/json" \
    -d '{"amount":200000,"device_id":"customer1"}'
  ```
  Expected: {"score": 10, "action": "ALLOW"}

- [ ] **Payment Processing with Signed Receipt** 
  ```bash
  make test #(now failing and stop here)
  ```
  Expected: All integration tests pass

## Cryptographic Operations

- [ ] **HSM Key Generation**
  ```bash
  docker-compose exec -T softhsm softhsm2-util --show-slots
  ```
  Expected: RSA key pair and AES key present

- [ ] **Public Key Retrieval**
  ```bash
  make dump-hsm
  ```
  Expected: Public key in base64 and PEM formats

- [ ] **Receipt Signing (RSA-SHA256)**
  ```bash
  TOKEN=$(make -s token)
  curl -X POST http://localhost:10000/api/payment/sign \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"message":"test"}'
  ```
  Expected: Base64-encoded RSA signature returned

- [ ] **Signature Verification**
  ```bash
  make verify-sig MESSAGE='test' SIGNATURE='<base64_signature>'
  ```
  Expected: "Signature verification PASSED"

## Data Persistence & Reconciliation

- [ ] **Payment Intent Storage**
  ```bash
  docker-compose exec -T postgres_db psql -U payment_user -d payment_gateway -c \
    "SELECT count(*) FROM payment_intents;"
  ```
  Expected: Count > 0

- [ ] **Used Token Tracking (Replay Prevention)**
  ```bash
  docker-compose exec -T postgres_db psql -U payment_user -d payment_gateway -c \
    "SELECT count(*) FROM used_payment_tokens;"
  ```
  Expected: Count > 0

- [ ] **Reconciliation Receipt Storage**
  ```bash
  docker-compose exec -T postgres_db psql -U payment_user -d payment_gateway -c \
    "SELECT count(*) FROM reconciliation_receipts;"
  ```
  Expected: Count > 0

- [ ] **RabbitMQ Message Queue**
  ```bash
  docker-compose exec -T rabbitmq rabbitmq-diagnostics queues
  ```
  Expected: "reconciliation_queue" listed

## Logging & Observability

- [ ] **Payment Orchestrator Logs**
  ```bash
  make logs-payment | grep -E "\[TOKENIZE\]|\[PAYMENT\]|\[RECEIPT\]"
  ```
  Expected: Detailed logs for each operation

- [ ] **Fraud Engine Logs**
  ```bash
  make logs-fraud | grep "\[FRAUD_SCORE\]"
  ```
  Expected: Fraud scoring decisions logged

- [ ] **Reconciliation Worker Logs**
  ```bash
  make logs-worker | grep "\[RECONCILIATION\]"
  ```
  Expected: Receipt processing logs

- [ ] **Envoy Gateway Logs**
  ```bash
  make logs-envoy | grep "access_log"
  ```
  Expected: HTTP request/response logs

## Security Verification

- [ ] **PCI-DSS Scope Reduction**
  - [ ] PAN never stored on server (only HSM token)
  - [ ] Payment token format: "hsm:v1:..." (encrypted)
  - [ ] Replay attack prevention via token hash

- [ ] **Non-Repudiation**
  - [ ] Receipt signed with RSA private key in HSM
  - [ ] Signature stored in database
  - [ ] Signature verifiable with public key

- [ ] **HSM Key Protection**
  - [ ] Private key marked as non-extractable
  - [ ] Key operations logged
  - [ ] Token access controlled via PIN

## Cleanup & Troubleshooting

- [ ] **Service Logs Accessible**
  ```bash
  make debug-logs SERVICE=payment
  make debug-logs SERVICE=fraud
  make debug-logs SERVICE=reconciliation
  ```
  Expected: Logs displayed without errors

- [ ] **Clean Shutdown**
  ```bash
  make down
  ```
  Expected: All containers stopped

- [ ] **Clean Restart**
  ```bash
  make clean
  make up
  make health
  ```
  Expected: All services healthy after restart

## Final Verification

- [ ] **Full Integration Test** 
  ```bash
  make test
  ```
  Expected: All tests pass with summary output

- [ ] **Documentation Complete**
  - [ ] INFRASTRUCTURE.md updated
  - [ ] README.md reflects Stage 1 status
  - [ ] Scripts are executable and documented

- [ ] **Code Quality**
  ```bash
  make lint
  ```
  Expected: No syntax errors

## Sign-Off

- [ ] All checklist items completed
- [ ] Integration test passing
- [ ] Documentation reviewed
- [ ] Ready for Stage 2

**Date Completed:** _______________
**Verified By:** _______________
