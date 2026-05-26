"""
Semantic similarity scorer for the Zecpath ATS Engine.

Uses TF-IDF vectorisation with cosine similarity to measure how closely
a candidate resume matches a job description. Fully deterministic —
no LLM calls anywhere in this module.

Dependency: pip install scikit-learn --break-system-packages
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.logger import get_logger


class SemanticScorer:
    """
    Computes semantic similarity between resume text and a job description
    using TF-IDF (unigram + bigram) vectorisation and cosine similarity.

    All computation is local and deterministic. No LLM calls are made.
    """

    def __init__(self) -> None:
        """Initialise the logger."""
        self.logger = get_logger(__name__)

    def score(self, resume_text: str, jd_text: str) -> float:
        """
        Compute a percentage semantic similarity score between two text inputs.

        A TfidfVectorizer is fit on both texts simultaneously, producing
        two vectors whose cosine similarity is returned as a 0–100 float.

        Args:
            resume_text: Candidate resume text or any extracted section content.
            jd_text: Raw plain text of the job description.

        Returns:
            Float in the range 0.0–100.0. Returns 0.0 when either input is
            empty, under 20 characters after stripping, or when any internal
            error occurs.
        """
        # Guard: empty or too-short inputs
        if not resume_text or len(resume_text.strip()) < 20:
            self.logger.debug(
                "resume_text is empty or under 20 chars — returning 0.0."
            )
            return 0.0

        if not jd_text or len(jd_text.strip()) < 20:
            self.logger.debug(
                "jd_text is empty or under 20 chars — returning 0.0."
            )
            return 0.0

        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                max_features=500,
                ngram_range=(1, 2),
            )
            tfidf_matrix = vectorizer.fit_transform([resume_text, jd_text])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            raw_score = float(similarity[0][0])
            result = round(raw_score * 100, 2)

            self.logger.debug(
                "Semantic score: %.2f (raw cosine: %.4f).", result, raw_score
            )
            return result

        except Exception as exc:
            self.logger.warning(
                "SemanticScorer.score() failed: %s — returning 0.0.", exc
            )
            return 0.0

    def score_sections(self, segmented_resume: dict, jd_text: str) -> float:
        """
        Score semantic similarity using only the skills and experience sections
        from a segmented resume against the job description text.

        Args:
            segmented_resume: Structured resume dict from the Day 8 segmenter.
                Expected shape: ``{"sections": [{"section": "skills",
                "content": "..."}, ...]}``.
            jd_text: Raw plain text of the job description.

        Returns:
            Float similarity score 0.0–100.0. Returns 0.0 when no skills or
            experience sections are found or when extracted text is too short.
        """
        relevant_sections = {"skills", "experience"}
        sections = segmented_resume.get("sections", [])

        extracted_parts: list[str] = []
        for sec in sections:
            if (
                isinstance(sec, dict)
                and sec.get("section") in relevant_sections
            ):
                content = sec.get("content", "").strip()
                if content:
                    extracted_parts.append(content)

        if not extracted_parts:
            self.logger.debug(
                "score_sections(): no skills or experience sections found "
                "— returning 0.0."
            )
            return 0.0

        combined_text = " ".join(extracted_parts)
        self.logger.debug(
            "score_sections(): extracted %d chars from %d section(s).",
            len(combined_text),
            len(extracted_parts),
        )
        return self.score(combined_text, jd_text)