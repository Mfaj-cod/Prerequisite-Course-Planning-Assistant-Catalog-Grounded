from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import normalize_course_code


COURSE_CODE_PATTERN = re.compile(r"\b[A-Z]{2,4}\s?\d{4}\b")
GRADE_ORDER = {
    "A+": 13,
    "A": 12,
    "A-": 11,
    "B+": 10,
    "B": 9,
    "B-": 8,
    "C+": 7,
    "C": 6,
    "C-": 5,
    "D+": 4,
    "D": 3,
    "D-": 2,
    "F": 1,
}


def extract_course_codes(text: str) -> list[str]:
    return [normalize_course_code(match.group(0)) for match in COURSE_CODE_PATTERN.finditer(text.upper())]


def dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def grade_meets_requirement(actual: str | None, minimum: str | None) -> bool | None:
    if minimum is None:
        return True
    if actual is None:
        return None
    normalized_actual = actual.upper().strip()
    normalized_minimum = minimum.upper().strip()
    if normalized_actual not in GRADE_ORDER or normalized_minimum not in GRADE_ORDER:
        return None
    return GRADE_ORDER[normalized_actual] >= GRADE_ORDER[normalized_minimum]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return sanitized.strip("_")
