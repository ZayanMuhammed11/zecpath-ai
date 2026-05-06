import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger
from config.settings import DEFAULT_WEIGHTS, DEFAULT_SHORTLIST_THRESHOLD

logger = get_logger(__name__)

def test_default_weights_sum():
    """Scoring weights must add up to 100"""
    total = sum(DEFAULT_WEIGHTS.values())
    assert total == 100, f"Weights sum to {total}, expected 100"
    logger.info(f"Weights valid. Total = {total}")

def test_shortlist_threshold_range():
    """Threshold must be between 0 and 100"""
    assert 0 <= DEFAULT_SHORTLIST_THRESHOLD <= 100
    logger.info(f"Threshold valid: {DEFAULT_SHORTLIST_THRESHOLD}")

def test_basic_score_calculation():
    """Test a simple weighted score calculation"""
    candidate_scores = {
        "skills":     80,
        "experience": 70,
        "education":  90,
        "location":   60
    }
    weights = DEFAULT_WEIGHTS
    final_score = sum(
        candidate_scores[k] * weights[k] / 100
        for k in weights
    )
    logger.info(f"Calculated score: {final_score}")
    assert 0 <= final_score <= 100