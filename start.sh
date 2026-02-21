#!/bin/bash

echo "🚀 Starting Agentic Trip Planner - LangGraph Multi-Agent Edition"
echo "================================================================"

# Load .env if present
if [ -f .env ]; then
    echo "📄 Loading .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set!"
    echo "Please set it with: export OPENAI_API_KEY='your-key-here'"
    echo "Or copy .env.example to .env and fill in your key."
    echo ""
fi

# Optional Tavily key check
if [ -z "$TAVILY_API_KEY" ]; then
    echo "ℹ️  TAVILY_API_KEY not set – destination research will use LLM knowledge only."
    echo "   Get a free key at https://tavily.com for live web search."
    echo ""
fi

# Install dependencies if needed
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Remove old database to start fresh
if [ -f trip_planner.db ]; then
    echo "🗑️  Removing old database..."
    rm trip_planner.db
fi

# Start backend in background
echo "🔧 Starting FastAPI backend on http://localhost:8000..."
python main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "🎨 Starting Streamlit frontend on http://localhost:8501..."
cd streamlit_app
streamlit run app.py

# Cleanup on exit
trap "kill $BACKEND_PID 2>/dev/null; exit" INT TERM EXIT
