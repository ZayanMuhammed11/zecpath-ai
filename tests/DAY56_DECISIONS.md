# Day 56 Decisions — `tests/simulate_full_system_day56.py`

Location choice: this file lives at the project root as `DAY56_DECISIONS.md`
(not nested under a specific module folder), because this script is an
orchestration layer that touches all 9 modules and isn't owned by any single
one of them — same rationale implied by `simulate_full_candidate_journey.py`
living under `tests/` rather than under `interview_ai/`.

---

## 1. EducationObject workaround (mandatory, per task instructions)

`ats_engine/ats_scorer.py`'s `_score_education()` has a real, confirmed bug:
when `candidate_profile.education` arrives as a list of **plain dicts**, it
tries to rebuild each entry as an `EducationObject` using the fields
`education_level` and `year_of_completion` — neither of which exists on the
real `EducationObject` model in `schemas.py` (the real model requires
`location`, `start_year`, `end_year`, and `is_highest_qualification`, none of
which this remapping supplies). The resulting `pydantic.ValidationError` is
swallowed by a bare `except Exception: continue`, so every dict-shaped
education entry is silently dropped and education is scored as if the
candidate had none.

**`ats_scorer.py` was NOT touched** — fixing it is out of scope for this task
and is tracked separately as a backlog item, per the task instructions.

**Workaround applied:** every candidate's `education` field is populated as a
list of real `utils.schemas.EducationObject` instances (built with the real
fields: `degree`, `field_of_study`, `institution_name`, `location`,
`start_year`, `end_year`, `grade`, `grade_type`, `is_highest_qualification`),
never as plain dicts. Because `isinstance(edu, dict)` is `False` for a real
object, `_score_education()`'s broken dict-remapping branch (the
`if isinstance(edu, dict):` block) is never entered, and the object passes
straight through to `EducationParser.calculate_education_relevance()`
unmodified — the code path this task requires.

For the same reason, `candidate_profile` is passed into `ATSScorer.score()`
as the actual `CandidateProfile` **object** (never `.model_dump()`'d), so
`skills`, `experience`, and `certifications` also arrive as real Pydantic
objects and take the same "real object, not dict" path through
`ats_scorer.py`'s per-field normalization logic.

## 2. Fixed-float screening_score (deliberate, per task instructions)

`run_screening_pipeline()` (screening_ai/) is **not invoked live** anywhere
in this script. Per Day 40/45 project precedent, screening_ai is already
independently validated and proving it again is not this script's job. Each
candidate's `screening_score` is a fixed, hand-authored float chosen to be
roughly consistent with that candidate's overall calibre:

| candidate_id                    | screening_score | rationale (informal) |
|----------------------------------|-----------------|-----------------------|
| senior_full_qe_journey            | 82.0            | strong senior profile |
| mid_partial_qe_journey            | 70.0            | solid mid profile     |
| fresher_qe_journey                 | 42.0            | weak fresher profile  |
| flagged_integrity_qe_journey       | 78.0            | decent mid profile    |

This is stated explicitly here and in the script's module docstring so it is
never mistaken for a live screening_ai result.

## 3. Job profiles — which is real-calibrated vs newly authored

- **automotive_quality** (`build_automotive_job_profile()`): reuses the
  project's own previously-calibrated values — `must_have_skills =
  ["FMEA", "Control Plans", "SPC", "PPAP", "APQP"]`, the same
  `required_skills` list (FMEA, Control Plans, SPC, PPAP, APQP, CAPA, 8D,
  RCA, IATF 16949), and `shortlist_threshold = 40.0` — per the task's stated
  Day 18/Day 23 calibration history. This is the only job profile in this
  script backed by real prior calibration.
- **food_safety_systems** (`build_food_safety_job_profile()`): **newly
  authored** for this script. No prior real calibrated job profile exists
  for this sector on the platform. `required_skills`/`must_have_skills`
  (HACCP, GMP, SQF, ISO 22000, FSSC 22000) were chosen from real QE-domain
  terminology (matching `education_parser.py`'s own `QE_CERTIFICATIONS`
  categories), but the specific weightings and `shortlist_threshold = 45.0`
  are an authored guess, not an independently calibrated value.
- **pharmaceutical_quality** (`build_pharma_job_profile()`): **newly
  authored** for this script, same caveat as above. `required_skills`
  (GMP Pharmaceutical, CAPA, 21 CFR Part 211, IQ-OQ-PQ, GxP) reflect real
  pharma QE terminology, but `shortlist_threshold = 35.0` is an authored
  guess, not calibrated.

## 4. Other gaps, ambiguities, and assumptions resolved explicitly

- **`JobProfile` has no experience-duration fields.** `ats_scorer.py`'s
  `score()` reads `job_profile.get("experience_required_min_months", 0)` and
  `job_profile.get("experience_required_max_months", 9999)`, but the actual
  `utils.schemas.JobProfile` model (attached) has **no such fields at all**.
  Since `job_profile.model_dump()` therefore never contains these keys,
  `.get()` always falls back to its defaults (`0` and `9999`). With
  `min_months == 0`, `_score_experience()`'s duration-score branch always
  evaluates to `duration_score = 1.0` for every candidate in this script,
  regardless of actual tenure — experience discrimination in the final ATS
  score comes entirely from the `relevance_score` component (QE role-title
  match), not from duration. This is a genuine schema/engine mismatch, not
  something this script works around or hides — it is surfaced here as
  found.
- **`CertificationObject` has no `category` field.**
  `EducationParser.calculate_certification_relevance()` expects each
  certification dict to already carry a `category` key (e.g.
  `"methodology"`, `"food_safety"`) — normally populated by a parsing-time
  enrichment step (`_enrich_certification()`) that this script never runs,
  since certifications are hand-authored directly as schema objects. The
  real `utils.schemas.CertificationObject` model has no `category` field to
  begin with, so `cert.model_dump()` never contains one either. Consequence:
  for every candidate in this script, `calculate_certification_relevance()`
  will report `relevant_certifications = 0` and a base
  `certification_relevance_score` of `0.0`, regardless of how relevant the
  candidate's real certifications are — the resulting `cert_score` is driven
  entirely by the flat count bonus (`+5` for 1+ certs, `+10` for 3+ certs) in
  `_score_certifications()`. This is a real, observed limitation of the
  current schema/engine pairing, not a defect in this script, and is
  reported honestly rather than smoothed over (per the project's Day
  30/40/45 "report genuine findings" precedent).
- **`decision_ai.round_weights.get_weights()` internals are not visible to
  this task.** Only `decision_ai/unified_scoring_engine.py` was attached;
  the actual per-role-level base weights it reads from
  `decision_ai.round_weights` were not provided and are not invented here.
  Candidate round-score inputs were deliberately chosen with enough margin
  (e.g. `flagged_integrity_qe_journey`'s ATS/screening/HR/technical/machine
  test scores are all in the high-70s/low-80s) that the qualitative claims
  made in this script's output (e.g. "risk adjustment flips the
  recommendation") hold regardless of the exact undisclosed weight values,
  rather than depending on a specific numeric final_score this script
  cannot independently verify.
- **`interview_ai.behavior_analyzer`, `interview_ai.communication_engine`,
  and their associated models are not attached files.** This script reuses
  them exactly as already proven in the attached
  `tests/simulate_full_candidate_journey.py` reference (same import paths,
  same call signatures: `calculate_communication_score(answer_text)`,
  `analyze_behavior(answer_text, duration_seconds)`), without guessing at
  or modifying their internals.
- **`technical_ai.technical_interview_models.TechnicalSkillDomain` and
  `visual_behavior_ai`/`integrity_ai`'s Pydantic model field names** were
  not attached as separate files. Per the task's own instructions, their
  exact required fields are fully exposed by the attached engine files
  themselves (`REQUIRED_SIGNAL_KEYS`, `REQUIRED_EVENT_KEYS`, and the
  `SCORABLE_PHASES`/skill-domain string values documented in
  `technical_scoring_engine.py`), so no field name was guessed beyond what
  those constants make explicit.
- **`flagged_integrity_qe_journey`'s integrity event counts** were chosen to
  meet or exceed every value in both `EVENT_CAPS` and `WARNING_THRESHOLDS`
  from the attached `integrity_scoring.py` (tab_switch=6, focus_loss=6,
  external_voice=4, gaze_deviation=6 — all strictly above their respective
  caps/thresholds of 5/5/3/5 and 3/3/2/3). This drives a genuine
  `integrity_score = 0.0` / `risk_level = "High Risk"` through the real,
  unmodified formula in `integrity_scoring.py` — it is not a fabricated
  label, and the resulting `-15.0` point penalty in `final_decision_ai` is
  large enough to plausibly move the candidate's `final_recommendation`
  below the base `unified_score.recommendation`'s band, which is the
  required proof-of-chain-function for this candidate. The exact resulting
  labels depend on `decision_ai`'s undisclosed base weights (see above) and
  were not hand-verified against a specific numeric threshold for this
  reason — the summary table in this script's output reports whatever the
  real modules actually compute, without adjustment.
- **No execution in this environment.** This sandbox does not have the
  actual `ats_engine/`, `decision_ai/`, `interview_ai/`, `technical_ai/`,
  `machine_test_ai/`, `visual_behavior_ai/`, `integrity_ai/`,
  `final_decision_ai/`, or `hiring_report_ai/` packages installed (nor their
  third-party dependency, e.g. `groq`, used by the parser classes), and has
  no repo access beyond the files attached to this task. This script is
  therefore authored strictly to the documented interfaces of the attached
  files and could not be run end-to-end here to confirm it executes
  without error. It has not been fabricated or guessed beyond what those
  interfaces specify — anything genuinely undetermined is called out above
  rather than invented.

## 5. AI vs human comparison / accuracy — explicit statement

No real human-evaluator ground truth exists anywhere on this platform except
Sprint 1's already-calibrated 20-candidate ATS test suite. This script does
**not** compute or print any "AI vs human accuracy", "match rate", or
"score correlation" percentage anywhere, in the script or in this document.
Any mismatch between what a given module concludes for these four demo
profiles and what might intuitively be expected is a genuine finding to be
reported honestly, not smoothed over.

## 6. Performance / timing — explicit statement

No per-stage timing, latency, or throughput number is included anywhere in
this script's output. Consistent with Day 42/54 precedent: **not measured**,
no benchmark exists.
