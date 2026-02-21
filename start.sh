#!/bin/bash

echo "======================================================"
echo "  Agentic Trip Planner - CrewAI Multi-Agent Edition"
echo "======================================================"
echo ""

# Load .env if present
if [ -f .env ]; then
    echo "Loading .env file..."
    set -a; source .env; set +a
fi

# ── Detect LLM provider ─────────────────────────────────
PROVIDER="${LLM_PROVIDER:-openai}"
echo "LLM Provider: $PROVIDER"

case "$PROVIDER" in
    openai)
        if [ -z "$OPENAI_API_KEY" ]; then
            echo ""
            echo "ERROR: OPENAI_API_KEY not set!"
            echo "  Set it in .env or run:  export OPENAI_API_KEY='sk-...'"
            echo "  Get a key at https://platform.openai.com/api-keys"
            exit 1
        fi
        echo "  Model: ${LLM_MODEL:-gpt-4o-mini}"
        ;;
    gemini)
        if [ -z "$GEMINI_API_KEY" ]; then
            echo ""
            echo "ERROR: GEMINI_API_KEY not set!"
            echo "  Set it in .env or run:  export GEMINI_API_KEY='...'"
            echo "  Get a key at https://aistudio.google.com/apikey"
            exit 1
        fi
        echo "  Model: ${LLM_MODEL:-gemini-2.0-flash}"
        ;;
    anthropic)
        if [ -z "$ANTHROPIC_API_KEY" ]; then
            echo ""
            echo "ERROR: ANTHROPIC_API_KEY not set!"
            echo "  Set it in .env or run:  export ANTHROPIC_API_KEY='...'"
            echo "  Get a key at https://console.anthropic.com/settings/keys"
            exit 1
        fi
        echo "  Model: ${LLM_MODEL:-claude-sonnet-4-20250514}"
        ;;
    *)
        echo "  Unknown provider '$PROVIDER' - falling back to openai"
        ;;
esac

# ── Optional search key ─────────────────────────────────
if [ -n "$TAVILY_API_KEY" ]; then
    echo "  Web search: Tavily (enabled)"
elif [ -n "$SERPER_API_KEY" ]; then
    echo "  Web search: Serper (enabled)"
else
    echo "  Web search: disabled (set TAVILY_API_KEY or SERPER_API_KEY for live search)"
fi
echo ""

# ── Activate venv if present ─────────────────────────────
if [ -d .venv ]; then
    echo "Activating .venv..."
    source .venv/bin/activate
elif [ -d venv ]; then
    echo "Activating venv..."
    source venv/bin/activate
fi

# ── Install deps ─────────────────────────────────────────
echo "Installing dependencies..."
pip install -q -r requirements.txt

# ── Fresh database ───────────────────────────────────────
# if [ -f trip_planner.db ]; then
#     echo "Removing old database..."
#     rm trip_planner.db
# fi

# ── Start backend ────────────────────────────────────────
echo ""
echo "Starting FastAPI backend on http://localhost:8000 ..."
python main.py &
BACKEND_PID=$!
sleep 3

# ── Start frontend ───────────────────────────────────────
echo "Starting Streamlit frontend on http://localhost:8501 ..."
cd streamlit_app
streamlit run app.py

# ── Cleanup ──────────────────────────────────────────────
kill $BACKEND_PID 2>/dev/null
