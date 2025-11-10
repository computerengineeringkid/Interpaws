#!/bin/bash

# Interpaws Application Startup Script
# Days 12-14: Admin UI Integration & E2E Testing

echo "🚀 Starting Interpaws Application..."
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Navigate to project directory
cd "$(dirname "$0")"

echo "📦 Building and starting containers..."
docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."
echo "   - Database: Initializing..."
echo "   - Backend: Running migrations..."
echo "   - Frontend: Building Next.js app..."
echo "   - Ollama: Loading AI models..."

# Wait for backend to be healthy
echo ""
echo "Checking backend health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    echo "   Waiting... ($i/30)"
    sleep 2
done

# Wait for frontend to be healthy
echo ""
echo "Checking frontend health..."
for i in {1..30}; do
    if curl -s http://localhost:3000/ > /dev/null 2>&1; then
        echo "✅ Frontend is ready!"
        break
    fi
    echo "   Waiting... ($i/30)"
    sleep 2
done

echo ""
echo "=================================="
echo "✅ Interpaws Application is running!"
echo "=================================="
echo ""
echo "📱 Access the application:"
echo "   • Frontend: http://localhost:3000"
echo "   • Backend API: http://localhost:8000"
echo "   • API Docs: http://localhost:8000/docs"
echo ""
echo "👤 Client Access:"
echo "   • Login: http://localhost:3000/login"
echo "   • Portal: http://localhost:3000"
echo ""
echo "👨‍⚕️ Admin Access:"
echo "   • Login: http://localhost:3000/admin/login"
echo "   • Dashboard: http://localhost:3000/admin"
echo "   • Staff Management: http://localhost:3000/admin/staff"
echo "   • Surgeries: http://localhost:3000/admin/surgeries"
echo "   • Medications: http://localhost:3000/admin/medications"
echo ""
echo "📝 Next Steps:"
echo "   1. Create an admin account (see E2E_TESTING_GUIDE.md)"
echo "   2. Follow the testing guide for comprehensive testing"
echo "   3. Check logs: docker-compose logs -f"
echo ""
echo "🛑 To stop: docker-compose down"
echo "=================================="
