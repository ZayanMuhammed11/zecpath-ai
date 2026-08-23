# Day 52 Decisions — Final Recommendation AI (`final_decision_ai/`)

- **Module isolation confirmed.** `final_decision_ai/` has zero
  cross-module imports from `decision_ai/`, `integrity_ai/`,
  `visual_behavior_ai/`, or any other project module. It only imports
  from `final_decision_ai.final_decision_models` (intra-module) and
  `utils.logger`. All external data (unified score, integrity risk
  level, visual behavior score/level) is received as plain
  dicts/floats/strings, never as imported Pydantic model instances
  from other modules.

- **`final_recommendation` deliberately REUSES decision_ai's exact
  vocabulary and thresholds.** It reuses the exact lowercase
  `"selected"` / `"hold"` / `"rejected"` label family and the 75/55
  score thresholds, rather than inventing a new label family, because
  this stage is a *risk adjustment of the same decision*, not a new
  decision axis — the candidate is still being evaluated against the
  same three-way hiring outcome, just on a possibly-penalized score.
  This is the **opposite** choice from Days 48–50's
  `visual_behavior_ai/`, `integrity_ai/`, and `machine_test_ai/`,
  which deliberately used *independent* label families ("Low
  Risk"/"Moderate Risk"/"High Risk", engagement levels, practical-skill
  bands, etc.). Those modules measure genuinely different concepts
  from the hiring decision itself (integrity risk, visual engagement,
  practical skill), so inventing their own label vocabularies was
  correct there. Here, the concept being labeled — "should this
  candidate be selected, held, or rejected" — is unchanged from
  decision_ai's own concept, only the input score has moved, so
  reusing decision_ai's exact bands and wording is the right call.

- **`decision_confidence` is a NEW, distinctly-named, variance-based
  metric.** It is explicitly NOT the same concept as
  `decision_ai.UnifiedScore.confidence`, which is round-presence-based
  (derived from how many of the five hiring rounds were completed).
  `decision_confidence` instead measures how much a candidate's score
  moved as a result of the risk adjustment (`max(scores) - min(scores)`
  over `[base_final_score, adjusted_score]`), banded into high/medium/
  low. The two metrics answer different questions and must not be
  confused with one another — this is stated explicitly here, and in
  the module docstring of `final_decision_engine.py`, to prevent
  future confusion, per the project's known "backlog #35 three-way
  label divergence" concern.

- **`visual_behavior_ai` data is accepted but is PURELY
  informational.** It explicitly does NOT feed into `adjusted_score`
  or `final_recommendation`. This was a deliberate scope decision:
  `visual_behavior_ai`'s "engagement" scale has no risk semantics
  (unlike `integrity_ai`'s `risk_level`, which maps cleanly onto a
  penalty-points scale), so inventing an engagement-to-penalty mapping
  was rejected rather than fabricated. If a future day introduces a
  calibrated engagement-to-risk mapping, that would be a new, explicit
  decision — not something this module should guess at today.

- **No-fabrication rule for missing integrity data.** If
  `integrity_risk_level` is `None`, no penalty is applied, and this is
  explicitly represented in `RiskAdjustment.applied=False`. It is
  never silently defaulted to `"Low Risk"` or any other assumed value.
  `apply_risk_adjustment()` enforces this directly: the `None` branch
  is checked first and returns before any lookup into
  `RISK_PENALTIES` occurs.

- **`RISK_PENALTIES` values (0 / 7 / 15) are placeholder-reasonable
  constants,** not derived from any real calibration data — the same
  status as every other threshold constant introduced across Days
  46–51 of this project (e.g. `integrity_ai`'s `EVENT_CAPS` and
  `WARNING_THRESHOLDS`).

- **No `random` module used anywhere** in `final_decision_ai/`, per
  the project-wide determinism rule.

- **Ambiguity encountered and resolution:** the spec did not state
  whether `apply_risk_adjustment`'s `base_final_score` parameter
  should factor into the `reason` text. Resolved by keeping
  `base_final_score` in the function signature (for API symmetry and
  potential future use) but not referencing it in the `reason` string,
  since the given example reason strings ("Integrity risk level
  'Moderate Risk' applied a 7.0 point penalty.") only reference the
  risk level and penalty, not the base score. The base score is
  instead surfaced separately in `generate_final_reasoning()`'s output
  sentence, where the spec explicitly requires it.
