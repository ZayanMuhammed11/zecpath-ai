import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger

logger = get_logger(__name__)

def test_logger_works():
    """Test that the logging system is working"""
    logger.info("ATS test logger is working")
    assert True

def test_config_loads():
    """Test that settings load without errors"""
    from config.settings import LLM_MODEL, DEFAULT_SHORTLIST_THRESHOLD
    assert LLM_MODEL is not None
    assert DEFAULT_SHORTLIST_THRESHOLD == 70
    logger.info(f"Config loaded. Model: {LLM_MODEL}, Threshold: {DEFAULT_SHORTLIST_THRESHOLD}")

def test_folder_structure():
    """Test that all required folders exist"""
    required = ["parsers", "ats_engine", "screening_ai",
                "interview_ai", "scoring", "utils", "config"]
    for folder in required:
        assert os.path.isdir(folder), f"Missing folder: {folder}"
        logger.info(f"Folder exists: {folder}")