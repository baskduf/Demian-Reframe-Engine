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

When you use the default output path, runs are grouped under mode-specific folders such as `eval/reports/live/<run_id>/` and `eval/reports/static/<run_id>/`.

Compare two evaluation runs:

```bash
python -m eval.compare_runs --baseline eval/reports/static/run-a --candidate eval/reports/live/run-b --output-dir eval/reports/comparison/run-a-vs-run-b
```

Inspect locked baselines:

```bash
python -m eval.list_baselines list
python -m eval.show_baseline show --id expanded-live-eval
```

Comparison artifacts:

- `comparison.json`
- `comparison.md`

The bundled Korean GAD evaluation set is now an expanded curated regression set with explicit category mix tracking for:

- `automatic_thought`
- `distortion`
- `risk`
- `clarification`
- `emotion_behavior`

Current curated dataset size:

- `60` Korean GAD-focused cases
- tracked in `eval/datasets/sample_gad_gold.jsonl`
- summarized in `eval/datasets/sample_gad_gold.manifest.json`

Reports surface both overall metrics and subset metrics such as `automatic_thought_case_hit_rate`, `distortion_case_top3_hit_rate`, `clarification_case_accuracy`, and `risk_expected_case_recall`.

This dataset is still an internal prompt/parser regression tool, not clinical benchmarking evidence.

## Baseline Policy

The project now uses locked evaluation artifacts as official baselines.

- `expanded-live-eval` is the primary official curated baseline.
- `live-thought-distortion-v3` is a small-set reference run.
- `clarification-live-v2` is experimental.
- `synthetic-live-eval-002` is provisional and not valid for official performance claims.
- `synthetic-live-eval-005-reviewed-v2` is a reviewed synthetic reference for internal miss triage only.

Rules:

- if dataset, model, parser prompt, and risk prompt are unchanged, reuse the locked artifact instead of rerunning live eval
- if code, prompts, post-processing, or dataset changes, create a new run and compare against the locked baseline
- curated baselines and synthetic runs must not be treated as directly interchangeable quality evidence
- human-reviewed synthetic datasets are required before synthetic runs can be used for anything beyond internal development signals
- reviewed synthetic references are allowed for miss triage and prompt iteration, but not for official quality claims or freeze approval by themselves

## Synthetic Dataset Workflow

Synthetic evaluation data is now supported as a development-only workflow.

Directory layout:

- `eval/synthetic/config/`
- `eval/synthetic/raw/`
- `eval/synthetic/review/`
- `eval/synthetic/approved/`
- `eval/synthetic/manifests/`

Core workflow:

```bash
python -m eval.synthetic.generate --run-name synthetic-dev-001
python -m eval.synthetic.prepare_review --run-name synthetic-dev-001 --raw-path eval/synthetic/raw/synthetic-dev-001.jsonl
python -m eval.synthetic.promote --run-name synthetic-dev-001 --review-path eval/synthetic/review/synthetic-dev-001.jsonl --export-dataset-path eval/datasets/synthetic_dev.jsonl
```

Rules:

- generated cases first land in `raw`
- only schema-valid cases move into `review`
- only `approved` and validation-gated review records move into `approved` or exported evaluator datasets
- synthetic cases are for `dev/regression` use, not final effectiveness claims

## Current Performance Snapshot

Latest expanded Korean live evaluation baseline and follow-up runs are stored under `eval/reports/live/`.

What is currently strong:

- `schema_valid_rate = 1.00`
- `fallback_rate = 0.00`
- `risk_expected_case_recall = 1.00`
- `risk_false_negative_count = 0`
- distortion subset performance remains strong on the curated Korean regression set

What is still weaker:

- `automatic_thought` extraction remains the main recurring bottleneck
- `clarification` quality can improve at the cost of other metrics if prompts are made too aggressive
- recent clarification-focused runs improved `clarification_case_accuracy` but regressed `emotion_label_hit_rate` and overall `needs_clarification_accuracy`

The current evaluation stack should be read as an internal regression harness for prompt and parser iteration, not as clinical-grade evidence of effectiveness.

## Candidate Freeze Rule

The current model should be treated as a `candidate freeze`, not a production freeze.

- official quality judgment must continue to use `expanded-live-eval`
- synthetic reviewed runs are only for internal miss triage
- only misses classified as `model_error` should justify another model tweak
- misses classified as `gold_strictness` or `state_tradeoff` should be resolved in data policy or evaluation interpretation, not by changing the model

Current reviewed synthetic triage is recorded in:

- `eval/reports/triage/synthetic-reviewed-v2-triage.md`
- `eval/reports/triage/synthetic-reviewed-v2-triage.json`
- `eval/reports/triage/candidate-freeze-decision.md`

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

## Regulatory Status

This repository is aligned with FDA/SaMD-friendly engineering principles, but it is not submission-ready medical device software.

Important gaps still remain, including:

- formal requirements traceability
- risk management file / hazard analysis
- larger locked validation datasets
- clinical evaluation package
- QMS and release governance artifacts

Treat the repository as a strong prototype and evaluation scaffold, not a market-ready SaMD package.

## Security Note

- Use `OPENAI_API_KEY` only through environment variables.
- Do not commit API keys or secrets to the repository.
- If a key is ever exposed in chat, logs, screenshots, or shell history, rotate it immediately.

## Status

This repository currently provides a working scaffold and validation baseline for a rule-based CBT reframe engine with optional LLM assistance. It is intended as a controlled treatment-support engine foundation, not as an autonomous therapeutic agent.
