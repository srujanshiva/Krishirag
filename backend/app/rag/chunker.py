"""Text chunking with provenance and deterministic vector ID generation."""

import re
import uuid
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class TextChunk:
    chunk_index: int
    chunk_text: str
    vector_id: str
    page_number: Optional[int]
    section: Optional[str]


class DocumentChunker:
    """Sliding-window chunker with sentence and heading awareness."""

    def __init__(self, target_words: int = 320, overlap_words: int = 60):
        self.target_words = max(50, target_words)
        self.overlap_words = min(self.target_words // 2, max(0, overlap_words))

    @staticmethod
    def generate_vector_id(doc_checksum: str, chunk_index: int) -> str:
        """Deterministically generates a UUID v5 point ID from document checksum and chunk index."""
        seed = f"{doc_checksum}:{chunk_index}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))

    @staticmethod
    def detect_section_heading(text: str) -> Optional[str]:
        """Attempt to extract the primary section heading from a text block."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:5]:
            # Look for numbered headings or uppercase titles
            if re.match(r"^(\d+[\.\)]|[A-Z\s]{4,}|[A-Z][a-z]+(\s+[A-Z][a-z]+)*:)", line):
                if len(line) <= 100:
                    return line
        return None

    def chunk_pages(
        self,
        pages: List[Tuple[int, str]],
        doc_checksum: str,
    ) -> List[TextChunk]:
        """Split a list of (page_number, text) tuples into structured TextChunks."""
        chunks: List[TextChunk] = []
        global_chunk_idx = 0
        current_section: Optional[str] = None

        for page_num, raw_text in pages:
            if not raw_text or not raw_text.strip():
                continue

            detected = self.detect_section_heading(raw_text)
            if detected:
                current_section = detected

            # Clean and tokenize into words while preserving sentence flow
            cleaned_text = re.sub(r"[ \t]+", " ", raw_text).strip()
            words = cleaned_text.split()
            if not words:
                continue

            step = self.target_words - self.overlap_words
            if step <= 0:
                step = self.target_words

            start_idx = 0
            while start_idx < len(words):
                end_idx = min(start_idx + self.target_words, len(words))
                chunk_slice = words[start_idx:end_idx]
                chunk_str = " ".join(chunk_slice)

                vector_id = self.generate_vector_id(doc_checksum, global_chunk_idx)
                chunks.append(
                    TextChunk(
                        chunk_index=global_chunk_idx,
                        chunk_text=chunk_str,
                        vector_id=vector_id,
                        page_number=page_num,
                        section=current_section,
                    )
                )
                global_chunk_idx += 1

                if end_idx == len(words):
                    break
                start_idx += step

        return chunks
