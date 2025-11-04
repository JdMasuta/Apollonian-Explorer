#!/bin/bash
set -e

echo "🚀 Deploying Apollonian Gasket Visualizer..."

# Build frontend
echo "📦 Building frontend..."
cd frontend
npm run build
cd ..

# Copy frontend build to backend static
echo "📁 Copying build to backend static directory..."
mkdir -p backend/static
cp -r frontend/dist/* backend/static/

echo "✅ Deployment complete!"
echo ""
echo "To run in production:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  uvicorn main:app --host 0.0.0.0 --port 8000"
