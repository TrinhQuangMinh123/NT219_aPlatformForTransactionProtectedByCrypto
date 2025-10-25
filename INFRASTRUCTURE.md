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

## Security Notes

- Change all default passwords in `.env` for production
- Use proper secrets management (Vault, AWS Secrets Manager)
- Enable FIPS mode in softhsm2.conf for production
- Rotate keys regularly
- Monitor HSM access logs
