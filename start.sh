#!/bin/bash

echo "🚀 Starting Agentic Trip Planner - Hackathon Version"
echo "===================================================="

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set!"
    echo "Please set it with: export OPENAI_API_KEY='your-key-here'"
    echo ""
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
pip install -q -r requirements.txt

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
