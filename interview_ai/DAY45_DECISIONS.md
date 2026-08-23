# Day 45 Decisions — Full Candidate Journey Demonstration Script

## What this deliverable is

`tests/simulate_full_candidate_journey.py` is a standalone demonstration /
calibration script, run manually via:

```
python -m tests.simulate_full_candidate_journey
```

It is **not** a pytest file and is deliberately excluded from the pytest
suite, matching the Day 40 precedent (`tests/simulate_hr_interview.py`). It
demonstrates the real, already-tested HR interview scoring pipeline
(`interview_ai.hr_scoring_engine.hr_scoring_pipeline`) and the real
cross-round unified scoring pipeline
(`decision_ai.unified_scoring_engine.unified_scoring_pipeline`) running
end-to-end against four hand-authored demo candidate profiles.

## Demo data, not live data

All four candidate profiles (`senior_full_journey`, `mid_partial_journey`,
`fresher_full_journey`, `hesitant_mid_full_journey`) are fixed, hand-authored
dicts defined inline in the script. No random module is used anywhere. The
script is not connected to any live API and does not read, write, or
reference any real candidate data.

## Production-readiness

The script does not claim, anywhere in its docstrings, comments, or printed
output, that it is production-ready, that it is validated against real-world
accuracy, or that it is connected to a live API. It exists solely to
demonstrate the existing, already-implemented scoring pipelines operating
end-to-end on authored data.

## Missing screening_score — exercising the redistribution path

Profile `mid_partial_journey` deliberately sets `screening_score=None`. This
is the first time in this project that decision_ai's proportional
weight-redistribution path (`unified_scoring_engine.redistribute_weights`)
is exercised in a demonstration script, rather than only in unit tests. With
`screening_score` absent, only the `ats` and `hr` round weights are used, and
they are renormalized to sum to 1.0 before the final score is computed. The
script's printed output for this candidate shows `rounds_missing =
['screening']` and a `confidence` rating of `"medium"` (two of three rounds
present), confirming the redistribution path is exercised and not silently
skipped.

## No manager evaluation feedback

No manager evaluation feedback is included in this deliverable, because none
was available at the time this script was written. This script reflects only
the automated scoring pipeline outputs (communication, confidence/behavior,
HR interview scoring, and unified cross-round scoring); it makes no claim
about, and does not attempt to model, human/manager review.

## Two separate `RoleLevel` enums — explicit, non-interchangeable handling

`decision_ai.decision_models.RoleLevel` and
`interview_ai.interview_models.RoleLevel` are two independently-defined
`Enum` classes. Their string values happen to line up
(`"fresher"` / `"mid"` / `"senior"`), but they are not the same class and
must never be used interchangeably — passing an `interview_ai.RoleLevel`
member directly where a `decision_ai.RoleLevel` is expected (or vice versa)
would be a type error even though the enums look identical at a glance.

Each demo profile stores its role level as an `interview_ai.RoleLevel`
member (`InterviewRoleLevel`), since that is what
`hr_scoring_pipeline(..., role_level=...)` expects. When the script needs
the corresponding `decision_ai.RoleLevel` (`DecisionRoleLevel`) to build
`RoundScores` context for `unified_scoring_pipeline`, it is constructed
explicitly and only from the value:

```python
decision_role = DecisionRoleLevel(role_level.value)
```

This explicit, by-value construction is used every time a role level needs
to cross from the interview_ai side of the pipeline to the decision_ai side,
and the two enum instances are never assigned or compared directly against
one another anywhere in the script.
