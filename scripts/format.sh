#!/bin/bash
# 코드 포맷팅 실행 스크립트

set -e

cd "$(dirname "$0")/.."

echo "Running black formatter..."
uv run black backend/ main.py

echo "Formatting complete!"
