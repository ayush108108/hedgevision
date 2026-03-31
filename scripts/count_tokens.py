#!/usr/bin/env python3
"""
Walk the repository and count tokens for each text file using tiktoken.

Usage:
    python scripts/count_tokens.py [path]

If no path is provided, it defaults to the current directory.

The default filter excludes typical virtual environments, metadata folders and
other dev/tool directories (``.git``, ``venv``, ``node_modules``, etc.).  It
also limits the scan to source/file types that a developer normally cares
about.
"""

import sys
import os
from pathlib import Path

import tiktoken  # ensure your venv has tiktoken installed

# choose any encoding appropriate for your models
ENC = tiktoken.get_encoding("cl100k_base")

# directories to skip entirely
EXCLUDE_DIRS = {
    "venv",
    ".venv",
    ".git",
    "node_modules",
    "__pycache__",
    "build",
    "dist",
    ".eggs",
    "frontend-v2/node_modules",
}

# file extensions that we consider text/code for token counting
INCLUDE_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".txt",
    ".sh",
    ".sql",
    ".dockerfile",
    ".env",
}


def count_tokens_in_text(text: str) -> int:
    return len(ENC.encode(text))


def is_text_file(path: Path) -> bool:
    # look at extension; some files (Dockerfile) may not have a dot extension
    if path.suffix.lower() in INCLUDE_EXTS:
        return True
    name = path.name.lower()
    if name == "dockerfile" or name.endswith(".dockerfile"):
        return True
    return False


def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False


def main(root: Path):
    total = 0
    for p in root.rglob("*"):
        if p.is_file():
            if should_skip(p):
                continue
            if not is_text_file(p):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            tokens = count_tokens_in_text(text)
            total += tokens
            print(f"{p.relative_to(root)}: {tokens} tokens")
    print("\nTotal tokens:", total)


if __name__ == "__main__":
    root_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    main(root_dir)
