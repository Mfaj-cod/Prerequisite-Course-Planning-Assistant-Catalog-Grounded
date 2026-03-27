from __future__ import annotations

from dataclasses import dataclass

from langchain_chroma import Chroma # type: ignore
from langchain_core.documents import Document

from .config import VECTORSTORE_DIR, settings
from .embeddings import LocalSentenceTransformerEmbeddings
from .models import Citation, NormalizedSource
from .utils import slugify


@dataclass(frozen=True)
class IndexedChunk:
    chunk_id: str
    text: str
    metadata: dict[str, str | int | None]


def chunk_sources(sources: list[NormalizedSource]) -> list[IndexedChunk]:
    chunks: list[IndexedChunk] = []
    word_target = max(150, settings.chunk_size_tokens // 2)
    word_overlap = max(25, settings.chunk_overlap_tokens // 2)
    for source in sources:
        for section in source.sections:
            words = section.text.split()
            if not words:
                continue
            start = 0
            part = 0
            while start < len(words):
                end = min(len(words), start + word_target)
                chunk_words = words[start:end]
                chunk_id = f"{source.source_id}__{slugify(section.heading)}__{part}"
                chunks.append(
                    IndexedChunk(
                        chunk_id=chunk_id,
                        text=" ".join(chunk_words),
                        metadata={
                            "chunk_id": chunk_id,
                            "source_id": source.source_id,
                            "url": source.url,
                            "heading": section.heading,
                            "doc_type": source.doc_type,
                            "program": source.program,
                            "course_code": source.course_code,
                            "catalog_year": settings.catalog_year,
                        },
                    )
                )
                if end == len(words):
                    break
                start = max(end - word_overlap, start + 1)
                part += 1
    return chunks


def build_vectorstore(sources: list[NormalizedSource], force: bool = False) -> Chroma:
    embeddings = LocalSentenceTransformerEmbeddings(settings.embedding_model, local_files_only=False)
    if VECTORSTORE_DIR.exists() and force:
        for path in VECTORSTORE_DIR.glob("**/*"):
            if path.is_file():
                path.unlink()
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    chunks = chunk_sources(sources)
    documents = [Document(page_content=chunk.text, metadata=chunk.metadata) for chunk in chunks]
    return Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(VECTORSTORE_DIR),
        collection_name="catalog_course_planner",
    )


def load_vectorstore() -> Chroma:
    embeddings = LocalSentenceTransformerEmbeddings(settings.embedding_model, local_files_only=True)
    return Chroma(
        collection_name="catalog_course_planner",
        embedding_function=embeddings,
        persist_directory=str(VECTORSTORE_DIR),
    )


def make_citations(documents: list[Document]) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, str, str]] = set()
    for document in documents:
        url = str(document.metadata.get("url", ""))
        heading = str(document.metadata.get("heading", ""))
        chunk_id = str(document.metadata.get("chunk_id", ""))
        key = (url, heading, chunk_id)
        if key not in seen and url and heading and chunk_id:
            seen.add(key)
            citations.append(Citation(url=url, heading=heading, chunk_id=chunk_id))
    return citations
