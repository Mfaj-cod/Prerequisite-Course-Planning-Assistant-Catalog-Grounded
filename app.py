from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from catalog_assistant.assistant import CoursePlanningAssistant
from catalog_assistant.evaluation import ensure_sample_data
from catalog_assistant.models import StudentProfile
from catalog_assistant.utils import read_json


st.set_page_config(page_title="Catalog Course Planner", layout="wide")
st.title("Catalog-Grounded Course Planning Assistant")
st.caption("Purple Merit Assessment 1 demo using the UT Dallas 2025 undergraduate catalog.")

ensure_sample_data()
assistant = CoursePlanningAssistant.create()

sample_options = {
    "Computer Science sample": "data/samples/sample_profile_cs.json",
    "Software Engineering sample": "data/samples/sample_profile_se.json",
}

with st.sidebar:
    st.header("Profile")
    sample_name = st.selectbox("Load sample profile", list(sample_options.keys()))
    default_profile = read_json(Path(sample_options[sample_name]))
    profile_text = st.text_area("Student profile JSON", value=json.dumps(default_profile, indent=2), height=320)
    if st.button("Build / Refresh Index"):
        with st.spinner("Fetching sources and rebuilding the vector index..."):
            assistant.ensure_index(force=True)
        st.success("Index refreshed.")

try:
    profile = StudentProfile.model_validate_json(profile_text)
except Exception as exc:
    st.error(f"Profile JSON is invalid: {exc}")
    st.stop()

query_tab, plan_tab = st.tabs(["Ask a Question", "Generate Plan"])

with query_tab:
    query = st.text_input("Question", value="Can I take CS 4347 next term?")
    if st.button("Run Question"):
        response = assistant.answer_query(query, profile)
        st.subheader("Answer / Plan")
        st.write(response.answer_plan)
        st.subheader("Why (requirements/prereqs satisfied)")
        for item in response.why:
            st.write(f"- {item}")
        st.subheader("Citations")
        for citation in response.citations:
            st.write(f"- {citation.url} | {citation.heading} | {citation.chunk_id}")
        st.subheader("Clarifying questions")
        for item in response.clarifying_questions or ["None"]:
            st.write(f"- {item}")
        st.subheader("Assumptions / Not in catalog")
        for item in response.assumptions_not_in_catalog or ["None"]:
            st.write(f"- {item}")

with plan_tab:
    if st.button("Generate Next-Term Plan"):
        response = assistant.generate_plan(profile)
        st.subheader("Answer / Plan")
        st.write(response.answer_plan)
        st.subheader("Why (requirements/prereqs satisfied)")
        for item in response.why:
            st.write(f"- {item}")
        st.subheader("Citations")
        for citation in response.citations:
            st.write(f"- {citation.url} | {citation.heading} | {citation.chunk_id}")
        st.subheader("Assumptions / Not in catalog")
        for item in response.assumptions_not_in_catalog or ["None"]:
            st.write(f"- {item}")
