"""
Pytest test suite for Zecpath AI resume extraction engine.
Tests cover PDF reader, DOCX reader, text cleaner, and the main pipeline.
"""

import pytest
from unittest.mock import MagicMock, patch
from utils.logger import get_logger
from parsers.pdf_reader import PDFReader
from parsers.docx_reader import DOCXReader
from parsers.text_cleaner import TextCleaner
from parsers import extract_resume_text

logger = get_logger(__name__)


# ============================================================
# PDF READER TESTS
# ============================================================

def test_pdf_reader_file_not_found():
    """
    Ensure PDFReader raises FileNotFoundError when the
    given file path does not exist on disk.
    """
    logger.info("Running test: test_pdf_reader_file_not_found")
    reader = PDFReader()
    with pytest.raises(FileNotFoundError):
        reader.extract_text("non_existent_resume.pdf")


# ============================================================
# DOCX READER TESTS
# ============================================================

def test_docx_reader_file_not_found():
    """
    Ensure DOCXReader raises FileNotFoundError when the
    given file path does not exist on disk.
    """
    logger.info("Running test: test_docx_reader_file_not_found")
    reader = DOCXReader()
    with pytest.raises(FileNotFoundError):
        reader.extract_text("non_existent_resume.docx")


# ============================================================
# TEXT CLEANER TESTS
# ============================================================

def test_text_cleaner_removes_special_chars():
    """
    Ensure TextCleaner removes null bytes, page breaks,
    non-breaking spaces, and zero-width spaces from input text.
    """
    logger.info("Running test: test_text_cleaner_removes_special_chars")
    raw = "Hello\x00World\x0cThis\xa0is\u200ba\u200ctest\u200d"
    cleaner = TextCleaner()
    result = cleaner.clean(raw)

    assert "\x00" not in result, "Null byte should be removed"
    assert "\x0c" not in result, "Page break should be removed"
    assert "\xa0" not in result, "Non-breaking space should be removed"
    assert "\u200b" not in result, "Zero-width space should be removed"
    assert "\u200c" not in result, "Zero-width non-joiner should be removed"
    assert "\u200d" not in result, "Zero-width joiner should be removed"


def test_text_cleaner_normalizes_bullets():
    """
    Ensure TextCleaner replaces all bullet point variants
    (•, ●, ►, ▪) with "- ".
    """
    logger.info("Running test: test_text_cleaner_normalizes_bullets")
    raw = "• Item one\n● Item two\n► Item three\n▪ Item four"
    cleaner = TextCleaner()
    result = cleaner.clean(raw)

    assert "•" not in result, "Bullet • should be replaced"
    assert "●" not in result, "Bullet ● should be replaced"
    assert "►" not in result, "Bullet ► should be replaced"
    assert "▪" not in result, "Bullet ▪ should be replaced"
    assert result.count("- ") >= 4, "All bullets should become '- '"


def test_text_cleaner_normalizes_whitespace():
    """
    Ensure TextCleaner collapses multiple spaces into one
    and reduces excessive newlines to a maximum of two.
    """
    logger.info("Running test: test_text_cleaner_normalizes_whitespace")
    raw = "Hello    World\n\n\n\n\nNext   Section"
    cleaner = TextCleaner()
    result = cleaner.clean(raw)

    assert "    " not in result, "Multiple spaces should be collapsed"
    assert "\n\n\n" not in result, "More than 2 consecutive newlines not allowed"


def test_text_cleaner_fixes_section_headings():
    """
    Ensure TextCleaner converts ALL-CAPS section headings
    to Title Case.
    """
    logger.info("Running test: test_text_cleaner_fixes_section_headings")
    raw = "WORK EXPERIENCE\nSome company\n\nEDUCATION\nSome university"
    cleaner = TextCleaner()
    result = cleaner.clean(raw)

    assert "Work Experience" in result, "WORK EXPERIENCE should become Work Experience"
    assert "Education" in result, "EDUCATION should become Education"


def test_text_cleaner_removes_noise():
    """
    Ensure TextCleaner removes page number patterns like 'Page 1 of 3'
    and lines of only repeated symbols like '-------------------'.
    """
    logger.info("Running test: test_text_cleaner_removes_noise")
    raw = (
        "John Doe\n"
        "Page 1 of 3\n"
        "-------------------\n"
        "Software Engineer\n"
        "==========="
    )
    cleaner = TextCleaner()
    result = cleaner.clean(raw)

    assert "Page 1 of 3" not in result, "Page number line should be removed"
    assert "-------------------" not in result, "Symbol line should be removed"
    assert "===========" not in result, "Symbol line should be removed"
    assert "John Doe" in result, "Valid content must be preserved"
    assert "Software Engineer" in result, "Valid content must be preserved"


# ============================================================
# MAIN PIPELINE TESTS
# ============================================================

def test_extract_resume_text_unsupported_format():
    """
    Ensure extract_resume_text raises ValueError when given
    an unsupported file type such as .jpg.
    """
    logger.info("Running test: test_extract_resume_text_unsupported_format")

    # We patch os.path.exists to return True so the unsupported
    # format check is reached instead of FileNotFoundError
    with patch("os.path.exists", return_value=True):
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_resume_text("resume_photo.jpg")