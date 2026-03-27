from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .config import PROCESSED_DIR, VECTORSTORE_DIR, settings
from .indexing import build_vectorstore, load_vectorstore, make_citations
from .ingest import ingest_sources
from .models import AssistantResponse, Citation, NormalizedSource, StudentProfile, normalize_course_code
from .programs import PROGRAMS, ProgramDefinition
from .rules import CourseRule, EligibilityResult, RuleParser, evaluate_rule
from .utils import dedupe_keep_order, extract_course_codes, read_json

try:
    from langchain_groq import ChatGroq
except Exception:
    ChatGroq = None


@dataclass
class CoursePlanningAssistant:
    sources: list[NormalizedSource]
    source_lookup: dict[str, NormalizedSource]
    course_lookup: dict[str, NormalizedSource]
    program_lookup: dict[str, ProgramDefinition]
    rule_lookup: dict[str, CourseRule]
    vectorstore_ready: bool = False
    vectorstore: object | None = None

    @classmethod
    def create(cls) -> "CoursePlanningAssistant":
        if not (PROCESSED_DIR / "normalized_sources.json").exists():
            sources = ingest_sources(force=False)
        else:
            payload = read_json(PROCESSED_DIR / "normalized_sources.json")
            sources = [NormalizedSource.model_validate(item) for item in payload]
        rule_parser = RuleParser()
        course_lookup = {source.course_code: source for source in sources if source.course_code}
        rule_lookup = {
            code: rule_parser.parse_course_rule(code, source.course_metadata)
            for code, source in course_lookup.items()
        }
        return cls(
            sources=sources,
            source_lookup={source.source_id: source for source in sources},
            course_lookup=course_lookup,
            program_lookup=PROGRAMS,
            rule_lookup=rule_lookup,
            vectorstore_ready=VECTORSTORE_DIR.exists(),
        )

    def ensure_index(self, force: bool = False) -> None:
        sources = ingest_sources(force=force)
        build_vectorstore(sources, force=force)
        rule_parser = RuleParser()
        self.sources = sources
        self.source_lookup = {source.source_id: source for source in sources}
        self.course_lookup = {source.course_code: source for source in sources if source.course_code}
        self.rule_lookup = {
            code: rule_parser.parse_course_rule(code, source.course_metadata)
            for code, source in self.course_lookup.items()
        }
        self.vectorstore_ready = True
        self.vectorstore = None

    def answer_query(self, query: str, profile: StudentProfile | None = None) -> AssistantResponse:
        profile = profile or StudentProfile()
        route = self._route_query(query)
        if self._is_not_in_docs_question(query):
            return self._abstain_response(route=route)
        if route == "plan":
            return self.generate_plan(profile, query=query)
        if route == "program_rule":
            return self.answer_program_rule(query, profile)
        return self.answer_prerequisite(query, profile)

    def answer_prerequisite(self, query: str, profile: StudentProfile) -> AssistantResponse:
        target_course = self._extract_target_course(query)
        if not target_course or target_course not in self.rule_lookup:
            return self._abstain_response("prerequisite", ["I could not match the target course to the curated catalog corpus."])
        rule = self.rule_lookup[target_course]
        clarifying_questions = self._clarifying_questions_for_prereq(profile, rule)
        citations = dedupe_citations(self._citations_for_course(target_course) + self._retrieval_citations(query, course_code=target_course))
        if clarifying_questions:
            return AssistantResponse(
                answer_plan=f"I need a bit more information before I can determine whether you are eligible for {target_course}.",
                why=["The catalog rule includes grade-sensitive or profile-sensitive requirements that are not fully present in the student profile."],
                citations=citations,
                clarifying_questions=clarifying_questions,
                assumptions_not_in_catalog=[],
                decision="Need more info",
                route="prerequisite",
            )
        result = evaluate_rule(rule, profile)
        response = AssistantResponse(
            answer_plan=self._render_prereq_answer(target_course, result),
            why=self._build_prereq_why(target_course, result),
            citations=citations,
            clarifying_questions=[],
            assumptions_not_in_catalog=result.assumptions,
            decision=result.decision,
            route="prerequisite",
        )
        return self._maybe_refine_with_llm(query, response)

    def answer_program_rule(self, query: str, profile: StudentProfile) -> AssistantResponse:
        program_id = profile.target_program or self._extract_program_id(query)
        if not program_id or program_id not in self.program_lookup:
            return AssistantResponse(
                answer_plan="I need your target program before I can answer this requirement question.",
                why=["Program requirement questions depend on whether you are following the Computer Science or Software Engineering degree plan."],
                citations=[],
                clarifying_questions=["Which target program should I use: computer-science or software-engineering?"],
                assumptions_not_in_catalog=[],
                decision="Need more info",
                route="program_rule",
            )
        program = self.program_lookup[program_id]
        lowered = query.lower()
        answer_lines: list[str] = []
        why: list[str] = []
        if "technical elective" in lowered:
            answer_lines.append(f"{program.name} requires {program.technical_elective_credit_hours} semester credit hours of technical electives.")
            why.append(f"The degree plan includes a technical elective bucket worth {program.technical_elective_credit_hours} semester credit hours.")
        if "upper" in lowered and "division" in lowered:
            answer_lines.append(f"{program.name} requires at least {program.upper_division_hours} upper-division semester credit hours.")
            why.append(f"The degree plan states a minimum of {program.upper_division_hours} upper-division semester credit hours.")
        if "total" in lowered and "credit" in lowered:
            answer_lines.append(f"{program.name} totals {program.total_credit_hours} semester credit hours.")
            why.append(f"The degree plan total for {program.name} is {program.total_credit_hours} semester credit hours.")
        if ("left" in lowered or "remaining" in lowered or "still have" in lowered) and not answer_lines:
            remaining = self._remaining_program_courses(program, profile)
            if remaining:
                answer_lines.append(f"You still have {len(remaining)} named major courses remaining in the curated v1 planner: {', '.join(remaining[:10])}.")
            else:
                answer_lines.append("You have completed all curated major courses tracked in the v1 planner.")
            why.append("I compared your completed courses against the curated major preparatory, core, and technical-elective buckets.")
        if not answer_lines:
            return self._abstain_response("program_rule")
        response = AssistantResponse(
            answer_plan=" ".join(answer_lines),
            why=why + list(program.notes),
            citations=dedupe_citations(self._citations_for_source(program.source_id) + self._retrieval_citations(query, source_id=program.source_id)),
            clarifying_questions=[],
            assumptions_not_in_catalog=["The v1 planner only models the curated major buckets and does not compute the full university core automatically."],
            decision="Eligible",
            route="program_rule",
        )
        return self._maybe_refine_with_llm(query, response)

    def generate_plan(self, profile: StudentProfile, query: str | None = None) -> AssistantResponse:
        clarifying_questions = self._clarifying_questions_for_plan(profile)
        if clarifying_questions:
            return AssistantResponse(
                answer_plan="I need a little more information before I can propose a next-term plan.",
                why=["Term planning depends on the target program, current completions, and your course or credit cap for the next term."],
                citations=[],
                clarifying_questions=clarifying_questions,
                assumptions_not_in_catalog=[],
                decision="Need more info",
                route="plan",
            )
        assert profile.target_program is not None
        program = self.program_lookup[profile.target_program]
        remaining = self._remaining_program_courses(program, profile)
        eligible: list[tuple[str, EligibilityResult]] = []
        for course_code in remaining:
            rule = self.rule_lookup.get(course_code)
            result = evaluate_rule(rule, profile) if rule else EligibilityResult("Eligible", [], [], [])
            if result.decision == "Eligible":
                eligible.append((course_code, result))
        eligible.sort(key=lambda item: self._course_rank(item[0], program), reverse=True)
        selected: list[tuple[str, EligibilityResult]] = []
        credit_total = 0
        max_courses = profile.max_courses or 4
        max_credits = profile.max_credits or 12
        for course_code, result in eligible:
            credits = self._course_credit_hours(course_code)
            if len(selected) >= max_courses:
                break
            if credit_total + credits > max_credits:
                continue
            selected.append((course_code, result))
            credit_total += credits
        if not selected:
            return AssistantResponse(
                answer_plan="I could not find an eligible next-term course plan from the curated v1 course set.",
                why=["The remaining curated courses appear to require prerequisites that are not yet satisfied in the provided profile."],
                citations=self._citations_for_source(program.source_id),
                clarifying_questions=[],
                assumptions_not_in_catalog=["Course availability by semester is not included in the catalog corpus used here."],
                decision="Not eligible",
                route="plan",
            )
        why = []
        citations = self._citations_for_source(program.source_id)
        for course_code, _ in selected:
            why.append(f"{course_code} fits the {program.name} requirement buckets and its prerequisites appear satisfied.")
            citations.extend(self._citations_for_course(course_code))
        response = AssistantResponse(
            answer_plan="Suggested next-term plan: " + ", ".join(code for code, _ in selected) + ".",
            why=dedupe_keep_order(why),
            citations=dedupe_citations(citations + self._retrieval_citations(query or "Generate next term plan", program=program.program_id)),
            clarifying_questions=[],
            assumptions_not_in_catalog=[
                "Course availability by semester is not stated in the provided catalog pages, so you should confirm the schedule of classes.",
                "Advisor approval may still be needed for transfer-credit interpretation or catalog-year exceptions.",
            ],
            decision="Eligible",
            route="plan",
        )
        return self._maybe_refine_with_llm(query or "Generate a course plan", response)

    def render_response_text(self, response: AssistantResponse) -> str:
        lines = [f"Answer / Plan: {response.answer_plan}", "Why (requirements/prereqs satisfied):"]
        lines.extend([f"- {line}" for line in response.why] or ["- None"])
        lines.append("Citations:")
        lines.extend([f"- {citation.url} | {citation.heading} | {citation.chunk_id}" for citation in response.citations] or ["- None"])
        lines.append("Clarifying questions (if needed):")
        lines.extend([f"- {item}" for item in response.clarifying_questions] or ["- None"])
        lines.append("Assumptions / Not in catalog:")
        lines.extend([f"- {item}" for item in response.assumptions_not_in_catalog] or ["- None"])
        return "\n".join(lines)

    def _maybe_refine_with_llm(self, query: str, response: AssistantResponse) -> AssistantResponse:
        if not settings.groq_api_key or ChatGroq is None:
            return response
        try:
            llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0.1)
            citations = "\n".join(f"- {c.url} | {c.heading} | {c.chunk_id}" for c in response.citations[:6])
            prompt = (
                "Rewrite the answer into concise student-facing prose without changing the decision, requirements, or assumptions. "
                "Return strict JSON with keys answer_plan, why, assumptions_not_in_catalog.\n\n"
                f"Query: {query}\nDecision: {response.decision}\n"
                f"Current answer: {response.answer_plan}\n"
                f"Why bullets: {json.dumps(response.why)}\n"
                f"Assumptions: {json.dumps(response.assumptions_not_in_catalog)}\n"
                f"Citations: {citations}"
            )
            raw = llm.invoke(prompt).content
            payload = json.loads(extract_json_block(raw))
            response.answer_plan = str(payload.get("answer_plan", response.answer_plan))
            if isinstance(payload.get("why"), list):
                response.why = [str(item) for item in payload["why"]]
            if isinstance(payload.get("assumptions_not_in_catalog"), list):
                response.assumptions_not_in_catalog = [str(item) for item in payload["assumptions_not_in_catalog"]]
        except Exception:
            return response
        return response

    def _retrieval_citations(self, query: str, course_code: str | None = None, source_id: str | None = None, program: str | None = None) -> list[Citation]:
        if not VECTORSTORE_DIR.exists():
            return []
        try:
            if self.vectorstore is None:
                self.vectorstore = load_vectorstore()
            docs = self.vectorstore.similarity_search(query, k=settings.retrieval_k)
            filtered = []
            for doc in docs:
                if course_code and doc.metadata.get("course_code") == course_code:
                    filtered.append(doc)
                elif source_id and doc.metadata.get("source_id") == source_id:
                    filtered.append(doc)
                elif program and doc.metadata.get("program") == program:
                    filtered.append(doc)
                elif not any([course_code, source_id, program]):
                    filtered.append(doc)
            return make_citations(filtered[: settings.rerank_k])
        except Exception:
            return []

    def _route_query(self, query: str) -> str:
        lowered = query.lower()
        if any(keyword in lowered for keyword in ["can i take", "what do i need before", "eligible for", "before enrolling in", "prerequisite"]):
            return "prerequisite"
        if any(keyword in lowered for keyword in ["plan my next term", "plan my next semester", "suggest a plan", "build me a plan", "next term plan", "next semester plan", "schedule my courses"]):
            return "plan"
        if any(keyword in lowered for keyword in ["technical elective", "credit hours", "upper-division", "requirement", "degree plan", "total credits"]):
            return "program_rule"
        return "prerequisite"

    def _extract_target_course(self, query: str) -> str | None:
        patterns = [
            r"(?:take|enroll(?:ing)? in|before enrolling in|for)\s+([A-Z]{2,4}\s?\d{4})",
            r"what do i need before\s+([A-Z]{2,4}\s?\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, query, flags=re.IGNORECASE)
            if match:
                return normalize_course_code(match.group(1))
        codes = extract_course_codes(query)
        if len(codes) == 1:
            return codes[0]
        lowered = query.lower()
        if "can i take" in lowered and codes:
            return codes[0]
        return codes[-1] if codes else None

    def _extract_program_id(self, query: str) -> str | None:
        lowered = query.lower()
        if "software engineering" in lowered:
            return "software-engineering"
        if "computer science" in lowered:
            return "computer-science"
        return None

    def _is_not_in_docs_question(self, query: str) -> bool:
        lowered = query.lower()
        return any(keyword in lowered for keyword in ["which semester", "availability", "professor", "teacher", "who teaches", "what time", "section number", "usually scheduled", "offered every", "offered in", "waive", "waiver", "seat", "seats left"])

    def _abstain_response(self, route: str, extra_assumptions: list[str] | None = None) -> AssistantResponse:
        assumptions = [
            "I don't have that information in the provided catalog/policies.",
            "Check the advisor, department page, or schedule of classes for that detail.",
        ]
        if extra_assumptions:
            assumptions.extend(extra_assumptions)
        return AssistantResponse(
            answer_plan="I don't have that information in the provided catalog/policies.",
            why=["The requested detail is not explicitly stated in the curated catalog corpus."],
            citations=[],
            clarifying_questions=[],
            assumptions_not_in_catalog=assumptions,
            decision="Need more info",
            route=route,
        )

    def _clarifying_questions_for_prereq(self, profile: StudentProfile, rule: CourseRule) -> list[str]:
        questions: list[str] = []
        if not profile.completed_courses:
            questions.append("Which courses have you completed already?")
        if profile.catalog_year is None:
            questions.append("Which catalog year should I use for your program?")
        if rule.min_grade_by_course:
            relevant = [code for code in rule.min_grade_by_course if any(course.code == code and not course.grade for course in profile.completed_courses)]
            if relevant:
                questions.append(f"What grades did you earn in {', '.join(relevant)}?")
        return questions[:5]

    def _clarifying_questions_for_plan(self, profile: StudentProfile) -> list[str]:
        questions: list[str] = []
        if profile.catalog_year is None:
            questions.append("Which catalog year should I use?")
        if profile.target_program is None:
            questions.append("Which target program should I plan for: computer-science or software-engineering?")
        if not profile.completed_courses:
            questions.append("Which courses have you already completed, and what grades did you earn where relevant?")
        if profile.target_term is None:
            questions.append("Which target term should I plan for, such as Fall or Spring?")
        if profile.max_courses is None and profile.max_credits is None:
            questions.append("What is your limit for next term: max courses, max credits, or both?")
        return questions[:5]

    def _citations_for_course(self, course_code: str) -> list[Citation]:
        source = self.course_lookup.get(course_code)
        if not source:
            return []
        citations: list[Citation] = []
        for section in source.sections:
            if section.heading in {"Prerequisites", "Prerequisite or Corequisite", "Corequisite", "Course Description"}:
                citations.append(Citation(url=source.url, heading=section.heading, chunk_id=f"{source.source_id}__{section.heading.lower().replace(' ', '_')}__0"))
        return dedupe_citations(citations)

    def _citations_for_source(self, source_id: str) -> list[Citation]:
        source = self.source_lookup.get(source_id)
        if not source:
            return []
        citations = [
            Citation(url=source.url, heading=section.heading, chunk_id=f"{source.source_id}__{section.heading.lower().replace(' ', '_')}__0")
            for section in source.sections[:4]
        ]
        return dedupe_citations(citations)

    def _build_prereq_why(self, target_course: str, result: EligibilityResult) -> list[str]:
        why = [f"Decision: {result.decision} for {target_course}."]
        if result.satisfied:
            why.append("Satisfied evidence: " + ", ".join(result.satisfied) + ".")
        if result.decision != "Eligible" and result.missing:
            why.append("Missing or unmet requirements: " + ", ".join(result.missing) + ".")
        if result.decision == "Eligible" or not result.missing:
            why.append("No unmet prerequisite, corequisite, or standing requirement was detected from the provided profile.")
        return why

    def _render_prereq_answer(self, target_course: str, result: EligibilityResult) -> str:
        if result.decision == "Eligible":
            return f"You appear eligible to take {target_course} based on the completed-course profile I checked against the catalog prerequisites."
        if result.decision == "Not eligible":
            return f"You do not yet appear eligible to take {target_course}. The next step is to complete the missing prerequisite requirements listed below."
        return f"I need more information before I can determine whether you are eligible to take {target_course}."

    def _remaining_program_courses(self, program: ProgramDefinition, profile: StudentProfile) -> list[str]:
        completed = {course.code for course in profile.completed_courses}
        buckets = list(program.major_preparatory_courses) + list(program.major_core_courses) + list(program.technical_electives)
        return [course for course in buckets if course not in completed]

    def _course_rank(self, course_code: str, program: ProgramDefinition) -> int:
        score = 0
        if course_code in program.major_core_courses:
            score += 5
        if course_code in program.technical_electives:
            score += 2
        for other_rule in self.rule_lookup.values():
            serialized = f"{other_rule.prerequisite_expr} {other_rule.prereq_or_coreq_expr} {other_rule.corequisite_expr}"
            if course_code in serialized:
                score += 1
        return score

    def _course_credit_hours(self, course_code: str) -> int:
        source = self.course_lookup.get(course_code)
        if source and source.course_metadata and source.course_metadata.credit_hours:
            return source.course_metadata.credit_hours
        return 3


def dedupe_citations(citations: list[Citation]) -> list[Citation]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[Citation] = []
    for citation in citations:
        key = (citation.url, citation.heading, citation.chunk_id)
        if key not in seen:
            seen.add(key)
            unique.append(citation)
    return unique


def extract_json_block(raw: str) -> str:
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    return match.group(0) if match else raw





