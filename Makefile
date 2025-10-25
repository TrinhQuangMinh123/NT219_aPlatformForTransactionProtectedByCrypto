.PHONY: up down clean test lint ps logs token

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

logs-all:
	$(COMPOSE) logs -f

 test:
	$(COMPOSE) up -d --remove-orphans
	./scripts/integration_test.sh

 token:
	./scripts/auth_token.sh

