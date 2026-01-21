@echo off
echo Starting JobForge stack...
docker compose up -d

echo Waiting for API to be healthy...
:wait
docker compose ps api | findstr "healthy" >nul
if errorlevel 1 (
    timeout /t 2 >nul
    echo   Waiting...
    goto wait
)

echo Services ready!
start http://localhost:8080

echo.
echo JobForge running:
echo   Demo:     http://localhost:8080
echo   API:      http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo To stop: docker compose down
