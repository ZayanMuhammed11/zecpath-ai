# Day 50 Decisions -- machine_test_ai/

## 1. Domain deviation (intentional)

This module intentionally models a generic software-engineering
machine test (coding / debugging tasks) rather than the platform's
established Quality Engineering domain (see `technical_ai/`'s
`TechnicalSkillDomain` enum for that established precedent). This is
per explicit direction from the project owner, for internship
learning purposes only -- it is **not** a design error, and it is
**not** an inconsistency with `technical_ai/`'s QE-sector precedent.
The platform's real target domain remains QE hiring
(automotive/food-safety/pharmaceutical sectors); Day 50 is a
deliberate, scoped exception to that pattern.

## 2. Caller-supplied vs. derived distinction

This module contains no code execution engine, no sandboxing, no
test-runner, and no static-analysis/linting logic anywhere in this
codebase. Every numeric input this module works with falls into
exactly one of two categories, and the two are never blurred together:

- **Real deterministic ratios, computed from caller-supplied raw
  counts/measurements**: `correctness` (from `passed_test_count` /
  `total_test_count`), `efficiency` (from `runtime_seconds` /
  `runtime_baseline_seconds`), and `problem_solving` (from
  `attempts`).
- **A fully opaque caller-supplied judgment score**: `code_quality`
  alone. It cannot be deterministically derived without execution
  tooling or an LLM/human reviewer, neither of which exists in this
  module's scope (or anywhere in the codebase yet). It is passed
  through unchanged.

## 3. Module isolation

Zero imports from `interview_ai/`, `technical_ai/`, `screening_ai/`,
`ats_engine/`, `scoring/`, `decision_ai/`, `visual_behavior_ai/`, or
`integrity_ai/`. `machine_test_scoring.py` only imports from
`machine_test_ai.machine_test_models` (intra-module). Any
shared-looking constant or helper (`_capped_ratio`, `ATTEMPTS_CAP`)
is duplicated by value from the patterns established in
`integrity_ai.integrity_scoring`, never imported cross-module.

## 4. Not wired into decision_ai/ or any other system

This module is deliberately unwired, single day's scope -- the same
precedent already established for `visual_behavior_ai/` (Day 48) and
`integrity_ai/` (Day 49). No `decision_ai/` integration and no other
module integration is performed this day.

## 5. FINAL_SCORE_WEIGHTS is an explicit, stated split

`FINAL_SCORE_WEIGHTS` (`task_score` 0.75 / `time_score` 0.25) is an
explicit, stated weight split, chosen and documented deliberately.
This corrects the reviewed manager sample's unexplained 80/20 blend
of task_score and time_score, which carried no documented rationale.

## 6. Validation approach deviates from technical_ai/integrity_ai

`calculate_machine_test_score` constructs `MachineTestSubmission`
directly from the input dict and lets Pydantic raise its own
`ValidationError` for missing or invalid keys -- it does **not** add a
separate manual missing-key pre-check, unlike
`technical_ai.technical_scoring_pipeline` and
`integrity_ai.calculate_integrity_score`. This is a deliberate,
considered deviation, not an oversight: every field on
`MachineTestSubmission` is unconditionally required with an explicit
`Field` constraint and no optional/None-tolerant semantics, so
Pydantic's own validation error is already sufficiently clear about
which field is missing or invalid.

## 7. Decision thresholds and wording are independently scoped

`get_machine_test_decision`'s thresholds (70 / 45) and its wording
("Strong Practical Fit" / "Moderate Practical Fit" / "Weak Practical
Fit") are independently scoped from every other decision-band label
family on the platform (which use different thresholds, e.g. 75/55
for HR/technical). This is deliberate, as part of the project's
ongoing mitigation of its known multi-label-divergence concern.

## 8. Determinism

No use of the `random` module anywhere in this module.
