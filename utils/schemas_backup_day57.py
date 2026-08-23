from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


# =========================================================
# ENUMS
# =========================================================

class SkillLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class CompanyType(str, Enum):
    product = "product"
    service = "service"
    startup = "startup"
    mnc = "mnc"
    government = "government"


class EmploymentType(str, Enum):
    fulltime = "fulltime"
    parttime = "parttime"
    internship = "internship"
    contract = "contract"
    freelance = "freelance"


class GradeType(str, Enum):
    cgpa = "cgpa"
    percentage = "percentage"
    grade = "grade"


class EducationLevel(str, Enum):
    high_school = "high_school"
    diploma = "diploma"
    bachelors = "bachelors"
    masters = "masters"
    phd = "phd"
    any = "any"


class JobStatus(str, Enum):
    active = "active"
    paused = "paused"
    closed = "closed"


# =========================================================
# METADATA MODELS
# =========================================================

class ParsingMetadata(BaseModel):
    model_used: str = Field(
        ...,
        description="LLM or parsing model used for extraction"
    )

    parsed_at: str = Field(
        ...,
        description="Timestamp when parsing occurred in ISO format"
    )

    confidence_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score of parsed data"
    )

    parsing_version: str = Field(
        ...,
        description="Version of resume/JD parser"
    )


# =========================================================
# ENTITY 1 - SKILL OBJECT
# =========================================================

class SkillObject(BaseModel):
    name: str = Field(
        ...,
        description="Name of the skill"
    )

    level: SkillLevel = Field(
        ...,
        description="Proficiency level of the skill"
    )

    years_of_experience: float = Field(
        ...,
        ge=0,
        description="Years of experience in the skill"
    )

    is_primary_skill: bool = Field(
        ...,
        description="Whether the skill is a primary/core skill"
    )


# =========================================================
# ENTITY 2 - EXPERIENCE OBJECT
# =========================================================

class ExperienceObject(BaseModel):
    company_name: str = Field(
        ...,
        description="Name of the company"
    )

    role_title: str = Field(
        ...,
        description="Job role/title"
    )

    department: Optional[str] = Field(
        None,
        description="Department within the company"
    )

    company_type: CompanyType = Field(
        ...,
        description="Type of company"
    )

    location: str = Field(
        ...,
        description="Work location"
    )

    employment_type: EmploymentType = Field(
        ...,
        description="Employment type"
    )

    start_date: str = Field(
        ...,
        description='Start date in "YYYY-MM" format'
    )

    end_date: Optional[str] = Field(
        None,
        description='End date in "YYYY-MM" format'
    )

    is_current: bool = Field(
        ...,
        description="Whether this is the current job"
    )

    duration_months: int = Field(
        ...,
        ge=0,
        description="Total duration of employment in months"
    )

    responsibilities: List[str] = Field(
        default_factory=list,
        description="List of job responsibilities"
    )

    technologies_used: List[str] = Field(
        default_factory=list,
        description="Technologies used in this role"
    )

    achievements: List[str] = Field(
        default_factory=list,
        description="Achievements in this role"
    )


# =========================================================
# ENTITY 3 - EDUCATION OBJECT
# =========================================================

class EducationObject(BaseModel):
    degree: str = Field(
        ...,
        description="Degree obtained"
    )

    field_of_study: str = Field(
        ...,
        description="Field of study"
    )

    institution_name: str = Field(
        ...,
        description="Name of institution"
    )

    location: str = Field(
        ...,
        description="Institution location"
    )

    start_year: int = Field(
        ...,
        description="Starting year of education"
    )

    end_year: int = Field(
        ...,
        description="Completion year of education"
    )

    grade: Optional[str] = Field(
        None,
        description="Obtained grade or score"
    )

    grade_type: Optional[GradeType] = Field(
        None,
        description="Type of grading system"
    )

    is_highest_qualification: bool = Field(
        ...,
        description="Whether this is the highest qualification"
    )


# =========================================================
# ENTITY 4 - CERTIFICATION OBJECT
# =========================================================

class CertificationObject(BaseModel):
    name: str = Field(
        ...,
        description="Certification name"
    )

    issuing_organization: str = Field(
        ...,
        description="Organization issuing the certification"
    )

    issue_date: str = Field(
        ...,
        description='Issue date in "YYYY-MM" format'
    )

    expiry_date: Optional[str] = Field(
        None,
        description='Expiry date in "YYYY-MM" format'
    )

    credential_id: Optional[str] = Field(
        None,
        description="Credential identifier"
    )

    is_expired: bool = Field(
        ...,
        description="Whether certification is expired"
    )


# =========================================================
# ENTITY 5 - PROJECT OBJECT
# =========================================================

class ProjectObject(BaseModel):
    project_name: str = Field(
        ...,
        description="Name of the project"
    )

    description: str = Field(
        ...,
        description="Project description"
    )

    technologies_used: List[str] = Field(
        default_factory=list,
        description="Technologies used in the project"
    )

    role: str = Field(
        ...,
        description="Role of the candidate in the project"
    )

    duration_months: Optional[int] = Field(
        None,
        ge=0,
        description="Project duration in months"
    )

    project_url: Optional[str] = Field(
        None,
        description="Project URL or GitHub repository"
    )

    is_live: bool = Field(
        ...,
        description="Whether the project is currently live"
    )

    achievements: List[str] = Field(
        default_factory=list,
        description="Achievements or outcomes of the project"
    )


# =========================================================
# ENTITY 6 - CANDIDATE PROFILE
# =========================================================

class CandidateProfile(BaseModel):
    candidate_id: str = Field(
        ...,
        description="Unique candidate identifier"
    )

    full_name: str = Field(
        ...,
        description="Full name of the candidate"
    )

    email: str = Field(
        ...,
        description="Candidate email address - validated at API layer"
    )

    phone: str = Field(
        ...,
        description="Candidate phone number"
    )

    location: str = Field(
        ...,
        description="Candidate city and state"
    )

    linkedin_url: Optional[str] = Field(
        None,
        description="LinkedIn profile URL"
    )

    portfolio_url: Optional[str] = Field(
        None,
        description="Portfolio website URL"
    )

    github_url: Optional[str] = Field(
        None,
        description="GitHub profile URL"
    )

    total_experience_months: int = Field(
        0,
        ge=0,
        description="Total work experience in months"
    )

    current_role: Optional[str] = Field(
        None,
        description="Current job role"
    )

    current_company: Optional[str] = Field(
        None,
        description="Current company"
    )

    skills: List[SkillObject] = Field(
        default_factory=list,
        description="List of candidate skills"
    )

    experience: List[ExperienceObject] = Field(
        default_factory=list,
        description="List of work experiences"
    )

    education: List[EducationObject] = Field(
        default_factory=list,
        description="Educational qualifications"
    )

    certifications: List[CertificationObject] = Field(
        default_factory=list,
        description="Professional certifications"
    )

    projects: List[ProjectObject] = Field(
        default_factory=list,
        description="Projects completed by the candidate"
    )

    languages_known: List[str] = Field(
        default_factory=list,
        description="Languages known by the candidate"
    )

    expected_salary_inr: Optional[int] = Field(
        None,
        ge=0,
        description="Expected salary in INR"
    )

    notice_period_days: Optional[int] = Field(
        None,
        ge=0,
        description="Notice period in days"
    )

    is_actively_looking: bool = Field(
        ...,
        description="Whether candidate is actively seeking opportunities"
    )

    raw_text: Optional[str] = Field(
        None,
        description="Original raw resume text before parsing"
    )

    parsing_metadata: ParsingMetadata = Field(
        ...,
        description="Resume parsing metadata"
    )

    @model_validator(mode="after")
    def compute_total_experience(self):
        self.total_experience_months = sum(
            exp.duration_months for exp in self.experience
        )
        return self


# =========================================================
# ENTITY 7 - JOB PROFILE
# =========================================================

class ScoringWeights(BaseModel):
    skills: int = Field(
        ...,
        ge=0,
        le=100,
        description="Weight assigned to skills"
    )

    experience: int = Field(
        ...,
        ge=0,
        le=100,
        description="Weight assigned to experience"
    )

    education: int = Field(
        ...,
        ge=0,
        le=100,
        description="Weight assigned to education"
    )

    location: int = Field(
        ...,
        ge=0,
        le=100,
        description="Weight assigned to location"
    )

    @model_validator(mode="after")
    def validate_total_weights(self):
        total = (
            self.skills +
            self.experience +
            self.education +
            self.location
        )

        if total != 100:
            raise ValueError(
                f"Scoring weights must sum to 100. Current sum is {total}"
            )

        return self


class JobProfile(BaseModel):
    job_id: str = Field(
        ...,
        description="Unique job identifier"
    )

    title: str = Field(
        ...,
        description="Job title"
    )

    department: Optional[str] = Field(
    None,
    description="Department name"
    )

    company_name: Optional[str] = Field(
        None,
        description="Company name"
    )

    company_type: Optional[CompanyType] = Field(
        None,
        description="Type of company"
    )

    location: Optional[str] = Field(
        None,
        description="Job location"
    )

    employment_type: Optional[EmploymentType] = Field(
        None,
        description="Employment type"
    )

    salary_min_inr: Optional[int] = Field(
        None,
        ge=0,
        description="Minimum salary in INR"
    )

    salary_max_inr: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum salary in INR"
    )
    required_skills: List[SkillObject] = Field(
        default_factory=list,
        description="Required skills"
    )

    preferred_skills: List[SkillObject] = Field(
        default_factory=list,
        description="Preferred skills"
    )

    must_have_skills: List[str] = Field(
        default_factory=list,
        description="Mandatory skills"
    )

    required_education_level: EducationLevel = Field(
        ...,
        description="Required education qualification"
    )

    required_education_field: List[str] = Field(
        default_factory=list,
        description="Required fields of study"
    )

    responsibilities: List[str] = Field(
        default_factory=list,
        description="Job responsibilities"
    )

    nice_to_have: List[str] = Field(
        default_factory=list,
        description="Optional preferred qualifications"
    )

    shortlist_threshold: float = Field(
        ...,
        ge=0,
        le=100,
        description="Shortlisting threshold percentage"
    )

    scoring_weights: ScoringWeights = Field(
        ...,
        description="Scoring weights configuration"
    )

    jd_raw_text: Optional[str] = Field(
        None,
        description="Original raw job description text"
    )

    parsing_metadata: ParsingMetadata = Field(
        ...,
        description="JD parsing metadata"
    )


if __name__ == "__main__":
    print("Schemas loaded successfully")