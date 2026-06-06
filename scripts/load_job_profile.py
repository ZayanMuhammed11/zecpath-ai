"""
scripts/load_job_profile.py

CLI utility to load a parsed JD JSON file into Redis under the key
job_profile:{job_id}. This unblocks POST /ats/score which requires
the job profile to exist in Redis before scoring.

Usage (PowerShell):
    python scripts/load_job_profile.py --jd_file data/jd_parsed/some_jd.json --job_id J001
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse
import json

from api.redis_client import get_redis
from utils.logger import get_logger

logger = get_logger(__name__)


def load_job_profile(jd_file_path: str, job_id: str) -> bool:
    """
    Read a parsed JD JSON file and store it in Redis under job_profile:{job_id}.

    Args:
        jd_file_path: Path to the parsed JD JSON file.
        job_id:       Unique job identifier (e.g. "J001").

    Returns:
        True on success, False on any failure.
    """
    try:
        with open(jd_file_path, "r", encoding="utf-8") as f:
            jd_data = json.load(f)

        redis_client = get_redis()
        redis_key = f"job_profile:{job_id}"
        redis_client.set(redis_key, json.dumps(jd_data))

        logger.info(
            "Job profile loaded into Redis. job_id=%s, file=%s, key=%s",
            job_id,
            jd_file_path,
            redis_key,
        )
        return True

    except FileNotFoundError as e:
        logger.error("JD file not found. path=%s error=%s", jd_file_path, e)
        return False
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in JD file. path=%s error=%s", jd_file_path, e)
        return False
    except Exception as e:
        logger.error(
            "Unexpected error loading job profile. job_id=%s error=%s", job_id, e
        )
        return False


def main() -> None:
    """Parse CLI arguments and invoke load_job_profile."""
    parser = argparse.ArgumentParser(
        description="Load a parsed JD JSON file into Redis for ATS scoring."
    )
    parser.add_argument(
        "--jd_file",
        type=str,
        required=True,
        help="Path to the parsed JD JSON file (e.g. data/jd_parsed/some_jd.json)",
    )
    parser.add_argument(
        "--job_id",
        type=str,
        required=True,
        help="Job ID to store in Redis (e.g. J001)",
    )
    args = parser.parse_args()

    success = load_job_profile(jd_file_path=args.jd_file, job_id=args.job_id)
    if success:
        print(f"[OK] job_profile:{args.job_id} loaded from {args.jd_file}")
    else:
        print(f"[FAILED] Could not load job_profile:{args.job_id}. Check logs.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()