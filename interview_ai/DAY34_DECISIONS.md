# DAY34_DECISIONS.md — Day 34 Follow-Up Engine

Factual log of every judgment call made beyond what the Day 34 prompt
explicitly specified. Conflicts with interview_models.py are noted separately.

---

## Template wording and structure

- **Template placeholder chosen**: `{text}` (referring to `question.text`).
  The prompt showed `'{question.text}'` inline in example strings; in the
  actual implementation these are `str.format()` templates stored in a dict,
  so the placeholder must be a simple name — `{text}` was used consistently
  across every template.

- **Two-tier lookup design**: Templates live in two module-level dicts:
  `_CATEGORY_TEMPLATES` (keyed by `(FollowUpAction, InterviewQuestionCategory)`
  tuple) and `_DEFAULT_TEMPLATES` (keyed by `FollowUpAction` alone).
  `generate_followup_text` tries the category-specific dict first and falls
  back to the default. This keeps all branching in one lookup rather than an
  `if/elif` chain, matching the prompt's "no branching logic duplicated across
  multiple functions" requirement.

- **`_quality_to_action` placement**: Defined at module level as
  `_QUALITY_TO_ACTION` (a `Dict[AnswerQuality, FollowUpAction]`) rather than
  inside `decide_followup_action`. Module-level placement avoids re-creating
  the dict on every call and makes the decision table visible alongside the
  template dicts for easier review. This is a style choice; behaviour is
  identical either way.

---

## Category-specific templates added

The prompt said "vary the template slightly per InterviewQuestionCategory if
you can do so cleanly." The following (action, category) pairs received custom
wording; all others fall through to the default:

| Action                    | Category                         | Variation rationale |
|---------------------------|----------------------------------|---------------------|
| request_clarification     | role_based_technical             | Asks specifically which "technical approach or tool" was meant |
| request_clarification     | role_based_non_technical         | Steers toward a "concrete situation or outcome" |
| request_clarification     | teamwork_culture_fit             | Asks for the candidate's "specific role or contribution" |
| request_elaboration       | role_based_technical             | Invites a "technical step or implementation detail" |
| request_elaboration       | career_goals                     | Anchors elaboration to "the next few years" |
| request_elaboration       | strengths_weaknesses             | Asks how the trait "shaped the way you work" |
| request_example           | role_based_technical             | Asks for a "specific technical example" |
| request_example           | teamwork_culture_fit             | Asks for a "team situation" example |
| request_example           | strengths_weaknesses             | Asks for a "concrete example that illustrates" |
| request_example           | career_goals                     | Asks for "a step you have taken toward" the goal |

Categories **introduction** and **availability** received no category-specific
override: introduction questions are typically one-directional (no follow-up
needed in practice), and availability questions are factual enough that the
default template is adequate. Both categories still work correctly via the
default fallback.

---

## Override check ordering in `build_followup_result`

The prompt specified override checks only inside `decide_followup_action`.
`build_followup_result` also needs to produce a `reason` string that
identifies which branch fired. The reason-string `if/elif` block mirrors the
override order in `decide_followup_action` exactly (eligibility first,
max-attempts second, quality last), so the two stay in sync if either is
updated.

---

## `record_question_asked` — idempotent branch return value

When `question_id` is already present, the function returns
`state.model_copy()` (a new copy with no mutations) rather than the original
`state` reference. Rationale: the prompt instructs callers to use the returned
value; returning a copy rather than the input reference prevents accidental
aliasing by callers who assume they always receive a fresh object. Behaviour
for the test (`"Q1" not in original_state.questions_asked`) is identical
either way.

---

## `record_question_asked` — list construction

The updated `questions_asked` list is built as
`list(state.questions_asked) + [question_id]`. This creates a fresh list
rather than appending to a shared reference, ensuring no mutation of the
original field even in environments where Pydantic's internal list is the
same object as the one passed in.

---

## No conflicts with `interview_models.py`

All field names and types used from `InterviewQuestion` (`question_id`, `text`,
`category`, `phase`, `follow_up_eligible`, `order`) and `InterviewState`
(`questions_asked`, and fields required for construction) match the attached
file exactly. No fields were added to either model.

---

## Logging format

Log lines use `%s` positional interpolation (lazy formatting) consistent with
the `get_logger` formatter already established in `utils/logger.py`. Each INFO
line includes `question_id`, `quality`, and `action` at minimum; override
branches also log the override reason inline.

---

## Test helper `make_state` — type annotation

`make_state` uses the `list[str] | None` union syntax (Python 3.10+ builtin
generics), consistent with Python 3.12.7 as specified in the environment
constraint. `List[str]` from `typing` was deliberately not used in the test
file to match modern style.
