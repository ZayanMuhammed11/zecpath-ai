"""
Zecpath AI — Resume Text Extraction Engine
Public API for extracting and cleaning text from PDF and DOCX resume files.
"""

import os
from utils.logger import get_logger
from parsers.pdf_reader import PDFReader
from parsers.docx_reader import DOCXReader
from parsers.text_cleaner import TextCleaner
from parsers.section_classifier import SectionClassifier      # noqa: F401
from parsers.section_tagger import SectionTagger              # noqa: F401

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def extract_resume_text(
    file_path: str,
    save_output: bool = False,
    output_dir: str = "data"
) -> str:
    """
    Full pipeline: detect file type, extract raw text, clean it,
    optionally save to disk, and return the clean text string.

    Args:
        file_path: Path to the resume file (.pdf or .docx).
        save_output: If True, saves cleaned text as a .txt file.
        output_dir: Directory where the .txt output will be saved.

    Returns:
        Clean extracted text string.

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If the file type is not supported.
    """
    logger.info(f"Starting resume extraction pipeline for: {file_path}")

    # Validate file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Resume file not found: {file_path}")

    # Detect file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Supported formats are: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # Step 1: Extract raw text using the appropriate reader
    logger.info(f"Detected file type: {ext} | Selecting reader...")

    if ext == ".pdf":
        reader = PDFReader()
        logger.info("Using PDFReader")
    else:
        reader = DOCXReader()
        logger.info("Using DOCXReader")

    raw_text = reader.extract_text(file_path)
    logger.info(f"Raw text extracted | Length: {len(raw_text)} chars")

    # Step 2: Clean the raw text
    logger.info("Passing raw text to TextCleaner...")
    cleaner = TextCleaner()
    clean_text = cleaner.clean(raw_text)
    logger.info(f"Text cleaning complete | Final length: {len(clean_text)} chars")

    # Step 3: Optionally save output to disk
    if save_output:
        _save_text_output(file_path, clean_text, output_dir)

    logger.info("Resume extraction pipeline complete.")
    return clean_text


def _save_text_output(
    source_file_path: str,
    clean_text: str,
    output_dir: str
) -> None:
    """
    Save cleaned text to a .txt file in the output directory.

    Args:
        source_file_path: Original input file path (used to derive output name).
        clean_text: Cleaned text string to save.
        output_dir: Directory path where output will be saved.
    """
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(source_file_path))[0]
    output_file = os.path.join(output_dir, f"{base_name}.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(clean_text)

    logger.info(f"Cleaned text saved to: {output_file}")
def segment_resume(
    clean_text: str,
    candidate_id: str = "UNKNOWN",
) -> dict:
    """
    Full segmentation pipeline: classify sections then tag with confidence.

    This is the primary entry point for downstream AI modules that need a
    structured, confidence-scored representation of a candidate's resume.

    Args:
        clean_text:   Cleaned resume text produced by extract_resume_text().
        candidate_id: Candidate identifier (e.g. "CAND-1001"). Defaults to
                      "UNKNOWN" when called without an ID.

    Returns:
        AI-ready tagged section dict as produced by SectionTagger.tag().
        Structure::

            {
                "candidate_id": "CAND-1001",
                "total_sections_found": 6,
                "sections": [
                    {
                        "section": "skills",
                        "content": "Python, Django, FastAPI...",
                        "line_count": 5,
                        "confidence": 1.0,
                        "detection_method": "exact_match"
                    },
                    ...
                ],
                "unclassified_content": "...",
                "tagging_metadata": {
                    "classifier_version": "v1.0.0",
                    "tagged_at": "<ISO 8601 timestamp>",
                    "total_lines_processed": 45,
                    "sections_detected": 6
                }
            }
    """
    classifier = SectionClassifier()
    classified = classifier.classify(clean_text)

    tagger = SectionTagger()
    # Inject detection methods from the classifier into the tagger
    # so confidence scores are derived from actual match type.
    tagger._injected_detection_methods = getattr(
        classifier, "_detection_methods", {}
    )

    tagged = tagger.tag(classified, candidate_id)
    return tagged


__all__ = [
    "extract_resume_text",
    "SectionClassifier",
    "SectionTagger",
    "segment_resume",
]