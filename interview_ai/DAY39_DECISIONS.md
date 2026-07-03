# Day 39 Decisions — Interview Summary Generator

- `InterviewSummaryComposite` is explicitly a display/recruiter-summary
  composite only — **not** the platform's future formal Decision
  Service cross-round aggregation (which will include ATS + Aptitude +
  Machine Test). This module does not resolve or preempt that future
  design; it exists solely to satisfy the Day 39 "summarize overall HR
  performance" deliverable.

- `aptitude_score` is carried through on both `InterviewSummaryComposite`
  and `InterviewSummary` for visibility/reporting only and is **never**
  included in the 0.4/0.3/0.3 weighted composite calculation. Day 38's
  boundary (aptitude uncoupled from HR scoring) is preserved unchanged.

- `compute_cultural_fit` replaces manager-sample keyword string-matching
  with a graduated score derived from the existing contradiction-flag
  and consistency-score signals already computed upstream (Day 36/37).
  No new text analysis is introduced in this module.

- `extract_inconsistencies` is explicitly scoped to Day 36's
  surface-level contrast-marker detection only (presence of markers
  like "but"/"however"). It is documented as NOT a semantic/logical
  contradiction analysis, to avoid overstating capability to recruiters
  reading the summary.

- `get_overall_decision` is duplicated by value from
  `hr_scoring_engine`'s band naming/cutoffs (>=75 Strong Hire, >=55
  Consider, else Reject) for display consistency — it is intentionally
  **not imported**, consistent with interview_ai's no-cross-file
  keyword/enum-sharing convention.

- No modification was made to any pre-existing file in `interview_ai/`
  (`hr_scoring_models.py`, `communication_models.py`,
  `confidence_models.py`, `aptitude_models.py`, `communication_engine.py`,
  `hr_scoring_engine.py`, or any other existing module). This deliverable
  only adds `summary_models.py`, `summary_generator.py`, this file, and
  the accompanying test module.
