"""
tests/test_ats_accuracy.py

Standalone ATS accuracy test runner — NOT a pytest suite.
Runs every resume in data/test_profiles/ground_truth.json through the
full API pipeline (upload → parse → poll → score), compares AI shortlist
decisions against human ground truth labels, computes accuracy metrics,
and writes structured results to:
    data/test_profiles/test_results.json
    data/test_profiles/test_results.csv

Prerequisites:
    - FastAPI server running on localhost:8000
    - Redis running on localhost:6379
    - job_profile:{job_id} loaded in Redis via scripts/load_job_profile.py

Run (PowerShell):
    python tests/test_ats_accuracy.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import csv
import json
import os
import time
from datetime import datetime

import requests

from utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "http://localhost:8000"
GROUND_TRUTH_PATH = "data/test_profiles/ground_truth.json"
OUTPUT_JSON_PATH = "data/test_profiles/test_results.json"
OUTPUT_CSV_PATH = "data/test_profiles/test_results.csv"


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------


def upload_resume(resume_file: str, job_id: str, candidate_id: str) -> str | None:
    """
    Upload a resume PDF via multipart POST to /resume/upload.

    Args:
        resume_file:  Local path to the PDF file.
        job_id:       Job ID associated with this scoring run.
        candidate_id: Candidate identifier.

    Returns:
        resume_id string on success, None on any failure.
    """
    url = f"{BASE_URL}/resume/upload"
    try:
        with open(resume_file, "rb") as f:
            files = {"file": (os.path.basename(resume_file), f, "application/pdf")}
            data = {"job_id": job_id, "candidate_id": candidate_id}
            response = requests.post(url, files=files, data=data, timeout=30)

        if response.status_code == 200:
            resume_id: str = response.json().get("resume_id")
            logger.info(
                "Resume uploaded. candidate_id=%s resume_id=%s", candidate_id, resume_id
            )
            return resume_id

        logger.error(
            "Upload failed. candidate_id=%s status=%s body=%s",
            candidate_id,
            response.status_code,
            response.text,
        )
        return None

    except Exception as e:
        logger.error("Upload exception. candidate_id=%s error=%s", candidate_id, e)
        return None


def trigger_parse(resume_id: str, candidate_id: str, job_id: str) -> str | None:
    """
    Trigger resume parsing via POST /resume/parse.

    Args:
        resume_id:    Resume ID returned from upload step.
        candidate_id: Candidate identifier.
        job_id:       Job ID for context.

    Returns:
        rq_job_id string on success, None on failure.
    """
    url = f"{BASE_URL}/resume/parse"
    payload = {
        "resume_id": resume_id,
        "candidate_id": candidate_id,
        "job_id": job_id,
    }
    try:
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            rq_job_id: str = response.json().get("job_id")
            logger.info(
                "Parse triggered. candidate_id=%s rq_job_id=%s",
                candidate_id,
                rq_job_id,
            )
            return rq_job_id

        logger.error(
            "Parse trigger failed. candidate_id=%s status=%s body=%s",
            candidate_id,
            response.status_code,
            response.text,
        )
        return None

    except Exception as e:
        logger.error("Parse trigger exception. candidate_id=%s error=%s", candidate_id, e)
        return None


def poll_until_done(
    rq_job_id: str,
    timeout_seconds: int = 120,
    poll_interval: int = 3,
) -> bool:
    """
    Poll GET /jobs/status/{rq_job_id} until the job finishes or times out.

    Args:
        rq_job_id:       RQ job ID to monitor.
        timeout_seconds: Maximum total wait time before giving up.
        poll_interval:   Seconds between each poll request.

    Returns:
        True when status is "finished", False on "failed" or timeout.
    """
    url = f"{BASE_URL}/jobs/status/{rq_job_id}"
    elapsed = 0

    while elapsed < timeout_seconds:
        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                job_status: str = response.json().get("job_status", "")

                if job_status == "finished":
                    logger.info("Job finished. rq_job_id=%s", rq_job_id)
                    return True

                if job_status == "failed":
                    logger.error("Job failed. rq_job_id=%s", rq_job_id)
                    return False

            time.sleep(poll_interval)
            elapsed += poll_interval

        except Exception as e:
            logger.error("Poll exception. rq_job_id=%s error=%s", rq_job_id, e)
            time.sleep(poll_interval)
            elapsed += poll_interval

    logger.warning(
        "Poll timeout exceeded. rq_job_id=%s timeout=%ss", rq_job_id, timeout_seconds
    )
    return False


def score_candidate(
    candidate_id: str, job_id: str, resume_id: str
) -> dict | None:
    """
    Request ATS scoring via POST /ats/score.

    Args:
        candidate_id: Candidate identifier.
        job_id:       Job to score against.
        resume_id:    Resume ID used during parsing.

    Returns:
        Full score response dict on success, None on failure.
    """
    url = f"{BASE_URL}/ats/score"
    payload = {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "resume_id": resume_id,
    }
    try:
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            logger.info(
                "Score received. candidate_id=%s job_id=%s", candidate_id, job_id
            )
            return response.json()

        logger.error(
            "Scoring failed. candidate_id=%s status=%s body=%s",
            candidate_id,
            response.status_code,
            response.text,
        )
        return None

    except Exception as e:
        logger.error("Score exception. candidate_id=%s error=%s", candidate_id, e)
        return None


def run_pipeline(test_case: dict, job_id: str) -> dict:
    """
    Execute the full upload → parse → poll → score pipeline for one test case.

    On any step failure the pipeline is halted for that candidate, pipeline_success
    is set to False, failure_reason is populated, and a partial result dict is
    returned (remaining fields default to safe values). The test run continues
    with the next candidate — no abort.

    Args:
        test_case: Single entry from ground_truth.json test_cases list.
        job_id:    Job ID from ground_truth.json.

    Returns:
        Result dict with keys:
            candidate_id, category, ground_truth_label,
            ai_shortlisted (bool), ai_score (float),
            ai_match_label (str), must_haves_met (bool),
            sub_scores (dict), pipeline_success (bool),
            failure_reason (str | None)
    """
    candidate_id: str = test_case["candidate_id"]
    resume_file: str = test_case["resume_file"]
    category: str = test_case["category"]
    ground_truth_label: str = test_case["ground_truth_label"]

    base_result: dict = {
        "candidate_id": candidate_id,
        "category": category,
        "ground_truth_label": ground_truth_label,
        "ai_shortlisted": False,
        "ai_score": 0.0,
        "ai_match_label": "",
        "must_haves_met": False,
        "sub_scores": {},
        "pipeline_success": False,
        "failure_reason": None,
    }

    # Step 1: Upload
    resume_id = upload_resume(resume_file, job_id, candidate_id)
    if resume_id is None:
        base_result["failure_reason"] = "upload_failed"
        return base_result

    # Step 2: Trigger parse
    rq_job_id = trigger_parse(resume_id, candidate_id, job_id)
    if rq_job_id is None:
        base_result["failure_reason"] = "parse_trigger_failed"
        return base_result

    # Step 3: Poll until done
    finished = poll_until_done(rq_job_id)
    if not finished:
        base_result["failure_reason"] = "parse_poll_failed_or_timeout"
        return base_result

    # Step 4: Score
    score_response = score_candidate(candidate_id, job_id, resume_id)
    if score_response is None:
        base_result["failure_reason"] = "scoring_failed"
        return base_result

    # All steps succeeded — populate full result
    base_result.update(
        {
            "ai_shortlisted": bool(score_response.get("shortlisted", False)),
            "ai_score": float(score_response.get("final_score", 0.0)),
            "ai_match_label": str(score_response.get("match_label", "")),
            "must_haves_met": bool(score_response.get("must_haves_met", False)),
            "sub_scores": score_response.get("sub_scores", {}),
            "pipeline_success": True,
            "failure_reason": None,
        }
    )
    return base_result


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def compute_confusion_matrix(results: list[dict]) -> dict:
    """
    Build a binary confusion matrix comparing ai_shortlisted vs ground truth.

    Only results where pipeline_success=True are included. Candidates where
    the pipeline failed are counted in skipped_count and excluded from all
    metric calculations.

    Ground truth mapping:
        "shortlist" → True (positive class)
        "rejected"  → False (negative class)

    Args:
        results: List of result dicts from run_pipeline().

    Returns:
        Dict with keys: tp, fp, fn, tn, skipped_count (all int).
    """
    tp = fp = fn = tn = skipped_count = 0

    for r in results:
        if not r["pipeline_success"]:
            skipped_count += 1
            continue

        gt_positive: bool = r["ground_truth_label"] == "shortlist"
        ai_positive: bool = r["ai_shortlisted"]

        if gt_positive and ai_positive:
            tp += 1
        elif not gt_positive and ai_positive:
            fp += 1
        elif gt_positive and not ai_positive:
            fn += 1
        else:
            tn += 1

    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "skipped_count": skipped_count}


def compute_metrics(cm: dict) -> dict:
    """
    Compute precision, recall, accuracy, and F1 from a confusion matrix.

    Division-by-zero cases return 0.0 for the affected metric.

    Args:
        cm: Dict returned by compute_confusion_matrix().

    Returns:
        Dict with keys:
            precision, recall, accuracy, f1 (float, 4 dp)
            total, shortlisted_count, rejected_count (int)
    """
    tp: int = cm["tp"]
    fp: int = cm["fp"]
    fn: int = cm["fn"]
    tn: int = cm["tn"]

    total = tp + fp + fn + tn
    shortlisted_count = tp + fn  # all actual positives
    rejected_count = fp + tn     # all actual negatives

    precision: float = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall: float = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    accuracy: float = (tp + tn) / total if total > 0 else 0.0
    f1: float = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "accuracy": round(accuracy, 4),
        "f1": round(f1, 4),
        "total": total,
        "shortlisted_count": shortlisted_count,
        "rejected_count": rejected_count,
    }


def compute_category_metrics(results: list[dict]) -> dict:
    """
    Compute per-category accuracy for successful pipeline runs only.

    Args:
        results: List of result dicts from run_pipeline().

    Returns:
        Dict keyed by category name:
            { "qe_fresher": {"accuracy": 0.85, "count": 4}, ... }
    """
    category_buckets: dict[str, dict] = {}

    for r in results:
        if not r["pipeline_success"]:
            continue

        cat: str = r["category"]
        if cat not in category_buckets:
            category_buckets[cat] = {"correct": 0, "total": 0}

        gt_positive: bool = r["ground_truth_label"] == "shortlist"
        ai_positive: bool = r["ai_shortlisted"]
        correct: bool = gt_positive == ai_positive

        category_buckets[cat]["correct"] += int(correct)
        category_buckets[cat]["total"] += 1

    category_metrics: dict = {}
    for cat, counts in category_buckets.items():
        acc = counts["correct"] / counts["total"] if counts["total"] > 0 else 0.0
        category_metrics[cat] = {
            "accuracy": round(acc, 4),
            "count": counts["total"],
        }

    return category_metrics


def identify_mismatches(results: list[dict]) -> list[dict]:
    """
    Identify candidates where the AI decision contradicts the ground truth.

    Only successful pipeline runs are considered.

    Args:
        results: List of result dicts from run_pipeline().

    Returns:
        List of dicts, each containing:
            candidate_id, category, ground_truth_label,
            ai_shortlisted, ai_score
    """
    mismatches: list[dict] = []

    for r in results:
        if not r["pipeline_success"]:
            continue

        gt_positive: bool = r["ground_truth_label"] == "shortlist"
        if r["ai_shortlisted"] != gt_positive:
            mismatches.append(
                {
                    "candidate_id": r["candidate_id"],
                    "category": r["category"],
                    "ground_truth_label": r["ground_truth_label"],
                    "ai_shortlisted": r["ai_shortlisted"],
                    "ai_score": r["ai_score"],
                }
            )

    return mismatches


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def save_results_json(
    results: list[dict],
    metrics: dict,
    category_metrics: dict,
    mismatches: list[dict],
    output_path: str,
) -> None:
    """
    Persist the full test run output as a structured JSON file.

    Args:
        results:          List of per-candidate result dicts.
        metrics:          Overall precision/recall/accuracy/f1 dict.
        category_metrics: Per-category accuracy dict.
        mismatches:       List of mismatch dicts.
        output_path:      Destination file path.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    output: dict = {
        "run_timestamp": datetime.utcnow().isoformat(),
        "total_tested": len(results),
        "metrics": metrics,
        "category_metrics": category_metrics,
        "mismatches": mismatches,
        "full_results": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    logger.info("JSON results saved. path=%s", output_path)


def save_results_csv(results: list[dict], output_path: str) -> None:
    """
    Persist per-candidate results as a CSV file.

    Columns: candidate_id, category, ground_truth_label, ai_shortlisted,
             ai_score, ai_match_label, must_haves_met, pipeline_success,
             failure_reason

    Args:
        results:     List of per-candidate result dicts.
        output_path: Destination file path.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fieldnames = [
        "candidate_id",
        "category",
        "ground_truth_label",
        "ai_shortlisted",
        "ai_score",
        "ai_match_label",
        "must_haves_met",
        "pipeline_success",
        "failure_reason",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    logger.info("CSV results saved. path=%s", output_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """
    Orchestrate the full ATS accuracy test run.

    Steps:
        1.  Load ground_truth.json
        2.  Log total test case count
        3.  Run pipeline for each test case
        4-7. Compute confusion matrix, metrics, category metrics, mismatches
        8.  Save JSON and CSV output files
        9.  Print formatted summary to console
        10. Log test run completion
    """
    # 1. Load ground truth
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        ground_truth: dict = json.load(f)

    job_id: str = ground_truth["job_id"]
    test_cases: list[dict] = ground_truth["test_cases"]

    # 2. Log count
    logger.info("ATS accuracy test started. total_cases=%d job_id=%s", len(test_cases), job_id)

    # 3. Run pipelines
    results: list[dict] = []
    for test_case in test_cases:
        logger.info("Running pipeline. candidate_id=%s", test_case["candidate_id"])
        result = run_pipeline(test_case, job_id)
        results.append(result)

    # 4. Confusion matrix
    cm = compute_confusion_matrix(results)

    # 5. Overall metrics
    metrics = compute_metrics(cm)

    # 6. Category metrics
    category_metrics = compute_category_metrics(results)

    # 7. Mismatches
    mismatches = identify_mismatches(results)

    # 8. Save outputs
    save_results_json(results, metrics, category_metrics, mismatches, OUTPUT_JSON_PATH)
    save_results_csv(results, OUTPUT_CSV_PATH)

    # 9. Print summary
    sep = "─" * 45
    all_categories = ["qe_fresher", "qe_mid", "qe_senior", "adjacent_role", "irrelevant"]

    print(f"\n{sep}")
    print("  ATS ACCURACY TEST RESULTS")
    print(sep)
    print(f"  Total tested    : {len(results)}")
    print(f"  Skipped         : {cm['skipped_count']} (pipeline failures)")
    print(sep)
    print(f"  Precision       : {metrics['precision'] * 100:.2f}%")
    print(f"  Recall          : {metrics['recall'] * 100:.2f}%")
    print(f"  Accuracy        : {metrics['accuracy'] * 100:.2f}%")
    print(f"  F1 Score        : {metrics['f1'] * 100:.2f}%")
    print(sep)
    print("  Category Breakdown:")
    for cat in all_categories:
        if cat in category_metrics:
            acc = category_metrics[cat]["accuracy"] * 100
            count = category_metrics[cat]["count"]
            print(f"    {cat:<15}: {acc:.2f}% ({count} cases)")
        else:
            print(f"    {cat:<15}: N/A (0 cases)")
    print(sep)
    print(f"  Mismatches      : {len(mismatches)} cases")
    print(f"  Results saved to: {OUTPUT_JSON_PATH}")
    print(f"{sep}\n")

    # 10. Log completion
    logger.info(
        "ATS accuracy test complete. precision=%.4f recall=%.4f",
        metrics["precision"],
        metrics["recall"],
    )


if __name__ == "__main__":
    main()