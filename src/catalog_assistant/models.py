from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def normalize_course_code(value: str) -> str:
    value = value.strip().upper().replace("-", " ")
    if " " not in value and len(value) > 4:
        return f"{value[:2]} {value[2:]}"
    return " ".join(value.split())


class CompletedCourse(BaseModel):
    code: str
    grade: str | None = None
    transfer: bool = False

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        return normalize_course_code(value)

    @field_validator("grade")
    @classmethod
    def _normalize_grade(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else value


class StudentProfile(BaseModel):
    catalog_year: str | None = "2025"
    target_program: Literal["computer-science", "software-engineering"] | None = None
    target_term: str | None = None
    max_courses: int | None = None
    max_credits: int | None = None
    completed_courses: list[CompletedCourse] = Field(default_factory=list)
    in_progress_courses: list[str] = Field(default_factory=list)

    @field_validator("in_progress_courses")
    @classmethod
    def _normalize_in_progress(cls, values: list[str]) -> list[str]:
        return [normalize_course_code(value) for value in values]


class Citation(BaseModel):
    url: str
    heading: str
    chunk_id: str


class AssistantResponse(BaseModel):
    answer_plan: str
    why: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)
    assumptions_not_in_catalog: list[str] = Field(default_factory=list)
    decision: str | None = None
    route: str | None = None


class SectionText(BaseModel):
    heading: str
    text: str


class CourseMetadata(BaseModel):
    code: str | None = None
    title: str | None = None
    credit_hours: int | None = None
    prerequisite_text: str | None = None
    prereq_or_coreq_text: str | None = None
    corequisite_text: str | None = None
    standing_text: str | None = None
    instructor_consent_required: bool = False


class NormalizedSource(BaseModel):
    source_id: str
    url: str
    accessed_on: str
    doc_type: str
    program: str | None = None
    course_code: str | None = None
    notes: str
    title: str
    text: str
    sections: list[SectionText]
    course_metadata: CourseMetadata | None = None


class EvalCase(BaseModel):
    id: str
    category: Literal["prereq_check", "prereq_chain", "program_rule", "not_in_docs"]
    student_profile: StudentProfile
    user_query: str
    expected_decision: str | None = None
    expected_abstain: bool = False
    required_courses_or_rules: list[str] = Field(default_factory=list)


class EvalOutcome(BaseModel):
    case_id: str
    category: str
    decision: str | None
    expected_decision: str | None
    abstained: bool
    expected_abstain: bool
    citation_count: int
    citation_resolvable: bool
    structured_output_valid: bool
    passed_decision_check: bool
    passed_abstain_check: bool
    response: AssistantResponse

