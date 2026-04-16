# Validation Plan

## Verification layers

- Unit tests for the state machine, risk rules, distortion rules, and template composition.
- API contract tests for required response fields and endpoint routing.
- Regression tests using fixed gold phrases for risk and distortion behavior.
- Scenario tests covering full-session behavior and interruption cases.
- Evaluation framework tests for Korean free-text structuring, clarification, distortion top-k recall, and risk false-negative tracking.

## Acceptance criteria

- All API responses expose version metadata and `transition_trace_id`.
- High-risk input interrupts normal flow from any state.
- Missing required slots prevent state advancement.
- State/event payloads are validated against state-specific typed schemas.
- Distortion candidate selection is deterministic for the same input.
- Audit records can reproduce the reasoning path used for a transition.

## Change control

- Any change to rules or templates must update the corresponding version string.
- Regression suites must run against the prior and new rule manifests.
- Audit schema changes require migration notes and backward compatibility review.

## Recommended test scenarios

1. Happy-path GAD session from creation to closure.
2. High-risk disclosure during mid-session event.
3. Out-of-scope adult check failure.
4. Repeated incomplete payload that stays in place.
5. Moderate-risk text that does not close the session but is logged.
6. Static sample evaluation run that produces deterministic summary and case reports.
