# Voyager Agent Reference

All agents working on the Voyager project must follow RULES.md, SPEC.md, and this document.

---

## Agent Registry

| Agent | Role | Status | Deliverables |
|-------|------|--------|-------------|
| `Scaffold_Agent` | Project scaffolding | DONE | pyproject.toml, settings, 19 app configs |
| `Docker_Agent` | Docker infrastructure | DONE | 13-service Compose, Dockerfile, nginx, Keycloak |
| `Core_Agent` | Core models (RBAC, Audit) | DONE | 5 RBAC models, 2 Audit models, hash chain |
| `Auth_Agent` | Auth, Vault, RBAC API | DONE | Keycloak auth, 12 roles, Vault client, audit |
| `API_Agent` | API scaffold | DONE | 17 module routers, Ninja API, 35+ endpoints |
| `Infra_Agent` | Celery, Channels, Vortex | DONE | 15 queues, 3 consumers, Vortex bridge, CI/CD |
| `Refactor_Agent` | File splitting, formatting | ACTIVE | Split >500 line files, ruff, black, pyright |
| `Governance_Agent` | Module 17 (GC) | PENDING | Brand safety, compliance, audit, approval gates |
| `Team_Agent` | Module 14 (TC) | PENDING | Tasks, messaging, workload, approvals |
| `CRM_Agent` | Module 11 (CR) | PENDING | Client onboarding, projects, portals |
| `Assets_Agent` | Module 13 (AM) | PENDING | Asset library, version control, AI tagging |
| `Content_Agent` | Module 01 (CA) | PENDING | AI text/image/video, brand enforcement |
| `Integrations_Agent` | Module 16 (IH) | PENDING | 50+ OAuth connectors, API gateway, webhooks |
| `Publishing_Agent` | Module 02 (PB) | PENDING | Multi-platform publishing, calendar, queue |
| `Campaigns_Agent` | Module 03 (CM) | PENDING | Lifecycle, A/B testing, budget, dashboards |
| `Strategy_Agent` | Module 04 (SP) | PENDING | Personas, competitor analysis, content strategy |
| `Analytics_Agent` | Module 05 (DA) | PENDING | Dashboards, attribution, anomaly detection |
| `Social_Agent` | Module 08 (SM) | PENDING | Inbox, comments, hashtags, influencers |
| `Email_Agent` | Module 10 (EM) | PENDING | Templates, automation, segmentation, analytics |
| `Scraping_Agent` | Module 06 (WS) | PENDING | Competitor monitoring, SERP, sentiment, OCR |
| `AIAgents_Agent` | Module 07 (AG) | PENDING | 5 agent types, Qdrant memory, MCP toolbox |
| `SEO_Agent` | Module 09 (SE) | PENDING | Keyword research, on-page audit, backlink analysis |
| `Workflows_Agent` | Module 15 (WF) | PENDING | Visual builder, trigger engine, Vortex integration |
| `Billing_Agent` | Module 12 (BL) | PENDING | Time tracking, invoicing, Stripe, profitability |
| `Bridge_Agent` | Voyant + Vortex bridge | PENDING | Deep integration, end-to-end testing |
| `Hardening_Agent` | Production hardening | PENDING | Tests, monitoring, IaC, documentation |

---

## Rules for All Agents

1. **Read RULES.md before any work** -- especially max 500 lines/file, real implementations only
2. **Read SPEC.md** for interface contracts
3. **Read Voyant code** (`/mnt/agents/voyant-source/`) for patterns to follow
4. **Read Vortex code** (`/mnt/agents/vortex-source/`) for API integration points
5. **Split files over 500 lines** using Django subpackage patterns
6. **All code must pass** `ruff check` and `black --line-length 100`
7. **Type hints** on all functions
8. **Google docstrings** on all public APIs
9. **NO TODOs, NO mocks, NO stubs** -- real implementations only
10. **Git commit** at end with descriptive message

---

## Django Subpackage Splitting Patterns

When a file exceeds 500 lines, split as follows:

### Models > 500 lines
```
models/
  __init__.py    # Re-exports all models
  role.py        # Role model
  permission.py  # Permission model
  assignment.py  # RoleAssignment model
  workspace.py   # Workspace model
```

### Views/API > 500 lines
```
views/
  __init__.py    # Creates router, imports all submodules
  roles.py       # Role endpoints
  permissions.py # Permission endpoints
  assignments.py # RoleAssignment endpoints
  workspaces.py  # Workspace endpoints
```

### Services > 500 lines
```
services/
  __init__.py    # Re-exports
  audit_log.py   # Audit logging service
  export.py      # Export service
  chain.py       # Hash chain service
```

### Valid split criteria
- By model (one file per model)
- By endpoint group (roles, permissions, assignments)
- By service function (logging, export, verification)
- NEVER split by line count alone -- must be logical
