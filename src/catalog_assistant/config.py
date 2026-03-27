from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
VECTORSTORE_DIR = DATA_DIR / "vectorstore"
EVAL_DIR = DATA_DIR / "eval"
SAMPLES_DIR = DATA_DIR / "samples"
REPORTS_DIR = PROJECT_ROOT / "reports"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="qwen/qwen3-32b", alias="GROQ_MODEL")
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chunk_size_tokens: int = 800
    chunk_overlap_tokens: int = 120
    retrieval_k: int = 8
    rerank_k: int = 5
    catalog_year: str = "2025"


settings = Settings()


def ensure_directories() -> None:
    for path in (DATA_DIR, RAW_DIR, PROCESSED_DIR, VECTORSTORE_DIR, EVAL_DIR, SAMPLES_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)

