# Day 46 Decisions — technical_ai/

## 1. New top-level module: `technical_ai/`, confirmed isolated

`technical_ai/` is a new, self-contained top-level module for the
technical interview system. It does **not** import from `interview_ai/`,
`screening_ai/`, `ats_engine/`, or any other existing project module.
This follows the same cross-module isolation convention documented in
`interview_ai/interview_models.py` ("Duplicate enums are intentional;
interview_ai follows the same cross-module isolation rule as ats_engine,
scoring, and screening_ai"). `technical_ai` extends that convention
rather than being an exception to it.

Verified: `technical_ai/technical_interview_models.py` and
`technical_ai/technical_question_bank.py` only import from the Python
standard library, `pydantic`, `utils.logger`, and `technical_ai` itself.

## 2. `TechnicalDifficulty` is a deliberately separate concept from `RoleLevel`

`interview_ai.interview_models.RoleLevel` (fresher / mid / senior /
all_levels, boundaries at 12 and 84 months) governs HR-round question
applicability. `technical_ai.technical_interview_models
.TechnicalDifficulty` (basic / intermediate / advanced, boundaries at 24
and 60 months) governs technical-question progression only.

These two concepts are **not** interchangeable and there is no
conversion function between them anywhere in this module. A candidate's
`RoleLevel` and `TechnicalDifficulty` are computed independently from the
same underlying `total_experience_months` value using two different pure
functions with two different boundary sets — this is intentional, not an
oversight, per the Day 46 task brief's explicit year-based boundaries
(0–2 years → basic, 3–5 years → intermediate, 5+ years → advanced).

## 3. Skill domains map to the platform's three real sectors

`TechnicalSkillDomain` has exactly three members —
`automotive_quality`, `food_safety_systems`, `pharmaceutical_quality` —
matching Zecpath's three real QE sectors (automotive manufacturing, food
safety, pharmaceutical quality), not generic software/tech stacks. The
seed data in `data/technical_interview_questions.json` reflects
sector-real content: IATF 16949 / PPAP / Control Plans / SPC (automotive),
HACCP / GMP / allergen control / audits (food safety), and GMP /
validation protocols (IQ/OQ/PQ) / batch record review / deviation-CAPA
(pharmaceutical).

## 4. No Redis in this module — file-based only

`TechnicalQuestionBankManager` has no `save_to_redis` / `load_from_redis`
methods and no Redis client dependency anywhere in the module. This
mirrors the Day 38 precedent set by
`interview_ai/aptitude_question_bank.py` (`AptitudeQuestionBankManager`),
not the Redis-backed pattern used by `InterviewQuestionBankManager`
(Day 33). Persistence strategy for technical question banks beyond
file-based loading is not decided as part of Day 46.

## 5. `TechnicalInterviewState.current_difficulty` is mutable; the adaptation trigger is out of scope

`TechnicalInterviewState.current_difficulty` is a plain, mutable
`TechnicalDifficulty` field — the model allows an interview's effective
difficulty tier to change mid-interview (e.g., an interview that starts
at `intermediate` could move to `advanced`). However, **this file defines
the state shape only**. No logic that decides *when* or *why*
`current_difficulty` should change is implemented here, and no
`AnswerQuality`-style classification of live technical/video answers
feeds into it in this module.

This is explicitly tied to **open backlog item #13**: the
`AnswerQuality` classification source for live technical/video answers
is still an unresolved platform architectural question. Until that
backlog item is resolved, any mutation of `current_difficulty` after
initial resolution via `resolve_technical_difficulty()` is future work
performed by a not-yet-built engine, not by this module.

## 6. No question-selection engine or state-machine built in Day 46

Day 46 scope is models + a static, deterministic question bank manager
only:

- `technical_ai/technical_interview_models.py` — Pydantic v2 models and
  the pure `resolve_technical_difficulty()` function.
- `technical_ai/technical_question_bank.py` —
  `TechnicalQuestionBankManager`, which loads, validates, wraps, filters,
  and deterministically sorts questions from a static JSON file.

No adaptive interview flow, no conversation engine, and no state-machine
transition logic (mirroring `interview_ai`'s Day 29
`ConversationStateMachine`) was built in this module. Building the
engine that actually drives a live technical interview — including the
`current_difficulty` adaptation signal referenced in item 5 above — is
future work, not Day 46 scope.
