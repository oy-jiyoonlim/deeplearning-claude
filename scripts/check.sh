#!/bin/bash
# 코드 품질 체크 스크립트 (포맷팅 검사만, 수정하지 않음)

set -e

cd "$(dirname "$0")/.."

echo "=== Code Quality Check ==="
echo ""

echo "[1/2] Checking formatting with black..."
uv run black --check --diff backend/ main.py
echo "  ✓ Formatting OK"

echo ""
echo "[2/2] Running tests..."
cd backend && uv run pytest tests/ -v
echo "  ✓ Tests OK"

echo ""
echo "=== All checks passed ==="
