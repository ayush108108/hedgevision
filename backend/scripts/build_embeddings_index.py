"""
Build an embeddings-backed code index using OpenAI embeddings.
Produces backend/code_index.json with fields:
{
  "meta": {"model": "text-embedding-3-small", "generated_at": "...", "chunk_lines": 200, "chunk_overlap": 30},
  "chunk_count": N,
  "chunks": [
    {"path": "api/services/foo.py", "start_line": 1, "end_line": 180, "content": "...", "embedding": [..] },
    ...
  ]
}
This index is consumed by run_dual_provider_audit.py.
"""
from __future__ import annotations

import os
import json
import time
import argparse
from typing import List, Dict, Any, Iterable, Tuple

# Prefer same include/exclude as rebuild script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_PATH = os.path.join(ROOT, "code_index.json")
SOURCE_DIRS = [
    os.path.join(ROOT, "api"),
    os.path.join(ROOT, "scripts"),
    os.path.join(ROOT, "migrations"),
    os.path.join(ROOT, "clients"),
    os.path.join(ROOT, "tests"),
]
INCLUDE_EXTS = {".py", ".md", ".sql", ".yml", ".yaml", ".toml"}
EXCLUDE_DIR_SNIPPETS = {"__pycache__", "htmlcov", "node_modules", ".git", "venv"}
MAX_FILE_BYTES = 400_000

# Chunking params
CHUNK_LINES = 200
CHUNK_OVERLAP = 30
MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def load_dotenv_into_process() -> None:
    """Minimal .env loader (root and backend/api/.env) without extra deps."""
    candidates = [
        os.path.join(os.path.dirname(ROOT), ".env"),  # repo root
        os.path.join(ROOT, ".env"),  # backend/.env (if any)
        os.path.join(ROOT, "api", ".env"),  # backend/api/.env
        os.path.abspath(os.path.join(ROOT, "..", ".env")),
    ]
    for p in candidates:
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" not in line or line.strip().startswith("#"):
                        continue
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v)
        except Exception:
            pass


def should_index(path: str) -> bool:
    if any(s in path for s in EXCLUDE_DIR_SNIPPETS):
        return False
    _, ext = os.path.splitext(path)
    if ext.lower() not in INCLUDE_EXTS:
        return False
    try:
        return os.path.getsize(path) <= MAX_FILE_BYTES
    except OSError:
        return False


def iter_files() -> Iterable[str]:
    for src in SOURCE_DIRS:
        if not os.path.isdir(src):
            continue
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if not any(x in os.path.join(root, d) for x in EXCLUDE_DIR_SNIPPETS)]
            for fn in files:
                full = os.path.join(root, fn)
                if should_index(full):
                    yield full


def chunk_lines(lines: List[str], chunk_lines: int, overlap: int) -> Iterable[Tuple[int, int, str]]:
    n = len(lines)
    if n == 0:
        return []
    start = 0
    while start < n:
        end = min(start + chunk_lines, n)
        content = "".join(lines[start:end])
        if content.strip():
            yield start + 1, end, content
        if end == n:
            break
        start = max(end - overlap, start + 1)


def build_chunks() -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    for path in iter_files():
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            continue
        for s, e, content in chunk_lines(lines, CHUNK_LINES, CHUNK_OVERLAP):
            chunks.append({
                "path": rel,
                "start_line": s,
                "end_line": e,
                "content": content,
            })
    return chunks


def embed_chunks(chunks: List[Dict[str, Any]], batch_size: int = 64) -> None:
    from openai import OpenAI  # type: ignore
    load_dotenv_into_process()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY not set in environment or .env")
    client = OpenAI(api_key=api_key)

    # Batch embed contents
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        inputs = [c["content"] for c in batch]
        resp = client.embeddings.create(model=MODEL, input=inputs)
        if len(resp.data) != len(batch):
            raise RuntimeError("Embeddings count mismatch")
        for c, d in zip(batch, resp.data):
            c["embedding"] = d.embedding


def timestamp_utc() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def main() -> None:
    parser = argparse.ArgumentParser(description="Build embeddings-backed code index using OpenAI")
    parser.add_argument("--out", type=str, default=OUT_PATH, help="Stable index path (also used as fallback). Default: backend/code_index.json")
    parser.add_argument("--versioned", action="store_true", help="Also write a versioned file with UTC timestamp suffix")
    parser.add_argument("--no-stable", action="store_true", help="Do not write the stable out path; only write the versioned file")
    parser.add_argument("--model", type=str, default=MODEL, help="Embedding model (default: text-embedding-3-small)")
    args = parser.parse_args()
    # Update model global after parsing (avoid prior use before global declaration)
    globals()['MODEL'] = args.model
    # Build chunks
    chunks = build_chunks()
    if not chunks:
        raise SystemExit("No chunks found to index")

    # Embed
    embed_chunks(chunks)

    # Write index
    payload = {
        "meta": {
            "model": MODEL,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "chunk_lines": CHUNK_LINES,
            "chunk_overlap": CHUNK_OVERLAP,
        },
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    ts_suffix = timestamp_utc()
    out_stable = os.path.abspath(args.out)
    out_versioned = os.path.splitext(out_stable)
    out_versioned = f"{out_versioned[0]}_{ts_suffix}{out_versioned[1]}"

    if args.versioned or args.no_stable:
        with open(out_versioned, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        print(f"Built versioned embeddings index at {out_versioned} with {len(chunks)} chunks using {MODEL}")

    if not args.no_stable:
        with open(out_stable, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        print(f"Built embeddings index at {out_stable} with {len(chunks)} chunks using {MODEL}")


if __name__ == "__main__":
    main()
