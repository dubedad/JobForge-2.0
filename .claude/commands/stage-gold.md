# Stage Gold Layer

Stage the complete JobForge 2.0 Gold Power BI semantic model with tables from the gold layer.

## Prerequisites
- Power BI Desktop must be open with a blank or target .pbix file
- The file should be saved before running this command
- Claude Code must be running in VS Code Pro (not terminal mode) for MCP access

## Execution

When this command runs, Claude will:
1. Connect to Power BI Desktop using MCP
2. Create all tables with correct schemas from gold layer parquet files
3. Create all relationships to dim_noc
4. Validate the result

**No manual intervention required** - you'll have a fully staged model ready for visuals.

---

## EXECUTE: Stage Gold Model

### Step 1: Connect to Power BI Desktop

First, find and connect to the local Power BI Desktop instance.

```
Use mcp__powerbi-modeling__connection_operations with operation: ListLocalInstances
Then connect to the instance found.
```

### Step 2: Create Tables

Create tables in this order: dim_noc first (primary dimension), then all fact/attribute tables.

**Gold Layer Path:** `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge 2.0\data\gold\`

#### 2.1 dim_noc (Primary Dimension)
```json
{"operation": "Create", "createDefinition": {"name": "dim_noc", "description": "NOC 2021 Dimension Table - Unit Groups with hierarchical structure", "mExpression": "let\n    Source = Parquet.Document(File.Contents(\"C:\\Users\\Administrator\\Dropbox\\++ Results Kit\\JobForge 2.0\\data\\gold\\dim_noc.parquet\"))\nin\n    Source", "columns": [{"name": "unit_group_id", "dataType": "String", "sourceColumn": "unit_group_id"}, {"name": "noc_code", "dataType": "String", "sourceColumn": "noc_code"}, {"name": "class_title", "dataType": "String", "sourceColumn": "class_title"}, {"name": "class_definition", "dataType": "String", "sourceColumn": "class_definition"}, {"name": "hierarchical_structure", "dataType": "String", "sourceColumn": "hierarchical_structure"}, {"name": "_source_file", "dataType": "String", "sourceColumn": "_source_file"}, {"name": "_ingested_at", "dataType": "DateTime", "sourceColumn": "_ingested_at"}, {"name": "_batch_id", "dataType": "String", "sourceColumn": "_batch_id"}, {"name": "_layer", "dataType": "String", "sourceColumn": "_layer"}]}}
```

#### 2.2 dim_occupations (Level 6 Dimension)
```json
{"operation": "Create", "createDefinition": {"name": "dim_occupations", "description": "Level 6 Occupations dimension with OASIS codes", "mExpression": "let\n    Source = Parquet.Document(File.Contents(\"C:\\Users\\Administrator\\Dropbox\\++ Results Kit\\JobForge 2.0\\data\\gold\\dim_occupations.parquet\"))\nin\n    Source"}}
```

#### 2.3 job_architecture
```json
{"operation": "Create", "createDefinition": {"name": "job_architecture", "description": "Job architecture with NOC mappings", "mExpression": "let\n    Source = Parquet.Document(File.Contents(\"C:\\Users\\Administrator\\Dropbox\\++ Results Kit\\JobForge 2.0\\data\\gold\\job_architecture.parquet\"))\nin\n    Source"}}
```

#### 2.4 COPS Tables (8 tables)

M Expression template (replace {table_name}):
```
let
    Source = Parquet.Document(File.Contents("C:\\Users\\Administrator\\Dropbox\\++ Results Kit\\JobForge 2.0\\data\\gold\\{table_name}.parquet"))
in
    Source
```

| Table | Description |
|-------|-------------|
| cops_employment | Employment projections by year |
| cops_employment_growth | Employment growth projections |
| cops_immigration | Immigration supply projections |
| cops_other_replacement | Other replacement demand |
| cops_other_seekers | Other job seekers supply |
| cops_retirement_rates | Retirement rate projections |
| cops_retirements | Retirement demand projections |
| cops_school_leavers | School leavers supply projections |

#### 2.5 OASIS Tables (5 tables)

| Table | Description |
|-------|-------------|
| oasis_skills | Skills proficiency ratings |
| oasis_abilities | Abilities proficiency ratings |
| oasis_knowledges | Knowledge proficiency ratings |
| oasis_workactivities | Work activities ratings |
| oasis_workcontext | Work context ratings |

#### 2.6 Element Tables (8 tables)

| Table | Description |
|-------|-------------|
| element_additional_information | Additional information for NOC groups |
| element_employment_requirements | Employment requirements |
| element_example_titles | Example job titles |
| element_exclusions | Job exclusions |
| element_labels | Labels for NOC elements |
| element_lead_statement | Lead statements for NOC groups |
| element_main_duties | Main duties text |
| element_workplaces_employers | Workplaces and employers info |

### Step 3: Create Relationships

Create relationships connecting each table to dim_noc[unit_group_id].

**Tables with `unit_group_id` key:**
- job_architecture
- All cops_* tables
- All oasis_* tables
- All element_* tables
- dim_occupations

Use relationship_operations with:
```json
{"operation": "Create", "relationshipDefinition": {"name": "dim_noc_to_{table}", "fromTable": "{table}", "fromColumn": "unit_group_id", "toTable": "dim_noc", "toColumn": "unit_group_id", "crossFilteringBehavior": "OneDirection", "isActive": true}}
```

### Step 4: Validation

After all objects are created, validate:
1. List tables - expect 24 tables
2. List relationships - expect 23 relationships (all except dim_noc itself)
3. Execute test query: `EVALUATE ROW("NOC Count", COUNTROWS(dim_noc))`

Report success or any errors to the user.

---

## Result

After execution, you will have a fully staged Gold model with:
- **24 tables** (2 dimension, 22 fact/reference tables)
- **23 relationships** (star schema centered on dim_noc)
- Ready for visuals - no Apply changes prompt needed

## Table Summary

| Category | Tables | Source |
|----------|--------|--------|
| Dimensions | dim_noc, dim_occupations | StatCan NOC 2021 |
| Job Architecture | job_architecture | WiQ Pipeline |
| Labour Market | cops_* (8 tables) | ESDC COPS |
| Skills/Abilities | oasis_* (5 tables) | O*NET/OASIS |
| NOC Elements | element_* (8 tables) | StatCan NOC 2021 |
