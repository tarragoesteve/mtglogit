#!/bin/bash

# echo "================================"
# echo "🚀 Initializing visualizer"
# echo "================================"
# echo ""

# # Check if we're in the right directory
# if [ ! -f "script.js" ]; then
#     echo "❌ Error: script.js not found"
#     echo "Run this script from the docs/ directory"
#     exit 1
# fi

# # Create virtual environment if it doesn't exist
# if [ ! -d "venv" ]; then
#     echo "📦 Creating Python virtual environment..."
#     python3 -m venv venv
#     if [ $? -ne 0 ]; then
#         echo "❌ Error: Failed to create virtual environment"
#         exit 1
#     fi
# fi

# # Activate virtual environment
# echo "📦 Activating virtual environment..."
# source venv/bin/activate

# # Install dependencies
# echo "📥 Installing dependencies..."
# pip install -q -r requirements.txt
# if [ $? -ne 0 ]; then
#     echo "❌ Error: Failed to install dependencies"
#     deactivate
#     exit 1
# fi

echo ""
echo "📊 Step 1: Generating data.json from results/ folders..."
echo ""

if command -v python3 &> /dev/null; then
    python3 wrinfo.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ Error running wrinfo.py"
        deactivate
        exit 1
    fi
else
    echo "❌ Error: python3 not found"
    deactivate
    exit 1
fi

echo ""
echo "📋 Step 2: Updating datasets.json..."
echo ""

python generate_datasets.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error running generate_datasets.py"
    deactivate
    exit 1
fi

echo ""
echo "================================"
echo "✅ Initialization completed!"
echo "================================"
echo ""
echo "🌐 To start the server, run:"
echo "   source venv/bin/activate"
echo "   python3 -m http.server"
echo ""
echo "📖 Then open http://localhost:8000 in your browser"
echo ""


