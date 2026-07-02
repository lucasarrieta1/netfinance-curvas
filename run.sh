#!/usr/bin/env bash
set -e
[ -f .env ] && export $(grep -v '^#' .env | xargs)
: "${FEED:=mock}"
echo "▶ NetFinance Curvas · feed=$FEED · http://localhost:8000"
uvicorn app.main:app --reload --port 8000
