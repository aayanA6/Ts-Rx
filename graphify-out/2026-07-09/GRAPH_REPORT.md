# Graph Report - Ts-Rx  (2026-07-08)

## Corpus Check
- 50 files · ~42,050 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 568 nodes · 1238 edges · 33 communities (29 shown, 4 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 101 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8d20ffcb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.py
- schemas.py
- api.ts
- get_settings
- devDependencies
- index-DYZRKu1Q.js
- diagnosisSummary.ts
- content.js
- TS-RX Setup Guide
- _extract_proposed_fix
- compilerOptions
- compilerOptions
- TS-RX — Ship-by-Friday Plan
- notifier.py
- j
- c
- yt
- nf
- manifest.json
- HackCanada
- tsrx-agent.sh
- check_auth_rate_limit
- GUID
- ke
- Al
- setup.sh script
- tsconfig.json
- vite.extension.config.ts
- __init__.py
- analysis-agent

## God Nodes (most connected - your core abstractions)
1. `RequestIdFilter` - 39 edges
2. `User` - 29 edges
3. `AnalysisJobCreate` - 25 edges
4. `Analyzer` - 21 edges
5. `AnalysisJob` - 19 edges
6. `AnalysisWorker` - 18 edges
7. `compilerOptions` - 18 edges
8. `compilerOptions` - 16 edges
9. `get_settings()` - 14 edges
10. `SelectiveCodeRetriever` - 14 edges

## Surprising Connections (you probably didn't know these)
- `_analyzer()` --indirect_call--> `Analyzer`  [INFERRED]
  tests/test_analyzer_markdown.py → analysis_agent/analyzer.py
- `test_normalize_step_from_action_uses_description_when_command_is_placeholder()` --calls--> `_normalize_step_from_action()`  [EXTRACTED]
  tests/test_execution_plan_cleanup.py → analysis_agent/main.py
- `test_extract_solution_steps_removes_manual_prefix_and_safety_note()` --calls--> `_extract_solution_steps()`  [EXTRACTED]
  tests/test_execution_plan_cleanup.py → analysis_agent/main.py
- `Analyzer` --uses--> `GeminiClient`  [INFERRED]
  analysis_agent/analyzer.py → analysis_agent/gemini_client.py
- `Analyzer` --uses--> `GeminiClientError`  [INFERRED]
  analysis_agent/analyzer.py → analysis_agent/gemini_client.py

## Import Cycles
- None detected.

## Communities (33 total, 4 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.07
Nodes (73): confidence_from_report(), create_access_token(), create_refresh_token(), decode_token(), generate_api_key(), generate_reset_token(), hash_api_key(), hash_password() (+65 more)

### Community 1 - "schemas.py"
Cohesion: 0.08
Nodes (58): Analyzer, _build_structured_summary(), _extract_section_bullets(), _has_required_sections(), _normalize_optional_string(), _normalize_summary_markdown(), _parse_confidence(), AnalysisReport (+50 more)

### Community 2 - "api.ts"
Cohesion: 0.09
Nodes (40): App(), params, Dashboard(), Header(), HeaderProps, stringToColor(), initialResetToken, LoginPage() (+32 more)

### Community 3 - "get_settings"
Cohesion: 0.09
Nodes (17): get_settings(), Path, Settings, get_db(), AsyncSession, GeminiClient, GeminiClientError, Any (+9 more)

### Community 4 - "devDependencies"
Cohesion: 0.06
Nodes (31): dependencies, clsx, date-fns, framer-motion, js-confetti, lucide-react, react, react-dom (+23 more)

### Community 5 - "index-DYZRKu1Q.js"
Cohesion: 0.07
Nodes (27): Af, ba, cp(), df, ec, _f, ff, Fl (+19 more)

### Community 6 - "diagnosisSummary.ts"
Cohesion: 0.17
Nodes (18): formatAge(), IncidentCard(), ReviewModal(), resolveIncident(), buildFallbackSummary(), getDiagnosisSummaryMarkdown(), hasRequiredSections(), isLowQualitySummary() (+10 more)

### Community 7 - "content.js"
Cohesion: 0.16
Nodes (23): buildTab(), ensureTab(), findMachinesContainer(), findSettingsContainer(), getMainContainer(), getNavBottom(), getPageBg(), getTabContainer() (+15 more)

### Community 8 - "TS-RX Setup Guide"
Cohesion: 0.09
Nodes (21): 10. Verifying everything works, 1. Get a Gemini API key, 2. Clone the repo, 3. Local development (no Docker), 3a. Start Postgres and Redis, 3b. Backend, 3c. Frontend, 4. Production deployment (+13 more)

### Community 9 - "_extract_proposed_fix"
Cohesion: 0.16
Nodes (19): _build_summary_fallback(), _clean_step_text(), _dedupe_steps(), _extract_evidence_highlights(), _extract_proposed_fix(), _extract_solution_steps(), _extract_top_hypotheses(), _find_destructive_steps() (+11 more)

### Community 10 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+11 more)

### Community 11 - "compilerOptions"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, isolatedModules, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 12 - "TS-RX — Ship-by-Friday Plan"
Cohesion: 0.12
Nodes (16): Code fixes (30 min, blocking), First-run checklist (30 min), Friday, July 4 — Polish, harden, optional extras (~2–4 hrs), Hardening (1 hr, blocking for production), Known limitations to be aware of (not blocking but should know), Nice-to-have (2–3 hrs, not blocking), Start the stack (30 min), Status snapshot (what's already done) (+8 more)

### Community 13 - "notifier.py"
Cohesion: 0.33
Nodes (10): _post_webhook(), Sends a plaintext email. Returns False (no-op) if SMTP isn't configured., Fire all enabled notification channels. Errors are logged, never raised., _send_discord(), _send_email(), send_incident_notification(), _send_ntfy(), _send_raw_email() (+2 more)

### Community 14 - "j"
Cohesion: 0.27
Nodes (11): dp(), fp(), gf, gp(), j(), jp(), kp(), lp() (+3 more)

### Community 15 - "c"
Cohesion: 0.29
Nodes (10): c(), Ga(), hp(), _p(), tp(), Ul(), Xa(), xp() (+2 more)

### Community 16 - "yt"
Cohesion: 0.36
Nodes (9): ap(), ep(), ip(), np(), op(), rp(), sp(), up() (+1 more)

### Community 17 - "nf"
Cohesion: 0.22
Nodes (9): bd(), Bi(), ef(), lf(), nf(), qd(), rf(), tf() (+1 more)

### Community 18 - "manifest.json"
Cohesion: 0.25
Nodes (7): content_scripts, description, host_permissions, manifest_version, name, version, web_accessible_resources

### Community 19 - "HackCanada"
Cohesion: 0.25
Nodes (7): Backend (analysis agent), Core API endpoints, Frontend (Vite), HackCanada, Intake JSON format (Uptime Kuma style), Repo structure, Safety constraints

### Community 20 - "tsrx-agent.sh"
Cohesion: 0.43
Nodes (4): install_systemd(), report_incident(), run_loop(), tsrx-agent.sh script

### Community 21 - "check_auth_rate_limit"
Cohesion: 0.47
Nodes (5): check_auth_rate_limit(), _client_ip(), Request, FastAPI dependency — raises 429 when the client IP exceeds the auth rate limit., # NOTE: Per-process only — limits are not shared across multiple uvicorn workers

### Community 22 - "GUID"
Cohesion: 0.33
Nodes (3): GUID, Platform-independent GUID type. Uses PostgreSQL's UUID natively;     falls back, TypeDecorator

### Community 23 - "ke"
Cohesion: 0.33
Nodes (6): Dl(), Ja(), ke(), Qa(), sf(), uf()

### Community 24 - "Al"
Cohesion: 0.40
Nodes (5): Al(), Bf, Qf, Wi(), zf

### Community 25 - "setup.sh script"
Cohesion: 0.83
Nodes (3): die(), log(), setup.sh script

## Knowledge Gaps
- **148 isolated node(s):** `df`, `ff`, `pf`, `mf`, `Ml` (+143 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisJobCreate` connect `schemas.py` to `main.py`, `get_settings`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `UptimeStatus` connect `schemas.py` to `main.py`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `Analyzer` connect `schemas.py` to `main.py`, `get_settings`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `RequestIdFilter` (e.g. with `AnalysisJob` and `AnalysisReport`) actually correct?**
  _`RequestIdFilter` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `User` (e.g. with `forgot_password()` and `login()`) actually correct?**
  _`User` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `AnalysisJobCreate` (e.g. with `Analyzer` and `RequestIdFilter`) actually correct?**
  _`AnalysisJobCreate` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Analysis agent package.`, `Returns (plaintext_key, hashed_key). Plaintext returned only once.`, `Returns (plaintext_token, hashed_token). Plaintext is embedded in the reset link` to the rest of the system?**
  _159 weakly-connected nodes found - possible documentation gaps or missing edges._