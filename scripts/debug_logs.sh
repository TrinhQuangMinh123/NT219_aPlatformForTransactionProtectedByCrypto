#!/usr/bin/env bash
set -euo pipefail

SERVICE=${1:-all}

echo "[DEBUG] Collecting logs from services..."

case "$SERVICE" in
  payment)
    echo "[DEBUG] Payment Orchestrator logs:"
    docker-compose logs --tail=50 payment_orchestrator
    ;;
  fraud)
    echo "[DEBUG] Fraud Engine logs:"
    docker-compose logs --tail=50 fraud_engine
    ;;
  reconciliation)
    echo "[DEBUG] Reconciliation Worker logs:"
    docker-compose logs --tail=50 reconciliation_worker
    ;;
  order)
    echo "[DEBUG] Order Service logs:"
    docker-compose logs --tail=50 order_service
    ;;
  envoy)
    echo "[DEBUG] Envoy Gateway logs:"
    docker-compose logs --tail=50 envoy
    ;;
  keycloak)
    echo "[DEBUG] Keycloak logs:"
    docker-compose logs --tail=50 keycloak
    ;;
  hsm)
    echo "[DEBUG] SoftHSM logs:"
    docker-compose logs --tail=50 softhsm
    ;;
  all)
    echo "[DEBUG] All service logs:"
    docker-compose logs --tail=30
    ;;
  *)
    echo "Usage: $0 {payment|fraud|reconciliation|order|envoy|keycloak|hsm|all}"
    exit 1
    ;;
esac
