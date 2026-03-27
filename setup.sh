#!/bin/bash
# NexGen AI Corp — One-click setup script for Mac

set -e

echo ""
echo "🏢 NexGen AI Corp — Setup"
echo "=========================="
echo ""

# ── Check/install Python ──────────────────────────────────────────────────────
echo "📦 Checking Python..."

if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo $PY_VER | cut -d. -f1)
    PY_MINOR=$(echo $PY_VER | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
        echo "   ✅ Python $PY_VER found"
        PYTHON=python3
    else
        echo "   ⚠️  Python $PY_VER is too old. Installing 3.11+ via Homebrew..."
        brew install python@3.11
        PYTHON=python3.11
    fi
else
    echo "   ❌ Python not found. Installing via Homebrew..."
    brew install python
    PYTHON=python3
fi

# ── Add Homebrew to PATH if needed ────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    eval "$(/opt/homebrew/bin/brew shellenv zsh)" 2>/dev/null || true
fi

# ── Create virtual environment ────────────────────────────────────────────────
echo ""
echo "🔧 Creating virtual environment..."
$PYTHON -m venv .venv
source .venv/bin/activate
echo "   ✅ Virtual environment created at .venv/"

# ── Install dependencies ──────────────────────────────────────────────────────
echo ""
echo "📥 Installing dependencies (this may take 1-2 minutes)..."
pip install --upgrade pip -q
pip install -e . -q
echo "   ✅ All dependencies installed"

# ── Set up .env ───────────────────────────────────────────────────────────────
echo ""
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env from template"
else
    echo "📝 .env already exists"
fi

# ── Show API key instructions ─────────────────────────────────────────────────
echo ""
echo "🔑 You need 3 API keys (all free tiers available):"
echo ""
echo "   1. ANTHROPIC_API_KEY  → https://console.anthropic.com/settings/keys"
echo "   2. GOOGLE_API_KEY     → https://aistudio.google.com/app/apikey"
echo "   3. TAVILY_API_KEY     → https://app.tavily.com  (free: 1000 searches/month)"
echo ""
echo "Opening .env for you to fill in..."
sleep 1
open -e .env 2>/dev/null || nano .env

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "✅ Setup complete!"
echo ""
echo "When you've filled in your API keys, run:"
echo ""
echo "   source .venv/bin/activate"
echo "   python main.py start --dry-run    # Test without real API calls"
echo "   python main.py start              # Launch the full company"
echo ""
