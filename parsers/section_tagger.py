"""
Section Tagger for Zecpath AI Hiring Platform.
Attaches confidence scores and metadata to classified resume sections.
"""

from datetime import datetime, timezone
from utils.logger import get_logger

logger = get_logger(__name__)

CLASSIFIER_VERSION = "v1.0.0"

# Confidence scores per detection method
_CONFIDENCE_MAP: dict[str, float] = {
    "exact_match":  1.0,
    "fuzzy_match":  0.8,
    "all_caps":     0.6,
    "colon_suffix": 0.5,
    "other":        0.0,
    "header":       0.0,
    "prefix_match": 0.9
}


class SectionTagger:
    """
    Converts raw classified sections (from SectionClassifier) into a
    structured, AI-ready dict with confidence scores and tagging metadata.
    """

    def tag(
        self,
        classified_sections: dict[str, list[str]],
        candidate_id: str,
    ) -> dict:
        """
        Tag each section with a confidence score and build the AI-ready output.

        Confidence scoring:
            - 1.0  → exact keyword match
            - 0.8  → fuzzy keyword match
            - 0.6  → ALL CAPS heading rule
            - 0.5  → ends-with-colon rule
            - 0.0  → "other" or "header" (unclassified)

        Args:
            classified_sections: Output of SectionClassifier.classify().
                                  Keys are section names; values are line lists.
                                  The classifier stores detection methods in
                                  classifier._detection_methods if available.
            candidate_id: Unique identifier for the candidate (e.g. "CAND-1001").

        Returns:
            AI-ready dict with candidate_id, sections list, unclassified_content,
            total_sections_found, and tagging_metadata.
        """
        logger.info(
            "Tagging sections for candidate '%s'. Raw sections: %s",
            candidate_id, list(classified_sections.keys())
        )

        tagged_sections: list[dict] = []
        unclassified_lines: list[str] = []
        total_lines_processed: int = 0

        # Pull detection_methods from classifier if attached (best effort)
        detection_methods: dict[str, str] = getattr(
            self, "_injected_detection_methods", {}
        )

        for section_name, lines in classified_sections.items():
            total_lines_processed += len(lines)

            if section_name in ("header", "other"):
                unclassified_lines.extend(lines)
                continue

            # Determine detection method & confidence
            detection_method = detection_methods.get(section_name, "exact_match")
            confidence = _CONFIDENCE_MAP.get(detection_method, 0.5)

            content = "\n".join(line for line in lines if line.strip())
            line_count = len([l for l in lines if l.strip()])

            section_entry = {
                "section":          section_name,
                "content":          content,
                "line_count":       line_count,
                "confidence":       confidence,
                "detection_method": detection_method,
            }
            tagged_sections.append(section_entry)

            logger.debug(
                "Tagged section '%s': lines=%d, confidence=%.1f, method=%s",
                section_name, line_count, confidence, detection_method
            )

        # Header lines also go into unclassified (already handled above)
        unclassified_content = "\n".join(
            line for line in unclassified_lines if line.strip()
        )

        sections_detected = len(tagged_sections)
        tagged_at = datetime.now(timezone.utc).isoformat()

        result = {
            "candidate_id":         candidate_id,
            "total_sections_found": sections_detected,
            "sections":             tagged_sections,
            "unclassified_content": unclassified_content,
            "tagging_metadata": {
                "classifier_version":   CLASSIFIER_VERSION,
                "tagged_at":            tagged_at,
                "total_lines_processed": total_lines_processed,
                "sections_detected":    sections_detected,
            },
        }

        logger.info(
            "Tagging complete for '%s'. Sections found: %d, "
            "Total lines processed: %d",
            candidate_id, sections_detected, total_lines_processed
        )
        return result