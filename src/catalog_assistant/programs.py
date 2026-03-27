from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgramDefinition:
    program_id: str
    name: str
    source_id: str
    source_url: str
    requirement_heading: str
    total_credit_hours: int
    upper_division_hours: int
    free_elective_hours: int
    major_preparatory_courses: tuple[str, ...]
    major_core_courses: tuple[str, ...]
    technical_electives: tuple[str, ...]
    technical_elective_credit_hours: int
    notes: tuple[str, ...]


PROGRAMS: dict[str, ProgramDefinition] = {
    "computer-science": ProgramDefinition(
        program_id="computer-science",
        name="Computer Science (BS)",
        source_id="program_cs_bs",
        source_url="https://catalog.utdallas.edu/2025/undergraduate/programs/ecs/computer-science",
        requirement_heading="II. Major Requirements",
        total_credit_hours=124,
        upper_division_hours=45,
        free_elective_hours=10,
        major_preparatory_courses=(
            "ECS 1100",
            "CS 1200",
            "CS 1337",
            "CS 1436",
            "CS 2305",
            "CS 2336",
            "CS 2340",
            "ECS 2390",
        ),
        major_core_courses=(
            "CS 3162",
            "CS 3341",
            "CS 3345",
            "CS 3354",
            "CS 3377",
            "CS 4141",
            "CS 4337",
            "CS 4341",
            "CS 4347",
            "CS 4348",
            "CS 4349",
            "CS 4384",
            "CS 4485",
        ),
        technical_electives=(
            "CS 4365",
            "CS 4375",
            "CS 4390",
            "SE 4351",
            "SE 4367",
        ),
        technical_elective_credit_hours=12,
        notes=(
            "The catalog requires 12 semester credit hours of major technical electives.",
            "The catalog requires enough upper-division coursework to total 45 upper-division semester credit hours.",
        ),
    ),
    "software-engineering": ProgramDefinition(
        program_id="software-engineering",
        name="Software Engineering (BS)",
        source_id="program_se_bs",
        source_url="https://catalog.utdallas.edu/2025/undergraduate/programs/ecs/software-engineering",
        requirement_heading="II. Major Requirements",
        total_credit_hours=123,
        upper_division_hours=45,
        free_elective_hours=4,
        major_preparatory_courses=(
            "ECS 1100",
            "CS 1200",
            "CS 1337",
            "CS 1436",
            "CS 2305",
            "CS 2336",
            "SE 3306",
            "SE 3354",
            "ECS 2390",
        ),
        major_core_courses=(
            "SE 3162",
            "SE 3306",
            "SE 3341",
            "SE 3345",
            "SE 3354",
            "SE 4347",
            "SE 4348",
            "SE 4351",
            "SE 4352",
            "SE 4367",
            "SE 4381",
            "SE 4485",
        ),
        technical_electives=(
            "CS 4365",
            "CS 4375",
            "CS 4384",
            "CS 4390",
            "SE 4367",
        ),
        technical_elective_credit_hours=12,
        notes=(
            "The catalog requires a guided elective in mathematics and 12 semester credit hours of SE technical electives.",
            "The catalog requires enough upper-division coursework to total 45 upper-division semester credit hours.",
        ),
    ),
}
