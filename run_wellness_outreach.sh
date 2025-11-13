#!/bin/bash
#
# Wellness Outreach Runner Script
# 
# This script runs the wellness outreach system inside the Docker backend container.
# 
# Usage:
#   ./run_wellness_outreach.sh          # Run with default settings
#   ./run_wellness_outreach.sh --help   # Show help
#

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Interpaws Wellness Outreach System Runner              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if containers are running
if ! docker-compose ps | grep -q "backend.*Up"; then
    echo -e "${RED}❌ Backend container is not running.${NC}"
    echo "Starting containers..."
    docker-compose up -d
    echo "Waiting for services to be ready..."
    sleep 10
fi

echo -e "${GREEN}✅ Backend container is running${NC}"
echo ""
echo -e "${BLUE}Running wellness outreach script...${NC}"
echo ""

# Run the wellness outreach script
docker-compose exec -T backend python -m app.wellness_outreach

echo ""
echo -e "${GREEN}✅ Wellness outreach complete!${NC}"
echo ""
echo "📝 Check backend/outreach_log.txt for email records"
echo ""
