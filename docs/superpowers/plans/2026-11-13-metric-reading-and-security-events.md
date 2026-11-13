# Metric Reading and Security Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Explain the dashboard's statistics in context and compare each official company disclosure's observed security return with a pre-event factor reference, with and without cash distributions.

**Architecture:** Reuse the existing frozen public data and local-only imported equity path. Compute separate price and total event models on the same aligned dates, then surface both in the local equity interface with short interpretation text. Keep GDELT links outside quantitative event calculations.

**Tech Stack:** Python 3.12, FastAPI, SQLite, numpy, pytest, React 18, TypeScript, Vite.

**Spec:** `docs/superpowers/specs/2026-11-13-metric-reading-and-security-events.md`

## Global Constraints

- Public deployment never receives imported equity prices or proventos.
- News association and abnormal returns are descriptive, never labeled causal.
- Every price and total event pair uses identical sessions and factor IDs.
- GDELT seen time is not exact publication time.

## Review Focus

- Cash distribution on the event session changes total return and not price return.
- No distribution leaves the two event modes equal.
- Cancelled CVM documents have no measured impact.
- Missing pre-event sessions and post-event sessions display explicit reasons.
- Small cohorts do not show a confidence interval.

---

### Task 1: Dual-mode event evidence

**Files:** Modify `backend/app/analysis/company_impact.py`, `backend/app/api/routes/local.py`, `backend/app/api/schemas.py`; test in `backend/tests/test_company_news.py`.

**Interfaces:** `study_filing_impact(..., return_mode="total")` accepts `price` or `total`. `/api/local/equity/{ticker}/news-impact` returns `windows` (total, backward compatible), `price_windows`, and mode-specific cohorts for CVM facts and market communications. The same document and aligned dates drive both modes.

- [x] Write tests for a cash payment on an event day, same date sample, cancellation, and API fields.
- [x] Run targeted tests red.
- [x] Implement model target selection and response fields.
- [x] Run targeted and full backend tests green; commit.

### Task 2: Explanations in context

**Files:** Create `frontend/src/components/MetricGuide.tsx`, modify `frontend/src/App.tsx`, `frontend/src/components/EquityLab.tsx`, `frontend/src/types.ts`, `frontend/src/styles.css`, and `docs/METODOLOGIA.md`.

**Interfaces:** Static explanations of definitions and units appear next to the corresponding measure; event interpretation includes the selected security, source document, observed and expected returns, difference, amount of sample evidence, and the selected price or total mode.

- [x] Implement visible, concise help and event mode switch in the existing dashboard.
- [x] Verify type check, production build, desktop and mobile views; update methodology.
- [x] Run complete backend suite and commit.

### Task 3: Verified external news

**Files:** Add `backend/app/data/article_import.py`; modify local API, equity interface, tests, README and methodology.

- [x] Validate publication dates, explicit time zones, HTTPS sources and file size in the local API.
- [x] Apply the same pre-event factor models to every supplied article, keeping its cohort separate from CVM disclosures.
- [x] Show source, date, observed and expected returns, difference and proventos mode for each article.
- [x] Run backend and frontend verification; commit.
