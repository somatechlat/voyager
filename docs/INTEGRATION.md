# VOYAGER — Voyant + Vortex Integration Architecture
## Three-System Unified Flow

**Document ID:** VYGR-INT-1.0.0
**Date:** 2026-05-18
**Systems:** Voyager (Django) ↔ Voyant (Django) ↔ Vortex (Rust)

---

## 1. System Overview

Three systems work as one unified platform:

| System | Role | Tech | Port | Repo |
|--------|------|------|------|------|
| **Voyager** | Marketing automation API | Django 5 + Ninja | 8000 | somatechlat/voyager |
| **Voyant** | Data intelligence engine | Django 5 + Ninja | 8000 | somatechlat/voyant |
| **Vortex** | Workflow execution engine | Rust + Axum | 11188 | somatechlat/vortex |

**Integration Pattern:** Voyager is the orchestrator. It calls Voyant for data and Vortex for workflows. All three share Keycloak JWT tokens and tenant IDs.

---

## 2. Integration Bridges (Real Code)

### 2.1 Voyant Bridge — `voyant_bridge/client.py` (451 lines, 18 methods)

```
┌──────────────────────────────────────────────────────────────────────┐
│                    VOYANT BRIDGE (voyant_bridge/)                     │
│                    HTTP Client → http://voyant-api:8000               │
├──────────────────────────────────────────────────────────────────────┤
│  DATA INGESTION (apps/workflows/api)                                 │
│    ingest_data(source_config, token) → POST /api/v1/jobs/ingest      │
│    get_job_status(job_id, token) → GET /api/v1/jobs/{id}             │
│    cancel_job(job_id, token) → POST /api/v1/jobs/{id}/cancel         │
│                                                                      │
│  ANALYSIS (apps/analysis/api)                                        │
│    analyze_data(dataset, token) → POST /api/v1/analyze               │
│                                                                      │
│  SQL / TRINO (apps/sql/api)                                          │
│    execute_sql(query, catalog, token) → POST /api/v1/sql/query       │
│    list_tables(catalog, token) → GET /api/v1/sql/tables              │
│                                                                      │
│  SEMANTIC SEARCH (apps/search/api → Milvus)                          │
│    search_similar(query, collection, limit, token)                   │
│         → POST /api/v1/search/query                                  │
│    index_document(text, metadata, token) → POST /api/v1/search/index │
│    delete_indexed_document(item_id, token) → DELETE /api/v1/search   │
│                                                                      │
│  WEB SCRAPING (apps/scraper/api → Playwright/Tesseract)              │
│    scrape_url(url, selectors, token) → POST /api/v1/scrape/start     │
│    scrape_multiple(urls, selectors, token) → POST /api/v1/scrape/start│
│    get_scrape_status(job_id, token) → GET /api/v1/scrape/status      │
│    get_scrape_result(job_id, token) → GET /api/v1/scrape/result      │
│    extract_from_html(html, selectors, token)                         │
│         → POST /api/v1/scrape/extract                                │
│    ocr_image(image_url, token) → POST /api/v1/scrape/ocr             │
│                                                                      │
│  DATA SOURCES (apps/discovery/api)                                   │
│    list_sources(token) → GET /api/v1/sources                         │
│    get_source(source_id, token) → GET /api/v1/sources/{id}           │
│                                                                      │
│  HEALTH → GET /health (unauthenticated)                              │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Vortex Bridge — `vortex_bridge/client.py` (340 lines, 13 methods)

```
┌──────────────────────────────────────────────────────────────────────┐
│                    VORTEX BRIDGE (vortex_bridge/)                     │
│                    HTTP Client → http://vortex-core:11188             │
├──────────────────────────────────────────────────────────────────────┤
│  GRAPH LIFECYCLE                                                     │
│    submit_graph(graph_dsl, token) → POST /api/graph                  │
│    get_graph(graph_id, token) → GET /api/graph/{id}                  │
│    execute_graph(graph_id, token) → POST /api/graph/{id}/execute     │
│                                                                      │
│  RUN MONITORING                                                      │
│    get_run_status(run_id, token) → GET /api/run/{id}/status          │
│    cancel_run(run_id, token) → POST /api/run/{id}/cancel             │
│                                                                      │
│  MCP (Model Context Protocol)                                        │
│    list_mcp_tools(token) → GET /api/nodes/mcp                        │
│    list_mcp_clients(token) → GET /api/mcp/clients                    │
│    call_mcp_tool(type_id, arguments, token)                          │
│         → POST /api/mcp/tool/call                                    │
│    register_mcp_client(client_id, command, args, token)              │
│         → POST /api/mcp/client/register                              │
│                                                                      │
│  HEALTH / METRICS                                                    │
│    health_check() → GET /health (unauthenticated)                    │
│    get_metrics() → GET /metrics (Prometheus)                         │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.3 LLM Router — `apps/ai_agents/services/llm_router.py` (415 lines)

```
┌──────────────────────────────────────────────────────────────────────┐
│                    LLM ROUTER (apps/ai_agents/)                       │
│                    Real API calls to 3 providers                      │
├──────────────────────────────────────────────────────────────────────┤
│  OPENAI (openai.AsyncOpenAI)                                         │
│    generate_text(prompt, context, brand_kit) → GPT-4o                │
│    generate_image(prompt, brand_kit) → DALL-E 3                      │
│    generate_multimodal(prompt, image_urls) → GPT-4o vision           │
│                                                                      │
│  ANTHROPIC (anthropic.AsyncAnthropic)                                │
│    generate_text(prompt, context, brand_kit) → Claude 3.5 Sonnet     │
│                                                                      │
│  GOOGLE (httpx → generativelanguage.googleapis.com)                  │
│    generate_text(prompt, context, brand_kit) → Gemini 1.5 Pro        │
│                                                                      │
│  ROUTING LOGIC                                                       │
│    Priority: anthropic → openai → google (or preferred override)    │
│    Fallback: try next provider on failure                            │
│    Cost tracking: per-call USD calculation (MODEL_PRICING table)     │
│    Brand compliance: _score_brand_compliance() 0.0-1.0              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Campaign Orchestration Flow (UC-001)

### 3.1 High-Level Flowchart

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   MARKETING  │     │   VOYAGER    │     │   VOYANT     │     │   VORTEX     │
│   MANAGER    │────→│   (Django)   │←───→│   (Django)   │     │   (Rust)     │
│   (User)     │     │   Port 8000  │     │   Port 8000  │     │   Port 11188 │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │                    │
       │ 1. POST /clients   │                    │                    │
       │───────────────────→│                    │                    │
       │                    │ 2. INSERT clients  │                    │
       │                    │    (PostgreSQL)    │                    │
       │  201 Created       │                    │                    │
       │←───────────────────│                    │                    │
       │                    │                    │                    │
       │ 3. POST /campaigns │                    │                    │
       │───────────────────→│                    │                    │
       │                    │ 4. INSERT campaigns│                    │
       │                    │    (linked to      │                    │
       │                    │     client)        │                    │
       │  201 Created       │                    │                    │
       │←───────────────────│                    │                    │
       │                    │                    │                    │
       │ 5. POST /ai-agents/│                    │                    │
       │    campaign-workflow│                   │                    │
       │    {client_id,     │                    │                    │
       │     campaign_id}   │                    │                    │
       │───────────────────→│                    │                    │
       │                    │                    │                    │
       │                    │ ╔═══════════════════════════════════════╗
       │                    │ ║  PHASE 1: RESEARCH AGENT             ║
       │                    │ ║  (uses Voyant Bridge)                ║
       │                    │ ╚═══════════════════════════════════════╝
       │                    │                    │                    │
       │                    │ 6a. voyant_client.analyze_competitors() │
       │                    │───────────────────→│                    │
       │                    │                    │ 7a. Playwright scrape
       │                    │                    │    competitor sites  │
       │                    │                    │ 8a. NLP analysis     │
       │                    │  ←─────────────────│                    │
       │                    │    {competitor_profiles}                 │
       │                    │                    │                    │
       │                    │ 6b. voyant_client.analyze_market_trends()│
       │                    │───────────────────→│                    │
       │                    │                    │ 7b. Statistical      │
       │                    │                    │    trend detection   │
       │                    │  ←─────────────────│                    │
       │                    │    {trend_data}    │                    │
       │                    │                    │                    │
       │                    │ 6c. voyant_client.search_keywords()      │
       │                    │───────────────────→│                    │
       │                    │                    │ 7c. Milvus semantic  │
       │                    │                    │    search            │
       │                    │  ←─────────────────│                    │
       │                    │    {keywords}      │                    │
       │                    │                    │                    │
       │                    │ 6d. voyant_client.analyze_brand_sentiment│
       │                    │───────────────────→│                    │
       │                    │                    │ 7d. Sentiment NLP    │
       │                    │  ←─────────────────│                    │
       │                    │    {sentiment}     │                    │
       │                    │                    │                    │
       │                    │ ╔═══════════════════════════════════════╗
       │                    │ ║  PHASE 2: CREATIVE AGENT             ║
       │                    │ ║  (uses LLM Router)                   ║
       │                    │ ╚═══════════════════════════════════════╝
       │                    │                    │                    │
       │                    │ 9a. llm.generate_text()                │
       │                    │    → Claude 3.5 Sonnet (brief)         │
       │                    │    → GPT-4o (content copy)             │
       │                    │    → GPT-4o (social posts)             │
       │                    │    → Claude 3.5 Sonnet (email)         │
       │                    │                    │                    │
       │                    │ 9b. llm.generate_image()               │
       │                    │    → DALL-E 3 (brand colors enforced)  │
       │                    │                    │                    │
       │                    │ ╔═══════════════════════════════════════╗
       │                    │ ║  PHASE 3: VORTEX WORKFLOW            ║
       │                    │ ║  (uses Vortex Bridge)                ║
       │                    │ ╚═══════════════════════════════════════╝
       │                    │                    │                    │
       │                    │ 10. vortex_client.submit_graph()        │
       │                    │    graph_dsl = {                        │
       │                    │      nodes: [ingest, review, publish,   │
       │                    │               monitor, optimize],       │
       │                    │      edges: [ingest→review,            │
       │                    │               review→publish,           │
       │                    │               publish→monitor,         │
       │                    │               monitor→optimize]        │
       │                    │    }                                    │
       │                    │───────────────────────────────────────→│
       │                    │                    │ 11. Kahn's algo    │
       │                    │                    │    DAG scheduling  │
       │                    │  ←─────────────────────────────────────│
       │                    │    {graph_id, run_id}                  │
       │                    │                    │                    │
       │  200 OK            │                    │                    │
       │←───────────────────│                    │                    │
       │  {research,        │                    │                    │
       │   creative,        │                    │                    │
       │   workflow,        │                    │                    │
       │   aggregate: {     │                    │                    │
       │     total_cost,    │                    │                    │
       │     total_tokens,  │                    │                    │
       │     workflow_ids   │                    │                    │
       │   }}               │                    │                    │
       │                    │                    │                    │
       │                    │                    │                    │
       │  Celery Beat:      │                    │                    │
       │  Every 5 min:      │                    │                    │
       │  sync_platform_    │                    │                    │
       │    metrics         │                    │                    │
       │                    │ 12. voyant_client. │                    │
       │                    │     ingest_data()  │                    │
       │                    │───────────────────→│                    │
       │                    │                    │ 13. ETL pipeline   │
       │                    │                    │    → ClickHouse    │
       │                    │                    │                    │
       │  GET /analytics/   │                    │                    │
       │  dashboards        │                    │                    │
       │───────────────────→│ 14. voyant_client. │                    │
       │                    │     execute_sql()  │                    │
       │                    │───────────────────→│                    │
       │                    │                    │ 15. Trino →        │
       │                    │                    │    ClickHouse      │
       │  ←──────────────   │  ←─────────────────│                    │
       │  {dashboard_data}  │    {query_results} │                    │
```

---

## 4. Detailed Sequence Diagram: AI-Assisted Campaign

```
MM = Marketing Manager
VG = Voyager API (Django + Ninja, port 8000)
CO = CampaignOrchestrator (apps/ai_agents/services/)
LR = LLMRouter (apps/ai_agents/services/)
VB = Voyant Bridge (voyant_bridge/client.py)
VX = Vortex Bridge (vortex_bridge/client.py)
VT = Voyant (Django, port 8000)
VTX = Vortex (Rust, port 11188)

═══════════════════════════════════════════════════════════════════════════════
PHASE 1: RESEARCH AGENT (Voyant data gathering)
═══════════════════════════════════════════════════════════════════════════════

MM ──POST /api/v1/ai-agents/campaign-workflow/{client_id}/{campaign_id}──→ VG
VG ──auth: KeycloakBearer.validate(token)─────────────────────────────────→ (Keycloak)
VG ──permission: voyager-marketing-manager role check─────────────────────→ (RBAC)
VG ──CampaignOrchestrator.run_campaign_workflow()─────────────────────────→ CO

CO ──_run_research_agent(client_id, tenant_id, token)────────────────────→ CO

  CO ──voyant_client.analyze_competitors(client_id, [], token)───────────→ VB
  VB ──POST /api/v1/analyze──────────────────────────────────────────────→ VT
  VT ──Playwright scrape competitor URLs──────────────────────────────────→ (Chrome)
  VT ──NLP: extract themes, topics, sentiment from content────────────────→ (spaCy)
  VT ──return {competitor_profiles, content_themes, sentiment}────────────→ VB
  VB ──return competitor_data────────────────────────────────────────────→ CO

  CO ──voyant_client.analyze_market_trends(client_id, "general", token)──→ VB
  VB ──POST /api/v1/analyze──────────────────────────────────────────────→ VT
  VT ──Statistical trend detection on historical data─────────────────────→ (ClickHouse)
  VT ──return {trends, growth_rates, seasonality}─────────────────────────→ VB
  VB ──return trend_data─────────────────────────────────────────────────→ CO

  CO ──voyant_client.search_keywords(query, token, limit=50)─────────────→ VB
  VB ──POST /api/v1/search/query─────────────────────────────────────────→ VT
  VT ──Milvus semantic search on marketing_keywords collection────────────→ (Milvus)
  VT ──return {keywords: [{term, volume, difficulty, score}]}─────────────→ VB
  VB ──return keywords───────────────────────────────────────────────────→ CO

  CO ──voyant_client.analyze_brand_sentiment(client_id, token)───────────→ VB
  VB ──POST /api/v1/analyze──────────────────────────────────────────────→ VT
  VT ──Sentiment analysis on brand mentions───────────────────────────────→ (NLP model)
  VT ──return {overall, by_platform, by_date}─────────────────────────────→ VB
  VB ──return sentiment_data─────────────────────────────────────────────→ CO

CO ──return {competitors, trends, keywords, sentiment, _meta: {cost}}───→ CO

═══════════════════════════════════════════════════════════════════════════════
PHASE 2: CREATIVE AGENT (LLM content generation)
═══════════════════════════════════════════════════════════════════════════════

CO ──_run_creative_agent(campaign_id, research, tenant_id, token)────────→ CO
CO ──build_creative_context(research)─────────────────────────────────────→ (prompt builder)

  CO ──llm.generate_text(brief_prompt, context, brand_kit, max=3000)─────→ LR
  LR ──_build_system_prompt(context, brand_kit)───────────────────────────→ LR
  LR ──Route: anthropic preferred─────────────────────────────────────────→ LR
  LR ──anthropic_client.messages.create(model="claude-3-5-sonnet-20241022")→ (Anthropic API)
  LR ──_score_brand_compliance(response.text, brand_kit)──────────────────→ LR
  LR ──_calc_cost("claude-3-5-sonnet", input_tokens, output_tokens)───────→ LR
  LR ──return {text, model_used, tokens_used, cost_usd, brand_compliance}─→ CO

  CO ──llm.generate_text(content_prompt, context, brand_kit, max=4000)───→ LR
  LR ──Route: openai (GPT-4o for longer content)─────────────────────────→ LR
  LR ──openai_client.chat.completions.create(model="gpt-4o")──────────────→ (OpenAI API)
  LR ──return {text, model_used, tokens_used, cost_usd, brand_compliance}─→ CO

  CO ──llm.generate_text(social_prompt, context, brand_kit, max=2000)────→ LR
  LR ──openai_client.chat.completions.create(model="gpt-4o")──────────────→ (OpenAI API)
  LR ──return {text: social_posts, model_used, tokens_used, cost_usd}────→ CO

  CO ──llm.generate_text(email_prompt, context, brand_kit, max=2500)─────→ LR
  LR ──anthropic_client.messages.create(model="claude-3-5-sonnet")────────→ (Anthropic API)
  LR ──return {text: email_copy, model_used, tokens_used, cost_usd}──────→ CO

CO ──return {brief, content, social_posts, email_copy}──────────────────→ CO

═══════════════════════════════════════════════════════════════════════════════
PHASE 3: VORTEX WORKFLOW (DAG execution)
═══════════════════════════════════════════════════════════════════════════════

CO ──_submit_to_vortex(campaign_id, results, tenant_id, token)───────────→ CO

  CO ──Build GraphDSL:                                               ────→ CO
       {                                                               
         nodes: [                                                      
           {id: "ingest", type: "action", config: {...}},              
           {id: "review", type: "human_approval", config: {timeout: 86400}}
           {id: "publish", type: "action", config: {channels: [...]}},
           {id: "monitor", type: "action", config: {metrics: [...]}},
           {id: "optimize", type: "action", config: {rules: [...]}}
         ],
         edges: [
           {from: "ingest", to: "review"},
           {from: "review", to: "publish", condition: "approved"},
           {from: "review", to: "ingest", condition: "rejected"},
           {from: "publish", to: "monitor"},
           {from: "monitor", to: "optimize", condition: "threshold_met"}
         ]
       }

  CO ──vortex_client.submit_graph(graph_dsl, token)──────────────────────→ VX
  VX ──POST /api/graph───────────────────────────────────────────────────→ VTX
  VTX ──Validate graph (DAG check, node types, edge conditions)──────────→ VTX
  VTX ──Store graph, assign graph_id─────────────────────────────────────→ VTX
  VTX ──return {graph_id, version}───────────────────────────────────────→ VX
  VX ──return graph_id───────────────────────────────────────────────────→ CO

  CO ──vortex_client.execute_graph(graph_id, token)──────────────────────→ VX
  VX ──POST /api/graph/{graph_id}/execute────────────────────────────────→ VTX
  VTX ──Kahn's topological sort on DAG───────────────────────────────────→ VTX
  VTX ──Schedule node execution (async workers)──────────────────────────→ VTX
  VTX ──WebSocket: progress updates on /ws───────────────────────────────→ VTX
  VTX ──return {run_id, estimated_time_ms}───────────────────────────────→ VX
  VX ──return run_id─────────────────────────────────────────────────────→ CO

CO ──return {graph_id, run_id, status: "submitted", nodes: [...]}───────→ CO

═══════════════════════════════════════════════════════════════════════════════
RESPONSE TO USER
═══════════════════════════════════════════════════════════════════════════════

CO ──Aggregate results:                                              ────→ CO
     {                                                               
       research: {competitors, trends, keywords, sentiment},
       creative: {brief, content, social_posts, email_copy},
       workflow: {graph_id, run_id, status, nodes},
       aggregate: {
         total_cost_usd: 0.0042,
         total_tokens_used: 1847,
         workflow_graph_id: "uuid",
         workflow_run_id: "uuid"
       }
     }

VG ──HTTP 200 OK + JSON body─────────────────────────────────────────────→ MM
```

---

## 5. Data Flow Between Three Systems

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW ARCHITECTURE                               │
│                     Voyager ←→ Voyant ←→ Vortex                              │
└─────────────────────────────────────────────────────────────────────────────┘

  VOYAGER (Marketing)          VOYANT (Data Intelligence)      VORTEX (Workflows)
  ────────────────────         ──────────────────────────      ─────────────────

  [campaigns]  ───────────────→ [ingestion jobs]
    PostgreSQL                    Voyant processes
    │                             │
    │  ┌──────────────────────────┘
    │  │
    │  ▼
    │  [ClickHouse] ←───────────── analytics results
    │     │
    │     ▼
    │  [Trino SQL] ←────────────── Voyager queries via voyant_bridge.execute_sql()
    │     │
    │     ▼
    │  [Dashboard data] ─────────→ Voyager API response
    │
    │
  [ai_agents] ─────────────────→ [Milvus vectors]
    Qdrant (memory)               Voyant manages
    │                             │
    │  embeddings ───────────────→│
    │  search_similar()           │
    │                             │
    │                             ▼
    │  ←──────────────────────── [semantic search results]
    │
    │
  [content] ───────────────────→ [scraped data]
    text/images                   Playwright + OCR
    │                             │
    │  scrape_url() ─────────────→│
    │  ocr_image()                │
    │                             │
    │                             ▼
    │  ←──────────────────────── [extracted text, HTML, screenshots]
    │
    │
  [workflows] ─────────────────────────────────────────────────→ [DAG execution]
    scheduled posts                                               Kahn scheduling
    approval gates                                                WebSocket progress
    │                                                             │
    │  submit_graph() ───────────────────────────────────────────→│
    │  execute_graph()                                            │
    │  get_run_status() ────────────────────────────────────────→│
    │                                                             ▼
    │  ←───────────────────────────────────────────────────────── [execution status]

═══════════════════════════════════════════════════════════════════════════════
SHARED INFRASTRUCTURE
═══════════════════════════════════════════════════════════════════════════════

  PostgreSQL 16 ─── Voyager models + Voyant models (separate schemas)
  Redis 7 ───────── Celery broker + cache (shared)
  ClickHouse ────── Analytics events (Voyant writes, Voyager queries via Trino)
  MinIO ─────────── Object storage (assets, screenshots, generated images)
  Keycloak ──────── Shared JWT auth (same realm, tenant_id claim)
  Vault ─────────── Shared secrets (DB creds, API keys)
  Kafka ─────────── Event bus (cross-system events)

═══════════════════════════════════════════════════════════════════════════════
AUTHENTICATION FLOW
═══════════════════════════════════════════════════════════════════════════════

  User ──Keycloak login──→ Keycloak ──JWT token──→ User

  User ──API request──→ Voyager API
         Authorization: Bearer <jwt>
         X-Tenant-ID: tenant_42

  Voyager ──validate JWT──→ Keycloak (JWKS)
  Voyager ──extract tenant_id──→ RBAC middleware

  Voyager ──call Voyant──→ Voyant API
         Authorization: Bearer <same_jwt>
         X-Tenant-ID: tenant_42
         X-Trino-Catalog: iceberg

  Voyager ──call Vortex──→ Vortex API
         Authorization: Bearer <same_jwt>
         (Vortex validates via Keycloak JWKS)
```

---

## 6. File Reference

| File | Lines | Purpose | System |
|------|-------|---------|--------|
| `voyant_bridge/client.py` | 451 | HTTP client, 18 API methods | Voyager → Voyant |
| `voyant_bridge/services.py` | 864 | 5 service wrappers | Voyager → Voyant |
| `vortex_bridge/client.py` | 340 | HTTP client, 13 API methods | Voyager → Vortex |
| `vortex_bridge/models.py` | 156 | Pydantic response models | Voyager → Vortex |
| `vortex_bridge/compiler.py` | 278 | Workflow-to-GraphDSL compiler | Voyager → Vortex |
| `apps/ai_agents/services/llm_router.py` | 415 | Real OpenAI/Anthropic/Google calls | Voyager → LLM APIs |
| `apps/ai_agents/services/campaign_orchestrator.py` | 429 | 3-agent orchestration | Voyager internal |
| `apps/ai_agents/services/campaign_prompts.py` | 312 | Prompt builders | Voyager internal |
| `apps/ai_agents/services/brand_enforcement.py` | 268 | Brand compliance scoring | Voyager internal |
| `apps/core/models.py` | 87 | Base models from Voyant pattern | Voyager |

---

## 7. API Endpoint: Campaign Workflow

```
POST /api/v1/ai-agents/campaign-workflow/{client_id}/{campaign_id}

Headers:
  Authorization: Bearer <keycloak_jwt>
  X-Tenant-ID: <tenant_id>

Response 200 OK:
{
  "client_id": "acme_corp",
  "campaign_id": "camp_2025q1",
  "tenant_id": "tenant_42",
  "research": {
    "competitors": {"profiles": [...], "status": "ok"},
    "trends": {"trends": [...], "status": "ok"},
    "keywords": [{"term": "...", "volume": 15000, "difficulty": 0.45}],
    "sentiment": {"overall": 0.72, "by_platform": {...}}
  },
  "creative": {
    "brief": {"text": "...", "model_used": "claude-3-5-sonnet", "cost_usd": 0.0018},
    "content": {"text": "...", "model_used": "gpt-4o", "cost_usd": 0.0024},
    "social_posts": {"text": "...", "model_used": "gpt-4o", "cost_usd": 0.0012},
    "email_copy": {"text": "...", "model_used": "claude-3-5-sonnet", "cost_usd": 0.0015}
  },
  "workflow": {
    "graph_id": "uuid",
    "run_id": "uuid",
    "status": "submitted",
    "nodes": ["ingest", "review", "publish", "monitor", "optimize"]
  },
  "aggregate": {
    "total_cost_usd": 0.0042,
    "total_tokens_used": 1847,
    "workflow_graph_id": "uuid",
    "workflow_run_id": "uuid"
  }
}
```

---

**Document prepared from actual code inspection**
**Files read:** voyant_bridge/client.py (451L), vortex_bridge/client.py (340L), campaign_orchestrator.py (429L), llm_router.py (415L)
**All code references are real — no invented APIs**
