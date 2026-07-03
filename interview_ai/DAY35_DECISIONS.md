# DAY35_DECISIONS.md — Communication Skill Evaluation Module

Audit of judgment calls made during Day 35 implementation that were **not** explicitly
specified in the task prompt — only the gaps filled independently, not a summary of
what was asked.

---

- **`None` input handling in `calculate_communication_score`:** The prompt specified
  handling for empty strings and whitespace-only strings but did not address a `None`
  argument explicitly. The guard `if not text or not text.strip()` was used because
  it short-circuits on `None` (Python truthiness) before `.strip()` is called, avoiding
  an `AttributeError`, while keeping the guard to a single idiomatic line.

- **Regex splitting on `[.!?]` for sentence fragments:** `re.split(r"[.!?]", text)` is
  used consistently across `score_fluency` and `score_grammar`. This produces a trailing
  empty string when the text ends with a terminator (e.g. `"Hello."` → `["Hello", ""]`).
  In `score_fluency` this is benign — empty strings produce zero words and fail the
  `> 3` threshold automatically. In `score_grammar` the fragments list is filtered with
  `if f.strip()` before the average word count is computed, so trailing empties are
  discarded explicitly.

- **factor_b boundary interpretation for `score_grammar`:** The prompt stated "between
  4 and 25 (inclusive)" for the top band, interpreted as `4 <= avg_words <= 25`. The
  middle band was specified as "between 2 and 4 (exclusive of 4)" — implemented as
  `2 <= avg_words < 4` — combined via `or` with "greater than 25 and at most 40" —
  implemented as `25 < avg_words <= 40`. Values below 2 or above 40 fall to the 0.3
  band. These boundaries were adopted verbatim as written.

- **`filler_penalty` uses `re.findall` for occurrence counting:** `len(re.findall(pattern,
  text_lower))` is used rather than a substitution-based counter because `findall`
  directly returns all non-overlapping matches, making the count straightforward and
  readable.

- **Multi-word filler `"you know"` regex behaviour:** `re.escape("you know")` does not
  escape the space in Python 3.7+ (spaces have no special regex meaning), so the
  assembled pattern `r'\byou know\b'` correctly matches the two-word phrase as a whole.
  This mirrors the same `r'\b' + re.escape(word) + r'\b'` pattern style used in
  `screening_ai/stt_processor.py`.

- **`STRUCTURE_KEYWORDS` defined at module level rather than inside the function:** Kept
  at module level for consistency with `FILLER_WORDS` and to allow direct inspection in
  tests and future configuration without entering a function scope.

- **`get_communication_level` implemented as a standalone public function rather than a
  method on `CommunicationScore`:** Keeps Pydantic model classes free of business logic
  and makes the level-mapping function directly testable in isolation without constructing
  a full model instance.

- **`word_count` uses `len(text.split())` without additional strip:** `str.split()` with
  no arguments already handles leading/trailing whitespace and collapses internal runs,
  so no pre-strip is required. The empty-input guard above ensures this line is only
  reached for non-blank text.

- **No `__init__.py` created for `interview_ai/`:** The task prompt did not request one
  and the existing repository structure was not inspected; creating one risks conflicting
  with a pre-existing file. If import resolution fails, an `__init__.py` should be added
  separately.

- **This module deliberately does NOT produce or reference an `AnswerQuality`
  classification.** The existing `AnswerQuality` enum (good / basic / too_short /
  off_topic / no_answer) lives elsewhere in the codebase and concerns content relevance.
  This module is scoped exclusively to communication-quality scoring — fluency, grammar,
  vocabulary, clarity, structure, and filler density — and must not be extended to produce
  relevance or completeness judgments.

- **Speech pace and timing-based scoring was deliberately excluded from this module's
  scope.** Metrics such as words-per-minute, pause duration, and speech rate require raw
  audio timing data unavailable in a plain text string. This computation layer operates
  on text only; pace and timing scoring belongs in a future audio-aware layer that would
  integrate directly with real STT output.
