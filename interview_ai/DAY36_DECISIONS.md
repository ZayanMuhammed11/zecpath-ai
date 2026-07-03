# Day 36 Decisions — Confidence & Stress Indicators

- pace_score returns 0.5 (neutral) not 0.0 when duration_seconds <= 0,
  to avoid unfairly penalizing simulated candidates where no real
  timing data is available yet.
- UNCERTAINTY_PHRASES and STRESS_PATTERNS share two entries ("not
  sure", "maybe") — this overlap is intentional and kept because the
  two signals represent conceptually distinct things (knowledge
  confidence vs nervousness), but noted here so any future developer
  does not remove the overlap without understanding the intent.
- detect_surface_contradiction is named with "surface" deliberately —
  it detects linguistic contrast markers ("but", "however") only, not
  semantic contradiction; an answer that internally contradicts
  something said in a previous question is not caught by this check.
- behavioral_score aggregation normalizes all component scores to the
  0-100 scale explicitly before weighting, to avoid the implicit unit
  mismatch present in the manager's reference sample (where
  confidence_score was already 0-100 but sentiment_score and stress
  were 0-1 multiplied by 100 inline).
- The ConfidenceBehaviorScore output from this module is the
  confidence-signal source that Day 34's follow-up engine
  (followup_engine.py) was documented as waiting for (Day 34 backlog
  item #11); the actual wiring of this signal into follow-up decision
  logic is deferred to a later day.
- Word list constants (HESITATION_WORDS, UNCERTAINTY_PHRASES,
  POSITIVE_WORDS, NEGATIVE_WORDS) were copied by value from the
  attached screening_ai files — not by import — consistent with
  interview_ai's module isolation convention.
- The attached screening_ai/confidence_engine.py (post-Day-27) defines
  a single hesitation/filler list, HESITATION_PHRASES, rather than two
  separate lists. HESITATION_WORDS and UNCERTAINTY_PHRASES in
  confidence_analyzer.py were both populated from that single source
  list, since no separate uncertainty-specific list exists upstream.
  This means hesitation_score (regex word-count based) and
  uncertainty_score (membership-count based) currently draw on the
  same vocabulary but score it with different logic, producing two
  related-but-distinct signals from one source list. If screening_ai
  later splits these into two genuinely distinct lists, this module
  should be revisited to copy each value set separately.
- repeated_word_score and hesitation_score/uncertainty_score are
  intentionally independent of each other: a filler word like "um" or
  "uh" is not in HESITATION_WORDS/UNCERTAINTY_PHRASES (those lists
  only contain attached-source phrases such as "not sure", "i think",
  etc.), so filler interjections affect confidence only through the
  repetition and pace sub-scores, not through the hesitation or
  uncertainty sub-scores. This is a known scoping limitation inherited
  from the attached source lists, not a bug in this module.
- duration_seconds is typed as float (not int) throughout this layer,
  matching the prompt's function signatures, even though the
  screening_ai reference implementation used int — this is a
  value-only port, not a structural one.
