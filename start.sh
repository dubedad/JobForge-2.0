#!/bin/bash
# JobForge stack launcher with browser auto-open

echo "Starting JobForge stack..."
docker compose up -d

echo "Waiting for API to be healthy..."
until docker compose ps api | grep -q "healthy"; do
    sleep 2
    echo "  Waiting..."
done

echo "Services ready!"

# Open browser based on OS
DEMO_PORT=${DEMO_PORT:-8080}
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:$DEMO_PORT
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    start http://localhost:$DEMO_PORT
else
    xdg-open http://localhost:$DEMO_PORT 2>/dev/null || echo "Open http://localhost:$DEMO_PORT"
fi

echo ""
echo "JobForge running:"
echo "  Demo:     http://localhost:$DEMO_PORT"
echo "  API:      http://localhost:${API_PORT:-8000}"
echo "  API Docs: http://localhost:${API_PORT:-8000}/docs"
echo ""
echo "To stop: docker compose down"
