#!/usr/bin/env bash
# Post-deploy HTTPS/HSTS validation for NC-06.
# Usage: HOST=https://your-host.example.com bash scripts/check_https_prod.sh
set -euo pipefail

HOST="${HOST:-}"
if [[ -z "$HOST" ]]; then
  echo "Usage: HOST=https://your-host.example.com bash $0" >&2
  exit 1
fi

HTTP_HOST="${HOST/https:\/\//http://}"
HTTPS_HOST="${HOST/http:\/\//https://}"

echo "=== NC-06: HTTPS redirect + HSTS check ==="
echo ""

# 1. HTTP must redirect to HTTPS (301)
echo "[1] HTTP → HTTPS redirect"
STATUS=$(curl -sI -o /dev/null -w "%{http_code}" "$HTTP_HOST/health/")
if [[ "$STATUS" == "301" ]]; then
  echo "    PASS  $HTTP_HOST/health/ → 301"
else
  echo "    FAIL  $HTTP_HOST/health/ → $STATUS (expected 301)"
  exit 1
fi

# 2. HTTPS health check must return 200
echo "[2] HTTPS health check"
STATUS=$(curl -sI -o /dev/null -w "%{http_code}" "$HTTPS_HOST/health/")
if [[ "$STATUS" == "200" ]]; then
  echo "    PASS  $HTTPS_HOST/health/ → 200"
else
  echo "    FAIL  $HTTPS_HOST/health/ → $STATUS (expected 200)"
  exit 1
fi

# 3. HSTS header must be present with correct values
echo "[3] Strict-Transport-Security header"
HSTS=$(curl -sI "$HTTPS_HOST/health/" | grep -i "Strict-Transport-Security" || true)
if [[ -z "$HSTS" ]]; then
  echo "    FAIL  Strict-Transport-Security header absent"
  exit 1
fi
echo "    FOUND $HSTS"
[[ "$HSTS" == *"max-age=31536000"* ]] || { echo "    FAIL  missing max-age=31536000"; exit 1; }
[[ "$HSTS" == *"includeSubDomains"* ]] || { echo "    FAIL  missing includeSubDomains"; exit 1; }
[[ "$HSTS" == *"preload"* ]] || { echo "    FAIL  missing preload"; exit 1; }
echo "    PASS  HSTS values correct"

echo ""
echo "=== All checks passed ==="
