.PHONY: up down clean test lint ps logs token dump-hsm verify-sig debug-logs

COMPOSE=docker-compose

up:
	$(COMPOSE) up -d --remove-orphans

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

stop:
	$(COMPOSE) stop

restart: down up

down:
	$(COMPOSE) down

clean:
	$(COMPOSE) down --volumes --remove-orphans || true
	docker volume rm nt219_aplatformfortransactionprotectedbycrypto_postgres_data nt219_aplatformfortransactionprotectedbycrypto_softhsm_tokens || true

build:
	$(COMPOSE) build

status:
	docker ps

lint:
	python3 -m compileall services

logs-envoy:
	$(COMPOSE) logs -f envoy

logs-keycloak:
	$(COMPOSE) logs -f keycloak

logs-hsm:
	$(COMPOSE) logs -f softhsm

logs-worker:
	$(COMPOSE) logs -f reconciliation_worker

logs-payment:
	$(COMPOSE) logs -f payment_orchestrator

logs-fraud:
	$(COMPOSE) logs -f fraud_engine

logs-order:
	$(COMPOSE) logs -f order_service

logs-all:
	$(COMPOSE) logs -f

test:
	$(COMPOSE) up -d --remove-orphans
	./scripts/integration_test.sh

token:
	./scripts/auth_token.sh

dump-hsm:
	./scripts/dump_hsm.sh

verify-sig:
	@echo "Usage: make verify-sig MESSAGE='hello' SIGNATURE='base64_encoded_signature'"
	@echo "Example: make verify-sig MESSAGE='test' SIGNATURE='MEUCIQDx...'"
	@if [ -n "$(MESSAGE)" ] && [ -n "$(SIGNATURE)" ]; then \
		./scripts/verify_signature.sh "$(MESSAGE)" "$(SIGNATURE)"; \
	fi

debug-logs:
	@echo "Usage: make debug-logs SERVICE=<service_name>"
	@echo "Available services: payment, fraud, reconciliation, order, envoy, keycloak, hsm, all"
	@if [ -n "$(SERVICE)" ]; then \
		./scripts/debug_logs.sh "$(SERVICE)"; \
	else \
		./scripts/debug_logs.sh all; \
	fi

health:
	@echo "Checking service health..."
	@curl -sf http://localhost:10000/__ping && echo "✓ Envoy" || echo "✗ Envoy"
	@curl -sf http://localhost:8001/health && echo "✓ Order Service" || echo "✗ Order Service"
	@curl -sf http://localhost:8002/health && echo "✓ Payment Orchestrator" || echo "✗ Payment Orchestrator"
	@curl -sf http://localhost:8003/health && echo "✓ Fraud Engine" || echo "✗ Fraud Engine"
	@curl -sf http://localhost:8081/health 2>/dev/null && echo "✓ Keycloak" || echo "✗ Keycloak"
	@docker-compose exec -T postgres_db pg_isready -U payment_user 2>/dev/null && echo "✓ PostgreSQL" || echo "✗ PostgreSQL"
	@docker-compose exec -T rabbitmq rabbitmq-diagnostics ping 2>/dev/null && echo "✓ RabbitMQ" || echo "✗ RabbitMQ"
	@docker-compose exec -T softhsm softhsm2-util --show-slots 2>/dev/null | head -1 && echo "✓ SoftHSM" || echo "✗ SoftHSM"
