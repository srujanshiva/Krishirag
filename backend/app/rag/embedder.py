"""Local embedding generation using FastEmbed ONNX runtime."""

from typing import List, Optional
from fastembed import TextEmbedding
from loguru import logger
from backend.app.config import settings


class FastEmbedder:
    """Wrapper around FastEmbed TextEmbedding ensuring singleton model lifecycle."""

    _model: Optional[TextEmbedding] = None
    _current_model_name: Optional[str] = None

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.dimension: int = 384

        if FastEmbedder._model is None or FastEmbedder._current_model_name != self.model_name:
            logger.info(f"Initializing FastEmbed model: {self.model_name}")
            FastEmbedder._model = TextEmbedding(model_name=self.model_name)
            FastEmbedder._current_model_name = self.model_name

        self.model = FastEmbedder._model

    def embed_documents(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        """Compute embeddings for a batch of text passages."""
        if not texts:
            return []
        embeddings_generator = self.model.embed(texts, batch_size=batch_size)
        return [vector.tolist() for vector in embeddings_generator]

    def embed_query(self, query: str) -> List[float]:
        """Compute embedding for a single user search query."""
        results = self.embed_documents([query])
        if results:
            return results[0]
        return [0.0] * self.dimension
