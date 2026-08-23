# Day 53 Decisions — hiring_report_ai/

## Module isolation

- Confirmed zero cross-module imports. `hiring_report_ai/` imports only
  from `hiring_report_ai.hiring_report_models` (intra-module) and
  `utils.logger`. All external data (ATS results, unified scores,
  final decisions, interview summaries, technical scores, machine test
  scores, integrity scores, visual behavior scores) is received as
  plain caller-supplied dicts — never as imported Pydantic model
  instances from `decision_ai/`, `final_decision_ai/`, `integrity_ai/`,
  `visual_behavior_ai/`, `interview_ai/`, `technical_ai/`,
  `machine_test_ai/`, `screening_ai/`, `ats_engine/`, or `scoring/`.
  The attached files were used for reference/shape-matching only, to
  get field names right — never for importing.

## No new scoring or thresholding

- This module performs no scoring, thresholding, or re-judgment of any
  kind. Every score and label displayed in a `RoundSummary` (e.g.
  `match_label`, HR `decision`, technical `decision`, machine test
  `decision`) is sourced verbatim from the dict that the owning module
  already produced. `hiring_report_ai` has no knowledge of, and makes
  no assumptions about, how any of those labels or scores were
  computed.
- The one exception is `build_authoritative_recommendation()`, which
  **selects** among two already-computed recommendations rather than
  creating a new judgment. The fallback order is:
  1. `final_decision_ai` (`final_recommendation`) — chosen first
     because it is the most downstream stage in the pipeline and the
     only one that incorporates integrity-risk adjustment (per Day 52
     `final_decision_ai` design).
  2. `decision_ai` (`recommendation`) — used only if no
     `final_decision_data` was supplied, since it is the next-most
     complete cross-round recommendation available (no risk
     adjustment).
  3. `None` / `"none available"` — used only if neither upstream
     recommendation is supplied. In this case individual round labels
     remain visible in `rounds`, but none of them is ever promoted to
     "authoritative" — not ATS `match_label`, not HR `decision`, not
     technical `decision`, not machine test `decision`. Single-round
     labels are single-round-scoped signals, not cross-round hiring
     decisions, and conflating the two was exactly the problem this
     module exists to fix (see backlog items below).

## Backlog items addressed

This module directly addresses two longstanding project backlog
items:

- **#34** — there was previously no unified end-to-end explanation
  spanning a candidate's full hiring journey (ATS → screening → HR →
  technical → machine test → integrity/visual → final decision). The
  `HiringIntelligenceReport`, and specifically its `report_text`
  field, is that unified compilation.
- **#35** — a single candidate could previously receive multiple
  differently-scoped qualitative labels (ATS `match_label`, HR
  `decision`, technical `decision`, machine test `decision`,
  `decision_ai.recommendation`, `final_decision_ai.final_recommendation`)
  with no guidance on which one a recruiter should treat as
  authoritative. The `authoritative_recommendation` section, combined
  with the fixed `supporting_labels_note`, is the resolution
  mechanism: exactly one recommendation is surfaced as the one to act
  on, while every individual round's own label is still shown
  underneath — intentionally not hidden — explicitly framed via
  `SUPPORTING_LABELS_NOTE` as supporting context rather than a
  competing conclusion.

## screening_ai — known gap

- `screening_ai`'s real output shape was not attached for this build.
  Per instructions, only a generic `data.get("screening_score")` key
  is consumed for the screening round; `label_key=None` is passed to
  `build_round_summary`, so no screening label is extracted or
  displayed. This is a known gap, to be closed on a future day once
  the real `screening_ai` output/report field names are attached and
  verified.

## visual_behavior_ai — display only

- `visual_behavior_ai` data (`visual_behavior_score`, `level`) is
  carried through `BehavioralIntegrityNotes` for display only, the
  same precedent set by `final_decision_ai/` on Day 52. It never
  influences `build_authoritative_recommendation()` or any other
  computed value in this module — visual behavior data has no risk or
  scoring semantics.

## Ambiguity resolutions

- **`generate_report_text` signature**: the spec left the exact
  signature to my discretion, requiring only that it be called last,
  built purely from already-assembled report fields, and introduce no
  new value. I implemented it as a function taking the already-built
  `candidate_id`, `job_title`, `rounds`, `authoritative_recommendation`,
  and `highlights` as explicit arguments (rather than a pre-built
  partial `HiringIntelligenceReport` object), since `report_text` is
  itself a field on that model and the model can't be constructed
  before `report_text` exists. This avoids needing a two-phase
  model-then-patch construction while still guaranteeing `report_text`
  is derived strictly from data that is also present elsewhere in the
  final report.
- **`report_text` inclusion of "Risks" but not "Inconsistencies"**:
  the spec's bullet list for `generate_report_text` explicitly names
  "strengths/weaknesses/risks" as the non-empty lists to render, and
  does not mention inconsistencies in that sentence (unlike
  `HighlightsSection`, which does include `inconsistencies` as a
  field). I read this literally: `inconsistencies` is still carried on
  the `HighlightsSection` model in the structured report (per File 2
  spec), but is not rendered into the plain-text `report_text` summary
  bullets, since the spec's `generate_report_text` bullet list did not
  ask for it. Flagging this explicitly since it's a plausible
  omission in the spec rather than a deliberate exclusion — worth
  confirming on a future day.
- **`build_round_summary` for `hr_interview`**: per the spec,
  `hr_summary_data.get("composite")` is computed once in
  `build_hiring_report` and passed as the `data` argument. If
  `hr_summary_data` is supplied but has no `"composite"` key, this
  correctly evaluates to `None`, so the round is
  `included=False` — not a crash, consistent with `build_round_summary`'s
  general whole-round-presence contract.

## No `random` module

- No `random` module import or usage anywhere in this module.
