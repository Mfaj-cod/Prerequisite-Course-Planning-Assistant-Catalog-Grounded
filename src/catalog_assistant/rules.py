from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from .models import CompletedCourse, CourseMetadata, StudentProfile, normalize_course_code
from .utils import dedupe_keep_order, extract_course_codes, grade_meets_requirement


@dataclass
class RuleNode:
    operator: Literal["course", "and", "or", "standing", "consent"]
    value: str | None = None
    children: list["RuleNode"] = field(default_factory=list)


@dataclass
class CourseRule:
    course_code: str
    prerequisite_expr: RuleNode | None = None
    prereq_or_coreq_expr: RuleNode | None = None
    corequisite_expr: RuleNode | None = None
    min_grade_by_course: dict[str, str] = field(default_factory=dict)
    standing_required: str | None = None
    instructor_consent_allowed: bool = False


@dataclass
class EligibilityResult:
    decision: Literal["Eligible", "Not eligible", "Need more info"]
    satisfied: list[str]
    missing: list[str]
    assumptions: list[str]


TOKEN_PATTERN = re.compile(r"\(|\)|\bAND\b|\bOR\b|\bCONSENT\b|\b[A-Z]{2,4}\s?\d{4}\b|\b(?:FRESHMAN|SOPHOMORE|JUNIOR|SENIOR)_STANDING\b", re.IGNORECASE)


class RuleParser:
    def parse_course_rule(self, course_code: str, metadata: CourseMetadata | None) -> CourseRule:
        if metadata is None:
            return CourseRule(course_code=course_code)
        prerequisite_expr = parse_logic_expression(metadata.prerequisite_text or "")
        prereq_or_coreq_expr = parse_logic_expression(metadata.prereq_or_coreq_text or "")
        corequisite_expr = parse_logic_expression(metadata.corequisite_text or "")
        min_grades = {}
        for text in filter(None, [metadata.prerequisite_text, metadata.prereq_or_coreq_text, metadata.corequisite_text]):
            min_grades.update(extract_grade_requirements(text))
        return CourseRule(
            course_code=course_code,
            prerequisite_expr=prerequisite_expr,
            prereq_or_coreq_expr=prereq_or_coreq_expr,
            corequisite_expr=corequisite_expr,
            min_grade_by_course=min_grades,
            standing_required=metadata.standing_text,
            instructor_consent_allowed=metadata.instructor_consent_required,
        )


def extract_grade_requirements(text: str) -> dict[str, str]:
    requirements: dict[str, str] = {}
    group_pattern = re.compile(r"\(([^()]+)\)\s+with a grade of\s+([ABCDF][+-]?)\s+or better", re.IGNORECASE)
    for match in group_pattern.finditer(text):
        group_text, grade = match.groups()
        for code in extract_course_codes(group_text):
            requirements[normalize_course_code(code)] = grade.upper()
    single_pattern = re.compile(r"([A-Z]{2,4}\s?\d{4})\s+with a grade of\s+([ABCDF][+-]?)\s+or better", re.IGNORECASE)
    for match in single_pattern.finditer(text):
        code, grade = match.groups()
        requirements[normalize_course_code(code)] = grade.upper()
    return requirements


def _normalize_expression(text: str) -> str:
    normalized = text.upper()
    normalized = normalized.replace("PREREQUISITES:", "").replace("PREREQUISITE:", "")
    normalized = normalized.replace("PREREQUISITE OR COREQUISITE:", "")
    normalized = normalized.replace("COREQUISITE:", "")
    normalized = re.sub(r"\bWITH A GRADE OF\s+[ABCDF][+-]?\s+OR BETTER\b", "", normalized)
    normalized = re.sub(r"\bOR EQUIVALENT\b", "", normalized)
    normalized = re.sub(r"\bDATA SCIENCE MAJOR\b", "", normalized)
    normalized = re.sub(r"\bCOMPLETION OF ALL LOWER DIVISION COURSEWORK REQUIRED\b", "", normalized)
    normalized = re.sub(r"\bINSTRUCTOR CONSENT REQUIRED\b", " OR CONSENT ", normalized)
    normalized = re.sub(r"\bINSTRUCTOR CONSENT\b", " CONSENT ", normalized)
    normalized = re.sub(r"\b(FRESHMAN|SOPHOMORE|JUNIOR|SENIOR) STANDING\b", r" \1_STANDING ", normalized)
    normalized = normalized.replace(",", " AND ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def parse_logic_expression(text: str) -> RuleNode | None:
    if not text:
        return None
    normalized = _normalize_expression(text)
    if not extract_course_codes(normalized) and "STANDING" not in normalized and "CONSENT" not in normalized:
        return None
    tokens = [match.group(0).strip() for match in TOKEN_PATTERN.finditer(normalized)]
    expanded_tokens: list[str] = []
    for token in tokens:
        if token.endswith("_STANDING") or token == "CONSENT":
            expanded_tokens.append(token.upper())
        elif re.fullmatch(r"[A-Z]{2,4}\s?\d{4}", token, re.IGNORECASE):
            expanded_tokens.append(normalize_course_code(token))
        else:
            expanded_tokens.append(token.upper())
    parser = _ExpressionParser(expanded_tokens)
    return parser.parse()


class _ExpressionParser:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.index = 0

    def parse(self) -> RuleNode | None:
        if not self.tokens:
            return None
        return self._parse_or()

    def _peek(self) -> str | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def _consume(self) -> str:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def _parse_or(self) -> RuleNode | None:
        node = self._parse_and()
        children = [node] if node else []
        while self._peek() == "OR":
            self._consume()
            right = self._parse_and()
            if right:
                children.append(right)
        if not children:
            return None
        if len(children) == 1:
            return children[0]
        return RuleNode(operator="or", children=children)

    def _parse_and(self) -> RuleNode | None:
        node = self._parse_primary()
        children = [node] if node else []
        while self._peek() == "AND":
            self._consume()
            right = self._parse_primary()
            if right:
                children.append(right)
        if not children:
            return None
        if len(children) == 1:
            return children[0]
        return RuleNode(operator="and", children=children)

    def _parse_primary(self) -> RuleNode | None:
        token = self._peek()
        if token is None:
            return None
        if token == "(":
            self._consume()
            node = self._parse_or()
            if self._peek() == ")":
                self._consume()
            return node
        token = self._consume()
        if token == "CONSENT":
            return RuleNode(operator="consent", value="Instructor consent")
        if token.endswith("_STANDING"):
            return RuleNode(operator="standing", value=token.replace("_STANDING", "").title() + " standing")
        if re.fullmatch(r"[A-Z]{2,4}\s\d{4}", token):
            return RuleNode(operator="course", value=normalize_course_code(token))
        return None


def evaluate_rule(rule: CourseRule, profile: StudentProfile, allow_in_progress_for_coreq: bool = True) -> EligibilityResult:
    completed = {course.code: course for course in profile.completed_courses}
    in_progress = set(profile.in_progress_courses)
    satisfied: list[str] = []
    missing: list[str] = []
    assumptions: list[str] = []

    prereq_ok = _evaluate_expr(rule.prerequisite_expr, completed, in_progress, rule.min_grade_by_course, False, satisfied, missing)
    prereq_or_coreq_ok = _evaluate_expr(rule.prereq_or_coreq_expr, completed, in_progress, rule.min_grade_by_course, allow_in_progress_for_coreq, satisfied, missing)
    coreq_ok = _evaluate_expr(rule.corequisite_expr, completed, in_progress, rule.min_grade_by_course, allow_in_progress_for_coreq, satisfied, missing)

    if rule.standing_required:
        assumptions.append(f"{rule.standing_required} is required and cannot be verified from the provided profile.")
        missing.append(rule.standing_required)
    if rule.instructor_consent_allowed:
        assumptions.append("Instructor consent may provide an exception path, but the catalog does not let me verify whether that approval exists.")

    if prereq_ok is False or prereq_or_coreq_ok is False or coreq_ok is False:
        decision = "Not eligible"
    elif rule.standing_required:
        decision = "Need more info"
    elif prereq_ok is None or prereq_or_coreq_ok is None or coreq_ok is None:
        decision = "Need more info"
    else:
        decision = "Eligible"
    return EligibilityResult(
        decision=decision,
        satisfied=dedupe_keep_order(satisfied),
        missing=dedupe_keep_order(missing),
        assumptions=dedupe_keep_order(assumptions),
    )


def _evaluate_expr(
    node: RuleNode | None,
    completed: dict[str, CompletedCourse],
    in_progress: set[str],
    min_grades: dict[str, str],
    allow_in_progress: bool,
    satisfied: list[str],
    missing: list[str],
) -> bool | None:
    if node is None:
        return True
    if node.operator == "course":
        code = normalize_course_code(node.value or "")
        if code in completed:
            grade_check = grade_meets_requirement(completed[code].grade, min_grades.get(code))
            if grade_check is True:
                satisfied.append(code)
                return True
            if grade_check is None:
                missing.append(f"grade for {code}")
                return None
            missing.append(f"{code} with at least {min_grades.get(code)}")
            return False
        if allow_in_progress and code in in_progress:
            satisfied.append(f"{code} in progress")
            return True
        missing.append(code if code not in min_grades else f"{code} with at least {min_grades[code]}")
        return False
    if node.operator == "standing":
        missing.append(node.value or "standing")
        return None
    if node.operator == "consent":
        missing.append("instructor consent")
        return None
    child_results = [
        _evaluate_expr(child, completed, in_progress, min_grades, allow_in_progress, satisfied, missing)
        for child in node.children
    ]
    if node.operator == "and":
        if any(result is False for result in child_results):
            return False
        if any(result is None for result in child_results):
            return None
        return True
    if node.operator == "or":
        if any(result is True for result in child_results):
            return True
        if any(result is None for result in child_results):
            return None
        return False
    return None
