"""
Synonym Mapper for Zecpath AI hiring platform.
Normalizes role titles and skill names to standard canonical forms.
"""

from utils.logger import get_logger

logger = get_logger(__name__)

ROLE_SYNONYMS = {
    "qa engineer": "Quality Assurance Engineer",
    "qc engineer": "Quality Control Engineer",
    "qe": "Quality Engineer",
    "sqe": "Supplier Quality Engineer",
    "sde": "Supplier Development Engineer",
    "iqc engineer": "Incoming Quality Control Engineer",
    "six sigma bb": "Six Sigma Black Belt",
    "six sigma mbb": "Six Sigma Master Black Belt",
    "quality lead": "Lead Quality Engineer",
    "quality head": "Head of Quality",
    "qa manager": "Quality Assurance Manager",
    "qc manager": "Quality Control Manager",
    "vp quality": "Vice President Quality",
    "kaizen engineer": "Kaizen Specialist",
    "ci engineer": "Continuous Improvement Engineer",
    "ppap specialist": "PPAP Engineer",
    "lean engineer": "Lean Quality Engineer",
}

SKILL_SYNONYMS = {
    "spc": "Statistical Process Control",
    "fmea": "Failure Mode and Effects Analysis",
    "capa": "Corrective and Preventive Action",
    "rca": "Root Cause Analysis",
    "vsm": "Value Stream Mapping",
    "msa": "Measurement System Analysis",
    "doe": "Design of Experiments",
    "apqp": "Advanced Product Quality Planning",
    "ppap": "Production Part Approval Process",
    "qms": "Quality Management System",
    "tqm": "Total Quality Management",
    "7 qc tools": "Seven QC Tools",
    "7qc": "Seven QC Tools",
    "gauge r&r": "Gauge Repeatability and Reproducibility",
    "gr&r": "Gauge Repeatability and Reproducibility",
    "vapt": "Vulnerability Assessment and Penetration Testing",
    "5s": "5S Workplace Organization",
    "8d": "8D Problem Solving",
    "iq/oq/pq": "Validation Lifecycle IQ OQ PQ",
    "dmaic": "Six Sigma DMAIC",
    "dmadv": "Six Sigma DMADV",
    "selenium webdriver": "Selenium",
    "ms excel": "Microsoft Excel",
    "postgres": "PostgreSQL",
    "js": "JavaScript",
    "powerbi": "Power BI",
    "pbi": "Power BI",
}


class SynonymMapper:
    """
    Maps role title and skill name variations to standard canonical forms.
    All lookups are case-insensitive. Unmatched values are returned unchanged.
    """

    def map_role(self, role_title: str) -> str:
        """
        Map a role title to its canonical standard name.

        Args:
            role_title: Raw role title string from LLM output.

        Returns:
            Canonical role title if mapping exists, else original string.
        """
        key = role_title.strip().lower()
        mapped = ROLE_SYNONYMS.get(key)

        if mapped:
            logger.info(f"Role mapped: '{role_title}' -> '{mapped}'")
            return mapped

        return role_title

    def map_skills(self, skills: list) -> list:
        """
        Map skill name variations in a list of skill dicts to canonical names.

        Args:
            skills: List of dicts each containing at minimum a "name" key.

        Returns:
            Same list with skill names replaced by canonical forms where found.
        """
        mapped_skills = []

        for skill in skills:
            original_name = skill.get("name", "")
            key = original_name.strip().lower()
            canonical = SKILL_SYNONYMS.get(key)

            if canonical:
                logger.info(f"Skill mapped: '{original_name}' -> '{canonical}'")
                skill = {**skill, "name": canonical}

            mapped_skills.append(skill)

        return mapped_skills