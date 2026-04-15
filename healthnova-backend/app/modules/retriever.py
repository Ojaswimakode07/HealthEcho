from __future__ import annotations

import json
import re
from pathlib import Path

from app.core.config import settings
from app.modules.pdf_parser import parse_pdf_text

try:
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
except Exception:  # pragma: no cover
    FAISS = None
    HuggingFaceEmbeddings = None
    RecursiveCharacterTextSplitter = None
    Document = None


_TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".csv"}
_DOC_CACHE: list[dict[str, str]] | None = None
_VECTORSTORE_CACHE = None
_VECTORSTORE_READY = False
_EMBEDDINGS_CACHE = None
_EMBEDDINGS_READY = False


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(raw_path: str, fallback: str) -> Path:
    value = raw_path or fallback
    path = Path(value)
    if path.is_absolute():
        return path
    return (_backend_root() / path).resolve()


def _docs_dir() -> Path:
    return _resolve_path(getattr(settings, "medical_docs_dir", "../medical_docs"), "../medical_docs")


def _vectorstore_dir() -> Path:
    return _resolve_path(getattr(settings, "vectorstore_dir", "../vectorstore"), "../vectorstore")


def _iter_source_files() -> list[Path]:
    docs_dir = _docs_dir()
    if not docs_dir.exists():
        return []
    files: list[Path] = []
    for path in docs_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".pdf" or path.suffix.lower() in _TEXT_EXTENSIONS:
            files.append(path)
    return sorted(files)


def _read_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf_text(path)
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def _load_plain_docs() -> list[dict[str, str]]:
    global _DOC_CACHE
    if _DOC_CACHE is not None:
        return _DOC_CACHE

    cache_path = _vectorstore_dir() / "plain_docs_cache.json"
    if cache_path.exists():
      try:
          cached = json.loads(cache_path.read_text(encoding="utf-8"))
          if isinstance(cached, list):
              _DOC_CACHE = [
                  {
                      "source": str(item.get("source", "Medical context")),
                      "content": str(item.get("content", "")),
                  }
                  for item in cached
                  if isinstance(item, dict) and str(item.get("content", "")).strip()
              ]
              if _DOC_CACHE:
                  return _DOC_CACHE
      except Exception:
          pass

    docs: list[dict[str, str]] = []
    for file_path in _iter_source_files():
        text = _read_text(file_path)
        for chunk in _chunk_text(text):
            docs.append({"source": file_path.name, "content": chunk})

    _DOC_CACHE = docs
    return docs


def _embedding_model():
    global _EMBEDDINGS_CACHE, _EMBEDDINGS_READY
    if _EMBEDDINGS_READY:
        return _EMBEDDINGS_CACHE
    if HuggingFaceEmbeddings is None:
        _EMBEDDINGS_READY = True
        return None
    try:
        _EMBEDDINGS_CACHE = HuggingFaceEmbeddings(
            model_name=getattr(settings, "embeddings_model", "sentence-transformers/all-MiniLM-L6-v2")
        )
    except Exception:
        _EMBEDDINGS_CACHE = None
    _EMBEDDINGS_READY = True
    return _EMBEDDINGS_CACHE


def ingest_medical_docs() -> tuple[int, list[str]]:
    files = _iter_source_files()
    docs = _load_plain_docs()
    vectorstore_path = _vectorstore_dir()
    vectorstore_path.mkdir(parents=True, exist_ok=True)

    embeddings = _embedding_model()
    if embeddings and FAISS and RecursiveCharacterTextSplitter and Document:
        try:
            raw_documents: list[Document] = []
            splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
            for file_path in files:
                text = _read_text(file_path)
                if not text.strip():
                    continue
                chunks = splitter.split_text(text)
                raw_documents.extend(
                    Document(page_content=chunk, metadata={"source": file_path.name}) for chunk in chunks if chunk.strip()
                )
            if raw_documents:
                store = FAISS.from_documents(raw_documents, embeddings)
                store.save_local(str(vectorstore_path))
        except Exception:
            pass

    cache_path = vectorstore_path / "plain_docs_cache.json"
    try:
        cache_path.write_text(json.dumps(docs, ensure_ascii=True), encoding="utf-8")
    except Exception:
        pass

    return len(docs), [path.name for path in files]


def load_vectorstore():
    global _VECTORSTORE_CACHE, _VECTORSTORE_READY
    if _VECTORSTORE_READY:
        return _VECTORSTORE_CACHE

    embeddings = _embedding_model()
    if not (embeddings and FAISS):
        _VECTORSTORE_READY = True
        return None

    vectorstore_path = _vectorstore_dir()
    if not vectorstore_path.exists():
        _VECTORSTORE_READY = True
        return None

    try:
        _VECTORSTORE_CACHE = FAISS.load_local(
            str(vectorstore_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )
    except Exception:
        _VECTORSTORE_CACHE = None

    _VECTORSTORE_READY = True
    return _VECTORSTORE_CACHE


def _score_chunk(content: str, query_terms: list[str]) -> float:
    lowered = content.lower()
    score = 0.0
    for term in query_terms:
        if term in lowered:
            score += 1.0
    return score


def retrieve_context(query: str, top_k: int = 5) -> list[dict[str, str | float]]:
    query = (query or "").strip()
    if not query:
        return []

    vectorstore = load_vectorstore()
    if vectorstore is not None:
        try:
            results = vectorstore.similarity_search_with_score(query, k=top_k)
            return [
                {
                    "source": doc.metadata.get("source", "Medical context"),
                    "content": doc.page_content,
                    "score": float(score),
                }
                for doc, score in results
            ]
        except Exception:
            pass

    docs = _load_plain_docs()
    if not docs:
        return []

    query_terms = [term for term in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(term) > 2]
    ranked = []
    for entry in docs:
        score = _score_chunk(entry["content"], query_terms)
        if score > 0:
            ranked.append(
                {
                    "source": entry["source"],
                    "content": entry["content"],
                    "score": score,
                }
            )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_k]


def warm_retrieval_assets() -> None:
    _load_plain_docs()
    load_vectorstore()
