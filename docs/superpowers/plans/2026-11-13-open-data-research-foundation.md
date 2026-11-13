# Open Data Research Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a public, reproducible Tesouro/BCB research flow with cash-flow-adjusted regression and evidence-backed Copom event analysis.

**Architecture:** Offline adapters fetch official open datasets into a versioned SQLite snapshot. Pure analysis functions compute aligned returns, comparable OLS results, and event windows. FastAPI serves a typed research contract; React presents the research and its sources without requiring visitor API keys.

**Tech Stack:** Python 3.12+, FastAPI, SQLite, pandas, numpy, statsmodels, pytest; React 18, TypeScript, Vite.

**Spec:** `docs/superpowers/specs/2026-11-13-market-lens-quant-design.md`

## Global Constraints

- Only Tesouro and BCB datasets with source and ODbL attribution enter the public snapshot.
- Use the same dates and factors for adjusted and unadjusted regressions.
- Map publications after the session to the following available session; unknown publication time takes the conservative next-session path.
- Do not call temporal association causal impact or publish a 14-session forecast in this plan.
- All observations retain source URL, observation date, collection time, and normalization version; events retain publication and observed times.
- No API keys or credentials in the frontend or committed snapshot.

## Review Focus

- Missing or zero prices must never create infinite or invented returns; Task 2 tests rejection.
- A coupon on a day without a quote must enter the return interval containing its payment date; Task 2 tests this.
- Dataset refresh failure must leave the prior usable snapshot intact; Task 1 tests this.
- Same-day Copom publications with unknown or after-market time must not enter the preceding session; Task 3 tests this.
- A source event with insufficient pre-event or post-event observations must show an explicit unavailable reason; Task 3 tests this.

---

### Task 1: Versioned open-data snapshot

**Files:** Create `backend/app/data/{models,store,tesouro,bcb,copom,refresh}.py`, `backend/tests/test_data_pipeline.py`, and compact source fixtures in `backend/tests/fixtures/`; modify `backend/pyproject.toml` and `.gitignore`.

**Interfaces:** `refresh_snapshot(database_path: Path, fetched_at: datetime) -> RefreshSummary`; `SnapshotStore` exposes `list_series()`, `observations(series_id)`, `cash_flows(instrument_id)`, and `events(topic)` as typed dataclasses. Adapters parse the official CSV/JSON formats independently of HTTP. A command-line entry point performs refresh into a temporary database and atomically replaces the prior file only after validation.

- [ ] Add fixture-based tests for Tesouro title/maturity/date/decimal parsing, coupon `PU` per unit, BCB date/value parsing, Copom event ID/time/link, provenance fields, and atomic refresh failure.
- [ ] Run `pytest tests/test_data_pipeline.py -q` and confirm the tests fail for missing implementations.
- [ ] Implement parsers, fetchers with timeouts, schema, provenance, and atomic refresh; never commit raw credentials.
- [ ] Run `pytest tests/test_data_pipeline.py -q` and confirm all pass.
- [ ] Commit the independently usable data pipeline.

### Task 2: Return measures and comparable regressions

**Files:** Create `backend/app/analysis/{returns,regression}.py`, `backend/tests/test_returns_regression.py`.

**Interfaces:** `build_return_frame(prices, cash_flows, factors) -> ReturnFrame` carries price return, gross total return, aligned factor changes, and retained dates. `compare_regressions(frame, factor_ids, train_end) -> RegressionComparison` yields two fits and their coefficient, interval, residual, sample, and holdout metrics. Tesouro uses the sale price from one title/maturity; stock splits are outside this task.

- [ ] Test a coupon between quotes, zero/missing price, factor gaps, identical sample dates, a known OLS coefficient, and chronological holdout.
- [ ] Run `pytest tests/test_returns_regression.py -q` and confirm red.
- [ ] Implement return alignment, gross coupon adjustment, documented factor transforms, OLS, diagnostics, and holdout benchmark.
- [ ] Run the targeted test and confirm green.
- [ ] Commit the analysis engine.

### Task 3: Copom event window analysis

**Files:** Create `backend/app/analysis/event_study.py`, `backend/tests/test_event_study.py`.

**Interfaces:** `study_event(event, returns, benchmark, horizons=(1, 3, 5)) -> EventStudyResult` maps publication to first available session after publication and returns observed, benchmark and abnormal cumulative returns, availability reasons, and event source. A cohort function computes an uncertainty interval from non-overlapping comparable events.

- [ ] Test event before/after close, unknown time, holidays, insufficient window, and overlapping events; check calculations against small hand-worked series.
- [ ] Run `pytest tests/test_event_study.py -q` and confirm red.
- [ ] Implement alignment, window calculation, cohort summary, and uncertainty calculation with documented convention.
- [ ] Run the targeted test and confirm green.
- [ ] Commit the event analysis.

### Task 4: Research API

**Files:** Create `backend/app/api/routes/research.py`, `backend/app/api/schemas.py`, `backend/tests/test_research_api.py`; modify `backend/app/main.py`.

**Interfaces:** `GET /api/catalog`, `GET /api/series/{series_id}`, `GET /api/research/regression?instrument_id=...`, and `GET /api/events?topic=...` serve source-attributed, typed responses from one snapshot version. Every unavailable result uses a stable reason code and an explanatory Portuguese message.

- [ ] Test the full Tesouro/BCB/Copom fixture through the API, including missing series, insufficient data, source URLs, and matching regression samples.
- [ ] Run `pytest tests/test_research_api.py -q` and confirm red.
- [ ] Implement the routes and response models with bounded query windows.
- [ ] Run the targeted test and full `pytest -q` and confirm green.
- [ ] Commit the API.

### Task 5: Research dashboard

**Files:** Create `frontend/src/{api,types,styles.css}` and focused components under `frontend/src/components/`; modify `frontend/src/App.tsx` and `frontend/index.html`.

**Interfaces:** A visitor can select the public title, inspect price/coupon/factor charts and provenance, switch adjusted versus raw regression, compare side-by-side metrics, and open Copom event cards with 1/3/5-session observed versus benchmark movements. Empty/error/loading states disclose snapshot freshness and gaps.

- [ ] Implement the typed API client and accessible dashboard around the Task 4 contract, using no secret in browser code.
- [ ] Run `npm run build` and resolve type/build errors.
- [ ] Manually exercise the complete flow in a browser against the fixture/snapshot, including the adjustment toggle and an event card.
- [ ] Commit the dashboard.

### Task 6: Reproducibility and delivery

**Files:** Modify `README.md`, `docs/ARQUITETURA.md`, and deployment configuration only where the running flow requires it; create `docs/METODOLOGIA.md` and source attribution manifest.

**Interfaces:** One documented command creates the open-data snapshot; one documented command runs the backend and another the frontend. The method document states source versions, price/coupon convention, regression specification, event windows, benchmark, uncertainty, and limitations.

- [ ] Run a clean snapshot refresh from official sources and inspect title coverage, coupon dates, Copom events and attribution.
- [ ] Run all backend tests and frontend build, then exercise the API and UI from the refreshed snapshot.
- [ ] Document exact reproduction steps and a visible portfolio narrative with screenshots.
- [ ] Commit documentation and verified snapshot metadata.
