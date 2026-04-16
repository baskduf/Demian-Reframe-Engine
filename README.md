# Demian Reframe Engine

Rule-based CBT treatment support engine for adult GAD, designed with FDA/SaMD-friendly constraints in mind.

This project is not a free-form counseling bot. The core therapeutic flow is controlled by a deterministic CBT state machine, safety rules, and audit logging. LLMs are used only as support components for structured parsing, candidate recommendation, and language rendering.

## Product Direction

- Target condition: adult generalized anxiety disorder (GAD)
- Product type: structured CBT cognitive restructuring support software
- Core engine: deterministic state machine + rule tables + safety branching
- LLM role: input interpreter, candidate recommender, language renderer
- Not supported: diagnosis, delusion adjudication, final clinical judgment, independent crisis handling

## Core Principles

- Rules decide treatment flow.
- Safety rules override normal session flow.
- LLM output is candidate-only, never final clinical truth.
- All important decisions must be reproducible and auditable.
- Versioned prompts, rules, and engine behavior must be traceable.

## Current Capabilities

- FastAPI API for structured CBT session flow
- GAD-oriented CBT states from risk screening to summary
- Deterministic risk screening for suicidality, psychotic-like expression, and acute deterioration
- Deterministic distortion suggestion rules
- Optional LLM-assisted parsing of free text into CBT candidates
- Optional LLM-assisted candidate distortion/risk support and template rendering
- SQLite persistence for sessions, artifacts, transition logs, risk logs, and LLM invocation logs
- Audit endpoint with transition, risk, event, and LLM invocation history

## High-Level Architecture

```text
User Input
  -> Safety Rules
  -> LLM Assist Layer (optional)
  -> Validator / Candidate Filter
  -> Rule-Based CBT Engine
  -> Session State Transition
  -> Audit Logging
```

Subsystems:

- `app/domain`: deterministic CBT rules, state machine, risk logic, distortion logic
- `app/services`: session orchestration and LLM gateway integration
- `app/llm`: structured output contracts, OpenAI client, parser, renderer, risk assist
- `app/persistence`: SQLite repositories and append-only style logs
- `app/api`: FastAPI routes
- `docs`: product and validation design docs
- `tests`: unit, API, regression, and scenario coverage

## API Overview

Existing session APIs:

- `POST /v1/sessions`
- `GET /v1/sessions/{session_id}`
- `POST /v1/sessions/{session_id}/events`
- `POST /v1/sessions/{session_id}/risk-screen`
- `POST /v1/sessions/{session_id}/reassess-risk`
- `GET /v1/sessions/{session_id}/artifacts`
- `GET /v1/protocols/{version}`
- `GET /v1/audit/sessions/{session_id}`

Typed event contract:

- `eligibility` -> `is_adult`, `target_condition`
- `situation` -> `situation_text`, `trigger_text`, optional `free_text`
- `worry` -> `automatic_thought`, `worry_prediction`, optional `free_text`
- `emotion` -> `emotions`, optional `body_symptoms`, optional `safety_behaviors`, optional `free_text`
- `distortion` -> `selected_distortion_ids`
- `evidence_for` -> `evidence_for`
- `evidence_against` -> `evidence_against`
- `alternative` -> `balanced_view`, `coping_statement`
- `rerate` -> `re_rated_anxiety`, `experiment_required`
- `experiment` -> `action`, `timebox`, optional `hypothesis`
- `summary` -> `summary_ack`

The wire shape remains `{ "event_type": "...", "payload": { ... } }`, but payloads are now validated against state-specific models internally.

LLM preview/debug APIs:

- `POST /v1/llm/parse-preview`
- `POST /v1/llm/render-preview`
- `GET /v1/health/llm`
- `POST /v1/llm/live-check`

## LLM Safety Boundary

Allowed:

- Convert free text into CBT slot candidates
- Suggest distortion candidates
- Suggest clarification need
- Render question or alternative-thought wording
- Provide risk-expression support flags

Not allowed:

- Diagnose mental disorders
- Determine delusions or psychosis
- Decide final treatment logic
- Decide session state transitions
- Independently handle crisis situations
- Invent unapproved therapeutic techniques

## Local Setup

Requirements:

- Python 3.11+

Install:

```bash
python -m pip install -e .[dev]
```

Run:

```bash
uvicorn app.main:app --reload
```

Optional environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL_STRUCTURER`
- `OPENAI_MODEL_RENDERER`
- `OPENAI_MODEL_RISK_ASSIST`
- `OPENAI_BASE_URL`
- `OPENAI_TIMEOUT_SECONDS`
- `LLM_CONFIDENCE_THRESHOLD`
- `OPENAI_ENABLE_LIVE_TESTS`
- `OPENAI_ENABLE_LIVE_EVAL`

If `OPENAI_API_KEY` is not set, the engine falls back to deterministic behavior and template-based rendering where applicable.

LLM diagnostics:

- `GET /v1/health/llm`: reports whether the app is configured for live OpenAI calls
- `POST /v1/llm/live-check`: performs a short structured-output verification call without creating a therapy session

## Testing

Run the full suite:

```bash
python -m pytest -q
```

Run live OpenAI integration tests only when you explicitly enable them:

```bash
$env:OPENAI_API_KEY="your-key"
$env:OPENAI_ENABLE_LIVE_TESTS="true"
python -m pytest -q -m live
```

Current coverage includes:

- state transition guards
- risk branching
- distortion regression checks
- API contracts
- audit logging
- LLM integration behavior with mocks
- optional live OpenAI verification when enabled

## Model Evaluation

Static sample evaluation:

```bash
python -m eval.run_eval --mode static
```

Live evaluation against the configured OpenAI integration:

```bash
$env:OPENAI_API_KEY="your-key"
$env:OPENAI_ENABLE_LIVE_EVAL="true"
python -m eval.run_eval --mode live
```

Evaluation artifacts are written to `eval/reports/`:

- `summary.json`
- `case_results.json`
- `report.md`

The sample evaluation set is intentionally small and is meant for parser/prompt iteration, not for clinical benchmarking.

## Design Docs

- [Engine Spec](docs/engine_spec.md)
- [Rule Catalog](docs/rule_catalog.md)
- [Validation Plan](docs/validation_plan.md)
- [Model Eval Plan](docs/model_eval_plan.md)

## Regulatory-Friendly Design Notes

- deterministic core treatment logic
- explicit safety-first branch handling
- append-only style audit history
- version tracking for rules, prompts, and engine behavior
- separation of clinical decision logic from ML/LLM assistance

## Status

This repository currently provides a working scaffold and validation baseline for a rule-based CBT reframe engine with optional LLM assistance. It is intended as a controlled treatment-support engine foundation, not as an autonomous therapeutic agent.
