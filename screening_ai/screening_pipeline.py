"""
screening_ai/screening_pipeline.py

Corrected integration pipeline replacing the previous simulation script
(tests/simulate_screening.py, Day 29/30) that manually inspected the STT
status field and silently skipped any result whose status was not
"processed" — completely bypassing the ConversationStateMachine's
retry-budget tracking, skip-with-advance logic, and follow-up branching.
That script short-circuited the flow contract established by Day 24
(stt_processor) and Day 29 (conversation_flow) with no retry counting,
no forced advancement after the budget is exhausted, and no follow-up
detection.

This module is the corrected version: it drives the ConversationStateMachine
properly by feeding every STT result into handle_response() and acting only
on the action string the machine returns, delegating all flow decisions to
the machine itself.

Sprint 2 — Day 29/30 integration gap, ahead of Day 32 handover wiring.
"""

from utils.logger import get_logger

from screening_ai.conversation_flow import ConversationStateMachine
from screening_ai.answer_engine import process_answer
from screening_ai.behavior_report import generate_behavior_report
from screening_ai.report_generator import generate_screening_report
from screening_ai.scoring_engine import score_answer
from screening_ai.stt_processor import clean_transcript

logger = get_logger(__name__)


def run_screening_pipeline(
    candidate_id: str,
    job_id: str,
    qa_pairs: list[dict],
) -> dict:
    """Drive a full screening interview through the state machine and return a report.

    Feeds each qa_pair's audio through the STT pipeline, passes the result
    into the ConversationStateMachine, and for every accepted answer runs the
    answer engine, scoring engine, and behavior report engine. Aggregates all
    results into a screening report augmented with pipeline-level metadata.

    Args:
        candidate_id: Unique identifier of the candidate being screened.
        job_id: Unique identifier of the role the candidate applied for.
        qa_pairs: List of question/answer dicts. Each dict must contain:
            - question_id (str): unique question identifier.
            - audio_text (str): raw transcript text from the STT layer.
            - confidence (float): STT confidence score (0.0–1.0).
            - expected_keywords (list[str] | None): optional keyword list from
              the Day 22 question bank; may be absent from the dict.
            - expected_intent (str | None): optional expected intent label;
              may be absent from the dict.

    Returns:
        The dict produced by generate_screening_report(), augmented with:
            - "skipped_qa_pairs" (int): number of questions the state machine
              skipped due to an exhausted retry budget.
            - "total_qa_pairs" (int): total number of qa_pairs passed in.
            - "behavior_reports" (list[dict]): the full raw list of behavior
              report dicts, one per accepted answer.

    Raises:
        Exception: Any exception raised by generate_screening_report() is
            logged at ERROR level and re-raised to the caller.
    """
    logger.info(
        "run_screening_pipeline entry — candidate_id=%s job_id=%s total_qa_pairs=%d",
        candidate_id,
        job_id,
        len(qa_pairs),
    )

    # -----------------------------------------------------------------------
    # Step 1 — Build the question list for ConversationStateMachine.
    #
    # The constructor accepts a list[dict] whose keys are read via .get()
    # internally (see conversation_flow.py: __init__ docstring and
    # handle_response). The full schema is: question_id, question,
    # follow_up_question, follow_up_trigger, mandatory, importance.
    # Only question_id and follow_up_trigger are actually accessed in the
    # code paths we exercise here; all others default safely to None/falsy
    # when absent. follow_up_trigger is set to False so that accepted answers
    # always return "next" rather than "follow_up" (the caller controls
    # follow-up intent at a higher level than this pipeline).
    # -----------------------------------------------------------------------
    questions: list[dict] = [
        {"question_id": qa["question_id"], "follow_up_trigger": False}
        for qa in qa_pairs
    ]

    # Step 2 — Construct the state machine.
    machine: ConversationStateMachine = ConversationStateMachine(questions)

    # Step 3 — Build an O(1) lookup so we can find the full qa_pair from
    # the question_id the state machine hands us in each iteration.
    qa_by_id: dict[str, dict] = {qa["question_id"]: qa for qa in qa_pairs}

    # Step 4 — Initialise per-run accumulators.
    answers: list[dict] = []
    scores: list[dict] = []
    behavior_reports: list[dict] = []
    skipped_count: int = 0

    # KEY DECISION (a) — Retry and skip bookkeeping are NOT duplicated here.
    # ConversationStateMachine.handle_response() is the single owner of the
    # retry budget: it increments retry_count[question_id] on every call and
    # decides whether to return "retry" (stay on question, no advance) or
    # "skip" (call self.advance() internally, then return). Tracking the same
    # count in this function would create split ownership and would risk a
    # double-advance if we ever called machine.advance() ourselves after the
    # machine already did. This pipeline's only job is to observe the returned
    # action string, increment skipped_count as a summary metric, and collect
    # results for accepted answers — nothing more.

    # TERMINATION GUARANTEE — This while loop is guaranteed to terminate and
    # cannot run forever. ConversationStateMachine tracks retry_count keyed by
    # question_id and increments it on every call to handle_response(). Per
    # conversation_flow.py, MAX_RETRIES = 2: handle_response() returns "retry"
    # only while retry_count[question_id] <= 2 (i.e. the first two bad
    # responses). On the third consecutive bad response to the same question,
    # retry_count becomes 3 (> MAX_RETRIES), so handle_response() calls
    # self.advance() unconditionally and returns "skip" — moving past that
    # question regardless of input quality. A valid response also calls
    # self.advance(). advance() increments current_index; once current_index
    # reaches len(questions), it sets self.completed = True, which causes
    # is_complete() to return True and exits this loop. With a finite question
    # list and at most MAX_RETRIES + 1 (= 3) handle_response() calls per
    # question before forced advancement, the loop always terminates.
    while not machine.is_complete():

        # Step 5a — Fetch the question currently in focus.
        current_question: dict | None = machine.get_current_question()
        if current_question is None:
            # Defensive guard: is_complete() should prevent reaching here, but
            # break if the machine index is somehow out of range.
            break

        # Step 5b — Extract the question_id from the machine's current state.
        question_id: str = current_question["question_id"]

        # Step 5c — Look up the full qa_pair for this question.
        qa: dict = qa_by_id[question_id]

        # Step 5d — Run the STT pre-cleaning pipeline.
        # clean_transcript returns: clean_text, confidence, status, issue.
        # status is one of: "processed" | "silence_detected" | "poor_audio_detected".
        stt_result: dict = clean_transcript(qa["audio_text"], qa["confidence"])

        # Step 5e — Feed the STT result into the state machine.
        # handle_response() returns one of four exact strings:
        #   "retry"     — issue detected, retry budget not yet exhausted; no advance.
        #   "skip"      — issue detected, budget exhausted; machine already advanced.
        #   "follow_up" — valid answer, follow_up_trigger was True; machine advanced.
        #   "next"      — valid answer, no follow-up trigger; machine advanced.
        action: str = machine.handle_response(
            stt_result["status"],
            stt_result["clean_text"],
        )

        # Step 5f — Retry: the machine has decided to re-ask the same question.
        # KEY DECISION (a): handle_response() already incremented retry_count
        # and deliberately did NOT call advance() — do not duplicate either.
        if action == "retry":
            continue

        # Step 5g — Skip: the retry budget for this question is exhausted.
        # KEY DECISION (a): handle_response() already called self.advance()
        # before returning "skip" — calling advance() again here would
        # double-advance, skipping the next question entirely. The only
        # action this pipeline takes is incrementing its own summary counter.
        if action == "skip":
            skipped_count += 1
            continue

        # Step 5h — Answer accepted: action is "follow_up" or "next".
        # Both values signal that stt_processor classified the audio as valid
        # and the state machine recorded the exchange and advanced. Run all
        # three downstream processing layers and collect the results.

        answer_result: dict = process_answer(
            question_id,
            stt_result["clean_text"],
            expected_keywords=qa.get("expected_keywords"),
            expected_intent=qa.get("expected_intent"),
        )

        score_result: dict = score_answer(answer_result)

        behavior_result: dict = generate_behavior_report(
            stt_result["clean_text"],
            duration_seconds=8,
        )

        answers.append(answer_result)
        scores.append(score_result)
        behavior_reports.append(behavior_result)

    # -----------------------------------------------------------------------
    # Step 6 — Aggregate into a screening report.
    # -----------------------------------------------------------------------
    try:
        report: dict = generate_screening_report(
            candidate_id,
            job_id,
            answers,
            scores,
            behavior_reports,
        )
    except Exception as e:
        logger.error(
            "run_screening_pipeline failed at generate_screening_report — "
            "candidate_id=%s job_id=%s error=%s",
            candidate_id,
            job_id,
            e,
        )
        raise

    # -----------------------------------------------------------------------
    # Step 7 — Augment the report with pipeline-level metadata before return.
    #
    # KEY DECISION (b) — "behavior_reports" is stored as the full raw list,
    # not summarised. The Day 30 simulation script accessed
    # report["behavior_reports"][0]["communication_strength"] directly to
    # inspect the first question's communication quality. A future caller will
    # need to perform the same per-entry inspection (e.g. to check any
    # question's communication_strength, confidence_score, or sentiment).
    # Collapsing the list to a single summary value here would permanently
    # destroy that access path for any downstream consumer. The report dict
    # from generate_screening_report() does not include this list, so it must
    # be added explicitly.
    # -----------------------------------------------------------------------
    report["skipped_qa_pairs"] = skipped_count
    report["total_qa_pairs"] = len(qa_pairs)
    report["behavior_reports"] = behavior_reports

    logger.info(
        "run_screening_pipeline exit — candidate_id=%s job_id=%s "
        "skipped_count=%d decision=%s",
        candidate_id,
        job_id,
        skipped_count,
        report.get("decision"),
    )

    return report
