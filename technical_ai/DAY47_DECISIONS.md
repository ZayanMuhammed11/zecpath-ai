# Day 47 Decisions — technical_ai/ Technical Answer Scoring Engine

This continues the `technical_ai/` module (new as of Day 46) with a
technical answer scoring engine: `technical_scoring_models.py` and
`technical_scoring_engine.py`. Written in the same style as
`interview_ai/hr_scoring_models.py` and `interview_ai/hr_scoring_engine.py`,
which served as pattern references only — nothing was imported from
`interview_ai/`.

1. **`accuracy` is caller-supplied, never classified from text.**
   This engine does not attempt to determine whether an answer is
   correct. `accuracy` is always a float in [0.0, 1.0] passed in by the
   caller, mirroring the caller-supplied `relevance_score` pattern in
   `interview_ai/hr_scoring_engine.py`. This is the technical-track
   counterpart of the same open platform backlog item covering live
   answer-quality classification (already open for the HR interview
   track's `relevance_score`). Not resolved here, not attempted here.

2. **Decision band thresholds (75/55) match the HR interview engine's
   thresholds** for platform-wide consistency, but the label TEXT is
   deliberately different ("Strong/Moderate/Weak Technical Fit" vs HR's
   "Strong Hire/Consider/Reject") specifically to avoid compounding the
   existing three-way score-label divergence already documented as an
   open platform backlog item — a recruiter should never see two
   differently-scoped "Reject" labels for the same candidate.

3. **No difficulty-based score multiplier was implemented.** A
   candidate's `TechnicalDifficulty` tier affects which QUESTIONS they
   are asked (handled entirely by `technical_question_bank.py`'s
   `applicable_difficulties` filter, built Day 46) — it does NOT
   inflate or adjust the raw 0-100 score an individual answer receives.
   This was a deliberate rejection of a difficulty-based score
   multiplier, to avoid harder-tier questions structurally producing
   inflated scores that hit the 100-point ceiling.

4. **Only `experience_based`, `conceptual`, and `scenario_based` phase
   questions are depth-scored.** `introduction` and `closing` phase
   questions are logistics/rapport-oriented and are excluded from
   scoring by design (`SCORABLE_PHASES`), not by omission.

5. **Marker word lists** (`DEPTH_MARKERS`, `LOGIC_MARKERS`,
   `REAL_WORLD_MARKERS`) are duplicated by value, written fresh for
   this module, not imported from `interview_ai.aptitude_scoring`
   despite the shared ratio-based scoring TECHNIQUE — module isolation
   applies to constants as well as logic.

6. **`get_skill_breakdown` intentionally omits any `skill_domain` with
   zero scored answers** from its output dict, rather than fabricating
   a 0.0 entry — consistent with project-wide no-fabrication precedent.

7. **`round_weights.py` was not available and was not guessed at.**
   The prompt referenced `interview_ai/round_weights.py`'s
   `ROLE_WEIGHTS` assertion pattern as a style precedent, but that file
   was not attached and its exact syntax is unknown. Rather than
   fabricate or guess at unseen code, `technical_scoring_engine.py`
   uses its own simple, self-contained equivalent:
   `assert sum(DEFAULT_WEIGHTS.values()) == 1.0` placed directly after
   the `DEFAULT_WEIGHTS` dict definition. This is noted here as a
   deliberate simplification, per the module isolation / no-fabrication
   rule for this prompt.
