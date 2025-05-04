#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Create SSL certificates if they don't exist
if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
    echo -e "${GREEN}Generating SSL certificates...${NC}"
    mkdir -p ssl
    openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365 -subj "/CN=localhost"
fi

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
    -e SSL_CERT_PATH=/etc/ssl/certs/cert.pem \
    -e SSL_KEY_PATH=/etc/ssl/certs/key.pem \
    -v $(pwd)/ssl:/etc/ssl/certs \
    digital-ocean-app

echo -e "\n${GREEN}Container is running!${NC}"
echo "You can access the app at: https://localhost:8080"
echo -e "\nTo view logs, run: docker logs -f digital-ocean-app-container"
echo "To stop the container, run: docker stop digital-ocean-app-container"
echo "To remove the container, run: docker rm digital-ocean-app-container"
echo "To remove the image, run: docker rmi digital-ocean-app" 