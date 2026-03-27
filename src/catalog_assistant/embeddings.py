from __future__ import annotations

import inspect
import os
from functools import cached_property

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


class LocalSentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str, local_files_only: bool = True) -> None:
        self.model_name = model_name
        self.local_files_only = local_files_only

    @cached_property
    def _model(self) -> SentenceTransformer:
        signature = inspect.signature(SentenceTransformer.__init__)
        if "local_files_only" in signature.parameters:
            return SentenceTransformer(self.model_name, local_files_only=self.local_files_only)
        return self._load_with_offline_env_compat()

    def _load_with_offline_env_compat(self) -> SentenceTransformer:
        keys = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
        previous = {key: os.environ.get(key) for key in keys}
        try:
            if self.local_files_only:
                os.environ["HF_HUB_OFFLINE"] = "1"
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
            else:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            return SentenceTransformer(self.model_name)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([text], normalize_embeddings=True).tolist()[0]
