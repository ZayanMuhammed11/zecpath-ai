# Day 38 Decisions — Aptitude Logic Design

Date: Day 38, Sprint 4
Scope: `interview_ai/aptitude_models.py`, `interview_ai/aptitude_question_bank.py`,
`interview_ai/aptitude_scoring.py`, `interview_ai/scenario_evaluator.py`,
`data/aptitude_questions.json`, and associated tests.

## Decisions

- **`AptitudeCategory` duplicated independently.** `interview_models.py`
  was NOT modified. This follows the Day 34 `AnswerQuality` precedent:
  new enums for a new capability are defined in their own models module
  rather than appended to existing shared model files.

- **Aptitude scoring is NOT wired into `hr_scoring_engine.py`.** This is
  deliberate. Cross-round aggregation of aptitude and HR interview scores
  is a future Decision Service concern and is explicitly out of scope for
  Day 38. `aptitude_scoring.py` and `hr_scoring_engine.py` remain
  independent, uncoupled modules today.

- **`REASONING_MARKERS` defined independently from
  `communication_engine.STRUCTURE_KEYWORDS`.** Despite conceptual
  overlap (both are discourse/sequencing markers), the list is
  duplicated by value inside `aptitude_scoring.py`, not imported. This
  is consistent with the project-wide rule that interview_ai submodules
  never share word/phrase lists by import — only by value duplication.

- **Ratio-based scoring replaces the manager sample's 3-tier keyword
  bins throughout** (`aptitude_scoring.py` and `scenario_evaluator.py`).
  Rationale: fixed bins triggered by a single keyword hit were already
  identified as a weakness pattern in Days 30 and 35 — a lone matched
  keyword could push a shallow answer to a top-tier score. Graduated,
  distinct-marker-count ratios (with a length floor on
  `score_problem_solving`) require broader evidence of reasoning quality
  before a high score is reached.

- **Redis storage for the aptitude question bank is deferred.** File-based
  loading only (`AptitudeQuestionBankManager.load_from_file`) is
  implemented today. This mirrors the interim treatment given to the
  Day 33 storage layer choice. Adding `save_to_redis` /
  `load_from_redis` methods (matching `InterviewQuestionBankManager`'s
  pattern) is an explicit Sprint 3 backlog item.

- **`SCENARIO_PATTERNS` is an extensible registry**, not hardcoded
  per-call logic. It is a module-level `dict[str, list[str]]` in
  `scenario_evaluator.py`, seeded with the 3 scenario types used in
  `data/aptitude_questions.json` (`deadline_pressure`, `team_conflict`,
  `learning_agility`). Future days can add new scenario types by adding
  a new registry entry — `evaluate_scenario()` itself does not need to
  change.

## Out of scope for Day 38

- Wiring `aptitude_score` into any composite candidate score.
- Redis persistence for `AptitudeQuestionBank`.
- Additional scenario types beyond the 3 seeded in the registry.
