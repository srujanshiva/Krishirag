"""Citation parsing, verification against retrieved chunks, and hallucination stripping."""

import re
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple
from loguru import logger

from backend.app.rag.retriever import RetrievedChunk
from backend.app.schemas.citations import CitationResponse

# Pattern matching citation markers like [UUID], [chunk_id], [chunk: id]
CITATION_PATTERN = re.compile(
    r"\[(?:chunk[:\s]*)?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}|[a-zA-Z0-9_\-:]{6,64})\]",
    re.IGNORECASE,
)


@dataclass
class ValidatedCitations:
    cleaned_answer: str
    citations: List[CitationResponse]
    stripped_count: int
    valid_count: int


class CitationValidator:
    """Validates citations in LLM-generated answers against retrieved evidence passages."""

    @classmethod
    def validate(
        cls,
        raw_answer: str,
        retrieved_chunks: List[RetrievedChunk],
    ) -> ValidatedCitations:
        """Parse, verify, and filter citations against retrieved chunks."""
        valid_chunks_map: Dict[str, RetrievedChunk] = {
            chunk.chunk_id: chunk for chunk in retrieved_chunks
        }

        matched_ids: List[str] = CITATION_PATTERN.findall(raw_answer)
        stripped_count = 0
        accepted_chunk_ids: Set[str] = set()

        def replacement_fn(match: re.Match) -> str:
            nonlocal stripped_count
            full_match = match.group(0)
            cand_id = match.group(1).strip()

            if cand_id in valid_chunks_map:
                accepted_chunk_ids.add(cand_id)
                return full_match  # Keep valid citation in text
            else:
                # Hallucinated or non-existent chunk ID
                stripped_count += 1
                logger.warning(
                    f"Stripping hallucinated/unretrieved citation ID '{cand_id}' from generated answer."
                )
                return ""  # Strip out of output text

        cleaned_text = CITATION_PATTERN.sub(replacement_fn, raw_answer)
        # Clean up any leftover double spaces or orphaned brackets/spaces
        cleaned_text = re.sub(r" +", " ", cleaned_text)
        cleaned_text = re.sub(r" \.", ".", cleaned_text).strip()

        # Build structured CitationResponse list preserving order of retrieved chunks
        citations_list: List[CitationResponse] = []
        # If model cited specific chunks, include those; otherwise if grounded, include cited chunks
        for chunk in retrieved_chunks:
            if chunk.chunk_id in accepted_chunk_ids:
                excerpt = chunk.chunk_text[:300].strip()
                if len(chunk.chunk_text) > 300:
                    excerpt += "..."

                citations_list.append(
                    CitationResponse(
                        chunk_id=chunk.chunk_id,
                        document_title=chunk.document_title,
                        publisher=chunk.publisher,
                        source_url=chunk.source_url,
                        publication_date=None,
                        page_number=chunk.page_number,
                        section=chunk.section,
                        excerpt=excerpt,
                    )
                )

        logger.info(
            f"Citation validation complete: {len(citations_list)} valid citations, "
            f"{stripped_count} hallucinated citations stripped."
        )

        return ValidatedCitations(
            cleaned_answer=cleaned_text,
            citations=citations_list,
            stripped_count=stripped_count,
            valid_count=len(citations_list),
        )
