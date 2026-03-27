from __future__ import annotations

import argparse
from pathlib import Path

from .assistant import CoursePlanningAssistant
from .evaluation import ensure_sample_data, run_evaluation
from .models import StudentProfile
from .utils import read_json


def load_profile(path: str | None) -> StudentProfile:
    if not path:
        return StudentProfile()
    payload = read_json(Path(path))
    return StudentProfile.model_validate(payload)


def handle_ingest(args: argparse.Namespace) -> None:
    assistant = CoursePlanningAssistant.create()
    assistant.ensure_index(force=args.force)
    print("Ingestion and vector indexing complete.")


def handle_ask(args: argparse.Namespace) -> None:
    assistant = CoursePlanningAssistant.create()
    profile = load_profile(args.profile_file)
    response = assistant.answer_query(args.query, profile)
    if args.json:
        print(response.model_dump_json(indent=2))
    else:
        print(assistant.render_response_text(response))


def handle_plan(args: argparse.Namespace) -> None:
    assistant = CoursePlanningAssistant.create()
    profile = load_profile(args.profile_file)
    response = assistant.generate_plan(profile)
    if args.json:
        print(response.model_dump_json(indent=2))
    else:
        print(assistant.render_response_text(response))


def handle_eval(args: argparse.Namespace) -> None:
    assistant = CoursePlanningAssistant.create()
    summary = run_evaluation(assistant)
    printable = {key: value for key, value in summary.items() if key != "outcomes"}
    print(printable)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Catalog-grounded course planning assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Fetch sources and build the vector index")
    ingest_parser.add_argument("--force", action="store_true", help="Redownload sources and rebuild the index from scratch")
    ingest_parser.set_defaults(func=handle_ingest)

    ask_parser = subparsers.add_parser("ask", help="Answer a prerequisite or catalog-grounded question")
    ask_parser.add_argument("--query", required=True, help="Student question")
    ask_parser.add_argument("--profile-file", help="Path to a JSON student profile")
    ask_parser.add_argument("--json", action="store_true", help="Print JSON instead of the formatted output")
    ask_parser.set_defaults(func=handle_ask)

    plan_parser = subparsers.add_parser("plan", help="Generate a next-term course plan")
    plan_parser.add_argument("--profile-file", required=True, help="Path to a JSON student profile")
    plan_parser.add_argument("--json", action="store_true", help="Print JSON instead of the formatted output")
    plan_parser.set_defaults(func=handle_plan)

    eval_parser = subparsers.add_parser("eval", help="Run the 25-case evaluation suite and write reports")
    eval_parser.set_defaults(func=handle_eval)
    return parser


def main() -> None:
    ensure_sample_data()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
