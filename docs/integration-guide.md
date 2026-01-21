# JobForge Integration Guide

Complete setup and usage guide for the JobForge + Orbit workforce intelligence platform.

## Prerequisites

Before starting, ensure you have:

- **Docker Desktop** installed and running
  - Download from: https://www.docker.com/products/docker-desktop
  - Verify: `docker --version` and `docker compose version`
- **Anthropic API key** for data queries (text-to-SQL generation)
  - Create account: https://console.anthropic.com
  - Get API key: https://console.anthropic.com/settings/keys
- **2GB disk space** for container images and data

## Quick Start

Get JobForge running in 5 steps:

### 1. Clone Repository

```bash
git clone https://github.com/your-org/jobforge.git
cd jobforge
```

### 2. Copy Environment Template

```bash
cp .env.example .env
```

### 3. Add Your API Key

Edit `.env` and replace the placeholder with your Anthropic API key:

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_ACTUAL_KEY_HERE
```

**Important:** The API key is required for data queries. Without it, only metadata and compliance queries will work.

### 4. Run the Start Script

**Unix/Mac:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```cmd
start.bat
```

### 5. Browser Opens Automatically

Your browser opens to http://localhost:8080 showing the JobForge deployment wizard.

**Services:**
- **Demo UI:** http://localhost:8080 - SSE-powered deployment narration
- **Query API:** http://localhost:8000 - Natural language query endpoints
- **API Docs:** http://localhost:8000/docs - Interactive Swagger documentation

## Manual Start (Without Browser Auto-Open)

If you prefer to manage services manually:

```bash
# Start services in background
docker compose up -d

# Watch startup logs
docker compose logs -f

# Stop watching logs: Ctrl+C (services continue running)
```

Check service status:

```bash
docker compose ps
```

You should see:
```
NAME              COMMAND                  STATUS         PORTS
jobforge-api      "jobforge api --host…"   Up (healthy)   0.0.0.0:8000->8000/tcp
jobforge-demo     "jobforge demo --hos…"   Up             0.0.0.0:8080->8080/tcp
```

## Verifying Installation

### Health Check

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{"status": "ok"}
```

### List Available Tables

```bash
curl http://localhost:8000/api/tables
```

Expected response:
```json
{
  "tables": [
    "cops_employment",
    "cops_employment_growth",
    "cops_immigration",
    "cops_other_replacement",
    "cops_other_seekers",
    "cops_retirement_rates",
    "cops_retirements",
    "cops_school_leavers",
    "dim_noc",
    "dim_occupations",
    "element_additional_information",
    "element_employment_requirements",
    "element_example_titles",
    "element_exclusions",
    "element_labels",
    "element_lead_statement",
    "element_main_duties",
    "element_workplaces_employers",
    "job_architecture",
    "oasis_abilities",
    "oasis_knowledges",
    "oasis_skills",
    "oasis_workactivities",
    "oasis_workcontext"
  ],
  "count": 24
}
```

## Example Queries by Domain

### Labour Supply/Demand

Ask questions about workforce projections and market dynamics:

```bash
# Employment forecasts
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "How many software developers are projected for 2025?"}'

# Retirement rates
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the retirement rate for healthcare occupations?"}'

# Immigration numbers
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "Show immigration numbers for TEER 2 occupations in 2030"}'

# School leavers
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "How many school leavers expected in TEER 1 for 2028?"}'

# Employment growth
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the employment growth rate for NOC 21232?"}'
```

### Occupation Lookups

Query the National Occupational Classification (NOC) structure:

```bash
# NOC code lookup
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the class title for NOC 21232?"}'

# TEER listings
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "List all TEER 1 unit groups"}'

# Broad category exploration
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "Show all occupations in broad category 2"}'

# Main duties
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main duties for data analysts?"}'

# Example job titles
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "List example titles for software engineers"}'
```

### Skills and Proficiencies

Query OaSIS (Occupational and Skills Information System) data:

```bash
# Required skills
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "What skills are needed for data analysts?"}'

# Abilities
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "What abilities are required for NOC 21232?"}'

# Knowledge domains
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "List knowledge requirements for software developers"}'

# Work activities
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "What work activities are common in TEER 1 tech occupations?"}'
```

### Trend Analysis

Compare projections across years and categories:

```bash
# Growth forecast
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "Employment growth forecast for broad category 2 from 2023 to 2033"}'

# School leavers trend
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "How many school leavers expected in 2030 compared to 2025?"}'

# Retirement trends
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "Compare retirement rates between 2023 and 2033 for healthcare"}'

# Year-over-year comparison
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "Compare employment projections 2023 vs 2033 for TEER 1"}'
```

### Compliance and Lineage

Query metadata, provenance, and governance compliance:

```bash
# Data lineage
curl -X POST http://localhost:8000/api/query/metadata \
  -H "Content-Type: application/json" \
  -d '{"question": "Where does dim_noc data come from?"}'

# Table structure
curl -X POST http://localhost:8000/api/query/metadata \
  -H "Content-Type: application/json" \
  -d '{"question": "Describe table cops_employment"}'

# Upstream dependencies
curl -X POST http://localhost:8000/api/query/metadata \
  -H "Content-Type: application/json" \
  -d '{"question": "Show lineage for dim_occupations"}'

# DADM compliance
curl http://localhost:8000/api/compliance/dadm

# DAMA DMBOK compliance
curl http://localhost:8000/api/compliance/dama

# Classification compliance
curl http://localhost:8000/api/compliance/classification
```

## API Reference

### POST /api/query/data

Query WiQ data using natural language.

**Request:**
```json
{
  "question": "How many software developers are projected for 2025?"
}
```

**Response:**
```json
{
  "question": "How many software developers are projected for 2025?",
  "sql": "SELECT \"2025\" FROM cops_employment WHERE noc_code = '21232'",
  "explanation": "This query finds the employment projection for NOC 21232 (Software developers and programmers) in year 2025 from the COPS employment forecast table.",
  "results": [{"2025": 297400}],
  "row_count": 1,
  "error": null
}
```

**Features:**
- Generates SQL from natural language using Claude API
- Executes against gold layer Parquet files via DuckDB
- Provides explanation for transparency
- Returns structured results with row count
- Includes source attribution in metadata

**Requires:** `ANTHROPIC_API_KEY` in `.env`

### POST /api/query/metadata

Answer questions about data lineage and structure.

**Request:**
```json
{
  "question": "Where does dim_noc come from?"
}
```

**Response:**
```json
{
  "question": "Where does dim_noc come from?",
  "answer": "dim_noc is sourced from Statistics Canada National Occupational Classification (NOC) 2021. The transformation path is: Statistics Canada NOC → staged/noc_structure.csv → bronze/dim_noc.parquet → silver/dim_noc.parquet → gold/dim_noc.parquet. It contains 516 occupational unit groups with full TEER hierarchy."
}
```

**Features:**
- Pattern-based intent matching (no API key required)
- Traverses lineage graph built from metadata catalog
- Provides transformation path from source to gold
- Includes DADM compliance references when relevant

### GET /api/compliance/{framework}

Generate compliance report for governance framework.

**Supported frameworks:**
- `dadm` - Directive on Automated Decision Making
- `dama` - DAMA DMBOK knowledge areas
- `classification` - Job classification policy alignment

**Request:**
```bash
curl http://localhost:8000/api/compliance/dadm
```

**Response:** Requirements Traceability Matrix (RTM) in JSON format mapping WiQ artifacts to framework requirements.

### GET /api/tables

List all available gold tables.

**Request:**
```bash
curl http://localhost:8000/api/tables
```

**Response:**
```json
{
  "tables": ["cops_employment", "dim_noc", "..."],
  "count": 24
}
```

### GET /api/health

Health check endpoint for service orchestration.

**Request:**
```bash
curl http://localhost:8000/api/health
```

**Response:**
```json
{"status": "ok"}
```

**Used by:** Docker Compose healthcheck and startup scripts.

## Stopping the Stack

### Stop Services (Keep Data)

```bash
docker compose down
```

This stops containers but preserves data volumes and images.

### Stop Services and Remove Volumes

```bash
docker compose down -v
```

**Warning:** This removes all data volumes. Gold layer Parquet files in `./data/gold` are NOT affected (volume mounted from host).

### View Logs

```bash
# All services
docker compose logs

# Specific service
docker compose logs api
docker compose logs demo

# Follow logs (tail -f)
docker compose logs -f api
```

## Troubleshooting

### Connection Refused Errors

**Symptom:**
```
curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**Cause:** API service not ready yet. Healthcheck still in progress.

**Solution:** Wait 10-15 seconds for healthcheck to pass. Check status:
```bash
docker compose ps
```

Look for `(healthy)` status on `jobforge-api`.

### CORS Errors in Browser

**Symptom:**
```
Access to fetch at 'http://localhost:8000/api/query/data' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Cause:** Frontend port not in CORS_ORIGINS.

**Solution:** Edit `.env` and add your frontend origin:
```bash
# .env
CORS_ORIGINS=http://localhost:8080,http://localhost:3000
```

Then restart:
```bash
docker compose down
docker compose up -d
```

### Invalid API Key Error

**Symptom:**
```json
{
  "type": "about:blank",
  "title": "Query Error",
  "status": 500,
  "detail": "Authentication error from Claude API",
  "guidance": "Check your ANTHROPIC_API_KEY in .env file"
}
```

**Cause:** Missing or invalid `ANTHROPIC_API_KEY`.

**Solution:**
1. Get valid API key from https://console.anthropic.com/settings/keys
2. Update `.env` file with correct key
3. Restart services: `docker compose restart api`

### No Results Returned

**Symptom:** Query succeeds but returns empty results `[]`.

**Possible causes:**
1. **Query filters too restrictive** - Try broader question
2. **NOC code doesn't exist** - Check valid NOC codes: `curl http://localhost:8000/api/tables`
3. **Year out of range** - COPS data covers 2023-2033

**Debug:** Check the generated SQL in the response to understand what was queried.

### Container Won't Start

**Symptom:**
```
Error response from daemon: driver failed programming external connectivity
```

**Cause:** Port already in use (another service on 8000 or 8080).

**Solution:** Change ports in `.env`:
```bash
API_PORT=8001
DEMO_PORT=8081
```

Then restart: `docker compose up -d`

### Permission Errors (Linux)

**Symptom:**
```
Permission denied: '/app/data/gold'
```

**Cause:** Docker volume mount permissions issue.

**Solution:** Fix ownership:
```bash
sudo chown -R $USER:$USER ./data
docker compose down
docker compose up -d
```

## Next Steps

- **Learn the architecture:** Read [docs/architecture.md](./architecture.md) for system design details
- **Extend query patterns:** See [docs/extending-intents.md](./extending-intents.md) to add custom intents
- **Explore API interactively:** Visit http://localhost:8000/docs for Swagger UI
- **Try the demo:** Open http://localhost:8080 to see the deployment wizard

## Support

For issues and questions:
- Check troubleshooting section above
- Review API documentation: http://localhost:8000/docs
- Check Docker logs: `docker compose logs -f`
- Verify .env configuration matches .env.example

## Production Deployment

This Docker Compose setup is designed for **development and demo purposes**.

For production deployment, consider:
- Use environment-specific `.env` files (`.env.production`)
- Implement API rate limiting and authentication
- Add monitoring (Prometheus, Grafana)
- Use secrets management (Docker Swarm secrets, Kubernetes secrets)
- Configure reverse proxy (nginx, Traefik) with HTTPS
- Set up log aggregation (ELK stack, Loki)
- Implement backup strategy for data volumes
- Configure resource limits in docker-compose.yml
