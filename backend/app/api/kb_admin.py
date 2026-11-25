"""
Admin endpoints for Knowledge Base management.
Allows uploading and hot-indexing documents (PDF, DOCX, CSV, TXT, MD) without service restart.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status

from app.rag.ingest import ChromaKnowledgeBase
from app.rag.tools import get_retriever

router = APIRouter(prefix="/kb", tags=["Knowledge Base Admin"])

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../knowledge_base/uploads")
)
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Hot-Ingest Document into Knowledge Base",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (.pdf, .docx, .txt, .md, .csv)"),
    category: str = Form(None, description="Optional category label (pricing, faq, specs)"),
) -> Dict[str, Any]:
    """
    Uploads a document file to the knowledge base and indexes it into ChromaDB in real-time.
    Immediately updates the hybrid vector + BM25 index with zero server downtime.
    """
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    ext = Path(filename).suffix.lower()
    if ext not in {".pdf", ".docx", ".txt", ".md", ".csv"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed: .pdf, .docx, .txt, .md, .csv",
        )

    dest_path = os.path.join(UPLOAD_DIR, filename)

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Hot-ingest into ChromaDB
    kb = ChromaKnowledgeBase()
    chunks_count = kb.ingest_file(dest_path, category=category)

    # Re-sync in-memory BM25 index
    retriever = get_retriever()
    retriever._sync_bm25_index()

    return {
        "status": "success",
        "filename": filename,
        "chunks_indexed": chunks_count,
        "message": f"Successfully ingested {chunks_count} chunks from '{filename}'. Available immediately for RAG.",
    }


@router.get(
    "/status",
    summary="Get Knowledge Base Indexing Status",
)
async def get_kb_status() -> Dict[str, Any]:
    """
    Returns total indexed chunks and document collection metadata.
    """
    kb = ChromaKnowledgeBase()
    count = kb.collection.count()
    return {
        "collection": kb.collection.name,
        "total_chunks": count,
        "persist_dir": kb.persist_dir,
    }
