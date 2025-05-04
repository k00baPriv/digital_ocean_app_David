#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color



# Default Trading View field ID
TRADING_VIEW_FIELD_ID=${TRADING_VIEW_FIELD_ID}

echo -e "${GREEN}Removing old Docker images to ensure clean rebuild...${NC}"
docker rmi digital-ocean-app || true

echo -e "${GREEN}Building Docker image...${NC}"
docker build -t digital-ocean-app .

echo -e "\n${GREEN}Stopping any existing containers...${NC}"
docker stop digital-ocean-app-container || true
docker rm digital-ocean-app-container || true

echo -e "\n${GREEN}Starting the container...${NC}"
docker run -d \
    --name digital-ocean-app-container \
    -p 8080:8080 \
    -e TRADING_VIEW_FIELD_ID=${TRADING_VIEW_FIELD_ID} \
    digital-ocean-app

echo -e "\n${GREEN}Container is running!${NC}"
echo "You can access the app at: https://localhost:8080"
echo "Using Trading View field ID: ${TRADING_VIEW_FIELD_ID}"
echo -e "\nTo view logs, run: docker logs -f digital-ocean-app-container"
echo "To stop the container, run: docker stop digital-ocean-app-container"
echo "To remove the container, run: docker rm digital-ocean-app-container"
echo "To remove the image, run: docker rmi digital-ocean-app" 