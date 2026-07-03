# Day 40 Decisions — HR Interview Simulation

- No `random` module is used anywhere in this deliverable. All 4 candidate
  profiles (`confident_senior`, `hesitant_mid`, `inexperienced_fresher`,
  `overqualified_senior`) are fixed, authored synthetic text and metadata,
  consistent with the project-wide determinism requirement.
- Each profile's `EXPECTED_OUTCOME` entry is **our own authored design
  expectation** for how the current scoring weights should behave — it is
  not real human-evaluator ground truth. No accuracy percentage against
  real human judgment is claimed or computable from this data, because no
  real human evaluation data exists for this project.
- Aptitude scoring is intentionally excluded from this simulation. Day 40's
  scope is the HR interview system (communication + confidence/behavior +
  HR scoring + summary), consistent with Day 38/39's explicit decoupling of
  aptitude from HR scoring. `generate_interview_summary` is called with
  `aptitude=None`.
- Any mismatch between actual pipeline output and an authored expectation is
  reported as-is in the script's output — not adjusted, hidden, or explained
  away in code. In the run performed while building this deliverable, 1 of 4
  profiles matched its authored expectation; the other 3 are genuine
  findings about how the current weighting behaves on these inputs (see
  "Simulation run" below).
- The script pattern (standalone, not pytest, invoked via
  `python -m tests.simulate_hr_interview`) mirrors the Day 30
  `tests/simulate_screening.py` precedent.
- No modification was made to any attached file
  (`communication_engine.py`, `confidence_analyzer.py`,
  `behavior_analyzer.py`, `hr_scoring_engine.py`, `hr_weights.py`,
  `interview_models.py`, `summary_generator.py`).

## Simulation run — real, authoritative results (all 14 dependency files present)

All 14 `interview_ai` dependency files referenced by the pipeline
(`communication_engine.py`, `communication_models.py`,
`confidence_analyzer.py`, `confidence_models.py`, `sentiment_engine.py`,
`behavior_rules.py`, `behavior_analyzer.py`, `hr_scoring_engine.py`,
`hr_scoring_models.py`, `hr_weights.py`, `interview_models.py`,
`summary_generator.py`, `summary_models.py`, `aptitude_models.py`) were
supplied in full for this run. `tests/simulate_hr_interview.py` was
executed unmodified against them, end to end, via
`python -m tests.simulate_hr_interview`. The script was verified to be
correctly wired (function signatures, Pydantic field names, and import
paths all match the real modules) with zero changes required. No
reconstructed stand-ins were used anywhere in this run; only a `pydantic`
package install and a minimal `utils/logger.py` shim (not one of the 14
dependency files, never previously attached, contains no scoring logic)
were needed to let the real modules import.

Results below are the actual output of the real pipeline and are now
authoritative for this project.

| candidate_id | communication_score | confidence_score | behavioral_score | contradiction_detected | hr_score | overall_score | actual_decision | expected_decision | result |
|---|---|---|---|---|---|---|---|---|---|
| confident_senior | 100.00 | 92.50 | 86.25 | False | 96.37 | 94.42 | Strong Hire | Strong Hire | MATCH |
| hesitant_mid | 50.00 | 50.00 | 41.00 | True | 49.00 | 46.90 | Reject | Consider | MISMATCH |
| inexperienced_fresher | 92.00 | 92.50 | 86.25 | False | 75.22 | 83.56 | Strong Hire | Consider | MISMATCH |
| overqualified_senior | 100.00 | 92.50 | 86.25 | True | 78.88 | 87.43 | Strong Hire | Consider | MISMATCH |

**1 of 4 profiles matched their authored expectation.** As stated above,
these mismatches are genuine findings about current pipeline behavior, not
errors to be corrected in this deliverable:

- `hesitant_mid`: the answer text contains a contrast marker ("but I'm not
  totally sure"), which triggers `detect_surface_contradiction` — a
  mechanism the authored expectation did not anticipate for this profile.
  Combined with low communication (50.00) and low confidence (50.00), the
  result lands in Reject rather than the authored Consider.
- `inexperienced_fresher`: communication (92.00) and confidence (92.50)
  scored higher than the authored expectation anticipated for a short,
  simple answer, and fresher-level weighting favors communication (0.30),
  producing Strong Hire rather than the authored Consider.
- `overqualified_senior`: the single contrast marker ("However, I sometimes
  found...") did trigger `contradiction_detected=True` as anticipated, and
  did drop the consistency sub-score to 0.3 as described. The magnitude of
  that drop was not enough to move the result out of the Strong Hire band
  (hr_score 78.88, overall 87.43, both above the 75 cutoff) — the mechanism
  fired as expected, but the authored expectation overestimated its size.

No further re-run is needed for this deliverable; this run used the real,
unmodified source for every dependency module.
