---
type: quick
plan: 001
wave: 1
files_modified:
  - src/jobforge/api/static/index.html
  - src/jobforge/api/routes.py
autonomous: true

must_haves:
  truths:
    - "User sees landing page at root (/) explaining JobForge"
    - "User can type a question and get formatted results"
    - "User can browse example queries by business use case"
    - "Developer can access /docs for API reference"
  artifacts:
    - path: "src/jobforge/api/static/index.html"
      provides: "Landing page with query UI and examples"
      min_lines: 200
  key_links:
    - from: "src/jobforge/api/routes.py"
      to: "src/jobforge/api/static/index.html"
      via: "StaticFiles mount at /"
      pattern: "StaticFiles"
---

<objective>
Create a user-facing landing page at root (/) with query UI and example queries.

Purpose: Replace technical Swagger landing with business-friendly interface for workforce analysts
Output: Static HTML page served at / with query interface, example questions, and link to /docs
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/jobforge/api/routes.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create landing page HTML with query UI and examples</name>
  <files>src/jobforge/api/static/index.html</files>
  <action>
Create static/index.html with vanilla HTML/CSS/JS:

**Header section:**
- JobForge logo/title
- Tagline: "Workforce Intelligence Query Platform"
- Brief description: "Ask questions about Canadian workforce data in plain English"

**Query input section:**
- Large text input with placeholder "Ask a question about workforce data..."
- Submit button
- Loading indicator (hidden by default)

**Example queries section organized by use case:**

**Forecasting (COPS data):**
- "What is the projected employment for software engineers in 2028?"
- "Show demand vs supply trends for healthcare workers 2025-2030"
- "Which occupations have the largest projected shortages?"

**Skills Intelligence (NOC/O*NET):**
- "What skills are required for data scientists?"
- "Compare the skill profiles of project managers and business analysts"
- "Which occupations require Python programming?"

**Compliance and Governance:**
- "Show DADM compliance status for our data pipeline"
- "What tables exist and where did they come from?"
- "How does occupation data flow through the system?"

**Lineage and Metadata:**
- "How many tables are in the gold layer?"
- "What columns are in dim_noc?"
- "Where does cops_school_leavers data come from?"

**Results section:**
- Initially shows "Results will appear here" placeholder
- Displays query results with:
  - Question asked
  - SQL generated (if data query)
  - Explanation
  - Data table (if applicable)
  - Error message formatting

**Footer:**
- Link to /docs (API Reference)
- Link to GitHub (if applicable)
- Version info

**JavaScript:**
- Submit handler calls POST /api/query/data with {question: text}
- On error 4xx, falls back to POST /api/query/metadata
- Displays results in results section
- Shows/hides loading indicator

**CSS (inline or style tag):**
- Clean, modern design (no framework needed)
- Responsive layout
- Card-style example sections
- Syntax highlighting for SQL (simple pre/code styling)
- Error state styling (red border, error message)
  </action>
  <verify>File exists at src/jobforge/api/static/index.html with >200 lines</verify>
  <done>Landing page HTML with query form, example queries by category, results display</done>
</task>

<task type="auto">
  <name>Task 2: Mount static files and serve landing page at root</name>
  <files>src/jobforge/api/routes.py</files>
  <action>
Update create_api_app() to serve static files:

1. Add imports:
   - from fastapi.staticfiles import StaticFiles
   - from fastapi.responses import FileResponse
   - from pathlib import Path

2. After api_app creation, mount static files:
   ```python
   # Get the static directory path relative to this file
   static_dir = Path(__file__).parent / "static"

   # Serve landing page at root
   @api_app.get("/", response_class=FileResponse)
   async def landing_page():
       return FileResponse(static_dir / "index.html")
   ```

3. Ensure static directory is created if missing (or document requirement)

Note: Do NOT use StaticFiles mount at "/" as it conflicts with API routes.
Use explicit FileResponse for the index.html only.
  </action>
  <verify>curl http://localhost:8000/ returns HTML content (not JSON)</verify>
  <done>Root (/) serves landing page, /docs still works for API reference</done>
</task>

<task type="auto">
  <name>Task 3: Verify integration</name>
  <files></files>
  <action>
Start the API server and verify:

1. Run: cd "c:/Users/Administrator/Dropbox/++ Results Kit/JobForge 2.0" && python -m jobforge api &

2. Test landing page:
   - curl http://localhost:8000/ should return HTML
   - HTML should contain "JobForge" title
   - HTML should contain example queries

3. Test API still works:
   - curl http://localhost:8000/docs should return Swagger UI
   - curl http://localhost:8000/api/health should return {"status": "ok"}
   - curl http://localhost:8000/api/tables should return table list

4. Stop the server
  </action>
  <verify>All curl commands return expected responses</verify>
  <done>Landing page served at /, API endpoints all functional, /docs accessible</done>
</task>

</tasks>

<verification>
- GET / returns HTML with JobForge title and query UI
- GET /docs returns Swagger documentation
- POST /api/query/data still accepts queries
- POST /api/query/metadata still accepts queries
- GET /api/health returns {"status": "ok"}
- GET /api/tables returns table list
</verification>

<success_criteria>
- Landing page loads at http://localhost:8000/
- Example queries visible and organized by use case (Forecasting, Skills, Compliance, Lineage)
- Query input accepts text and submits to API
- Results display formatted in the page
- Link to /docs works for API reference
</success_criteria>

<output>
After completion, create `.planning/quick/001-user-facing-landing-page/001-SUMMARY.md`
</output>
