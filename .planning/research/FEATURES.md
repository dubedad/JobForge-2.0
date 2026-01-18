# Feature Landscape: Workforce Intelligence Platform

**Domain:** Workforce Intelligence / Occupational Data Governance for Government of Canada
**Researched:** 2026-01-18
**Confidence:** MEDIUM-HIGH (synthesized from multiple authoritative sources)

---

## Table Stakes

Features users expect. Missing = product feels incomplete or unprofessional.

### Data Foundation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **NOC Ingestion & Parsing** | Core Canadian occupational data standard | Medium | NOC 2021 v1.0 from ESDC; structured hierarchy, 516 unit groups |
| **O*NET/SOC Integration** | International benchmark, richer skill descriptors than NOC alone | Medium | O*NET provides 923 occupations with KSAs, tasks, work context |
| **NOC-SOC Crosswalk** | Government analysts expect to compare US/Canada labor markets | Medium | Official crosswalks exist; need semantic reconciliation for edge cases |
| **Data Version Management** | Classification systems update periodically; must track which version | Low | NOC 2021, O*NET-SOC 2019; quarterly O*NET updates |
| **Metadata Storage** | All data governance artifacts need rich metadata | Low | Table/column descriptions, data types, update timestamps |

### Semantic Model Capabilities

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Power BI Semantic Model Deployment** | Primary BI platform for Government of Canada | Medium | Direct deployment via XMLA endpoint; Premium/Fabric workspace required |
| **Measure Definitions with DAX** | Analysts expect calculated metrics out-of-box | Medium | Headcount, FTE, vacancy rates, turnover metrics |
| **Relationships & Star Schema** | Dimensional modeling expected for analytical workloads | Medium | Occupation dimensions, time dimensions, organizational dimensions |
| **Row-Level Security (RLS)** | Government requires data access controls | Medium | Department-level, classification-level access patterns |
| **Model Documentation Export** | Data governance teams need to document models | Low | INFO.VIEW DAX functions enable metadata extraction |

### Data Governance Artifacts

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Data Dictionary Generation** | Standard governance deliverable | Low | Column-level definitions, data types, allowed values |
| **Business Glossary** | Common language for workforce terms | Medium | "Active employee," "vacancy," "FTE" must have standard definitions |
| **Data Lineage Tracking** | Required for audit and troubleshooting | High | Source-to-report traceability; critical for compliance |
| **Metadata Catalog** | Discovery of available data assets | Medium | Searchable inventory of tables, measures, relationships |
| **Export to Standard Formats** | Integration with enterprise catalog tools | Low | JSON, CSV, Excel exports for Collibra/Alation import |

### Query & Access

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Basic Search** | Users need to find occupations, skills | Low | Keyword search across NOC/O*NET titles and descriptions |
| **Filtering & Faceting** | Narrow results by category, skill type, etc. | Low | By NOC major group, skill level, work context |
| **Occupation Profiles** | Detailed view of single occupation | Low | Aggregate all attributes: KSAs, tasks, wages, outlook |
| **Skill Listings** | View skills by type or occupation | Low | Technical, interpersonal, problem-solving skill categories |

### Provenance & Compliance

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Source Attribution** | Track where each data element originated | Medium | NOC, O*NET, custom additions; timestamp of import |
| **Change History** | What changed and when | Medium | Version diffs for governance audits |
| **DADM Awareness** | Automated decisions must be flagged for directive compliance | Medium | Algorithmic Impact Assessment triggers; transparency requirements |

---

## Differentiators

Features that set the platform apart. Not expected, but highly valued when present.

### Semantic Intelligence

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Skills Ontology (Not Just Taxonomy)** | Dynamic relationships between skills, auto-updating | High | Taxonomy = hierarchical list; Ontology = network of relationships |
| **Semantic Crosswalks** | AI-assisted mapping between NOC/SOC/ESCO with confidence scores | High | ESCO-O*NET uses ML + human validation; apply same pattern |
| **Occupation Similarity Scoring** | "Jobs like this" recommendations | Medium | Embeddings-based similarity; useful for career pathing |
| **Skill Adjacency Mapping** | "Skills that often co-occur" insights | Medium | Network analysis of skill co-occurrence patterns |
| **Emerging Skills Detection** | Identify new skills before classification systems update | High | NLP on job postings, training catalogs; flag for human review |

### Conversational Interface

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Natural Language Query** | "Show me IT occupations requiring Python" without SQL | High | LLM-powered text-to-query; verified against semantic model |
| **Contextual Follow-up** | Maintain conversation context across queries | Medium | "Now filter by Vancouver region" builds on prior query |
| **Query Explanation** | Show what the system did to answer the question | Medium | Transparency for government use; builds trust |
| **Suggested Questions** | Prompt users with relevant follow-up queries | Low | Based on common query patterns and current context |
| **Multi-Modal Output** | Answer in text, tables, or charts based on query type | Medium | "Compare X vs Y" = chart; "What is X?" = prose |

### Intelligent Governance

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Auto-Generated Glossary Terms** | AI suggests business definitions from metadata | Medium | Amazon Bedrock approach: LLM analyzes schema, suggests terms |
| **Lineage Visualization** | Interactive data flow diagrams | High | Source-to-semantic-model-to-report traceability |
| **Impact Analysis** | "What breaks if I change this?" | High | Downstream dependency detection before changes |
| **Data Quality Scoring** | Automated quality metrics per data element | Medium | Completeness, consistency, timeliness scores |
| **Governance Workflow** | Term approval, ownership assignment, policy enforcement | High | Review cycles, stewardship assignment, certification |

### Workforce Intelligence Analytics

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Skills Gap Analysis** | Compare current workforce skills to target profiles | High | Requires skill inventory data beyond NOC/O*NET |
| **Labor Market Benchmarks** | Compare internal data to external LMI | Medium | Integration with Job Bank, Statistics Canada data |
| **Succession Risk Identification** | Flag single-points-of-failure in critical roles | High | Requires organizational and incumbent data |
| **Career Pathway Visualization** | Show progression routes between occupations | Medium | Based on skill overlap and organizational ladders |

### Job Description Support (Later Phase)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **JD Generation from NOC** | Auto-draft job descriptions using classification data | Medium | Pull tasks, KSAs from O*NET; adapt to GC context |
| **Bias Detection** | Flag exclusionary language in JDs | Medium | Textio-style analysis; DEI compliance |
| **Skill Requirement Suggestions** | Recommend skills based on occupation | Low | Direct from O*NET skill profiles |
| **Performance Agreement Templates** | Link job duties to measurable objectives | Medium | Connect tasks to outcomes; government performance cycle |

---

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time Job Posting Ingestion** | Massive scope creep; Job Bank already does this | Integrate with Job Bank API for LMI; don't replicate |
| **Full ATS/HRIS Functionality** | Existing government systems (PeopleSoft, Phoenix successor) | Provide governed data to those systems; don't replace |
| **Custom Classification Creation** | Undermines governance; creates data silos | Map custom roles to NOC; extend with attributes, not new taxonomies |
| **Employee-Level Data Storage** | Privacy/security complexity; not core mission | Focus on occupational data; point to HR systems for employees |
| **Salary Negotiation Tools** | Outside governance mandate; liability concerns | Provide salary ranges from LMI; don't advise on compensation |
| **Resume Parsing** | Solved problem; many vendors; scope creep | Integrate with existing solutions if needed later |
| **Training Delivery/LMS** | Separate domain; government has existing systems | Link skills to training catalogs; don't deliver training |
| **Automated Hiring Decisions** | DADM compliance nightmare; high risk | Support decisions; never make them autonomously |
| **Predictive Attrition Scoring** | Employee privacy concerns; limited data access | Provide occupational-level insights; not individual predictions |

---

## Feature Dependencies

```
Foundation Layer (must build first):
  NOC Ingestion --> O*NET Integration --> Crosswalk Mapping
       |                    |                    |
       v                    v                    v
  Metadata Storage <-- Version Management --> Source Attribution
       |
       v

Data Governance Layer (enables governance artifacts):
  Metadata Storage --> Data Dictionary Generation
       |                         |
       v                         v
  Business Glossary <------> Lineage Tracking
       |                         |
       v                         v
  Metadata Catalog --> Export to Standard Formats

Semantic Model Layer (enables BI consumption):
  Foundation Data --> Power BI Semantic Model
       |                         |
       v                         v
  Measure Definitions --> Row-Level Security
       |
       v
  Model Documentation Export

Query Layer (enables user access):
  Semantic Model --> Basic Search --> Filtering
       |                    |
       v                    v
  Natural Language Query (requires: semantic model + LLM integration)

Advanced Analytics (requires governance layer):
  Lineage Tracking --> Impact Analysis
  Business Glossary --> Auto-Generated Terms (with AI)
  Skills Ontology --> Skill Adjacency Mapping --> Career Pathways

Job Description Features (requires foundation + ontology):
  O*NET Skills Data --> JD Generation
  Skills Ontology --> Skill Requirement Suggestions
```

---

## MVP Recommendation

For MVP, prioritize building a solid governance foundation:

### Phase 1: Data Foundation
1. **NOC ingestion and parsing** - Core Canadian data
2. **O*NET integration** - Rich skill/task data
3. **Metadata storage** - Foundation for all governance
4. **Basic crosswalk** - NOC-SOC mapping

### Phase 2: Semantic Model
5. **Power BI semantic model deployment** - Primary consumption point
6. **Measure definitions** - Immediate analyst value
7. **Model documentation export** - Governance deliverable

### Phase 3: Governance Artifacts
8. **Data dictionary generation** - Automated from model
9. **Business glossary** - Standard terms for workforce domain
10. **Metadata catalog** - Discoverability

### Defer to Post-MVP:

| Feature | Reason to Defer |
|---------|-----------------|
| Natural Language Query | High complexity; core value without it |
| Skills Ontology | Taxonomy sufficient for MVP; ontology adds complexity |
| Lineage Visualization | Valuable but not blocking core use cases |
| JD Generation | Manager persona is "later" per project context |
| Skills Gap Analysis | Requires organizational data not in initial scope |
| Impact Analysis | Valuable after model is stable and in use |

---

## Complexity Estimates

| Complexity | Effort Range | Examples |
|------------|--------------|----------|
| **Low** | 1-3 days | Basic search, filtering, export formats |
| **Medium** | 1-2 weeks | Crosswalk mapping, measure definitions, RLS |
| **High** | 3-6 weeks | Natural language query, skills ontology, lineage visualization |

---

## Sources

### Workforce Intelligence Platforms
- [iMocha Workforce Intelligence Software](https://blog.imocha.io/workforce-intelligence-software)
- [Aura Best Workforce Analytics](https://blog.getaura.ai/best-workforce-analytics-software)
- [TalentGuard Workforce Intelligence Guide](https://www.talentguard.com/blog/what-is-workforce-intelligence)
- [Lightcast Workforce Intelligence](https://lightcast.io/workforce-intelligence)

### Occupational Data Systems
- [O*NET Resource Center](https://www.onetcenter.org/)
- [O*NET-SOC Taxonomy](https://www.onetcenter.org/taxonomy.html)
- [O*NET Crosswalks](https://www.onetcenter.org/crosswalks.html)
- [ESCO-O*NET Crosswalk Technical Report](https://esco.ec.europa.eu/en/about-esco/data-science-and-esco/crosswalk-between-esco-and-onet)
- [Government of Canada NOC Data Files](https://noc.esdc.gc.ca/Home/LMIDataFiles)
- [Labour Market Information Council](https://lmic-cimt.ca/)

### Data Governance Tools
- [TechTarget Top Data Governance Tools 2025](https://www.techtarget.com/searchdatamanagement/feature/15-top-data-governance-tools-to-know-about)
- [Secoda Data Dictionary Tools](https://www.secoda.co/blog/top-data-dictionary-tools)
- [Atlan Data Catalog Tools](https://atlan.com/data-catalog-tools/)
- [OvalEdge Data Lineage Tools](https://www.ovaledge.com/blog/data-lineage-tools)
- [LakeFS Data Lineage 2025](https://lakefs.io/blog/data-lineage-tools/)

### Power BI Semantic Models
- [Microsoft Learn: Semantic Models](https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand)
- [Microsoft Learn: XMLA Endpoint](https://learn.microsoft.com/en-us/fabric/enterprise/powerbi/service-premium-connect-tools)
- [DataBear: Data Dictionary in Power BI](https://databear.com/data-dictionary-in-power-bi/)
- [Power BI Governance Guide](https://bix-tech.com/power-bi-governance-the-practical-guide-to-balancing-control-and-selfservice-for-real-adoption/)

### Government of Canada Compliance
- [Directive on Automated Decision-Making](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592)
- [Guide on DADM Scope](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/guide-scope-directive-automated-decision-making.html)
- [ESDC LMI Evaluation](https://www.canada.ca/en/employment-social-development/corporate/reports/evaluations/learning-labour-information-web-approach.html)

### Conversational AI & Natural Language
- [Alation Natural Language Data Interfaces](https://www.alation.com/blog/natural-language-data-interfaces-guide/)
- [Tellius Conversational Analytics](https://www.tellius.com/platform/conversational-analytics)
- [Salary.com Conversational AI in HR](https://www.salary.com/resources/how-to/what-is-conversational-ai-in-hr-and-how-to-use-it)

### Skills & Workforce Planning
- [Gloat Skills Ontology Framework](https://gloat.com/blog/skills-ontology-framework/)
- [iMocha Skills Gap Analysis Tools](https://blog.imocha.io/skill-gap-analysis-tools)
- [INOP Skills-Based Workforce Planning](https://inop.ai/skills-based-workforce-planning-tools-the-ultimate-guide-for-hr-leaders/)
- [WithYouWithMe Skills Frameworks Explained](https://withyouwithme.com/blog/unlocking-talent-potential-understanding-skills-frameworks-taxonomies-and-ontologies-for-people-leaders/)

### AI Job Description Tools
- [Workable JD Generator](https://www.workable.com/job-description-generator)
- [ClickUp AI JD Generators 2025](https://clickup.com/blog/ai-job-description-generators/)
- [Skima AI JD Tools](https://skima.ai/blog/industry-trends-and-insights/best-ai-job-description-generator-tools)
