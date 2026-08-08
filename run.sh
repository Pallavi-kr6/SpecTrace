#!/usr/bin/env bash
# SpecTrace AI -- one-command setup & run
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

pip install -q -r requirements.txt

echo ""
echo "SpecTrace AI is starting at http://localhost:8000"
echo "(Click 'Load sample catalog' on the home page for an instant demo.)"
echo ""

cd backend
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
