"""
PDF text extraction module for Zecpath AI hiring platform.
Uses pdfplumber for robust PDF parsing with multi-column support.
"""

import os
import pdfplumber
from utils.logger import get_logger

logger = get_logger(__name__)


class PDFReader:
    """
    Extracts raw text from PDF resumes using pdfplumber.
    Handles multi-column layouts and corrupted files gracefully.
    """

    def extract_text(self, file_path: str) -> str:
        """
        Extract raw text from a PDF file.

        Args:
            file_path: Absolute or relative path to the PDF file.

        Returns:
            Raw extracted text as a single string with pages joined by newlines.

        Raises:
            FileNotFoundError: If the file does not exist at the given path.
            ValueError: If the file is corrupted or cannot be read.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"PDF file not found at path: {file_path}"
            )

        pages_text = []

        try:
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, start=1):
                    page_text = self._extract_page_text(page, page_num)
                    pages_text.append(page_text)

                logger.info(
                    f"PDF extraction successful: {os.path.basename(file_path)} "
                    f"| Pages extracted: {total_pages}"
                )

        except FileNotFoundError:
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to read PDF file '{file_path}'. "
                f"File may be corrupted or password-protected. Error: {e}"
            )

        return "\n".join(pages_text)

    def _extract_page_text(self, page, page_num: int) -> str:
        """
        Extract text from a single PDF page.
        Falls back to alternative settings if primary extraction returns empty.

        Args:
            page: A pdfplumber Page object.
            page_num: The 1-based page number (used for logging).

        Returns:
            Extracted text string from the page.
        """
        # Primary extraction with layout analysis for multi-column support
        text = page.extract_text(
            layout=True,
            x_tolerance=3,
            y_tolerance=3
        )

        if not text or not text.strip():
            logger.warning(
                f"Page {page_num} returned empty text on primary extraction. "
                f"Trying fallback settings."
            )
            # Fallback: looser tolerances for tricky layouts
            text = page.extract_text(
                layout=False,
                x_tolerance=5,
                y_tolerance=5
            )

        if not text or not text.strip():
            logger.warning(f"Page {page_num} is empty after fallback extraction.")
            return ""

        return text