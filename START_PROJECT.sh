#!/bin/bash
# Starts the databases, backend and frontend. Run the setup in README.md first.
cd "$(dirname "$0")" || exit 1

docker start law-firm-postgres law-firm-mongo

(cd backend && source venv/bin/activate && exec uvicorn app.main:app --reload) &
BACKEND=$!
trap 'kill $BACKEND' EXIT

cd frontend && npm run dev
