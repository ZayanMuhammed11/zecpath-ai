# Day 37 Decisions — HR Interview Scoring Engine

- `relevance_score` is a caller-supplied float placeholder. The
  answer-quality classification layer that will eventually produce
  this value (Day 34 backlog item #9) does not exist yet; this
  design keeps the scorer usable and testable without it.

- `score_consistency` takes explicit bool parameters
  (`contradiction_detected`, `is_vague`) rather than a dict — this
  makes the function self-documenting and testable without
  constructing an answer dict.

- `hr_weights.py` imports `RoleLevel` from
  `interview_ai/interview_models.py`. This is an intentional
  intra-module import within `interview_ai/`, not a cross-module
  boundary violation; it was chosen over duplicating the enum a
  fourth time or using raw strings.

- Three role levels (fresher/mid/senior) are used for weighting,
  rather than the manager sample's two (fresher/experienced) —
  aligned with Day 33's `resolve_role_level()` boundaries.
  `RoleLevel.all_levels` has no dedicated weight entry and falls
  back to `DEFAULT_WEIGHTS` via `get_weights()`.

- `aggregate_hr_scores` uses the arithmetic mean, not a sum —
  explicitly length-normalizing so interview length does not
  inflate or deflate the aggregate score.

- Decision thresholds (`get_hr_decision`): >= 75 → "Strong Hire",
  >= 55 → "Consider", else "Reject". These are fixed constants for
  Day 37 and not yet configurable per role level.

- No cross-module imports were added. `hr_scoring_models.py`,
  `hr_weights.py`, and `hr_scoring_engine.py` only import from
  `interview_ai.interview_models`, `interview_ai.hr_scoring_models`,
  and `interview_ai.hr_weights` as permitted, plus
  `utils.logger.get_logger` per project convention.
