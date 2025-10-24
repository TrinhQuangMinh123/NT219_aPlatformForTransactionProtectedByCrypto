# Infrastructure Scaffolding Guide

## Overview
This docker-compose setup defines a complete microservices architecture for the secure payment gateway PoC.

## Services

### Core Infrastructure
- **postgres_db**: PostgreSQL database for all services
- **rabbitmq**: Message queue for async processing
- **softhsm**: Hardware Security Module (SoftHSM2) for key management

### Application Services
- **api_gateway**: Main API entry point (port 8000)
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
- API Gateway: http://localhost:8000
- RabbitMQ Management: http://localhost:15672 (guest/guest)
- PostgreSQL: localhost:5432

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
- `JWT_SECRET`: JWT signing secret
- `STRIPE_SECRET_KEY`: Stripe API key (sandbox)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

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
