#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Load environment variables from .env file
if [ -f .env ]; then
    echo -e "${GREEN}Loading environment variables from .env file...${NC}"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${GREEN}No .env file found, using default values...${NC}"
fi

# Default values if not set in .env
TRADING_VIEW_FIELD_ID=${TRADING_VIEW_FIELD_ID:-3358}
REDIS_USERNAME=${REDIS_USERNAME:-default}
REDIS_PASSWORD=${REDIS_PASSWORD:-default}
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}

echo -e "${GREEN}Environment variables:${NC}"
echo "TRADING_VIEW_FIELD_ID: ${TRADING_VIEW_FIELD_ID}"
echo "REDIS_HOST: ${REDIS_HOST}"
echo "REDIS_PORT: ${REDIS_PORT}"
echo "REDIS_USERNAME: ${REDIS_USERNAME}"
echo "REDIS_PASSWORD: ${REDIS_PASSWORD}"

echo -e "\n${GREEN}Removing old Docker images to ensure clean rebuild...${NC}"
docker rmi digital-ocean-app || true

echo -e "${GREEN}Building Docker image...${NC}"
docker build \
    --build-arg TRADING_VIEW_FIELD_ID=${TRADING_VIEW_FIELD_ID} \
    --build-arg REDIS_HOST=${REDIS_HOST} \
    --build-arg REDIS_PORT=${REDIS_PORT} \
    --build-arg REDIS_USERNAME=${REDIS_USERNAME} \
    -t digital-ocean-app .

echo -e "\n${GREEN}Stopping any existing containers...${NC}"
docker stop digital-ocean-app-container || true
docker rm digital-ocean-app-container || true

echo -e "\n${GREEN}Starting the container...${NC}"
docker run -d \
    --name digital-ocean-app-container \
    -p 8080:8080 \
    -e REDIS_PASSWORD=${REDIS_PASSWORD} \
    digital-ocean-app

echo -e "\n${GREEN}Container is running!${NC}"
echo "You can access the app at: https://localhost:8080"
echo "Using Trading View field ID: ${TRADING_VIEW_FIELD_ID}"
echo "Using Redis host: ${REDIS_HOST}"
echo "Using Redis port: ${REDIS_PORT}"
echo "Using Redis username: ${REDIS_USERNAME}"
echo "Using Redis password: ${REDIS_PASSWORD}"
echo -e "\nTo view logs, run: docker logs -f digital-ocean-app-container"
echo "To stop the container, run: docker stop digital-ocean-app-container"
echo "To remove the container, run: docker rm digital-ocean-app-container"
echo "To remove the image, run: docker rmi digital-ocean-app" 