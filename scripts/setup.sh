#!/bin/bash
set -e

echo "🚀 Setting up Apollonian Gasket Visualizer..."

# Backend
echo "📦 Setting up backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Frontend
echo "⚛️  Setting up frontend..."
cd frontend
npm install
cd ..

# Root
echo "🔧 Installing root dependencies..."
npm install

echo "✅ Setup complete! Run 'npm run dev' to start both servers."
