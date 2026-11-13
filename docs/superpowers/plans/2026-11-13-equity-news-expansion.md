# Equity and News Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the public research workbench to imported Brazilian equity data, commodities, and traceable company news events while preserving the public open-data demo.

**Architecture:** A validated local CSV import adds equity prices and corporate actions to the same snapshot contract. Additional adapters bring CVM filings, GDELT metadata, and Brent/other permitted commodities. The existing regression and event-study engines run against typed series with source-specific calendars and rights flags.

**Tech Stack:** Python 3.12+, FastAPI, SQLite, pandas, numpy, statsmodels, pytest; React 18, TypeScript, Vite.

**Spec:** `docs/superpowers/specs/2026-11-13-market-lens-quant-design.md`

## Global Constraints

- Do not publish raw equity quotes or dividends from a provider whose public-display terms are unresolved.
- Imported equity datasets are local-only by default and are not committed or served from the public demo.
- Original and adjusted stock returns use the same calendar and factor sample; splits are accounted for separately from cash dividends/JCP.
- News keeps original source, URL, publication time, collection time, event-company mapping, and source rights.
- News association and event returns are never labeled causal effects.

## Review Focus

- An ex-dividend event without amount/date must disable total-return comparison; Task 1 tests it.
- A split must not appear as a negative investment return; Task 1 tests it.
- A refiled or cancelled CVM document must not create duplicate independent events; Task 2 tests it.
- GDELT detection time must not be presented as exact publication time; Task 2 tests it.
- Monthly commodities must not be silently forward-filled into daily regressions; Task 3 tests it.

---

### Task 1: Equity import and cash distributions

**Files:** Create `backend/app/data/equity_import.py` and `backend/tests/test_equity_import.py`; extend snapshot schema, returns API, and dashboard import flow.

**Interfaces:** `import_equity_csv(price_file, action_file, rights="local_only") -> ImportSummary` validates ticker, date, close, split factor, dividend/JCP amount and ex-date. `build_return_frame` supports split-adjusted price return and gross total return with/without cash distributions. Import results remain in a separate local database path excluded from Git. The public deployment rejects server-side uploads; the import flow is available only when running locally until a privacy-safe browser-only implementation exists.

- [ ] Test malformed CSV, duplicated dates, wrong ticker, split plus dividend, missing event fields, same-sample regression comparison, and public/local rights separation.
- [ ] Run targeted test and confirm red.
- [ ] Implement import, validation, split/cash adjustment, API and UI entry points.
- [ ] Run targeted and full tests plus frontend build; confirm green.
- [ ] Commit the equity workflow.

### Task 2: Company events and news context

**Files:** Create `backend/app/data/{cvm,gdelt}.py`, `backend/tests/test_company_news.py`; extend event API and timeline components.

**Interfaces:** `parse_cvm_ipe(zip_bytes) -> list[Event]` retains filing identity, company code, publication/replacement status, title and source link. `parse_gdelt_metadata(payload) -> list[NewsItem]` retains URL, source, seen-at, and explicitly uncertain publication time. A mapping table links original-universe tickers to CVM company codes, with a documented verification method.

- [ ] Test relevant filings, replacements/cancellations, unrelated companies, duplicate articles, missing times, and after-close mapping.
- [ ] Run targeted test and confirm red.
- [ ] Implement adapters and timeline evidence cards; link to source documents rather than copying full articles.
- [ ] Run targeted and full tests plus frontend build; confirm green.
- [ ] Commit the news workflow.

### Task 3: Commodities and expanded factor analysis

**Files:** Create `backend/app/data/{eia,world_bank}.py`, `backend/tests/test_factors.py`; extend catalog, regression selection, and methodology.

**Interfaces:** Adapters add Brent daily from EIA and selected Pink Sheet monthly commodities with source, unit, currency, and rights metadata. EIA publishes a downloadable workbook without an API key, while the FRED API requires a registered key. The factor selector shows only daily factors compatible with the daily model; monthly series remain separate until publication timing can be aligned. Transforms are explicit.

- [ ] Test EIA missing observations and source identity, Pink Sheet monthly dates/units, daily-versus-monthly mismatch, and no-lookahead alignment.
- [ ] Run targeted test and confirm red.
- [ ] Implement adapters, factor validation, UI controls, and source descriptions.
- [ ] Run targeted and full tests plus frontend build; confirm green.
- [ ] Commit the factor expansion.

### Task 4: Portfolio publication review

**Files:** Update README, methodology, attribution manifest, screenshots, deployment config, and CI.

**Interfaces:** Public demo opens without keys, offers the Tesouro/Copom study, and clearly identifies local-only equity research. News evidence, methods, dates, sample sizes, and limits are accessible from the UI.

- [ ] Run clean install, full backend suite, frontend build, snapshot refresh and browser walkthrough.
- [ ] Check every displayed source's terms and attribution; verify no local-only prices or secrets in build artifacts or repository.
- [ ] Update documentation and screenshots from the verified app.
- [ ] Commit the publication package.
