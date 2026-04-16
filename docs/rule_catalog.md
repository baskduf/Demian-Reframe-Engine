# Rule Catalog

## Risk rules

### High-risk rule families

- `suicidal_intent`: explicit self-harm or suicide intent, plan, means, or preparation.
- `psychotic_expression`: command hallucination language, reality detachment, persecutory certainty, severe disorganization.
- `acute_deterioration`: severe escalation with inability to maintain control, extreme agitation, panic collapse, or total functional shutdown.

### Moderate-risk rule families

- passive death wishes or hopelessness without explicit plan.
- escalating anxiety with major sleep loss or loss of functioning.
- recent self-harm history references without current plan.

### Disposition rules

- Any high-risk rule match forces `risk_level=high` and state `crisis`.
- Any moderate-risk rule match with no high-risk rule gives `risk_level=moderate`.
- Ambiguous but concerning language is escalated upward rather than downgraded.

## Cognitive distortion categories

| Distortion ID | Description | Example cues |
| --- | --- | --- |
| `catastrophizing` | jumps to worst-case outcome | disaster, ruined, terrible, cannot recover |
| `fortune_telling` | predicts negative future as certain | will fail, definitely go wrong |
| `intolerance_of_uncertainty` | cannot accept uncertainty without alarm | cannot handle not knowing |
| `probability_overestimation` | overstates likelihood of threat | probably means something bad is coming |
| `should_statements` | rigid rule or demand language | should, must, have to |
| `mind_reading` | assumes others' thoughts or judgments | they think I am incompetent |
| `overgeneralization` | global conclusion from isolated events | this always happens, everything goes wrong |
| `self_blame` | excessive personal responsibility | it is all my fault |

## State-level rules

### `risk_screen`
- Inputs: checklist fields plus optional free text.
- Output: `RiskAssessment`.
- Transition:
  - `high` -> `crisis`
  - else -> `eligibility_check`

### `eligibility_check`
- Required:
  - `is_adult=true`
  - `target_condition="gad"`
  - exclusion flags absent
- Out-of-scope flags:
  - minor status
  - unsupported condition
  - need for diagnostic interpretation

### `distortion_hypothesis`
- Candidate generation reads `automatic_thought` and `worry_prediction`.
- Rule matches are stored as machine-readable `rule_code`.
- The engine proposes up to 3 candidates: 1 primary and 2 secondary.

### `alternative_thought`
- Inputs:
  - `balanced_view`
  - `coping_statement`
- Composition template:
  - `A more balanced view is: {balanced_view}. A workable next response is: {coping_statement}.`

### `summary_plan`
- Outputs include:
  - key worry
  - selected distortion labels
  - alternative thought
  - optional experiment plan

## Template bundle IDs

- `risk.high`
- `risk.moderate`
- `eligibility.out_of_scope`
- `prompt.situation`
- `prompt.worry`
- `prompt.emotion`
- `prompt.distortion`
- `prompt.evidence_for`
- `prompt.evidence_against`
- `prompt.alternative`
- `prompt.re_rate`
- `prompt.experiment`
- `summary.complete`
