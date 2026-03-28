#!/bin/bash
# Double-click this file to launch NexGen AI Corp.
# Your browser will open automatically.

# Go to the project folder (same folder as this file)
cd "$(dirname "$0")"

# ── Find Python ───────────────────────────────────────────────────────────────
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON=python3
else
    osascript -e 'display alert "Python not found" message "Run setup.sh first:\n\nbash setup.sh" as critical'
    exit 1
fi

# ── Install deps if venv missing ─────────────────────────────────────────────
if [ ! -f ".venv/bin/python" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install -e . -q
    PYTHON=".venv/bin/python"
fi

# ── Pull latest updates ───────────────────────────────────────────────────────
if command -v git &>/dev/null && [ -d ".git" ]; then
    echo "🔄 Pulling latest updates..."
    git pull --quiet 2>/dev/null || true
fi

# ── Check for .env ────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
fi

# ── Launch ────────────────────────────────────────────────────────────────────
echo ""
echo "🏢 Starting NexGen AI Corp..."
echo "   Your browser will open in a moment."
echo "   Close this window to stop the company."
echo ""

$PYTHON main.py start
