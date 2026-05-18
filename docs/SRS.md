# VOYAGER — Software Requirements Specification
## ISO/IEC/IEEE 29148:2018 Compliant

**Document ID:** VYGR-SRS-1.0.0
**Date:** 2026-05-18
**Status:** DRAFT — Pending Review
**Classification:** Internal — Confidential

---

## Table of Contents

1. [Scope](#1-scope)
2. [References](#2-references)
3. [Definitions and Acronyms](#3-definitions-and-acronyms)
4. [System Overview](#4-system-overview)
5. [System Context](#5-system-context)
6. [Stakeholder Requirements](#6-stakeholder-requirements)
7. [Functional Requirements](#7-functional-requirements)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [Use Case: AI-Assisted Campaign Creation](#9-use-case-ai-assisted-campaign-creation)
10. [Gap Analysis](#10-gap-analysis)
11. [Recommendations](#11-recommendations)

---

## 1. Scope

This document specifies the complete software requirements for **VOYAGER**, an enterprise marketing automation platform built on Django 5, PostgreSQL, and Django Ninja. Voyager integrates with the existing **Voyant** (data intelligence) and **Vortex** (workflow engine) platforms.

### 1.1 Purpose
Define all functional and non-functional requirements for Voyager v1.0, including the complete user journey for creating an AI-assisted marketing campaign for a new client with a data-driven strategy.

### 1.2 In Scope
- 17 integrated modules covering the full marketing lifecycle
- Multi-tenant architecture with row-level security
- Full RBAC with 12 hierarchical roles
- 50+ platform integrations
- AI agent orchestration with persistent memory
- Real-time analytics and reporting

### 1.3 Out of Scope
- Frontend UI/UX implementation (separate specification)
- Mobile application
- Third-party platform API development (integration only)

---

## 2. References

| ID | Document | Version |
|----|----------|---------|
| R1 | Voyager Module Specifications (17 modules) | 1.0 |
| R2 | Voyant Architecture (github.com/somatechlat/voyant) | 3.0 |
| R3 | Vortex Architecture (github.com/somatechlat/vortex) | 3.0 |
| R4 | ISO/IEC/IEEE 29148:2018 — Requirements Engineering | 2018 |
| R5 | Voyager RULES.md (coding standards) | 1.0 |
| R6 | Voyager AGENTS.md (agent registry) | 1.0 |

---

## 3. Definitions and Acronyms

| Term | Definition |
|------|-----------|
| **Tenant** | An isolated organization/workspace within Voyager with its own data, users, and configurations |
| **RBAC** | Role-Based Access Control — 12 hierarchical roles from superadmin to guest |
| **MCP** | Model Context Protocol — standard for AI tool integration |
| **DAG** | Directed Acyclic Graph — workflow execution structure |
| **HITL** | Human-in-the-Loop — approval gates requiring human intervention |
| **Persona** | Detailed audience profile with demographics, psychographics, behavioral data |
| **SERP** | Search Engine Results Page |
| **RFM** | Recency, Frequency, Monetary — segmentation model |
| **OKR** | Objectives and Key Results — goal framework |
| **Pacing** | Budget allocation algorithm (even/accelerated/front-loaded/performance) |

---

## 4. System Overview

### 4.1 Architecture

```
+-------------------------------+
|         CLIENT LAYER          |
|  React SPA / Django Admin     |
+-------------------------------+
              |
+-------------------------------+
|      API GATEWAY (Nginx)      |
|  Rate limiting, SSL, WAF      |
+-------------------------------+
              |
+-------------------------------+
|    VOYAGER API (Django+Ninja) |
|  /api/v1/ — 17 module routers |
|  JWT auth, RBAC middleware    |
+-------------------------------+
              |
+---------+---+-----------------+---+-----------------+
|         |                       |                     |
|  VOYANT |           VORTEX     |   EXTERNAL APIs     |
|  (Data) |          (Workflows)  |   (50+ platforms)  |
|         |                       |                     |
+---------+-----------------------+---------------------+
              |
+---------+---+---------+---+---------+---+---------+
|PostgreSQL|Redis|ClickHouse|Qdrant|MinIO|Kafka|
|   (16)   | (7) |         |      |     |     |
+----------+-----+---------+------+-----+-----+
```

### 4.2 Module Map (17 Modules)

| Code | Module | Purpose | Status |
|------|--------|---------|--------|
| CA-01 | Content Creation Engine | AI text/image/video generation | Implemented |
| PB-02 | Publishing & Scheduling | Multi-platform distribution | Implemented |
| CM-03 | Campaign Management | 8-stage lifecycle, budget, A/B | Implemented |
| SP-04 | Strategy & Planning | Personas, OKR, competitor analysis | Implemented |
| DA-05 | Data Analytics & Reporting | Dashboards, attribution, anomaly | Implemented |
| WS-06 | Web Scraping & Intelligence | Competitor monitoring, SERP, OCR | Implemented |
| AG-07 | AI Agents with Memory | 5 agent types, Qdrant, MCP | Implemented |
| SM-08 | Social Media Management | Inbox, comments, influencers | Implemented |
| SE-09 | SEO Management | Keywords, audits, rank tracking | Implemented |
| EM-10 | Email Marketing | Templates, automation, segments | Implemented |
| CR-11 | Client CRM | Onboarding, projects, portals | Implemented |
| BL-12 | Billing & Financial | Time, invoicing, Stripe, P&L | Implemented |
| AM-13 | Asset Management (DAM) | Storage, versioning, AI tagging | Implemented |
| TC-14 | Team Collaboration | Tasks, messaging, workload | Implemented |
| WF-15 | Workflow Automation | Visual builder, Vortex integration | Implemented |
| IH-16 | Integrations Hub | 50+ OAuth, circuit breaker | Implemented |
| GC-17 | Governance & Compliance | FDA/FTC/GDPR, approval gates | Implemented |

---

## 5. System Context

### 5.1 External Systems

| System | Protocol | Purpose |
|--------|----------|---------|
| Voyant | Django app import | Data processing, ingestion, ETL |
| Vortex | HTTP API (port 11188) | Workflow engine, DAG execution |
| Keycloak | JWT (RS256) | Authentication, token validation |
| HashiCorp Vault | hvac client | Secrets management |
| PostgreSQL 16 | psycopg3 | Primary database |
| Redis 7 | redis-py | Cache, Celery broker |
| ClickHouse | HTTP API | Analytics data store |
| Qdrant | gRPC/HTTP | Vector store (agent memory) |
| MinIO | S3 API | Object storage |
| Kafka | kafka-python | Event bus |
| 50+ Platforms | OAuth 2.0 / REST | Social, ads, analytics, email |

---

## 6. Stakeholder Requirements

### 6.1 Marketing Manager
- Create and manage campaigns for multiple clients
- View cross-platform performance dashboards
- Approve content before publishing
- Track budget consumption and ROI

### 6.2 Content Creator
- Generate AI-assisted content with brand enforcement
- Access templates and brand kits
- Submit content for approval
- View content performance analytics

### 6.3 Client Manager
- Onboard new clients with intake forms
- Manage client projects and deliverables
- Share white-label portals with clients
- Track client profitability

### 6.4 Compliance Officer
- Review all content for regulatory compliance (FDA/FINRA/FTC)
- Manage GDPR consent and DSR requests
- Monitor approval gates and escalation
- Generate audit reports

### 6.5 Analyst
- Build custom dashboards with 100+ metrics
- Run attribution models across channels
- Detect performance anomalies
- Export data for external analysis

---

## 7. Functional Requirements

### 7.1 RBAC Requirements (RB-001 to RB-012)

| ID | Requirement | Priority |
|----|-------------|----------|
| RB-001 | System shall support 12 hierarchical roles | High |
| RB-002 | Roles shall inherit permissions from parent roles | High |
| RB-003 | System shall support workspace-scoped permissions | High |
| RB-004 | System shall enforce field-level permissions | Medium |
| RB-005 | System shall support time-bound role assignments | Medium |
| RB-006 | System shall audit all permission changes | High |

### 7.2 Content Creation Requirements (CA-001 to CA-010)

| ID | Requirement | Priority |
|----|-------------|----------|
| CA-001 | System shall generate text using GPT-4o, Claude 3.5, Gemini with routing | High |
| CA-002 | System shall generate images using DALL-E 3, SDXL with brand colors | High |
| CA-003 | System shall generate video scripts with voiceover and subtitles | Medium |
| CA-004 | System shall enforce brand kit compliance (forbidden words, tone) | High |
| CA-005 | System shall support Jinja2 templates with variable substitution | High |
| CA-006 | System shall adapt content for 7 platforms with character limits | High |
| CA-007 | System shall generate A/B test variants with statistical validation | Medium |
| CA-008 | System shall track revision history with word-level diff | Medium |
| CA-009 | System shall repurpose content across formats (blog->thread->video) | Medium |
| CA-010 | System shall check grammar with LanguageTool integration | Low |

### 7.3 Campaign Management Requirements (CM-001 to CM-008)

| ID | Requirement | Priority |
|----|-------------|----------|
| CM-001 | System shall manage 8-stage campaign lifecycle with transition rules | High |
| CM-002 | System shall support 8 channel types with dependency management | High |
| CM-003 | System shall run A/B tests with Bayesian and frequentist statistics | High |
| CM-004 | System shall implement 4 budget pacing algorithms | High |
| CM-005 | System shall generate AI campaign briefs from objectives | Medium |
| CM-006 | System shall provide real-time ClickHouse dashboards | High |
| CM-007 | System shall clone campaigns with selective inheritance | Medium |
| CM-008 | System shall calculate ROI with 6 attribution models | High |

### 7.4 Strategy Requirements (SP-001 to SP-006)

| ID | Requirement | Priority |
|----|-------------|----------|
| SP-001 | System shall create audience personas with demographic/psychographic data | High |
| SP-002 | System shall analyze competitors via NLP on digital presence | Medium |
| SP-003 | System shall build content strategies with topic clusters | High |
| SP-004 | System shall manage editorial calendars with workload balancing | Medium |
| SP-005 | System shall track OKR/KPI with hierarchical alignment | Medium |
| SP-006 | System shall conduct automated market research | Low |

### 7.5 AI Agent Requirements (AG-001 to AG-007)

| ID | Requirement | Priority |
|----|-------------|----------|
| AG-001 | System shall orchestrate 5 agent types with lifecycle management | High |
| AG-002 | System shall provide persistent memory via Qdrant vector store | High |
| AG-003 | System shall assemble context from brand+audience+performance+memory | High |
| AG-004 | System shall support multi-agent collaboration with 5 patterns | Medium |
| AG-005 | System shall implement MCP toolbox with tool registry | Medium |
| AG-006 | System shall provide learning loop with outcome analysis | Medium |
| AG-007 | System shall enforce resource limits (API calls, cost, memory) | High |

---

## 8. Non-Functional Requirements

### 8.1 Performance

| Metric | Requirement |
|--------|-------------|
| API Response (p50) | < 100ms |
| API Response (p99) | < 500ms |
| Auth | < 20ms |
| Content Generation | < 5s (async) |
| Dashboard Load | < 2s |
| Concurrent Users | 10,000+ |
| TPS | 10,000+ |
| Data Ingestion | 1M+ events/hour |

### 8.2 Security

| Requirement | Implementation |
|-------------|---------------|
| Authentication | Keycloak JWT (RS256) |
| Authorization | RBAC with 12 roles, field-level permissions |
| Secrets | HashiCorp Vault, dynamic DB credentials |
| Data Encryption | AES-256 at rest, TLS 1.3 in transit |
| Audit | SHA-256 hash chain, immutable logs |
| Compliance | FDA 21 CFR Part 11, FINRA 2210, GDPR, CCPA, COPPA |

### 8.3 Availability

| Requirement | Target |
|-------------|--------|
| Uptime | 99.9% |
| RTO | < 4 hours |
| RPO | < 1 hour |
| Blue-Green Deployment | Supported |

---

## 9. Use Case: AI-Assisted Campaign Creation

### 9.1 Use Case Description

**UC-001: Create AI-Assisted Campaign for New Client with Data-Driven Strategy**

**Actors:** Marketing Manager (MM), AI Agent (AG), Compliance Officer (CO)

**Preconditions:**
- User authenticated with voyager-marketing-manager role
- Integration connections available for target platforms
- Brand kit configured for client industry

**Postconditions:**
- New client created in CRM
- Data-driven strategy defined with personas and competitor analysis
- Campaign created with AI-generated brief and content
- Content scheduled for publishing across platforms
- Analytics tracking configured

**Success Criteria:**
- Campaign moves from Planning → Launch within configured SLA
- All content passes brand compliance (score >= 80)
- All content passes regulatory compliance (GC-002)
- Budget pacing stays within ±5% of target

---

### 9.2 Business Process Flowchart

```
+------------------------------------------------------------------+
|  PHASE 1: CLIENT ONBOARDING                                      |
|  Module: CR-11 (Client CRM)                                      |
+------------------------------------------------------------------+
                                                                  |
    [MM]                                                          |
      |                                                           |
      v                                                           |
+-------------+                                                   |
| 1. Create   |                                                   |
|    Client   |                                                   |
+-------------+                                                   |
      |                                                           |
      v                                                           |
+-------------+     +-------------------+                         |
| 2. Fill     |---->| Client Intake Form|                         |
|    Intake   |     | - Industry        |                         |
|    Form     |     | - Goals           |                         |
+-------------+     | - Target Audience |                         |
      |             | - Budget Range    |                         |
      |             +-------------------+                         |
      v                                                           |
+-------------+                                                   |
| 3. Brand    |                                                   |
|    Question-|                                                   |
|    naire    |                                                   |
+-------------+                                                   |
      |                                                           |
      v                                                           |
+-------------+                                                   |
| 4. Auto-    |                                                   |
|    Setup    |                                                   |
|    Tenant/  |                                                   |
|    Workspace|                                                   |
+-------------+                                                   |
      |                                                           |
      +-------------------> [PHASE 2]                              |
                                                                  |
+------------------------------------------------------------------+
|  PHASE 2: STRATEGY DEVELOPMENT                                   |
|  Modules: SP-04 (Strategy), WS-06 (Scraping), AG-07 (AI Agents) |
+------------------------------------------------------------------+
                                                                  |
      +-------------------> [from Phase 1]                        |
      |                                                           |
      v                                                           |
+-------------+                                                   |
| 5. Competitor|                                                  |
|    Analysis |                                                   |
+-------------+                                                   |
      |                                                           |
      +------+------+------+                                      |
      |      |      |      |                                      |
      v      v      v      v                                      |
+-----+ +-----+ +-----+ +-----+                                  |
|Scrap| |NLP  | |SWOT | |Trend|                                  |
|Sites| |Analy| |Gen  | |Detec|                                  |
|     | |sis  | |     | |tion |                                  |
+-----+ +-----+ +-----+ +-----+                                  |
      |      |      |      |                                      |
      +------+------+------+                                      |
                |                                                 |
                v                                                 |
+-------------+     +----------------+                            |
| 6. AI Agent |---->| Research Agent |                            |
|    Research |     | - Market size  |                            |
|             |     | - Trends       |                            |
+-------------+     | - Keywords     |                            |
      |             +----------------+                            |
      v                                                           |
+-------------+                                                   |
| 7. Create   |                                                   |
|    Personas |                                                   |
|    (1-5)    |                                                   |
+-------------+                                                   |
      |                                                           |
      v                                                           |
+-------------+     +----------------------+                      |
| 8. Content  |---->| Strategy Builder     |                      |
|    Strategy |     | - Goal Mapping       |                      |
+-------------+     | - Topic Clusters     |                      |
      |             | - Format Mix         |                      |
      |             | - Channel Strategy   |                      |
      |             +----------------------+                      |
      |                                                           |
      +-------------------> [PHASE 3]                              |
                                                                  |
+------------------------------------------------------------------+
|  PHASE 3: CAMPAIGN CREATION                                      |
|  Modules: CM-03 (Campaigns), CA-01 (Content), GC-17 (Governance)|
+------------------------------------------------------------------+
                                                                  |
      +-------------------> [from Phase 2]                        |
      |                                                           |
      v                                                           |
+-------------+                                                   |
| 9. Create   |                                                   |
|    Campaign |                                                   |
|    (linked  |                                                   |
|    to client|                                                   |
|    & strategy|                                                  |
+-------------+                                                   |
      |                                                           |
      v                                                           |
+-------------+     +-----------------------+                     |
| 10. AI Brief|---->| AI Brief Generation   |                     |
|    Genera-  |     | - Objective Analysis  |                     |
|    tion     |     | - Persona Matching    |                     |
+-------------+     | - Competitive Landscape|                    |
      |             | - Channel Recommend.  |                     |
      |             +-----------------------+                     |
      v                                                           |
+-------------+     +-----------------------+                     |
| 11. Brand   |---->| Brand Safety Engine   |                     |
|    Safety   |     | - Profanity Check     |                     |
|    Check    |     | - Competitor Flag     |                     |
+-------------+     | - Topic Filter        |                     |
      |             +-----------------------+                     |
      v                                                           |
+-------------+     +-----------------------+                     |
| 12. Compliance|   | Industry Compliance   |                     |
|    Review   |---->| - FDA/FINRA/FTC/COPPA |                     |
|    (CO)     |     | - Rule Validation     |                     |
+-------------+     +-----------------------+                     |
      |                                                           |
      v                                                           |
+-------------+     +-----------------------+                     |
| 13. Approval|     | Approval Gate         |                     |
|    Gate     |     | - Creative Director   |                     |
|    (HITL)   |---->| - Compliance Officer  |                     |
+-------------+     | - Escalation: 24h     |                     |
      |             +-----------------------+                     |
      v                                                           |
+-------------+     +-----------------------+                     |
| 14. AI Content|   | Creative Agent        |                     |
|    Genera-  |---->| - Text: GPT-4o/Claude |                     |
|    tion     |     | - Image: DALL-E/SDXL  |                     |
+-------------+     | - Video: Script+Voice |                     |
      |             +-----------------------+                     |
      |                                                           |
      +-------------------> [PHASE 4]                              |
                                                                  |
+------------------------------------------------------------------+
|  PHASE 4: PUBLISHING & ANALYTICS                                 |
|  Modules: PB-02 (Publishing), DA-05 (Analytics)                  |
+------------------------------------------------------------------+
                                                                  |
      +-------------------> [from Phase 3]                        |
      |                                                           |
      v                                                           |
+-------------+                                                   |
| 15. Schedule|                                                   |
|    Content  |                                                   |
+-------------+                                                   |
      |                                                           |
      v                                                           |
+-------------+     +-----------------------+                     |
| 16. Multi-  |---->| Platform Publishers   |                     |
|    Platform |     | - Instagram Graph API |                     |
|    Publish  |     | - LinkedIn Marketing  |                     |
+-------------+     | - Twitter API v2      |                     |
      |             | - TikTok Marketing    |                     |
      |             | - YouTube Data API    |                     |
      |             +-----------------------+                     |
      v                                                           |
+-------------+                                                   |
| 17. Analytics|                                                  |
|    Dashboard|                                                   |
|    (Real-time|                                                  |
|    ClickHouse|                                                  |
+-------------+                                                   |
      |                                                           |
      v                                                           |
+-------------+                                                   |
| 18. Optimization|                                                |
|    Loop     |                                                   |
|    (AI Agent|                                                   |
|    feedback)|                                                   |
+-------------+                                                   |
      |                                                           |
      v                                                           |
+-------------+                                                   |
| 19. Final   |                                                   |
|    Reporting|                                                   |
|    & Archive|                                                   |
+-------------+                                                   |
                                                                  |
+------------------------------------------------------------------+
```

---

### 9.3 System Sequence Diagram

```
+------+  +------+  +--------+  +--------+  +--------+  +--------+  +------+  +---------+  +---------+  +---------+  +----------+
|  MM  |  |Voyager|  | Client |  |Strategy|  |Scraping|  |AI Agent|  |Campaign|  | Content |  |Governance|  | Publishing|  |Analytics |
|      |  | API   |  | Module |  | Module |  | Module |  | Module |  | Module |  | Module  |  | Module   |  | Module    |  | Module   |
+---+--+  +---+---+  +----+---+  +----+---+  +----+---+  +----+---+  +----+---+  +----+----+  +----+----+  +----+-----+  +----+-----+
    |          |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    |==== PHASE 1: CLIENT ONBOARDING ===========================================================|           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | POST /clients        |          |          |          |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          | CREATE client_record |          |          |          |          |           |           |            |            |
    |          |--------------------->|          |          |          |          |           |           |            |            |
    |          |          | INSERT clients table |          |          |          |           |           |            |            |
    |          |          | (tenant-scoped)      |          |          |          |           |           |            |            |
    |          |          | OK: client_id=UUID   |          |          |          |           |           |            |            |
    |          |<---------------------|          |          |          |          |           |           |            |            |
    | 201 Created            |          |          |          |          |          |           |           |            |            |
    | (client object)        |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | POST /clients/{id}/onboarding/complete                    |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          | AUTO-SETUP workspace + tenant config            |          |          |           |           |            |            |
    |          |--------------------->|          |          |          |          |           |           |            |            |
    |          |          | CREATE project (default)              |          |          |           |           |            |            |
    |          |          | CREATE brand_kit (from questionnaire)  |          |          |           |           |            |            |
    |          |          | OK                                     |          |          |           |           |            |            |
    |          |<---------------------|          |          |          |          |           |           |            |            |
    | 200 OK                 |          |          |          |          |          |           |           |            |            |
    | (setup complete)       |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    |==== PHASE 2: STRATEGY DEVELOPMENT =========================================================|           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | POST /strategy/competitors/analyze                          |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          | VALIDATE permissions (marketing-manager)          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    |          | SCRAPE competitor websites (WS-001)               |          |          |           |           |            |            |
    |          |-------------------------------------------------------------->|          |           |           |            |            |
    |          |          |          |          |          | HTTP GET (Playwright)            |           |           |            |            |
    |          |          |          |          |          |-----> External Sites             |           |           |            |            |
    |          |          |          |          |          |<----- HTML + Screenshots         |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          | NLP analysis on scraped content                     |           |           |            |            |
    |          |          |          |<---------------------------------------------------|           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          | GENERATE SWOT analysis                              |           |           |            |            |
    |          |          |          | DETECT trends                                       |           |           |            |            |
    |          |          |          | OK: competitor_profiles + trends                    |           |           |            |            |
    |          |          |<---------|          |          |          |           |           |            |            |
    | 200 OK   |          |          |          |          |          |          |           |           |            |            |
    | (competitors + SWOT) |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | POST /strategy/personas        |          |          |          |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          |          |          | CREATE persona_records                            |           |           |            |            |
    |          |          |          |--------------------->|          |          |           |           |            |            |
    |          |          |          |          | INSERT audience_personas                 |           |           |            |            |
    |          |          |          |          | OK: persona_ids                          |           |           |            |            |
    |          |          |          |<---------------------|          |          |           |           |            |            |
    | 201 Created          |          |          |          |          |          |           |           |            |            |
    | (persona objects)    |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | POST /strategy/content-strategies                            |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          |          |          | BUILD content strategy                              |           |           |            |            |
    |          |          |          | - Goal mapping                                      |           |           |            |            |
    |          |          |          | - Topic clusters (from keywords + personas)         |           |           |            |            |
    |          |          |          | - Format mix optimization                           |           |           |            |            |
    |          |          |          |--------------------->|          |          |           |           |            |            |
    |          |          |          |          | INSERT content_strategies                |           |           |            |            |
    |          |          |          |          | OK: strategy_id                          |           |           |            |            |
    |          |          |          |<---------------------|          |          |           |           |            |            |
    | 201 Created          |          |          |          |          |          |           |           |            |            |
    | (strategy object)    |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    |==== PHASE 3: CAMPAIGN + CONTENT CREATION ====================================================|           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | POST /campaigns      |          |          |          |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          | VALIDATE: client_id, strategy_id, permissions                        |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          | CREATE campaign (stage=planning)                                     |           |           |            |            |
    |          |---------------------------------------------------------------------->|           |           |            |            |
    |          |          |          |          |          |          | INSERT campaigns (linked to client + strategy) |            |            |
    |          |          |          |          |          |          | OK: campaign_id                            |            |            |
    |          |          |          |          |          |          |<-----------|           |            |            |
    | 201 Created          |          |          |          |          |          |           |           |            |            |
    | (campaign object)    |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | POST /campaigns/{id}/generate-brief                        |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          | ASSEMBLE context: client + strategy + personas + competitors    |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          | CALL Research Agent (AG-001)    |           |           |            |            |
    |          |          |          |          |          |---------------------------------->|           |            |            |
    |          |          |          |          |          |          |           | LLM API call (Claude/GPT)            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          | GENERATE brief (objective, channels, timeline) |            |
    |          |          |          |          |          |          |<-----------|           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          | STORE brief |          |          |          |          |           |           |            |            |
    |          | UPDATE campaign.stage = 'brief' |          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    | 200 OK   |          |          |          |          |          |           |           |            |            |
    | (generated brief)    |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | POST /governance/scan (brand safety)                        |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |           | SCAN content for brand compliance    |            |
    |          |          |          |          |          |          |           |------------------------>|            |            |
    |          |          |          |          |          |          |           |           | Check: profanity, competitors, topics  |
    |          |          |          |          |          |          |           |           | CALCULATE: brandComplianceScore 0-100  |
    |          |          |          |          |          |          |           |<----------|            |            |
    | 200 OK   |          |          |          |          |          |           |           |            |            |
    | (compliance scores)  |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | POST /governance/approvals (submit for approval)            |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |           | CREATE approval request (HITL)       |            |
    |          |          |          |          |          |          |           |           |------------------------>|            |
    |          |          |          |          |          |          |           |           | NOTIFY: Creative Director            |
    |          |          |          |          |          |          |           |           | SET: timeout = 24h                   |
    |          |          |          |          |          |          |           |           |<------------------------|            |
    | 201 Created          |          |          |          |          |          |           |           |            |            |
    | (approval request)   |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | .... TIME PASSES: CO approves content ....                   |          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    | Webhook: approval approved   |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | POST /content/generate       |          |          |          |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          | ASSEMBLE: brand_kit + strategy + brief + personas  |          |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          | CALL Creative Agent (AG-001)     |           |            |            |
    |          |          |          |          |          |          |---------------------------------->|            |            |
    |          |          |          |          |          |          |           |           | ROUTE: text->Claude, image->DALL-E  |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           | LLM API calls                          |
    |          |          |          |          |          |          |           |           | (OpenAI, Anthropic, Stability)        |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          | GENERATE content (text + image variants) |            |
    |          |          |          |          |          |          |<-----------|           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          | STORE: content_generations table             |          |          |           |           |            |            |
    |          | UPDATE campaign.stage = 'creative'           |          |          |           |           |            |            |
    | 201 Created          |          |          |          |          |          |           |           |            |            |
    | (content generations) |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    |==== PHASE 4: PUBLISHING & ANALYTICS =========================================================|            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | POST /publish/schedule       |          |          |          |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          | VALIDATE: content_id, platforms, scheduled_at           |          |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          | CREATE scheduled_posts records (per platform)           |          |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           | INSERT scheduled_posts |            |
    |          |          |          |          |          |          |           |           |----------------------->|            |
    |          |          |          |          |          |          |           |           | OK: scheduled_post_ids |            |
    |          |          |          |          |          |          |           |           |<-----------------------|            |
    | 201 Created          |          |          |          |          |          |           |           |            |            |
    | (scheduled posts)    |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    | .... Celery task fires at scheduled_at ....                   |          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           | Celery: publish_due_posts |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           | FOR each platform:     |            |
    |          |          |          |          |          |          |           |           |   CALL platform API    |            |
    |          |          |          |          |          |          |           |           |   (OAuth token from Vault)|            |
    |          |          |          |          |          |          |           |           |   POST content + media |            |
    |          |          |          |          |          |          |           |           |   STORE platform_post_id|           |
    |          |          |          |          |          |          |           |           |            |            |
    | UPDATE campaign.stage = 'launch'           |          |          |          |           |           |            |            |
    | UPDATE campaign.all_platforms_published = true          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    | .... Analytics sync starts ....                               |          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           |            | SYNC metrics |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |           |           |            | ClickHouse: |
    |          |          |          |          |          |          |           |           |            | INSERT analytics_events |
    |          |          |          |          |          |          |           |           |            | (impressions, clicks, etc)|
    |          |          |          |          |          |          |           |           |            |            |
    | GET /analytics/dashboards    |          |          |          |          |          |           |           |            |            |
    |--------------------->|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            | QUERY:     |
    |          |          |          |          |          |          |           |           |            | ClickHouse |
    |          |          |          |          |          |          |           |           |            | SELECT...  |
    |          |          |          |          |          |          |           |           |            | FROM analytics_events |
    |          |          |          |          |          |          |           |           |            | WHERE campaign_id = X |
    |          |          |          |          |          |          |           |           |            |            |
    | 200 OK   |          |          |          |          |          |           |           |            |            |
    | (dashboard widgets)  |          |          |          |          |          |           |           |            |            |
    |<---------------------|          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          |          |          |           |           |            |            |
    |==== CONTINUOUS OPTIMIZATION ==================================|           |           |            |            |
    |          |          |          |          |          |          |           |           |            |            |
    | .... Daily: AI Agent reviews performance ....                  |          |          |           |           |            |
    |          |          |          |          |          |          |           |           |            |            |
    |          |          |          |          |          | CALL Optimization Agent (AG-004) |            |            |
    |          |          |          |          |          |<-----------|           |            |            |
    |          |          |          |          |          | ANALYZE: ClickHouse data            |            |            |
    |          |          |          |          |          |          |           |            |            |
    |          |          |          |          |          | GENERATE: optimization suggestions  |            |            |
    |          |          |          |          |          | (bid adjustments, audience tweaks)  |            |            |
    |          |          |          |          |          |          |           |            |            |
    |          |          |          |          |          | WebSocket: notify MM of suggestions |            |            |
    |<---------------------|          |          |          |          |           |            |            |
    |          |          |          |          |          |          |           |            |            |
+------+  +------+  +--------+  +--------+  +--------+  +--------+  +--------+  +---------+  +---------+  +---------+  +----------+
```

---

### 9.4 Data Flow Diagram

```
+------------------------------------------------------------------------+
|                          DATA FLOW: CAMPAIGN CREATION                   |
+------------------------------------------------------------------------+
                                                                        |
  INPUT DATA SOURCES:                                                   |
  +------------------+  +------------------+  +------------------+     |
  | Client Intake    |  | Competitor Sites |  | Historical Data  |     |
  | (Form answers)   |  | (Scraped HTML)   |  | (ClickHouse)     |     |
  +--------+---------+  +--------+---------+  +--------+---------+     |
           |                     |                     |                 |
           |                     |                     |                 |
           v                     v                     v                 |
  +-------------------------------------------------------------+      |
  |                    VOYAGER PROCESSING ENGINE                 |      |
  |                                                              |      |
  |  +-------------+  +-------------+  +-------------+          |      |
  |  | Client Model|  | Strategy    |  | Campaign    |          |      |
  |  | (CR-11)     |  | Model (SP-04)|  | Model (CM-03)|        |      |
  |  |             |  |             |  |             |          |      |
  |  | - name      |  | - personas  |  | - objective |          |      |
  |  | - industry  |  | - competitors|  | - budget    |          |      |
  |  | - goals     |  | - content   |  | - stage     |          |      |
  |  | - budget    |  |   strategy  |  | - channels  |          |      |
  |  +------+------+  +------+------+  +------+------+          |      |
  |         |                |                |                  |      |
  |         +----------------+----------------+                  |      |
  |                          |                                     |      |
  |                          v                                     |      |
  |  +---------------------------------------------------------+   |      |
  |  |              AI AGENT CONTEXT ASSEMBLY (AG-07)          |   |      |
  |  |                                                          |   |      |
  |  |  context = {                                             |   |      |
  |  |    brand_kit:    brand_kit_rules,      // from CA-01     |   |      |
  |  |    audience:     persona_profiles,      // from SP-04    |   |      |
  |  |    performance:  historical_metrics,    // from DA-05    |   |      |
  |  |    memory:       agent_memory_entries,  // from Qdrant   |   |      |
  |  |    strategy:     content_strategy,      // from SP-04    |   |      |
  |  |    campaign:     campaign_objective,    // from CM-03    |   |      |
  |  |    compliance:   regulatory_rules       // from GC-17    |   |      |
  |  |  }                                                       |   |      |
  |  |                                                          |   |      |
  |  |  --> SENT TO LLM (Claude/GPT) FOR CONTENT GENERATION    |   |      |
  |  +---------------------------------------------------------+   |      |
  |                          |                                     |      |
  |                          v                                     |      |
  |  +---------------------------------------------------------+   |      |
  |  |              BRAND ENFORCEMENT LAYER (CA-004)            |   |      |
  |  |  - Forbidden words check                                 |   |      |
  |  |  - Tone compliance                                       |   |      |
  |  |  - Competitor mention flag                               |   |      |
  |  |  - Color palette enforcement (images)                    |   |      |
  |  |  --> brandComplianceScore (0-100)                        |   |      |
  |  +---------------------------------------------------------+   |      |
  |                          |                                     |      |
  |                          v                                     |      |
  |  +---------------------------------------------------------+   |      |
  |  |              GOVERNANCE COMPLIANCE LAYER (GC-017)        |   |      |
  |  |  - FDA 21 CFR Part 11 (pharma)                           |   |      |
  |  |  - FINRA 2210 (financial)                                |   |      |
  |  |  - FTC disclosure requirements                           |   |      |
  |  |  - COPPA (children)                                      |   |      |
  |  |  --> regulatoryComplianceScore (0-100)                   |   |      |
  |  +---------------------------------------------------------+   |      |
  |                          |                                     |      |
  |                          v                                     |      |
  |  +---------------------------------------------------------+   |      |
  |  |              OUTPUT STORAGE                              |   |      |
  |  |  PostgreSQL:                                             |   |      |
  |  |    - content_generations (text, image, video)            |   |      |
  |  |    - scheduled_posts (publishing queue)                  |   |      |
  |  |    - campaigns (status, stage)                           |   |      |
  |  |                                                          |   |      |
  |  |  ClickHouse:                                             |   |      |
  |  |    - analytics_events (performance metrics)              |   |      |
  |  |                                                          |   |      |
  |  |  Qdrant:                                                 |   |      |
  |  |    - agent_memory (embeddings for future campaigns)      |   |      |
  |  |                                                          |   |      |
  |  |  MinIO:                                                  |   |      |
  |  |    - media_assets (images, videos, thumbnails)           |   |      |
  |  +---------------------------------------------------------+   |      |
  +-------------------------------------------------------------+      |
                                                                        |
+------------------------------------------------------------------------+
```

---

## 10. Gap Analysis

### 10.1 Code vs Specification Gaps

| Module | Spec Requirements | Code Status | Gap | Severity |
|--------|-------------------|-------------|-----|----------|
| **CA-01** | 10 functions (CA-001 to CA-010) | 8 implemented | CA-009 (repurposing), CA-010 (grammar) | Medium |
| **PB-02** | 10 functions (PB-001 to PB-010) | 9 implemented | PB-010 (story/reel publishing) | Medium |
| **CM-03** | 8 functions (CM-001 to CM-008) | 8 implemented | None | Low |
| **SP-04** | 6 functions (SP-001 to SP-006) | 6 implemented | None | Low |
| **DA-05** | 8 functions (DA-001 to DA-008) | 7 implemented | DA-008 (SQL federation - Trino) | Medium |
| **WS-06** | 7 functions (WS-001 to WS-007) | 6 implemented | WS-007 (OCR/PDF parsing) | Medium |
| **AG-07** | 7 functions (AG-001 to AG-007) | 7 implemented | None | Low |
| **SM-08** | 7 functions (SM-001 to SM-007) | 7 implemented | None | Low |
| **SE-09** | 7 functions (SE-001 to SE-007) | 7 implemented | None | Low |
| **EM-10** | 6 functions (EM-001 to EM-006) | 6 implemented | None | Low |
| **CR-11** | 6 functions (CR-001 to CR-006) | 6 implemented | None | Low |
| **BL-12** | 7 functions (BL-001 to BL-007) | 7 implemented | None | Low |
| **AM-13** | 6 functions (AM-001 to AM-006) | 6 implemented | None | Low |
| **TC-14** | 6 functions (TC-001 to TC-006) | 6 implemented | None | Low |
| **WF-15** | 7 functions (WF-001 to WF-007) | 7 implemented | None | Low |
| **IH-16** | 6 functions (IH-001 to IH-006) | 6 implemented | None | Low |
| **GC-17** | 7 functions (GC-001 to GC-007) | 7 implemented | None | Low |

**Spec compliance: 118 of 122 functions implemented = 96.7%**

### 10.2 Missing Test Coverage

| Area | Required | Implemented | Gap |
|------|----------|-------------|-----|
| Model tests | 117 files | 0 | 100% gap |
| Service tests | 113 files | 5 | 95.6% gap |
| API tests | 127 files | 0 | 100% gap |
| Integration tests | 17 flows | 0 | 100% gap |
| E2E tests | 5 journeys | 0 | 100% gap |

### 10.3 Missing Infrastructure

| Component | Status | Impact |
|-----------|--------|--------|
| Django Admin configuration | Not started | Cannot manage data via admin |
| Migration files | Placeholders | Cannot run `migrate` |
| Docker validation | Not started | May have build errors |
| WebSocket consumers | Skeleton only | Real-time features broken |
| Vortex gRPC integration | HTTP only | Missing streaming support |
| ClickHouse schema | Not defined | Analytics won't work |
| Qdrant collection setup | Not defined | Agent memory won't work |

---

## 11. Recommendations

### 11.1 Priority 1: Critical (Must Do Before Production)

| # | Task | Effort | Files |
|---|------|--------|-------|
| 1 | Write Django Admin configs for all 19 apps | 2 days | 19 files |
| 2 | Generate real migration files (`makemigrations`) | 1 day | 19 files |
| 3 | Write model tests for all 117 model files | 5 days | 117 files |
| 4 | Write service tests for all 113 service files | 7 days | 113 files |
| 5 | Build ClickHouse schema for analytics | 2 days | 5 files |
| 6 | Build Qdrant collection setup for agent memory | 1 day | 2 files |

### 11.2 Priority 2: High (Should Do Before Production)

| # | Task | Effort | Files |
|---|------|--------|-------|
| 7 | Write API endpoint tests (all 127 view files) | 7 days | 127 files |
| 8 | Implement missing 4 spec functions | 2 days | 4 files |
| 9 | Complete WebSocket consumer implementations | 2 days | 3 files |
| 10 | Build Vortex gRPC streaming client | 2 days | 2 files |
| 11 | Docker Compose validation and fixes | 1 day | 3 files |
| 12 | Integration tests for Voyant bridge | 3 days | 8 files |

### 11.3 Priority 3: Medium (Nice to Have)

| # | Task | Effort | Files |
|---|------|--------|-------|
| 13 | E2E test: AI-assisted campaign creation (UC-001) | 3 days | 5 files |
| 14 | Performance optimization (query profiling) | 3 days | 20 files |
| 15 | OpenAPI documentation generation | 1 day | 1 file |
| 16 | Prometheus metrics instrumentation | 2 days | 19 files |

### 11.4 Total Effort Estimate

| Priority | Effort | Files |
|----------|--------|-------|
| P1: Critical | 18 days | 275 files |
| P2: High | 17 days | 266 files |
| P3: Medium | 9 days | 45 files |
| **Total** | **44 days** | **586 files** |

---

**Document prepared per ISO/IEC/IEEE 29148:2018**
**Author: Voyager Development Team**
**Review Status: Pending**
