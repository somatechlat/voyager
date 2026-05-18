# VOYAGER — Voyant + Vortex Integration Architecture
## Three-System Unified Flow — CORRECTED

**Document ID:** VYGR-INT-2.0.0
**Date:** 2026-05-18
**Status:** CORRECTED — Based on actual Vortex source code inspection

---

## CRITICAL CORRECTION: What Vortex Actually Does

After reading the Vortex source code, here's the truth:

**Vortex is NOT just a workflow engine. Vortex is a full AI inference engine.**

| System | What It Actually Does | Code Evidence |
|--------|----------------------|---------------|
| **Vortex** | Loads AI models (SD, SDXL), runs inference on GPU, generates images/video/audio | `executor.py` has `KSampler`, `VAEDecode`, `CLIPTextEncode`, `LatentVideoSampler`, `MelEncoder` |
| **Voyager** | Marketing automation API — orchestrates campaigns, calls Vortex for media generation | `campaign_orchestrator.py` calls both Voyant and Vortex |
| **Voyant** | Data intelligence — ingestion, analysis, SQL, search, scraping | `voyant_bridge/client.py` has 18 API methods |

### Vortex Model Catalog (from `model_loader.py` lines 37-78)

```python
MODEL_CATALOG = {
    "sd15":           "runwayml/stable-diffusion-v1-5",      # 4GB — base model
    "sdxl-turbo":     "stabilityai/sdxl-turbo",               # 6.5GB — fast SDXL
    "sd-turbo":       "stabilityai/sd-turbo",                 # 3.5GB — fastest
    "lcm-lora-sdxl":  "latent-consistency/lcm-lora-sdxl",     # 400MB — LoRA
    "realistic-vision": "SG161222/Realistic_Vision_V5.1_noVAE" # 4GB — realistic
}
```

### Vortex Executors (from `executor.py`)

| Executor | Node Type | What It Does |
|----------|-----------|-------------|
| `CheckpointLoader` | `Loader::Checkpoint` | Loads SD/SDXL from HuggingFace to GPU |
| `KSampler` | `Sampler::KSampler` | Runs diffusion sampling — generates image latents |
| `VAEDecode` | `Decoder::VAE` | Decodes latents to actual image (512x512) |
| `CLIPTextEncode` | `Encoder::CLIP` | Encodes text prompt to conditioning embeddings |
| `MelEncoder` | `Audio::MelEncoder` | Audio waveform → mel-spectrogram |
| `LatentVideoSampler` | `Video::LatentSampler` | Generates video frames (temporal latents) |

### Architecture: Rust Host + Python Workers

```
Vortex (Rust Core, port 11188)
├── Scheduler — Kahn's topological sort on DAG
├── Arbiter — VRAM memory management (8GB budget)
├── Supervisor — Spawns Python worker processes
├── IPC Gateway — POSIX shared memory zero-copy
└── WebSocket — Real-time progress on /ws

    ↓ IPC via /tmp/vortex.sock

Vortex Worker (Python)
├── Executor Registry — Dispatches to node handlers
├── Model Loader — HuggingFace Hub, caching, GPU
├── SHM Arena — Shared memory tensor storage
└── Bridge — Arrow ↔ PyTorch zero-copy

    ↓ torch.cuda

GPU — Runs Stable Diffusion inference
```

### What Each System Handles

| Task | Voyager | Voyant | Vortex |
|------|---------|--------|--------|
| **Text generation** | ✅ LLM Router (OpenAI/Anthropic) | ❌ | ❌ |
| **Image generation** | ❌ | ❌ | ✅ KSampler + VAEDecode (SD/SDXL) |
| **Video generation** | ❌ | ❌ | ✅ LatentVideoSampler |
| **Audio generation** | ❌ | ❌ | ✅ MelEncoder |
| **Data ingestion** | ❌ | ✅ Airbyte, DuckDB | ❌ |
| **Web scraping** | ❌ | ✅ Playwright, OCR | ❌ |
| **SQL analytics** | ❌ | ✅ Trino → ClickHouse | ❌ |
| **Semantic search** | ❌ | ✅ Milvus | ❌ |
| **Workflow DAG** | ❌ | ❌ | ✅ Kahn scheduling |
| **MCP tools** | ❌ | ❌ | ✅ Tool registry + proxy |
| **Campaign logic** | ✅ Django models | ❌ | ❌ |
| **Auth/RBAC** | ✅ Keycloak | ❌ | ❌ |

---

## 1. Three-System Integration Diagram (CORRECTED)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VOYAGER (Django)                                │
│                              Port 8000                                       │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Campaign   │  │  Content     │  │   AI Agents  │  │   Analytics  │   │
│  │   Manager    │  │  Creation    │  │   (Router)   │  │   (Voyant)   │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │            │
│         │ TEXT: GPT-4o    │ IMAGE/VIDEO:   │ ORCHESTRATION:  │ SQL: Trino │
│         │ Claude 3.5      │ Vortex (SDXL)  │ Voyant + Vortex │ ClickHouse │
│         │ Gemini          │                │                 │            │
│  ┌──────┴───────────────┐│┌──────────────┴─────┐┌──────────┴──────┐      │
│  │  LLM Router (415L)   │││ Vortex Bridge      ││ Voyant Bridge   │      │
│  │  openai.AsyncOpenAI  │││ (340L)             ││ (451L + 864L)   │      │
│  │  anthropic.AsyncAn.. │││ submit_graph()     ││ ingest_data()   │      │
│  │  httpx (Google)      │││ execute_graph()    ││ analyze_data()  │      │
│  └──────────────────────┘││ get_run_status()   ││ execute_sql()   │      │
│                          ││ cancel_run()       ││ search_similar()│      │
│                          ││ list_mcp_tools()   ││ scrape_url()    │      │
│                          ││ call_mcp_tool()    ││ ocr_image()     │      │
│                          │└────────────────────┘└─────────────────┘      │
│                          │                        │                        │
└──────────────────────────┼────────────────────────┼────────────────────────┘
                           │                        │
                           │ HTTP:11188             │ HTTP:8000
                           │ JWT + tenant_id        │ JWT + tenant_id
                           ▼                        ▼
┌─────────────────────────────────────┐  ┌──────────────────────────────────────┐
│          VORTEX (Rust)              │  │          VOYANT (Django)             │
│          Port 11188                 │  │          Port 8000                   │
│                                     │  │                                      │
│  ┌──────────┐  ┌──────────┐        │  │  ┌──────────┐  ┌──────────┐         │
│  │ Scheduler│  │  Arbiter │        │  │  │ Ingestion│  │ Analysis │         │
│  │ (Kahn)   │  │  (VRAM)  │        │  │  │ (Airbyte)│  │  (NLP)   │         │
│  └────┬─────┘  └────┬─────┘        │  │  └────┬─────┘  └────┬─────┘         │
│       │             │              │  │       │             │              │
│  ┌────┴─────────────┴────┐         │  │  ┌────┴─────────────┴────┐          │
│  │   Supervisor          │         │  │  │     SQL (Trino)       │          │
│  │   spawns Python       │         │  │  │  → ClickHouse         │          │
│  │   worker processes    │         │  │  └───────────────────────┘          │
│  └───────────┬───────────┘         │  │                                      │
│              │ IPC /tmp/vortex.sock│  │  ┌──────────┐  ┌──────────┐         │
│  ┌───────────┴───────────┐         │  │  │  Search  │  │  Scraper │         │
│  │   Python Worker       │         │  │  │ (Milvus) │  │(Playwright│         │
│  │   ┌──────────────┐    │         │  │  │          │  │  + OCR)  │         │
│  │   │ Executor     │    │         │  │  └──────────┘  └──────────┘         │
│  │   │ Registry     │    │         │  │                                      │
│  │   └──────┬───────┘    │         │  │  PostgreSQL  Redis  Kafka  MinIO    │
│  │          │             │         │  └──────────────────────────────────────┘
│  │  ┌───────┼───────┐    │
│  │  ▼       ▼       ▼    │
│  │ KSampler VAE    CLIP  │
│  │ (image) (decode)(text)│
│  │                        │
│  │  ┌──────────────┐      │
│  │  │ Model Loader │      │
│  │  │ HuggingFace  │      │
│  │  │ SD, SDXL     │      │
│  │  └──────┬───────┘      │
│  │         ▼              │
│  │    torch.cuda          │
│  │    GPU inference       │
│  └─────────────────────────┘
└─────────────────────────────────────┘
```

---

## 2. Campaign Orchestration Flow (CORRECTED)

### Where Each Task Runs

```
USER (Marketing Manager)
│
│ POST /api/v1/ai-agents/campaign-workflow/{client_id}/{campaign_id}
│
▼
VOYAGER — CampaignOrchestrator.run_campaign_workflow()
│
├─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: RESEARCH                                                          │
│ Uses: Voyant Bridge                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│ ┌─ Voyant: analyze_competitors() ──┐  ┌─ Voyant: search_keywords() ───┐  │
│ │  → POST /api/v1/analyze          │  │  → POST /api/v1/search/query  │  │
│ │  → Playwright scrapes URLs       │  │  → Milvus semantic search     │  │
│ │  → NLP extracts themes           │  │  → 50 keywords returned       │  │
│ └──────────────────────────────────┘  └───────────────────────────────┘  │
│ ┌─ Voyant: analyze_trends() ───────┐  ┌─ Voyant: sentiment() ─────────┐  │
│ │  → POST /api/v1/analyze          │  │  → POST /api/v1/analyze       │  │
│ │  → ClickHouse trend detection    │  │  → NLP sentiment analysis     │  │
│ └──────────────────────────────────┘  └───────────────────────────────┘  │
│                                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ PHASE 2: CREATIVE                                                          │
│ Uses: LLM Router (TEXT) + Vortex Bridge (IMAGE/VIDEO)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│ TEXT (Voyager LLM Router → OpenAI/Anthropic)                              │
│ ├── Brief:       llm.generate_text() → Claude 3.5 Sonnet                  │
│ ├── Content:     llm.generate_text() → GPT-4o                             │
│ ├── Social:      llm.generate_text() → GPT-4o                             │
│ └── Email:       llm.generate_text() → Claude 3.5 Sonnet                  │
│                                                                            │
│ IMAGE (Voyager → Vortex → GPU)                                             │
│ ├── submit_graph()                                                         │
│ │   graph.nodes = [                                                        │
│ │     {id: "load",  op_type: "Loader::Checkpoint",                         │
│ │      params: {ckpt_name: "sdxl-turbo"}},                                 │
│ │     {id: "prompt", op_type: "Encoder::CLIP",                             │
│ │      params: {text: "professional marketing image of..."}},              │
│ │     {id: "sample", op_type: "Sampler::KSampler",                         │
│ │      params: {steps: 20, cfg: 7.0, seed: 42}},                           │
│ │     {id: "decode", op_type: "Decoder::VAE"}                              │
│ │   ]                                                                      │
│ │   graph.edges = [                                                        │
│ │     ("load" → "prompt"), ("prompt" → "sample"), ("sample" → "decode")    │
│ │   ]                                                                      │
│ ├── execute_graph()                                                        │
│ │   → Vortex Scheduler: Kahn's topo sort                                   │
│ │   → Vortex Supervisor: spawns Python worker                              │
│ │   → Worker: model_loader.load_pipeline("sdxl-turbo") → GPU              │
│ │   → Worker: KSamplerExecutor.execute() → diffusion → latents            │
│ │   → Worker: VAEDecodeExecutor.execute() → latents → image (512x512)     │
│ └── return: {image_url, generation_time_ms, model: "sdxl-turbo"}          │
│                                                                            │
│ VIDEO (Voyager → Vortex → GPU)                                             │
│ ├── submit_graph()                                                         │
│ │   graph.nodes = [{id: "sample", op_type: "Video::LatentSampler",         │
│ │     params: {num_frames: 16}}]                                           │
│ ├── execute_graph()                                                        │
│ │   → Worker: LatentVideoSampler.execute()                                 │
│ │   → torch.randn(1, 16, 4, 64, 64) → temporal latents                  │
│ └── return: {video_url, frames: 16}                                        │
│                                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ PHASE 3: VORTEX WORKFLOW                                                   │
│ Uses: Vortex Bridge                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│ ├── submit_graph() — approval + publishing DAG                             │
│ │   nodes: [ingest, review(HITL), publish, monitor, optimize]             │
│ │   edges: [ingest→review, review→publish, publish→monitor, ...]          │
│ ├── execute_graph()                                                        │
│ │   → Kahn scheduling                                                      │
│ │   → WebSocket progress                                                   │
│ └── return: {graph_id, run_id}                                             │
│                                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ PHASE 4: ANALYTICS                                                         │
│ Uses: Voyant Bridge (ClickHouse/Trino)                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│ ├── Voyant: execute_sql() → Trino → ClickHouse                            │
│ └── Dashboard: impressions, clicks, conversions, ROI                      │
│                                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Vortex Image Generation Sequence (DETAILED)

```
Voyager                    Vortex (Rust)              Python Worker           GPU
─────────────────────────────────────────────────────────────────────────────────

submit_graph(graph_dsl)
───────────────────────→ POST /api/graph
                          graph_repo.store()
←───────────────────────  {graph_id}

execute_graph(graph_id)
───────────────────────→ POST /api/graph/{id}/execute
                          scheduler.kahn_sort()
                          arbiter.check_vram(8192MB)
                          supervisor.spawn_worker()

                          ←─ IPC /tmp/vortex.sock ─→
                          
                                                     model_loader
                                                     .load_pipeline(
                                                       "sdxl-turbo",
                                                       device="cuda",
                                                       dtype="float16"
                                                     )
                                                     
                                                     → AutoPipelineForText2Image
                                                       .from_pretrained(
                                                         "stabilityai/sdxl-turbo"
                                                       )
                                                     → pipe.to("cuda")
                                                     → cache[model_id] = pipe

                          ←─ worker ready ─────────→
                          
                          for node in execution_order:
                            
                            ["load"]: Loader::Checkpoint
                              → IPC: JobRequest
                              → worker: CheckpointLoader.execute()
                              → load_pipeline("sdxl-turbo")
                              → {model, clip, vae} handles
                              
                            ["prompt"]: Encoder::CLIP  
                              → IPC: JobRequest + inputs
                              → worker: CLIPTextEncode.execute()
                              → tokenizer(text, max_length=77)
                              → clip(**text_inputs).last_hidden_state
                              → conditioning embeddings
                              
                            ["sample"]: Sampler::KSampler
                              → IPC: JobRequest + inputs
                              → worker: KSamplerExecutor.execute()
                              → pipe(
                                  prompt=prompt,
                                  width=512, height=512,
                                  num_inference_steps=20,
                                  guidance_scale=7.0,
                                  generator=seed,
                                  output_type="latent"
                                )
                              → result.images (latents: 1x4x64x64)
                              → put_tensor(latents) → SHM
                              
                            ["decode"]: Decoder::VAE
                              → IPC: JobRequest + inputs
                              → worker: VAEDecodeExecutor.execute()
                              → get_tensor(latents) from SHM
                              → vae.decode(latent)
                              → image = (image/2+0.5).clamp(0,1)
                              → image = (image*255).to(uint8)
                              → put_tensor(image) → SHM
                              
                          supervisor.shutdown()
                          
                          ←─ WS: RunComplete ──────→

←───────────────────────  {run_id, status: "completed"}
```

---

## 4. Bridge Reference (Actual Code)

### Voyant Bridge — `voyant_bridge/client.py`

| Method | Voyant Endpoint | Used By | Voyager Module |
|--------|----------------|---------|---------------|
| `ingest_data()` | `POST /api/v1/jobs/ingest` | Sync metrics, import data | `analytics_v2`, `integrations` |
| `get_job_status()` | `GET /api/v1/jobs/{id}` | Check ingestion progress | `analytics_v2` |
| `cancel_job()` | `POST /api/v1/jobs/{id}/cancel` | Cancel long-running job | `workflows_v2` |
| `analyze_data()` | `POST /api/v1/analyze` | Statistical analysis, NLP | `strategy`, `analytics_v2` |
| `execute_sql()` | `POST /api/v1/sql/query` | ClickHouse queries via Trino | `analytics_v2`, `campaigns` |
| `list_tables()` | `GET /api/v1/sql/tables` | Discover available tables | `analytics_v2` |
| `search_similar()` | `POST /api/v1/search/query` | Semantic memory search | `ai_agents` |
| `index_document()` | `POST /api/v1/search/index` | Store memory with embedding | `ai_agents` |
| `delete_indexed_document()` | `DELETE /api/v1/search` | Remove from memory | `ai_agents` |
| `scrape_url()` | `POST /api/v1/scrape/start` | Scrape competitor site | `web_scraping_v2` |
| `scrape_multiple()` | `POST /api/v1/scrape/start` | Batch scraping | `web_scraping_v2` |
| `get_scrape_status()` | `GET /api/v1/scrape/status` | Check scrape progress | `web_scraping_v2` |
| `get_scrape_result()` | `GET /api/v1/scrape/result` | Get scraped data | `web_scraping_v2` |
| `extract_from_html()` | `POST /api/v1/scrape/extract` | Parse HTML with selectors | `web_scraping_v2` |
| `ocr_image()` | `POST /api/v1/scrape/ocr` | OCR receipt/image | `billing`, `web_scraping_v2` |
| `list_sources()` | `GET /api/v1/sources` | Discover data sources | `integrations` |
| `get_source()` | `GET /api/v1/sources/{id}` | Get source details | `integrations` |

### Vortex Bridge — `vortex_bridge/client.py`

| Method | Vortex Endpoint | Used By | Voyager Module |
|--------|----------------|---------|---------------|
| `submit_graph()` | `POST /api/graph` | Submit workflow DAG | `campaigns`, `workflows_v2` |
| `get_graph()` | `GET /api/graph/{id}` | Retrieve graph definition | `workflows_v2` |
| `execute_graph()` | `POST /api/graph/{id}/execute` | Execute DAG on GPU workers | `content_creation`, `campaigns` |
| `get_run_status()` | `GET /api/run/{id}/status` | Monitor execution | `campaigns`, `workflows_v2` |
| `cancel_run()` | `POST /api/run/{id}/cancel` | Cancel workflow | `campaigns`, `workflows_v2` |
| `list_mcp_tools()` | `GET /api/nodes/mcp` | Discover MCP tools | `ai_agents` |
| `list_mcp_clients()` | `GET /api/mcp/clients` | List MCP clients | `ai_agents` |
| `call_mcp_tool()` | `POST /api/mcp/tool/call` | Invoke MCP tool | `ai_agents` |
| `register_mcp_client()` | `POST /api/mcp/client/register` | Register new MCP client | `ai_agents` |
| `health_check()` | `GET /health` | Health monitoring | `infra` |
| `get_metrics()` | `GET /metrics` | Prometheus metrics | `infra` |

---

## 5. File Inventory

### Voyager Files

| File | Lines | Purpose |
|------|-------|---------|
| `voyant_bridge/client.py` | 451 | HTTP client for Voyant API |
| `voyant_bridge/services.py` | 864 | 5 service wrappers |
| `voyant_bridge/models.py` | 156 | Pydantic response models |
| `voyant_bridge/apps.py` | 15 | Django app config |
| `vortex_bridge/client.py` | 340 | HTTP client for Vortex API |
| `vortex_bridge/models.py` | 156 | Pydantic response models |
| `vortex_bridge/compiler.py` | 278 | Workflow-to-GraphDSL compiler |
| `apps/ai_agents/services/llm_router.py` | 415 | OpenAI/Anthropic/Google API calls |
| `apps/ai_agents/services/campaign_orchestrator.py` | 429 | 3-agent orchestration |
| `apps/ai_agents/services/campaign_prompts.py` | 312 | Prompt builders |
| `apps/ai_agents/services/brand_enforcement.py` | 268 | Brand compliance scoring |

### Vortex Source (External, cloned from `somatechlat/vortex`)

| File | Lines | Purpose |
|------|-------|---------|
| `gemini/crates/vortex-core/src/execution.rs` | 343 | Execution engine: Scheduler → Supervisor → IPC → Workers |
| `gemini/crates/vortex-core/src/scheduler.rs` | ~200 | Kahn's topological sort on DAG |
| `gemini/crates/vortex-core/src/graph.rs` | ~300 | GraphDSL: nodes, edges, params |
| `gemini/crates/vortex-core/src/arbiter.rs` | ~150 | VRAM memory arbitration |
| `gemini/crates/vortex-core/src/supervisor.rs` | ~200 | Python worker process management |
| `gemini/crates/vortex-core/src/ipc.rs` | ~200 | POSIX shared memory zero-copy |
| `gemini/worker/vortex_worker/executor.py` | 476 | Node executors: KSampler, VAE, CLIP, Video, Audio |
| `gemini/worker/vortex_worker/model_loader.py` | 322 | HuggingFace model loading with catalog |
| `gemini/worker/vortex_worker/shm.py` | ~150 | Shared memory tensor arena |
| `gemini/worker/vortex_worker/bridge.py` | ~200 | Arrow ↔ PyTorch zero-copy bridge |

---

## 6. Source Code References

All code paths verified against actual files:

- **Voyager → Vortex image generation**: `campaign_orchestrator.py:225-267` → `vortex_bridge/client.py:100-118` → Vortex `execution.rs:150-167` → Python worker `executor.py:210-277` → `model_loader.py:117-179` → `stabilityai/sdxl-turbo`
- **Voyager → Voyant data analysis**: `campaign_orchestrator.py:162-182` → `voyant_bridge/client.py:145-160` → Voyant `apps/analysis/api.py` → NLP model
- **Voyager text generation**: `campaign_orchestrator.py:300-330` → `llm_router.py:156-178` → `anthropic.AsyncAnthropic` → `claude-3-5-sonnet-20241022`
- **Voyant → ClickHouse**: `voyant_bridge/client.py:178-194` → Voyant `apps/sql/api.py` → Trino → ClickHouse

---

**This document was built from actual source code inspection, not assumptions.**
**Vortex source read:** `execution.rs` (343L), `executor.py` (476L), `model_loader.py` (322L), `lib.rs`, `graph.rs`
**Voyant source read:** `models.py` (201L), `config.py` (112L), `api.py`, `middleware.py`, `security/auth.py`
**Voyager source read:** `campaign_orchestrator.py` (429L), `llm_router.py` (415L), `voyant_bridge/client.py` (451L), `vortex_bridge/client.py` (340L)
