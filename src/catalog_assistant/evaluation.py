from __future__ import annotations

import csv
from statistics import mean

from .assistant import CoursePlanningAssistant
from .config import EVAL_DIR, REPORTS_DIR, SAMPLES_DIR, ensure_directories
from .models import CompletedCourse, EvalCase, EvalOutcome, StudentProfile
from .reporting import write_markdown_report
from .utils import write_json


def default_eval_cases() -> list[EvalCase]:
    cs_mid_profile = StudentProfile(
        target_program="computer-science",
        target_term="Fall",
        max_courses=4,
        max_credits=12,
        completed_courses=[
            CompletedCourse(code="CS 1200"),
            CompletedCourse(code="CS 1337", grade="A"),
            CompletedCourse(code="CS 2305", grade="B"),
            CompletedCourse(code="CS 2336", grade="B"),
            CompletedCourse(code="CS 2340", grade="B"),
            CompletedCourse(code="ECS 2390"),
            CompletedCourse(code="CS 3341", grade="B"),
            CompletedCourse(code="CS 3345", grade="B"),
            CompletedCourse(code="CS 3377", grade="B"),
        ],
    )
    se_mid_profile = StudentProfile(
        target_program="software-engineering",
        target_term="Spring",
        max_courses=4,
        max_credits=12,
        completed_courses=[
            CompletedCourse(code="CS 1200"),
            CompletedCourse(code="CS 1337", grade="A"),
            CompletedCourse(code="CS 2305", grade="B"),
            CompletedCourse(code="CS 2336", grade="B"),
            CompletedCourse(code="ECS 2390"),
            CompletedCourse(code="SE 3306", grade="B"),
            CompletedCourse(code="SE 3341", grade="B"),
            CompletedCourse(code="SE 3345", grade="B"),
            CompletedCourse(code="SE 3354", grade="A"),
        ],
    )
    early_profile = StudentProfile(
        target_program="computer-science",
        target_term="Fall",
        max_courses=4,
        max_credits=12,
        completed_courses=[
            CompletedCourse(code="CS 1200"),
            CompletedCourse(code="CS 1337", grade="B"),
            CompletedCourse(code="CS 2305", grade="B"),
        ],
    )
    return [
        EvalCase(id="p01", category="prereq_check", student_profile=cs_mid_profile, user_query="Can I take CS 4347 next term?", expected_decision="Eligible"),
        EvalCase(id="p02", category="prereq_check", student_profile=cs_mid_profile, user_query="Can I take CS 4348 next term?", expected_decision="Eligible"),
        EvalCase(id="p03", category="prereq_check", student_profile=cs_mid_profile, user_query="Can I take CS 4349?", expected_decision="Eligible"),
        EvalCase(id="p04", category="prereq_check", student_profile=cs_mid_profile, user_query="Can I take CS 4384?", expected_decision="Eligible"),
        EvalCase(id="p05", category="prereq_check", student_profile=cs_mid_profile, user_query="Can I take CS 4375?", expected_decision="Eligible"),
        EvalCase(id="p06", category="prereq_check", student_profile=early_profile, user_query="Can I take CS 3345?", expected_decision="Not eligible"),
        EvalCase(id="p07", category="prereq_check", student_profile=early_profile, user_query="Can I take CS 3354?", expected_decision="Not eligible"),
        EvalCase(id="p08", category="prereq_check", student_profile=early_profile, user_query="Can I take CS 4347?", expected_decision="Not eligible"),
        EvalCase(id="p09", category="prereq_check", student_profile=se_mid_profile, user_query="Can I take SE 4347?", expected_decision="Eligible"),
        EvalCase(id="p10", category="prereq_check", student_profile=se_mid_profile, user_query="Can I take SE 4348?", expected_decision="Not eligible"),
        EvalCase(id="c01", category="prereq_chain", student_profile=early_profile, user_query="What do I need before CS 4348?", expected_decision="Not eligible"),
        EvalCase(id="c02", category="prereq_chain", student_profile=cs_mid_profile, user_query="What do I need before CS 4390?", expected_decision="Eligible"),
        EvalCase(id="c03", category="prereq_chain", student_profile=cs_mid_profile, user_query="What do I need before CS 4337?", expected_decision="Eligible"),
        EvalCase(id="c04", category="prereq_chain", student_profile=se_mid_profile, user_query="What do I need before SE 4351?", expected_decision="Eligible"),
        EvalCase(id="c05", category="prereq_chain", student_profile=se_mid_profile, user_query="What do I need before SE 4367?", expected_decision="Not eligible"),
        EvalCase(id="r01", category="program_rule", student_profile=StudentProfile(target_program="computer-science"), user_query="How many technical elective credit hours does the Computer Science degree require?"),
        EvalCase(id="r02", category="program_rule", student_profile=StudentProfile(target_program="software-engineering"), user_query="How many upper-division hours are required for Software Engineering?"),
        EvalCase(id="r03", category="program_rule", student_profile=StudentProfile(target_program="computer-science"), user_query="What is the total credit hour requirement for Computer Science?"),
        EvalCase(id="r04", category="program_rule", student_profile=cs_mid_profile, user_query="What requirements do I still have left in my Computer Science degree?"),
        EvalCase(id="r05", category="program_rule", student_profile=se_mid_profile, user_query="What requirements do I still have left in my Software Engineering degree?"),
        EvalCase(id="n01", category="not_in_docs", student_profile=cs_mid_profile, user_query="Is CS 4347 offered every Fall?", expected_abstain=True),
        EvalCase(id="n02", category="not_in_docs", student_profile=cs_mid_profile, user_query="Who teaches CS 4348 this semester?", expected_abstain=True),
        EvalCase(id="n03", category="not_in_docs", student_profile=se_mid_profile, user_query="Which section number should I register for in SE 4351?", expected_abstain=True),
        EvalCase(id="n04", category="not_in_docs", student_profile=cs_mid_profile, user_query="Can an advisor waive CS 4349 for me?", expected_abstain=True),
        EvalCase(id="n05", category="not_in_docs", student_profile=se_mid_profile, user_query="What time of day is SE 4347 usually scheduled?", expected_abstain=True),
    ]


def ensure_sample_data() -> None:
    ensure_directories()
    sample_profiles = {
        "sample_profile_cs.json": {
            "catalog_year": "2025",
            "target_program": "computer-science",
            "target_term": "Fall",
            "max_courses": 4,
            "max_credits": 12,
            "completed_courses": [
                {"code": "CS 1200"},
                {"code": "CS 1337", "grade": "A"},
                {"code": "CS 2305", "grade": "B"},
                {"code": "CS 2336", "grade": "B"},
                {"code": "CS 2340", "grade": "B"},
                {"code": "ECS 2390"},
                {"code": "CS 3341", "grade": "B"},
                {"code": "CS 3345", "grade": "B"},
                {"code": "CS 3377", "grade": "B"}
            ],
            "in_progress_courses": []
        },
        "sample_profile_se.json": {
            "catalog_year": "2025",
            "target_program": "software-engineering",
            "target_term": "Spring",
            "max_courses": 4,
            "max_credits": 12,
            "completed_courses": [
                {"code": "CS 1200"},
                {"code": "CS 1337", "grade": "A"},
                {"code": "CS 2305", "grade": "B"},
                {"code": "CS 2336", "grade": "B"},
                {"code": "ECS 2390"},
                {"code": "SE 3306", "grade": "B"},
                {"code": "SE 3341", "grade": "B"},
                {"code": "SE 3345", "grade": "B"},
                {"code": "SE 3354", "grade": "A"}
            ],
            "in_progress_courses": []
        }
    }
    for filename, payload in sample_profiles.items():
        write_json(SAMPLES_DIR / filename, payload)
    write_json(EVAL_DIR / "eval_cases.json", [case.model_dump(mode="json") for case in default_eval_cases()])


def run_evaluation(assistant: CoursePlanningAssistant) -> dict[str, float | int | list[EvalOutcome]]:
    ensure_sample_data()
    outcomes: list[EvalOutcome] = []
    cases = default_eval_cases()
    for case in cases:
        response = assistant.answer_query(case.user_query, case.student_profile)
        abstained = response.answer_plan.startswith("I don't have that information")
        citation_resolvable = all(citation.url and citation.chunk_id for citation in response.citations)
        structured = bool(response.answer_plan) and isinstance(response.why, list) and isinstance(response.assumptions_not_in_catalog, list)
        passed_decision_check = True if case.expected_decision is None else response.decision == case.expected_decision
        passed_abstain_check = abstained == case.expected_abstain
        outcomes.append(
            EvalOutcome(
                case_id=case.id,
                category=case.category,
                decision=response.decision,
                expected_decision=case.expected_decision,
                abstained=abstained,
                expected_abstain=case.expected_abstain,
                citation_count=len(response.citations),
                citation_resolvable=citation_resolvable,
                structured_output_valid=structured,
                passed_decision_check=passed_decision_check,
                passed_abstain_check=passed_abstain_check,
                response=response,
            )
        )
    citation_coverage = mean(1 if outcome.citation_count > 0 else 0 for outcome in outcomes) * 100
    prereq_outcomes = [outcome for outcome in outcomes if outcome.category in {"prereq_check", "prereq_chain"}]
    eligibility_correctness = mean(1 if outcome.passed_decision_check else 0 for outcome in prereq_outcomes) * 100
    abstention_outcomes = [outcome for outcome in outcomes if outcome.category == "not_in_docs"]
    abstention_accuracy = mean(1 if outcome.passed_abstain_check else 0 for outcome in abstention_outcomes) * 100
    summary = {
        "total_cases": len(outcomes),
        "citation_coverage_rate": round(citation_coverage, 2),
        "eligibility_correctness": round(eligibility_correctness, 2),
        "abstention_accuracy": round(abstention_accuracy, 2),
        "outcomes": outcomes,
    }
    _write_eval_artifacts(summary)
    return summary


def _write_eval_artifacts(summary: dict[str, float | int | list[EvalOutcome]]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    outcomes: list[EvalOutcome] = summary["outcomes"]  # type: ignore[assignment]
    write_json(
        REPORTS_DIR / "evaluation_metrics.json",
        {
            "total_cases": summary["total_cases"],
            "citation_coverage_rate": summary["citation_coverage_rate"],
            "eligibility_correctness": summary["eligibility_correctness"],
            "abstention_accuracy": summary["abstention_accuracy"],
        },
    )
    with (REPORTS_DIR / "manual_review.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case_id", "category", "decision", "expected_decision", "manual_decision_score", "manual_evidence_score", "manual_notes"])
        for outcome in outcomes:
            writer.writerow([outcome.case_id, outcome.category, outcome.decision, outcome.expected_decision, "", "", ""])
    transcript_cases = [outcomes[0], outcomes[15], outcomes[20]]
    transcript_md = ["# Example Transcripts", ""]
    for outcome in transcript_cases:
        transcript_md.append(f"## {outcome.case_id} - {outcome.category}")
        transcript_md.append("")
        transcript_md.append(outcome.response.answer_plan)
        transcript_md.append("")
        transcript_md.append("Why:")
        transcript_md.extend(f"- {line}" for line in outcome.response.why)
        transcript_md.append("")
        transcript_md.append("Citations:")
        transcript_md.extend(f"- {citation.url} | {citation.heading} | {citation.chunk_id}" for citation in outcome.response.citations)
        transcript_md.append("")
    write_markdown_report("example_transcripts", "Example Transcripts", "\n".join(transcript_md))
    summary_md = [
        "# Evaluation Summary",
        "",
        f"- Total cases: {summary['total_cases']}",
        f"- Citation coverage rate: {summary['citation_coverage_rate']}%",
        f"- Eligibility correctness: {summary['eligibility_correctness']}%",
        f"- Abstention accuracy: {summary['abstention_accuracy']}%",
        "",
        "## Manual Rubric",
        "",
        "- Decision correctness: Did the system choose Eligible, Not eligible, or Need more info correctly?",
        "- Evidence sufficiency: Did the response cite the relevant course/program/policy text?",
        "- Next-step quality: Did the response explain what the student should do next when blocked or uncertain?",
        "",
        "## Notes",
        "",
        "- Eligibility correctness is computed automatically against the curated evaluation labels and should be backed by spot-checked manual review.",
        "- Citation coverage treats a response as covered when it includes at least one citation.",
        "- Abstention accuracy checks whether the system correctly refused unsupported availability or schedule questions.",
    ]
    write_markdown_report("evaluation_summary", "Evaluation Summary", "\n".join(summary_md))
    write_markdown_report("submission_writeup", "Submission Write-Up", build_submission_writeup(summary))


def build_submission_writeup(summary: dict[str, float | int | list[EvalOutcome]]) -> str:
    return "\n".join(
        [
            "# Purple Merit Assessment 1 Write-Up",
            "",
            "## Chosen Catalog / Sources",
            "",
            "- Institution: The University of Texas at Dallas, 2025 Undergraduate Catalog",
            "- Sources include Computer Science and Software Engineering degree requirement pages, academic policy pages, degree plan policy pages, and curated CS/SE/ECS course descriptions.",
            "- The source manifest is generated automatically in `data/processed/source_manifest.json` with URL, access date, and notes.",
            "",
            "## Architecture Overview",
            "",
            "- Ingestion fetches official UT Dallas pages, normalizes sections, and stores raw plus processed artifacts.",
            "- Retrieval uses `BAAI/bge-small-en-v1.5` embeddings with a persisted local Chroma vector store.",
            "- A symbolic prerequisite engine evaluates eligibility and plan feasibility for correctness before any LLM phrasing step.",
            "- Groq is used as the optional final drafting layer, while correctness remains grounded in retrieved and parsed catalog data.",
            "",
            "## Chunking / Retrieval Tradeoffs",
            "",
            "- Sections are chunked to roughly 800-token-equivalent windows with overlap so prerequisite sentences stay intact.",
            "- Retrieval starts with top-k similarity search and the assistant emits citations using source URL, heading, and chunk id.",
            "",
            "## Evaluation Summary",
            "",
            f"- Citation coverage rate: {summary['citation_coverage_rate']}%",
            f"- Eligibility correctness: {summary['eligibility_correctness']}%",
            f"- Abstention accuracy: {summary['abstention_accuracy']}%",
            "",
            "## Failure Modes / Next Improvements",
            "",
            "- The current planner models curated major buckets rather than the entire university core.",
            "- Some catalog wording patterns would benefit from a richer symbolic parser for advisor exceptions and program-substitution rules.",
            "- A next iteration would add stronger reranking, richer plan explanations, and a deeper curriculum graph for multi-term planning.",
        ]
    )
