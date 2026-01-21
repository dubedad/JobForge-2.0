# Phase 13: Deployment and Documentation - Research

**Researched:** 2026-01-20
**Domain:** Docker Compose multi-service deployment, Python FastAPI, static frontend, integration documentation
**Confidence:** HIGH

## Summary

Phase 13 requires deploying Orbit + JobForge stack via Docker Compose with one-command startup, browser auto-launch, and complete integration documentation. Research focused on Docker Compose patterns for multi-service Python applications, environment variable best practices, browser auto-launch approaches, and documentation structure for integration guides.

**Key findings:**
- Docker Compose multi-service pattern: separate containers for FastAPI backend, static frontend (via nginx), with healthcheck-based startup ordering
- Browser auto-launch: Docker containers cannot directly open host browsers; solution requires wrapper script on host machine
- Environment variables: Use Pydantic BaseSettings with .env files for configuration; Docker secrets for sensitive data (API keys)
- CORS already configured in existing codebase but requires environment variable updates for Orbit frontend port
- Documentation structure: README for quick start + docs/ folder for detailed integration guide with architecture diagram (Mermaid)

**Primary recommendation:** Use 3-service Docker Compose (api, demo, orbit-frontend) with nginx for static files, healthchecks for startup ordering, Pydantic BaseSettings for env config, and a start.sh wrapper script for browser auto-launch on host.

## Standard Stack

The established libraries/tools for Docker Compose Python deployments:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Docker Compose | v2.30.0+ | Multi-container orchestration | Official Docker tool, 92% of IT orgs use containers |
| FastAPI | 0.115.0+ | Python API framework | Already in use, excellent Docker support, official docs |
| uvicorn | 0.30.0+ | ASGI server | FastAPI official recommendation, lightweight |
| nginx | 1.25+ | Static file serving, reverse proxy | Industry standard for serving static files in containers |
| pydantic-settings | 2.12.0+ | Environment variable management | Official Pydantic extension, type-safe config |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.0.0+ | .env file loading | Development environments, local testing |
| waitress | 3.0+ | Pure-Python WSGI server | Windows fallback if needed (uvicorn preferred) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| nginx | Python http.server | nginx is production-grade, handles static files efficiently |
| Docker Compose | Kubernetes | Overkill for local/personal use; Compose simpler for single-host |
| .env files | Docker secrets | Secrets better for production; .env simpler for local dev |

**Installation:**
```bash
# Already in pyproject.toml dependencies
pip install fastapi uvicorn pydantic-settings python-dotenv

# Docker Desktop includes Docker Compose v2.30.0+
# Verify: docker compose version
```

## Architecture Patterns

### Recommended Project Structure
```
JobForge 2.0/
├── docker-compose.yml           # Multi-service orchestration
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Template for users
├── start.sh                     # Wrapper script (browser auto-launch)
├── Dockerfile                   # FastAPI backend image
├── orbit/
│   ├── Dockerfile              # Orbit frontend static build (if needed)
│   ├── config/                 # Orbit adapter configs
│   │   ├── adapters/
│   │   │   └── jobforge.yaml  # Already exists
│   │   └── intents/
│   │       └── wiq_intents.yaml # Already exists
│   └── static/                 # Static HTML/JS/CSS (or served directly)
├── docs/
│   ├── architecture.md         # Mermaid diagram + system overview
│   ├── integration-guide.md    # Step-by-step setup + example queries
│   └── extending-intents.md    # Tutorial for adding query patterns
└── src/jobforge/
    └── api/
        └── routes.py           # CORS already configured
```

### Pattern 1: Multi-Service Docker Compose with Healthchecks
**What:** Define multiple services (api, demo, orbit-frontend) with healthcheck-based startup ordering to ensure dependencies are ready before dependent services start.

**When to use:** Multi-service applications where one service (frontend) depends on another (API) being ready.

**Example:**
```yaml
# Source: Docker official docs, healthcheck patterns
version: '3.9'

services:
  api:
    build: .
    container_name: jobforge-api
    ports:
      - "${API_PORT:-8000}:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - CORS_ORIGINS=http://localhost:${ORBIT_PORT:-3000},http://localhost:${DEMO_PORT:-8080}
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - jobforge-network

  demo:
    build: .
    container_name: jobforge-demo
    command: ["jobforge", "demo", "--host", "0.0.0.0", "--port", "8080"]
    ports:
      - "${DEMO_PORT:-8080}:8080"
    depends_on:
      api:
        condition: service_healthy
    networks:
      - jobforge-network

  orbit-frontend:
    image: nginx:1.25-alpine
    container_name: orbit-frontend
    ports:
      - "${ORBIT_PORT:-3000}:80"
    volumes:
      - ./orbit/static:/usr/share/nginx/html:ro
      - ./orbit/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      api:
        condition: service_healthy
    networks:
      - jobforge-network

networks:
  jobforge-network:
    driver: bridge
```

### Pattern 2: Pydantic BaseSettings for Environment Variables
**What:** Use Pydantic's BaseSettings class to automatically load, validate, and type-check environment variables from .env files.

**When to use:** Any FastAPI application requiring configuration (already partially implemented in routes.py).

**Example:**
```python
# Source: FastAPI official docs - https://fastapi.tiangolo.com/advanced/settings/
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "JobForge Query API"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    demo_port: int = 8080
    orbit_port: int = 3000
    anthropic_api_key: str
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

@lru_cache
def get_settings():
    return Settings()

# Use in FastAPI dependencies
settings = get_settings()
```

### Pattern 3: Browser Auto-Launch via Wrapper Script
**What:** Shell/batch script that runs docker-compose up, waits for healthcheck, then opens browser using OS-specific commands.

**When to use:** Local development/personal use where automatic browser launch improves UX.

**Example:**
```bash
# Source: Derived from Docker Compose startup patterns
#!/bin/bash
# start.sh - Cross-platform wrapper for docker-compose with browser auto-launch

echo "Starting JobForge + Orbit stack..."
docker compose up -d

echo "Waiting for services to be ready..."
# Wait for API healthcheck
until docker compose ps api | grep -q "healthy"; do
    sleep 2
done

echo "Services ready! Opening browser..."

# Detect OS and open browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open http://localhost:3000
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows (Git Bash/Cygwin)
    start http://localhost:3000
else
    # Linux
    xdg-open http://localhost:3000 2>/dev/null || echo "Please open http://localhost:3000 in your browser"
fi

echo ""
echo "JobForge stack running:"
echo "  - Orbit Chat:    http://localhost:3000"
echo "  - Demo Wizard:   http://localhost:8080"
echo "  - API Docs:      http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop (then run: docker compose down)"
```

### Pattern 4: Nginx for Static Frontend
**What:** Use nginx container to serve Orbit static files (HTML/JS/CSS) with reverse proxy configuration if needed.

**When to use:** Serving static frontend files in production-like environment.

**Example:**
```nginx
# Source: nginx Docker patterns for Python backends
# orbit/nginx.conf
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    server {
        listen 80;
        server_name localhost;

        # Serve static files
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;
        }

        # Proxy API requests if frontend needs it
        # (Not needed if frontend uses http://localhost:8000 directly)
        location /api/ {
            proxy_pass http://api:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

### Anti-Patterns to Avoid
- **Hardcoding ports/URLs in code:** Always use environment variables for configuration
- **Running database migrations on every container start:** Use one-time init scripts or separate migration service
- **Using shell form in Dockerfile CMD:** Breaks signal handling; always use exec form ["cmd", "arg"]
- **Exposing sensitive env vars in docker-compose.yml:** Use .env files and Docker secrets
- **No healthchecks:** Services start before dependencies are ready, causing connection failures

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser auto-launch from container | Python webbrowser module in container | Host-side wrapper script (start.sh) | Containers run headless; no access to host browser |
| Environment variable validation | Manual os.getenv() + type conversion | Pydantic BaseSettings | Type safety, validation, .env support, testing-friendly |
| Static file serving in Python | http.server module | nginx container | Production-grade performance, caching, MIME types |
| Service startup ordering | sleep delays, retry loops | Docker Compose depends_on + healthcheck | Race conditions cause flaky startups; healthchecks guarantee readiness |
| CORS configuration | Custom middleware | FastAPI CORSMiddleware | Already implements preflight, credentials, methods, headers correctly |
| Documentation diagrams | Manual PNG/SVG editing | Mermaid markdown syntax | Version-controllable, diff-friendly, renders in GitHub/editors |

**Key insight:** Docker Compose and FastAPI ecosystem provide battle-tested solutions for deployment patterns. Custom implementations introduce bugs and maintenance burden.

## Common Pitfalls

### Pitfall 1: CORS Origin Mismatch in Docker
**What goes wrong:** Frontend can't connect to API due to CORS errors even though CORSMiddleware is configured.

**Why it happens:** CORS_ORIGINS environment variable contains wrong ports or uses container-internal hostnames instead of localhost URLs that browser sees.

**How to avoid:**
- Always use `http://localhost:<port>` in CORS_ORIGINS, not container names or 0.0.0.0
- Update CORS_ORIGINS when adding Orbit frontend: `CORS_ORIGINS=http://localhost:3000,http://localhost:8080`
- Test CORS by checking browser console for "blocked by CORS policy" errors

**Warning signs:** Browser DevTools console shows CORS errors; API returns 200 but response is blocked

### Pitfall 2: depends_on Without Healthcheck
**What goes wrong:** Frontend container starts before API is ready, initial requests fail, users see errors.

**Why it happens:** `depends_on` only waits for container to START, not for service inside to be READY. API takes 5-10 seconds to initialize.

**How to avoid:**
- Always define healthcheck on services that others depend on
- Use `condition: service_healthy` in depends_on
- Healthcheck should test actual endpoint (e.g., /api/health), not just container running

**Warning signs:** Intermittent "connection refused" errors on first page load; works after refresh

### Pitfall 3: Environment Variables Not Loaded from .env
**What goes wrong:** Application starts but uses default values instead of values from .env file; ANTHROPIC_API_KEY missing.

**Why it happens:** Docker Compose doesn't automatically load .env into containers; Pydantic BaseSettings doesn't find .env file at expected path.

**How to avoid:**
- Docker Compose: use `env_file: .env` in service definition OR `environment:` with `${VAR}` substitution
- Pydantic: ensure .env file is in working directory of container (WORKDIR in Dockerfile)
- Always provide .env.example as template with dummy values

**Warning signs:** "ANTHROPIC_API_KEY not set" errors; config shows default values not .env values

### Pitfall 4: Volume Mount Path Mismatches
**What goes wrong:** Data directory not accessible in container; gold tables not found; API returns "no tables" errors.

**Why it happens:** Host path in volume mount doesn't match container's expected path; relative paths resolve differently.

**How to avoid:**
- Use absolute paths in Dockerfile WORKDIR: `WORKDIR /app`
- Mount data relative to app root: `./data:/app/data`
- Verify paths match PipelineConfig expectations (check config.py for data_root)

**Warning signs:** File not found errors for parquet files; lineage graph empty; /api/tables returns count: 0

### Pitfall 5: Browser Can't Open from Inside Container
**What goes wrong:** Python webbrowser.open() called in container startup script does nothing or crashes.

**Why it happens:** Containers run headless without display server or access to host's browser.

**How to avoid:**
- Never use webbrowser module in Dockerfile CMD or entrypoint
- Use host-side wrapper script (start.sh) to open browser AFTER containers start
- Check healthcheck status before opening browser

**Warning signs:** Container logs show webbrowser errors; browser doesn't open automatically

### Pitfall 6: Documentation Drift
**What goes wrong:** README instructions don't match actual docker-compose.yml; users can't start stack.

**Why it happens:** Docker Compose config updated but documentation not updated; example .env.example missing variables.

**How to avoid:**
- Update documentation in same commit as code changes
- Keep .env.example in sync with Settings model
- Test "Quick Start" instructions on fresh clone before committing

**Warning signs:** GitHub issues asking "how do I run this?"; .env.example missing new required variables

## Code Examples

Verified patterns from official sources:

### FastAPI Dockerfile (Official Pattern)
```dockerfile
# Source: https://fastapi.tiangolo.com/deployment/docker/
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for Docker cache optimization
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy application code
COPY src/ ./src/
COPY data/catalog/ ./data/catalog/
COPY orbit/ ./orbit/

# Expose port
EXPOSE 8000

# Use exec form for proper signal handling
CMD ["uvicorn", "jobforge.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Healthcheck with curl
```yaml
# Source: Docker Compose official docs
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 10s      # Check every 10 seconds
  timeout: 5s        # Fail if no response in 5 seconds
  retries: 5         # Try 5 times before marking unhealthy
  start_period: 10s  # Grace period for startup
```

### Environment Variable Loading (.env file)
```bash
# .env.example - Template for users to copy to .env
# Copy this file to .env and fill in your values

# API Configuration
API_PORT=8000
DEMO_PORT=8080
ORBIT_PORT=3000

# REQUIRED: Your Anthropic API key for data queries
ANTHROPIC_API_KEY=sk-ant-api03-...

# CORS origins (comma-separated, no spaces)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Optional: Override data directory
# DATA_ROOT=./data
```

### Docker Compose Service with Environment Variables
```yaml
# Source: Docker Compose environment variable best practices
services:
  api:
    build: .
    env_file: .env  # Load all variables from .env
    environment:
      # Override or add specific variables
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000,http://localhost:8080}
    ports:
      - "${API_PORT:-8000}:8000"
```

### CORS Configuration (Existing Pattern from routes.py)
```python
# Source: src/jobforge/api/routes.py (lines 49-61)
# Already implemented - just needs env var update

# Get allowed origins from environment (comma-separated)
origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
allowed_origins = [o.strip() for o in origins_str.split(",")]

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)
```

### Mermaid Architecture Diagram Example
```mermaid
# Source: Mermaid architecture diagram docs
graph TB
    subgraph "Docker Compose Stack"
        subgraph "Frontend Layer"
            Orbit[Orbit Chat UI<br/>nginx:1.25<br/>Port 3000]
            Demo[Demo Wizard UI<br/>uvicorn<br/>Port 8080]
        end

        subgraph "API Layer"
            API[JobForge Query API<br/>FastAPI + uvicorn<br/>Port 8000]
        end

        subgraph "Data Layer"
            Gold[(Gold Tables<br/>24 Parquet Files)]
            Catalog[(Metadata Catalog<br/>JSON Files)]
        end
    end

    User[User Browser] -->|http://localhost:3000| Orbit
    User -->|http://localhost:8080| Demo

    Orbit -->|POST /api/query/data<br/>POST /api/query/metadata| API
    Demo -->|GET /api/deploy/stream| API

    API -->|Query with DuckDB| Gold
    API -->|Lineage queries| Catalog

    style Orbit fill:#e1f5ff
    style Demo fill:#e1f5ff
    style API fill:#ffe1f5
    style Gold fill:#f5ffe1
    style Catalog fill:#f5ffe1
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| docker-compose (v1) | docker compose (v2) | 2022 | v2 is integrated into Docker CLI; v1 deprecated |
| tiangolo/uvicorn-gunicorn-fastapi image | Build from python:3.11 base | 2023 | Official FastAPI docs recommend building from scratch for flexibility |
| Shell form CMD in Dockerfile | Exec form CMD ["cmd", "arg"] | Always recommended | Exec form enables proper signal handling and graceful shutdown |
| Manual retry loops for service dependencies | depends_on with service_healthy | Docker Compose 2.1+ | Healthchecks guarantee service readiness, eliminate race conditions |
| Environment variables for secrets | Docker secrets | Docker Compose 3.1+ | Secrets stored securely, not exposed in logs or inspect output |
| Separate nginx + gunicorn containers | Single uvicorn container for small apps | 2024 trend | Simpler stack for low-traffic apps; add nginx only when needed |

**Deprecated/outdated:**
- **docker-compose command (hyphenated):** Use `docker compose` (space, no hyphen). v1 CLI deprecated but still works; v2 is future.
- **version field in docker-compose.yml:** No longer required in Compose v2; legacy from v1 schema validation.
- **tiangolo/uvicorn-gunicorn-fastapi:** Officially deprecated; FastAPI docs recommend custom Dockerfile.

## Open Questions

Things that couldn't be fully resolved:

1. **Orbit Frontend Implementation**
   - What we know: Orbit is 85% built, has adapter configs (jobforge.yaml, wiq_intents.yaml), has retrievers/ directory
   - What's unclear: Is Orbit a static HTML/JS app or a Python-served app? Need to confirm whether orbit/static/ exists or needs to be created
   - Recommendation: Check with planner if Orbit frontend is static files or requires build step. Assume static for now; adjust docker-compose.yml if Python-served.

2. **CLI Command for Orbit**
   - What we know: `jobforge api` and `jobforge demo` exist in cli/commands.py
   - What's unclear: Is there a `jobforge orbit` command or does Orbit run standalone?
   - Recommendation: Assume Orbit is static files served by nginx. If Orbit needs Python backend, add CLI command in implementation.

3. **Data Volume Persistence Strategy**
   - What we know: Gold tables exist in data/gold/, catalog in data/catalog/
   - What's unclear: Should Docker Compose mount existing data/ directory or use named volumes for persistence?
   - Recommendation: Mount ./data as volume for local dev (easy to inspect files). Use named volumes if deploying to shared server.

4. **Multi-Architecture Docker Images**
   - What we know: Python 3.11 base images support ARM64 and AMD64
   - What's unclear: Do we need to build multi-arch images for M1 Mac + Windows users?
   - Recommendation: Use standard python:3.11 base (supports both). Add multi-arch build only if users report issues.

## Sources

### Primary (HIGH confidence)
- [FastAPI Official Docker Deployment](https://fastapi.tiangolo.com/deployment/docker/) - Dockerfile patterns, exec form CMD, proxy headers
- [FastAPI Official Settings/Environment Variables](https://fastapi.tiangolo.com/advanced/settings/) - Pydantic BaseSettings, .env files, dependency injection
- [FastAPI Official CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/) - CORSMiddleware configuration
- [Docker Compose Official Documentation](https://docs.docker.com/compose/) - Multi-service patterns
- [Docker Official Best Practices - Environment Variables](https://docs.docker.com/compose/how-tos/environment-variables/best-practices/) - .env files, secrets
- [Docker Official Secrets Documentation](https://docs.docker.com/compose/how-tos/use-secrets/) - Managing sensitive data
- [Python Official webbrowser Module](https://docs.python.org/3/library/webbrowser.html) - Browser control limitations

### Secondary (MEDIUM confidence)
- [Better Stack: FastAPI Docker Best Practices](https://betterstack.com/community/guides/scaling-python/fastapi-docker-best-practices/) - Production patterns, .dockerignore
- [TestDriven.io: Dockerizing FastAPI](https://testdriven.io/blog/fastapi-docker-traefik/) - Multi-service setup with Postgres
- [Medium: Docker Compose Healthcheck Configuration](https://medium.com/@saklani1408/configuring-healthcheck-in-docker-compose-3fa6439ee280) - Healthcheck examples
- [Last9: Docker Compose Health Checks Guide](https://last9.io/blog/docker-compose-health-checks/) - service_healthy pattern
- [Baeldung: Run Script After Container Starts](https://www.baeldung.com/ops/docker-compose-run-script-on-start) - Post-startup hooks
- [Mermaid Official Architecture Diagrams](https://mermaid.ai/open-source/syntax/architecture.html) - Diagram syntax and examples
- [Hitchhiker's Guide to Python - Documentation](https://docs.python-guide.org/writing/documentation/) - Python doc structure recommendations

### Tertiary (LOW confidence)
- WebSearch: Docker Compose multi-service patterns (2026 searches - general ecosystem trends)
- WebSearch: Browser auto-launch with Docker (community forum discussions - no definitive solution)
- WebSearch: nginx + Python backend patterns (community tutorials - verified against official docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - FastAPI official docs, Docker official docs, existing pyproject.toml dependencies
- Architecture: HIGH - Docker Compose patterns from official docs, FastAPI deployment guide
- Pitfalls: HIGH - Verified from official docs and common issues in FastAPI/Docker GitHub repos
- Browser auto-launch: MEDIUM - No official Docker solution; wrapper script is community best practice
- Orbit frontend structure: LOW - Need to verify if static files exist or require build step

**Research date:** 2026-01-20
**Valid until:** 2026-02-20 (30 days - Docker Compose and FastAPI are stable, slow-moving technologies)
