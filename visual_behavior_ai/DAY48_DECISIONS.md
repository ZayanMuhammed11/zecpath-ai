# Day 48 Decisions — visual_behavior_ai

1. **No video/webcam/computer-vision logic.** This module contains
   zero video capture, zero webcam processing, and zero
   computer-vision logic of any kind. All four signals consumed by
   `calculate_visual_behavior_score` (`gaze_stability`,
   `head_stability`, `facial_engagement`, `attention_consistency`) are
   caller-supplied placeholders. No signal-extraction pipeline exists
   anywhere in this codebase yet — video interview infrastructure is
   unbuilt.

2. **Module isolation confirmed.** `visual_behavior_ai/` has zero
   imports from `interview_ai/`, `technical_ai/`, `screening_ai/`,
   `ats_engine/`, `scoring/`, or `decision_ai/`. The only intra-module
   import is `visual_behavior_scoring.py` importing from
   `visual_behavior_models.py`. Any shared-looking constant
   (`DEFAULT_WEIGHTS`, the ValueError-on-missing-key pattern) is
   duplicated by value from the conventions established in
   `technical_scoring_engine.py`, never imported from it.

3. **Deliberately unwired.** This module is NOT wired into
   `decision_ai/`, any summary generator, or any other round's
   scoring system this day. It produces one self-contained scoring
   capability only, matching the same "deliberately unwired, single
   day's scope" precedent already established elsewhere in this
   project.

4. **Independent decision-band wording.** `get_visual_behavior_level`'s
   thresholds (80/60/40) and labels ("Highly Engaged" / "Engaged" /
   "Variable Engagement" / "Low Engagement") are deliberately
   independent from both the HR decision bands (Strong Hire/Consider/
   Reject) and technical_ai's bands (Strong/Moderate/Weak Technical
   Fit). This is a conscious mitigation of the project's known
   "three-way score-label divergence" backlog concern, not an
   oversight.

5. **Missing-signal-key handling.** `calculate_visual_behavior_score`
   validates that all four `REQUIRED_SIGNAL_KEYS` are present and
   non-None in the input dict *before* constructing
   `VisualBehaviorSignals`, raising a `ValueError` that names exactly
   which field(s) are missing. This mirrors the ValueError pattern
   from `technical_scoring_engine.py`'s `technical_scoring_pipeline`.
   Out-of-range values (outside `[0.0, 1.0]`) are handled separately —
   by Pydantic's own `Field` constraints on `VisualBehaviorSignals`,
   not by manual range-checking code.

6. **No `random` module.** No use of the `random` module anywhere in
   this module, per the project-wide determinism rule.
