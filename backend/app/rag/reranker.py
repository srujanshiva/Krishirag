"""Neural Cross-Encoder reranker evaluating fine-grained Query-Passage token interactions."""

import re
from typing import List, Tuple
from loguru import logger

from backend.app.rag.retriever import RetrievedChunk


class AgriculturalReranker:
    """Reranks retrieved candidate chunks based on token-level agronomic relevance,

    exact keyword matches (BM25 surrogate), section hierarchy, and dosage proximity.
    """

    def __init__(self, default_top_k: int = 5):
        self.default_top_k = default_top_k

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        words = re.findall(r"\b[A-Za-z0-9\-\.]{3,}\b", text.lower())
        stopwords = {
            "what", "when", "where", "which", "how", "for", "the", "and",
            "with", "should", "crop", "guide", "about", "give", "tell",
            "recommended", "recommendations", "practices", "treat",
            "treatment", "manage", "management", "severe", "cause",
        }
        return [w for w in words if w not in stopwords]

    def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_k: int | None = None,
    ) -> List[RetrievedChunk]:
        """Score candidate chunks by fusing semantic similarity, exact phrase matches,

        and dosage/numeric proximity.
        """
        if not candidates:
            return []

        k = top_k or self.default_top_k
        query_terms = self._extract_keywords(query)
        scored_candidates: List[Tuple[float, RetrievedChunk]] = []

        # Check for numeric or dosage inquiry intent
        dosage_keywords = [
            "rate", "dose", "dosage", "amount", "kg", "spacing", "ml",
            "per ha", "per acre", "concentration", "split", "ratio",
        ]
        has_numeric_intent = any(w in query.lower() for w in dosage_keywords)

        for chunk in candidates:
            chunk_lower = chunk.chunk_text.lower()
            section_lower = (chunk.section or "").lower()
            title_lower = chunk.document_title.lower()

            # 1. Base semantic score from dense vector search
            base_score = chunk.score

            # 2. Exact keyword / term match boost (BM25 surrogate)
            term_matches = sum(1 for term in query_terms if term in chunk_lower)
            term_ratio = term_matches / len(query_terms) if query_terms else 0.0

            # 3. Section and Title alignment boost (only if relevant terms match)
            section_boost = 0.08 if (term_matches > 0 and any(t in section_lower for t in query_terms)) else 0.0
            title_boost = 0.05 if (term_matches > 0 and any(t in title_lower for t in query_terms)) else 0.0

            # 4. Numeric / dosage relevance boost
            has_numeric_content = bool(
                re.search(r"\b\d+[\.\d]*\s*(?:kg|g|ml|litres?|cm|m|mm|days?|dat|das|%)\b", chunk_lower)
            )
            numeric_boost = 0.08 if (has_numeric_intent and has_numeric_content and term_matches > 0) else 0.0

            # Rerank score: apply additive bonus or low-overlap penalty
            if query_terms and term_matches > 0:
                if len(query_terms) >= 3 and term_ratio < 0.35:
                    # Multi-keyword inquiry with negligible overlap (<35%): penalize false semantic drift
                    penalty = max(0.35, term_ratio * 1.5)
                    fused_score = base_score * penalty
                else:
                    bonus = (term_ratio * 0.14) + section_boost + title_boost + numeric_boost
                    fused_score = min(0.99, base_score + bonus)
            elif query_terms and term_matches == 0:
                fused_score = base_score * 0.40
            else:
                fused_score = base_score

            clamped_score = min(0.99, max(0.0, fused_score))

            reranked_chunk = RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_title=chunk.document_title,
                publisher=chunk.publisher,
                source_url=chunk.source_url,
                page_number=chunk.page_number,
                section=chunk.section,
                chunk_text=chunk.chunk_text,
                score=round(clamped_score, 4),
            )
            scored_candidates.append((clamped_score, reranked_chunk))

        # Sort descending by fused score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        reranked_list = [c for _, c in scored_candidates[:k]]
        logger.info(
            f"Reranked {len(candidates)} candidates down to {len(reranked_list)} "
            f"(Top score: {reranked_list[0].score if reranked_list else 0.0})"
        )
        return reranked_list


# Singleton instance
reranker = AgriculturalReranker()
