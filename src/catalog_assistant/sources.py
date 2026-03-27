from __future__ import annotations

from dataclasses import dataclass

from .models import normalize_course_code


CATALOG_ROOT = "https://catalog.utdallas.edu/2025/undergraduate"


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    url: str
    doc_type: str
    program: str | None = None
    course_code: str | None = None
    notes: str = ""


def _course_url(course_code: str) -> str:
    slug = normalize_course_code(course_code).replace(" ", "").lower()
    return f"{CATALOG_ROOT}/courses/{slug}"


def _course_source(course_code: str, notes: str = "") -> SourceSpec:
    normalized = normalize_course_code(course_code)
    return SourceSpec(
        source_id=normalized.lower().replace(" ", "_"),
        url=_course_url(normalized),
        doc_type="course",
        course_code=normalized,
        notes=notes or f"Course page for {normalized}.",
    )


SOURCE_SPECS: list[SourceSpec] = [
    SourceSpec(
        source_id="program_cs_bs",
        url=f"{CATALOG_ROOT}/programs/ecs/computer-science",
        doc_type="program",
        program="computer-science",
        notes="Official degree requirements for the BS in Computer Science.",
    ),
    SourceSpec(
        source_id="program_se_bs",
        url=f"{CATALOG_ROOT}/programs/ecs/software-engineering",
        doc_type="program",
        program="software-engineering",
        notes="Official degree requirements for the BS in Software Engineering.",
    ),
    SourceSpec(
        source_id="policy_academic",
        url=f"{CATALOG_ROOT}/policies/academic",
        doc_type="policy",
        notes="Academic policies including GPA, incomplete grades, advising, and transfer-related rules.",
    ),
    SourceSpec(
        source_id="policy_degree_plans",
        url=f"{CATALOG_ROOT}/policies/degree-plans",
        doc_type="policy",
        notes="Degree plan policy and advisor workflow guidance.",
    ),
]


COURSE_CODES = [
    "ECS 1100",
    "CS 1200",
    "CS 1337",
    "CS 1436",
    "CS 2305",
    "CS 2336",
    "CS 2340",
    "ECS 2390",
    "CS 3162",
    "SE 3162",
    "CS 3341",
    "SE 3341",
    "CS 3345",
    "SE 3345",
    "CS 3354",
    "SE 3306",
    "SE 3354",
    "CS 3377",
    "CS 4141",
    "CS 4337",
    "CS 4341",
    "CS 4347",
    "SE 4347",
    "CS 4348",
    "SE 4348",
    "CS 4349",
    "SE 4351",
    "SE 4352",
    "SE 4367",
    "CS 4365",
    "CS 4375",
    "CS 4384",
    "SE 4381",
    "CS 4390",
    "CS 4485",
    "SE 4485",
]


SOURCE_SPECS.extend(
    _course_source(course_code, notes="Course description page used for prerequisite reasoning and planning.")
    for course_code in COURSE_CODES
)

