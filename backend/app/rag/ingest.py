"""
Document Ingestion & Vector Indexing Pipeline for VoxSell Knowledge Base.

Supports PDF, DOCX, TXT, MD, and CSV files, chunks text into ~500 token windows with 50-token overlap,
computes normalized embeddings, and persists to ChromaDB with rich metadata.
"""

import os
import re
import csv
import glob
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

logger = logging.getLogger("voxsell.rag.ingest")
settings = get_settings()

COLLECTION_NAME = "voxsell_knowledge_base"


class DocumentChunker:
    """Chunks documents using natural sentence & paragraph boundaries with overlap."""

    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, source: str, category: str = "general") -> List[Dict[str, Any]]:
        """
        Splits raw text into overlapping semantic blocks.
        """
        # Clean extra whitespaces
        cleaned = re.sub(r'\n{3,}', '\n\n', text).strip()
        if not cleaned:
            return []

        chunks: List[Dict[str, Any]] = []
        start = 0
        text_len = len(cleaned)
        chunk_idx = 0

        while start < text_len:
            end = min(start + self.chunk_size, text_len)

            # Try to snap to nearest sentence or paragraph boundary
            if end < text_len:
                boundary = cleaned.rfind('\n\n', start, end)
                if boundary == -1 or boundary < start + (self.chunk_size // 2):
                    boundary = cleaned.rfind('. ', start, end)
                if boundary != -1 and boundary > start + (self.chunk_size // 2):
                    end = boundary + 1

            chunk_content = cleaned[start:end].strip()
            if chunk_content:
                chunk_id = f"{Path(source).stem}_{chunk_idx}"
                chunks.append({
                    "id": chunk_id,
                    "text": chunk_content,
                    "metadata": {
                        "source": os.path.basename(source),
                        "category": category,
                        "chunk_index": chunk_idx,
                        "char_length": len(chunk_content),
                    }
                })
                chunk_idx += 1

            start += self.chunk_size - self.chunk_overlap

        return chunks


class DocumentParser:
    """Parses text from various document file extensions."""

    @staticmethod
    def parse_file(file_path: str) -> str:
        ext = Path(file_path).suffix.lower()

        if ext in {".txt", ".md"}:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        elif ext == ".csv":
            content = []
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                for row in reader:
                    content.append(" | ".join(row))
            return "\n".join(content)

        elif ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                pages = [p.extract_text() or "" for p in reader.pages]
                return "\n\n".join(pages)
            except Exception as e:
                logger.error(f"Error parsing PDF {file_path}: {e}")
                return ""

        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(file_path)
                return "\n".join([p.text for p in doc.paragraphs if p.text])
            except Exception as e:
                logger.error(f"Error parsing DOCX {file_path}: {e}")
                return ""

        else:
            logger.warning(f"Unsupported file format: {ext} for {file_path}")
            return ""


class EmbeddingGenerator:
    """
    Generates dense embeddings for documents and queries.
    Uses OpenAI text-embedding-3-small when API key is present,
    or a high-speed deterministic dense hashing vector for zero-dependency local runs.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.LLM_API_KEY
        self.dim = 384

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a batch of texts.
        """
        if self.api_key and len(self.api_key) > 10:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                logger.warning(f"OpenAI embedding call failed ({e}). Falling back to local dense vector.")

        # High-speed deterministic 384-dimensional dense semantic hashing vector
        embeddings = []
        for text in texts:
            vec = [0.0] * self.dim
            words = re.findall(r'\b[a-zA-Z0-9_\$%-]+\b', text.lower())
            for i, w in enumerate(words):
                h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dim
                sign = 1.0 if (h >> 1) % 2 == 0 else -1.0
                vec[idx] += sign * (1.0 / (1.0 + 0.05 * i))

            # Normalize to unit vector
            norm = sum(x * x for x in vec) ** 0.5
            if norm > 0:
                vec = [x / norm for x in vec]
            embeddings.append(vec)

        return embeddings


class ChromaKnowledgeBase:
    """
    Interface for ChromaDB vector collection management and ingestion.
    """

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        self.chunker = DocumentChunker()
        self.embedder = EmbeddingGenerator()

    def ingest_file(self, file_path: str, category: Optional[str] = None) -> int:
        """
        Parses, chunks, embeds, and indexes a single document file into ChromaDB.
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return 0

        raw_text = DocumentParser.parse_file(file_path)
        if not raw_text:
            logger.warning(f"No extractable text in {file_path}")
            return 0

        cat = category or Path(file_path).stem
        chunks = self.chunker.chunk_text(raw_text, source=file_path, category=cat)
        if not chunks:
            return 0

        ids = [c["id"] for c in chunks]
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        embeddings = self.embedder.generate_embeddings(texts)

        # Upsert into ChromaDB
        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info(f"Ingested {len(chunks)} chunks from {file_path} into ChromaDB collection '{COLLECTION_NAME}'.")
        return len(chunks)

    def ingest_directory(self, dir_path: str) -> int:
        """
        Recursively scans and indexes all supported files in a directory.
        """
        supported_exts = ["*.md", "*.txt", "*.pdf", "*.docx", "*.csv"]
        total_chunks = 0

        for ext in supported_exts:
            for file_path in glob.glob(os.path.join(dir_path, ext)):
                chunks_count = self.ingest_file(file_path)
                total_chunks += chunks_count

        logger.info(f"Directory ingestion complete: {total_chunks} total chunks indexed from {dir_path}.")
        return total_chunks


def main():
    """CLI ingestion utility for knowledge_base/."""
    kb_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge_base"))
    print(f"[*] Ingesting knowledge base from: {kb_path}")
    kb = ChromaKnowledgeBase()
    count = kb.ingest_directory(kb_path)
    print(f"[SUCCESS] Ingested {count} chunks into ChromaDB.")


if __name__ == "__main__":
    main()
