from __future__ import annotations

import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup, Tag

from .config import PROCESSED_DIR, RAW_DIR, ensure_directories
from .models import CourseMetadata, NormalizedSource, SectionText, normalize_course_code
from .sources import SOURCE_SPECS, SourceSpec
from .utils import write_json

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 CatalogAssistant/0.1"


class SourceFetcher:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._fallback_pages: dict[str, str] = {}

    def fetch(self, spec: SourceSpec, force: bool = False) -> NormalizedSource:
        ensure_directories()
        raw_path = RAW_DIR / f"{spec.source_id}.html"
        if raw_path.exists() and not force:
            html = raw_path.read_text(encoding="utf-8")
        else:
            html = self._download_with_fallback(spec)
            raw_path.write_text(html, encoding="utf-8")
        normalized = normalize_source(spec, html)
        processed_path = PROCESSED_DIR / f"{spec.source_id}.json"
        processed_path.write_text(normalized.model_dump_json(indent=2), encoding="utf-8")
        return normalized

    def fetch_all(self, force: bool = False) -> list[NormalizedSource]:
        return [self.fetch(spec, force=force) for spec in SOURCE_SPECS]

    def _download_with_fallback(self, spec: SourceSpec) -> str:
        candidate_urls = [spec.url]
        if "/2025/undergraduate/" in spec.url:
            candidate_urls.append(spec.url.replace("/2025/undergraduate/", "/2025-undergraduate/"))
        last_error: Exception | None = None
        for url in candidate_urls:
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                if "Page Not Found" in response.text:
                    raise requests.HTTPError("Catalog page not found")
                return response.text
            except Exception as exc:
                last_error = exc
        if spec.doc_type == "course" and spec.course_code:
            return self._extract_course_html_from_listing(spec.course_code)
        raise RuntimeError(f"Unable to download source {spec.source_id}: {last_error}")

    def _extract_course_html_from_listing(self, course_code: str) -> str:
        subject = normalize_course_code(course_code).split()[0].lower()
        listing_url = f"https://catalog.utdallas.edu/2025/undergraduate/courses/{subject}"
        if listing_url not in self._fallback_pages:
            response = self.session.get(listing_url, timeout=30)
            response.raise_for_status()
            self._fallback_pages[listing_url] = response.text
        return self._fallback_pages[listing_url]


def normalize_source(spec: SourceSpec, html: str) -> NormalizedSource:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)
    sections = _extract_sections(spec, soup)
    flattened_text = "\n\n".join(f"{section.heading}\n{section.text}" for section in sections)
    course_metadata = _extract_course_metadata(spec, title, flattened_text)
    return NormalizedSource(
        source_id=spec.source_id,
        url=spec.url,
        accessed_on=datetime.now().date().isoformat(),
        doc_type=spec.doc_type,
        program=spec.program,
        course_code=spec.course_code,
        notes=spec.notes,
        title=title,
        text=flattened_text,
        sections=sections,
        course_metadata=course_metadata,
    )


def _extract_title(soup: BeautifulSoup) -> str:
    for selector in ("h1", "title"):
        node = soup.select_one(selector)
        if node and node.get_text(strip=True):
            return node.get_text(" ", strip=True)
    return "Untitled Source"


def _extract_sections(spec: SourceSpec, soup: BeautifulSoup) -> list[SectionText]:
    if spec.doc_type == "course" and spec.course_code:
        course_sections = _extract_course_sections(soup, spec.course_code)
        if course_sections:
            return course_sections
    sections = _extract_heading_sections(soup)
    if sections:
        return sections
    text = clean_text(soup.get_text("\n", strip=True))
    return [SectionText(heading="Document Text", text=text)]


def _extract_heading_sections(soup: BeautifulSoup) -> list[SectionText]:
    container = soup.select_one("main") or soup.select_one("#content") or soup.body or soup
    sections: list[SectionText] = []
    current_heading = "Overview"
    buffer: list[str] = []
    for node in container.descendants:
        if not isinstance(node, Tag):
            continue
        if node.name in {"h1", "h2", "h3", "h4"}:
            if buffer:
                text = clean_text("\n".join(buffer))
                if text:
                    sections.append(SectionText(heading=current_heading, text=text))
                buffer = []
            current_heading = clean_text(node.get_text(" ", strip=True)) or current_heading
        elif node.name in {"p", "li"}:
            text = clean_text(node.get_text(" ", strip=True))
            if text:
                buffer.append(text)
    if buffer:
        text = clean_text("\n".join(buffer))
        if text:
            sections.append(SectionText(heading=current_heading, text=text))
    return _compress_sections(sections)


def _extract_course_sections(soup: BeautifulSoup, course_code: str) -> list[SectionText]:
    title = _extract_title(soup)
    full_text = clean_text(soup.get_text("\n", strip=True))
    normalized_code = normalize_course_code(course_code)
    if normalized_code not in full_text:
        fallback = _extract_course_match_from_listing(full_text, normalized_code)
        if fallback:
            full_text = fallback
        else:
            return []
    overview = full_text
    prereq = _extract_field(full_text, "Prerequisites?")
    prereq_or_coreq = _extract_field(full_text, "Prerequisite or Corequisite")
    coreq = _extract_field(full_text, "Corequisite")
    sections = [SectionText(heading="Course Description", text=overview)]
    if prereq:
        sections.append(SectionText(heading="Prerequisites", text=prereq))
    if prereq_or_coreq:
        sections.append(SectionText(heading="Prerequisite or Corequisite", text=prereq_or_coreq))
    if coreq:
        sections.append(SectionText(heading="Corequisite", text=coreq))
    sections.append(SectionText(heading="Course Title", text=title))
    return _compress_sections(sections)


def _extract_course_match_from_listing(text: str, course_code: str) -> str | None:
    pattern = re.compile(rf"({re.escape(course_code)}\b.*?)(?=\b[A-Z]{{2,4}}\s?\d{{4}}\b|$)", re.IGNORECASE | re.DOTALL)
    match = pattern.search(text)
    if match:
        return clean_text(match.group(1))
    return None


def _extract_course_metadata(spec: SourceSpec, title: str, text: str) -> CourseMetadata | None:
    if spec.doc_type != "course":
        return None
    course_text = text.replace("\n", " ")
    title_match = re.search(r"\b([A-Z]{2,4}\s?\d{4})\b\s+(.+?)\((\d+) semester credit hour", course_text, flags=re.IGNORECASE)
    if title_match:
        code = normalize_course_code(title_match.group(1))
        title_value = title_match.group(2).strip()
        credit_hours = int(title_match.group(3))
    else:
        code = normalize_course_code(spec.course_code or "") if spec.course_code else None
        title_value = title
        credit_hours = None
    prerequisite_text = _extract_field(course_text, "Prerequisites?")
    prereq_or_coreq = _extract_field(course_text, "Prerequisite or Corequisite")
    coreq = _extract_field(course_text, "Corequisite")
    standing_match = re.search(r"\b(FRESHMAN|SOPHOMORE|JUNIOR|SENIOR) STANDING\b", course_text, re.IGNORECASE)
    instructor_consent_required = "instructor consent required" in course_text.lower()
    return CourseMetadata(
        code=code,
        title=title_value,
        credit_hours=credit_hours,
        prerequisite_text=prerequisite_text,
        prereq_or_coreq_text=prereq_or_coreq,
        corequisite_text=coreq,
        standing_text=standing_match.group(0).title() if standing_match else None,
        instructor_consent_required=instructor_consent_required,
    )


def _extract_field(text: str, label: str) -> str | None:
    pattern = re.compile(
        rf"{label}:\s*(.*?)(?=(?:Prerequisite or Corequisite|Corequisite|Recommended Corequisite|Credit cannot|Same as|\(\d|$))",
        flags=re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        value = clean_text(match.group(1))
        return value or None
    return None


def _compress_sections(sections: list[SectionText]) -> list[SectionText]:
    cleaned: list[SectionText] = []
    seen: set[tuple[str, str]] = set()
    for section in sections:
        heading = clean_text(section.heading)
        text = clean_text(section.text)
        key = (heading, text)
        if heading and text and key not in seen:
            seen.add(key)
            cleaned.append(SectionText(heading=heading, text=text))
    return cleaned


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    value = value.replace(" ,", ",").replace(" .", ".")
    return value.strip()


def build_manifest(sources: list[NormalizedSource]) -> list[dict[str, str | None]]:
    manifest: list[dict[str, str | None]] = []
    for source in sources:
        manifest.append(
            {
                "source_id": source.source_id,
                "url": source.url,
                "accessed_on": source.accessed_on,
                "doc_type": source.doc_type,
                "program": source.program,
                "course_code": source.course_code,
                "notes": source.notes,
                "title": source.title,
            }
        )
    return manifest


def ingest_sources(force: bool = False) -> list[NormalizedSource]:
    fetcher = SourceFetcher()
    sources = fetcher.fetch_all(force=force)
    write_json(PROCESSED_DIR / "source_manifest.json", build_manifest(sources))
    write_json(PROCESSED_DIR / "normalized_sources.json", [source.model_dump(mode="json") for source in sources])
    return sources
