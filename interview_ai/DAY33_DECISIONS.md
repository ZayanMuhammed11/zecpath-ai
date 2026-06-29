# interview_ai/DAY33_DECISIONS.md

Audit trail of every implementation decision made beyond what the Day 33
prompt explicitly specified. Reviewed before merging. Factual, brief.

---

## FILE 3 — data/hr_interview_questions.json

**Decision: order values are global-sequential across the entire bank (1–20),
not restarted per phase.**

Reason: A single global counter eliminates ambiguity when questions from
multiple phases are compared or sorted together; `_PHASE_ORDER` in the
manager handles phase sequencing independently of the `order` field, so
per-phase restart would add no value and would require a composite key.

---

## FILE 4 — interview_ai/interview_question_bank.py

**Decision: redis_client is passed as a direct parameter to `save_to_redis`
and `load_from_redis`, NOT stored in `__init__`.**

Reason: The prompt listed this as an explicit decision point. The stateless
approach was chosen over the `screening_ai.QuestionBankManager` pattern
because (a) it removes the need to construct a new manager instance per
Redis client in tests, (b) a `MagicMock` can be passed at the call site
without any constructor boilerplate, and (c) it keeps the manager safe
to reuse across requests with different Redis connections.

---

## FILE 4 — load_from_file error handling

**Decision: raises `ValueError` on the first invalid entry; does NOT skip
and continue the way `screening_ai.QuestionBankManager.load_from_file` does.**

Reason: The prompt explicitly specified "Raise a clear exception if validation
fails on any entry," which directly overrides the skip-and-warn pattern
visible in the attached `question_bank.py`. A bad question in the data file
is a configuration error, not a runtime warning.

---

## FILE 4 — _PHASE_ORDER module-level constant

**Decision: `_PHASE_ORDER` is derived at import time from `enumerate(InterviewPhase)`,
not hardcoded.**

Reason: If `InterviewPhase` ever gains a new member, the sort order updates
automatically without a second edit. The declaration order of the enum IS
the sort key by design (documented in the `InterviewPhase` docstring).

---

## FILE 6 — tests/test_interview_question_bank.py

**Decision: `make_manager()` takes no arguments; redis_client is NOT passed
to the constructor.**

Reason: Follows directly from the stateless-manager decision above. Mirrors
`make_manager()` in `tests/test_question_bank.py` in spirit, adjusted for
the new manager's signature.

**Decision: `test_load_from_file_parses_correctly` asserts count == 20.**

Reason: The JSON bank contains exactly 20 questions as authored. This number
must be updated manually if questions are added or removed from
`data/hr_interview_questions.json`.

---

## Conflict with prior Day 33 output (no attached file — noted for completeness)

A previous generation of these files omitted `interview_ai/__init__.py`,
which broke package imports. The file is now an explicit deliverable
(FILE 1) per the updated prompt. The file is empty, matching the pattern
described for `scoring/__init__.py` and `api/__init__.py`.

---

## No deviations from prompt on the following

- All enums are `str, Enum` subclasses. ✓
- `from utils.logger import get_logger` + `logger = get_logger(__name__)` in
  every non-JSON, non-Markdown file. ✓
- No imports from `screening_ai` anywhere in `interview_ai/`. ✓
- `random` module is not imported or used anywhere. ✓
- Redis key: `interview_question_bank:{job_id}`, no TTL. ✓
- `InterviewState` Redis key pattern documented in model docstring:
  `interview_state:{candidate_id}:{job_id}` — consistent with project
  convention; prompt did not specify a key for `InterviewState` (Day 34+). ✓
