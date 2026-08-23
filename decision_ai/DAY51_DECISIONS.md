# Day 51 Decisions — decision_ai/ extended from 3 rounds to 5 rounds

This document records the decisions behind extending the Day 41 Unified
Scoring Engine to aggregate 5 rounds (ats, screening, hr, technical,
machine_test) instead of 3 (ats, screening, hr).

## 1. machine_test_ai's domain mismatch is a deliberate, accepted inclusion

Day 50's `machine_test_ai/` module models a generic software-engineering
track rather than the platform's actual Quality Engineering domain. This
mismatch was known at the time this extension was made. Per explicit
platform-owner direction, `machine_test_ai/`'s output **is** to be
included as a first-class round in `decision_ai/`'s cross-round
aggregation regardless of that mismatch.

**This is a deliberate inclusion decision, not an oversight.** The domain
mismatch it carries into hiring decisions is being knowingly accepted per
the platform owner's explicit instruction, not silently absorbed or
overlooked during this extension.

## 2. decision_ai/ remains fully self-contained

No cross-module imports were added to support this extension.
`decision_ai/` still does not import from `technical_ai/`,
`machine_test_ai/`, or any other project module. `RoundScores` continues
to accept `technical_score` and `machine_test_score` as plain
caller-supplied floats — the caller remains responsible for extracting
e.g. `TechnicalInterviewScore.technical_score` or
`MachineTestScore.final_score` before calling into `decision_ai/`. This
mirrors the same self-containment rationale already recorded in
`DAY41_DECISIONS.md` for `RoleLevel`.

## 3. New 5-round ROLE_WEIGHTS table

```python
ROLE_WEIGHTS = {
    RoleLevel.fresher: {
        "ats": 0.15, "screening": 0.20, "hr": 0.25,
        "technical": 0.20, "machine_test": 0.20,
    },
    RoleLevel.mid: {
        "ats": 0.20, "screening": 0.15, "hr": 0.25,
        "technical": 0.25, "machine_test": 0.15,
    },
    RoleLevel.senior: {
        "ats": 0.20, "screening": 0.10, "hr": 0.25,
        "technical": 0.30, "machine_test": 0.15,
    },
}
```

Confirmed row sums (each equals 1.0):

- fresher: 0.15 + 0.20 + 0.25 + 0.20 + 0.20 = **1.00**
- mid: 0.20 + 0.15 + 0.25 + 0.25 + 0.15 = **1.00**
- senior: 0.20 + 0.10 + 0.25 + 0.30 + 0.15 = **1.00**

`DEFAULT_WEIGHTS`, `get_weights()`, and the startup-time sum-to-1.0
assertion loop in `round_weights.py` were left structurally unchanged —
they already operate generically over whatever `ROLE_WEIGHTS` contains
and required no edits to that logic itself, only the table's contents.

## 4. get_confidence() band redefinition — intentional behavior change

`get_confidence()` was rewritten to use **proportion of rounds present
out of 5**, not a raw count against the old 3-round assumption:

| Rounds present | Confidence |
|---|---|
| 5 or 4 | high |
| 3 or 2 | medium |
| 1 | low |

Under the Day 41 3-round version, a raw count mapped directly to a band
(3→high, 2→medium, 1→low). That mapping is no longer meaningful once
there are 5 possible rounds: for example, 2 of 5 rounds present is much
weaker signal than 2 of 3 rounds present, so a raw count would have
overstated confidence for partially-complete 5-round candidates.

**This band redefinition is an intentional, documented behavior change
driven by the round-count increase from 3 to 5 — it is not a defect fix
and there was nothing wrong with the Day 41 3-round version of this
function on its own terms.**

`_ROUND_FIELD_MAP` in `unified_scoring_engine.py` was extended to include
`technical` and `machine_test`. `redistribute_weights()`,
`calculate_unified_score()`, and `generate_reasoning()` already iterate
over this map (or over data derived from it) generically and required
**no changes beyond the map update itself** — no hardcoded round-count
logic was added to any of them. `calculate_hiring_fit()`,
`get_recommendation()`, and the orchestration logic in
`unified_scoring_pipeline()` were likewise left untouched beyond what
naturally follows from the map update; their thresholds and logic are
unchanged.

### Known pre-existing wording artifact (out of scope for this change)

`generate_reasoning()` contains a hardcoded fallback sentence — `"All
three rounds were included with no redistribution needed."` — used when
`rounds_missing` is empty. This string predates Day 51 and now reads as
inaccurate when all 5 rounds are present (it still says "three"). Per
the Day 51 scope (`generate_reasoning()` requires no changes beyond the
`_ROUND_FIELD_MAP` update), this string was **left as-is and not
corrected** in this change. Flagging it here for a future, explicitly
scoped fix rather than fixing it silently as a side effect of this
extension.

## 5. Which Day 41 tests required rewriting, and why

Of the 14 original tests, the following required rewriting because they
hardcoded 3-round weight math or 3-round confidence semantics that are
now invalid under the 5-round model:

- **`test_all_three_rounds_present_mid_role_exact_math`** → renamed
  `test_all_five_rounds_present_mid_role_exact_math`. Its `RoundScores`
  only populated `ats_score`/`screening_score`/`hr_score`; under the new
  model that leaves `technical_score` and `machine_test_score` at their
  `None` default, silently turning "all rounds present" into "3 of 5
  rounds present." Rewritten to populate all 5 fields and recomputed the
  expected `final_score` (81.5) against the new mid weights.
- **`test_missing_one_round_redistributes_and_scores_correctly`** — same
  root cause: the original only populated ats/hr (screening missing),
  which under 5 rounds would now also silently leave technical and
  machine_test missing, changing "1 of 3 missing" into "3 of 5 missing."
  Rewritten to populate ats/hr/technical/machine_test explicitly (only
  screening missing) and recomputed the expected redistributed weights
  and final_score (83.53) against the 0.85 present-weight-sum.
- **`test_get_confidence_maps_round_count_to_level`** → renamed
  `test_get_confidence_maps_proportion_of_five_to_level`. The old test
  only covered 3/2/1-present cases mapped 1:1 to high/medium/low, which
  is exactly the raw-count semantics that `get_confidence()` no longer
  implements. Rewritten to cover all five present-counts (5, 4, 3, 2, 1)
  against the new proportion-of-5 bands.
- **`test_generate_reasoning_reflects_real_computed_data`** — depended on
  the same `round_scores`/`weights`/`breakdown` as the rewritten "all
  rounds present" test, so it was updated in lockstep to use the new
  5-round data and re-verified that `hr` (still the top contributor) and
  the `selected` recommendation still appear in the generated reasoning.
- **`test_generate_reasoning_mentions_missing_rounds`** — same root cause
  as the "missing one round" test: the original ats/hr-only setup would
  now implicitly mean technical and machine_test are missing too.
  Rewritten to reuse the 4-of-5 (screening-only-missing) setup so the
  "missing rounds" callout in the reasoning text is unambiguously about
  screening alone, as originally intended.
- **`test_unified_scoring_pipeline_full_integration`** — its expected
  `final_score` was computed from `ROLE_WEIGHTS[RoleLevel.senior]`
  generically (so it did not silently break), but its `round_scores`
  only populated 3 of 5 fields, again changing "all rounds present, high
  confidence" into a partial-rounds case with lower confidence than
  intended. Rewritten to populate all 5 fields (recomputed final_score
  86.2, confidence "high") to preserve the original "full integration,
  everything present" intent.

The remaining 8 tests (`test_only_one_round_present_full_weight_and_low_confidence`,
`test_all_three_rounds_none_raises_value_error` → renamed
`test_all_rounds_none_raises_value_error` with an unchanged body,
`test_every_role_weight_set_sums_to_one`,
`test_get_weights_matches_each_defined_role_level`,
`test_recommendation_boundary_selected_at_75`,
`test_recommendation_boundary_rejected_and_hold`,
`test_hiring_fit_boundary_excellent_at_80`, and
`test_unified_scoring_pipeline_raises_for_no_rounds`) were re-verified by
hand and required **no logic changes** — they were either already
round-count-agnostic (boundary checks on a plain float score, generic
loops over `ROLE_WEIGHTS`) or already exercised a genuinely single-round
or zero-round edge case whose correct behavior is unaffected by how many
total round slots exist.

## 6. New tests added

Four new tests were added covering 5-round scenarios that were not
previously testable under the 3-round model:

1. `test_all_five_rounds_present_fresher_role_exact_math` — all 5 rounds
   present, fresher role_level, hand-computed `final_score` (71.0),
   `confidence == "high"`.
2. `test_exactly_two_of_five_rounds_present_confidence_medium` — 2 of 5
   rounds present (ats, technical), `confidence == "medium"`,
   redistributed weights hand-verified to sum to 1.0.
3. `test_exactly_three_of_five_rounds_present_confidence_medium` — 3 of
   5 rounds present (ats, hr, technical), `confidence == "medium"`,
   redistributed weights hand-verified to sum to 1.0.
4. `test_pipeline_includes_machine_test_score_contribution` — full
   `unified_scoring_pipeline()` run confirming `machine_test` appears in
   `rounds_included` with a nonzero `weighted_contribution`, and that
   varying `machine_test_score` changes the resulting `final_score`
   (i.e. it is not silently ignored).

Every `ROLE_WEIGHTS` entry summing to 1.0 under the new 5-round table is
already covered by the unchanged, fully generic
`test_every_role_weight_set_sums_to_one` — intentionally not duplicated
as a separate new test, per the instruction to confirm rather than
duplicate.

## 7. Backups

Before making any of the above changes, the pre-Day-51 versions of the
three modified files were backed up as:

- `decision_ai/decision_models_backup_day51.py`
- `decision_ai/round_weights_backup_day51.py`
- `decision_ai/unified_scoring_engine_backup_day51.py`
