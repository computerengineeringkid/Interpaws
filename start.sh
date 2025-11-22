#!/bin/bash

# Interpaws Smart Startup Script
# Usage: ./start.sh [--rebuild]

echo -e "\033[0;34m╔════════════════════════════════════════════════════════════════╗\033[0m"
echo -e "\033[0;34m║                   Interpaws VPMS Launcher                      ║\033[0m"
echo -e "\033[0;34m╚════════════════════════════════════════════════════════════════╝\033[0m"

# 1. PRE-FLIGHT CHECKS
# -----------------------------------------------------------
# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "\033[0;31m❌ Error: Docker is not running.\033[0m"
    echo "   Please start Docker Desktop and try again."
    exit 1
fi

# Check for Port Conflict (Ollama)
# Host port 11435 is used to avoid clashing with local Ollama desktop instances
if lsof -Pi :11435 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "\033[0;33m⚠️  Warning: Port 11435 is already in use.\033[0m"
    echo "   The bundled Ollama container needs this port."
    echo "   Please free it (or update the port mapping) before continuing."
    exit 1
fi

# 2. STARTUP LOGIC
# -----------------------------------------------------------
BUILD_FLAG=""

# Check for rebuild argument
if [[ "$1" == "--rebuild" ]]; then
    echo -e "\n\033[0;33m🔄 Rebuild requested. This will take a minute...\033[0m"
    BUILD_FLAG="--build"
else
    echo -e "\n\033[0;32m⚡ Fast-start mode enabled.\033[0m"
    echo "   (Use './start.sh --rebuild' if you installed new packages)"
fi

echo "📦 Orchestrating containers..."
# We assume the .env file is creating the necessary environment variables
# If not, we export the dummy keys just in case to prevent crash
if [ -z "$SENDGRID_API_KEY" ]; then
    export SENDGRID_API_KEY="mock_key_autogen"
    export SENDGRID_FROM_EMAIL="mock@interpaws.com"
fi

docker-compose up -d $BUILD_FLAG

# Ensure the standard model is present
echo -e "\n🤖 Pulling standard Ollama model (llama3)..."
if ! docker-compose exec ollama ollama pull llama3; then
    echo -e "\033[0;33m⚠️  Warning: Unable to pull llama3 automatically.\033[0m"
    echo "   Please run 'docker-compose exec ollama ollama pull llama3' manually after containers are healthy."
fi

# 3. HEALTH CHECKS
# -----------------------------------------------------------
echo -e "\n⏳ Waiting for services..."

check_service() {
    local url=$1
    local name=$2
    local max_retries=30
    
    echo -n "   - Checking $name..."
    for i in $(seq 1 $max_retries); do
        if curl -s --head "$url" >/dev/null; then
            echo -e " \033[0;32mOnline! ✅\033[0m"
            return 0
        fi
        sleep 1
    done
    echo -e " \033[0;31mTimed Out ❌\033[0m"
    return 1
}

# Verify Backend and Frontend
check_service "http://localhost:8000/docs" "Backend API"
BACKEND_STATUS=$?

check_service "http://localhost:3000" "Frontend UI"
FRONTEND_STATUS=$?

echo ""

if [ $BACKEND_STATUS -eq 0 ] && [ $FRONTEND_STATUS -eq 0 ]; then
    echo -e "\033[0;32m✅ SYSTEM OPERATIONAL\033[0m"
    echo "----------------------------------"
    echo "💻 Client: http://localhost:3000"
    echo "🛡️  Admin:  http://localhost:3000/admin/admin-login"
    echo "⚙️  API:    http://localhost:8000/docs"
else
    echo -e "\033[0;31m⚠️  SYSTEM PARTIALLY FAILED\033[0m"
    echo "   Run 'docker-compose logs backend' to debug."
fi
echo ""
