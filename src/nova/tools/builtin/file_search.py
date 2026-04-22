"""``file_search`` built-in tool.

Builds an in-memory vector index over opt-in directories and returns
the top-K most relevant files for a natural-language query. Uses the
zero-dependency ``HashingEmbedder`` by default; swap in
sentence-transformers or a cloud embedder for better quality.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from nova.tools.filter import Embedder, HashingEmbedder, cosine

TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".txt",
        ".md",
        ".rst",
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".json",
        ".toml",
        ".yaml",
        ".yml",
        ".csv",
        ".log",
        ".html",
        ".css",
        ".sh",
        ".go",
        ".rs",
        ".kt",
        ".java",
    }
)


@dataclass(frozen=True, slots=True)
class FileHit:
    path: Path
    score: float
    preview: str


@dataclass
class FileIndex:
    embedder: Embedder = field(default_factory=HashingEmbedder)
    max_bytes: int = 32_000
    _entries: list[tuple[Path, list[float], str]] = field(default_factory=list)

    def index_paths(self, paths: Iterable[Path]) -> int:
        """Index every text file under each directory; returns file count."""
        count = 0
        for root in paths:
            for path in _iter_text_files(root, self.max_bytes):
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                preview = content[:400]
                vec = self.embedder.embed(f"{path.name} {content[:2000]}")
                self._entries.append((path, vec, preview))
                count += 1
        return count

    def search(self, query: str, k: int = 5) -> list[FileHit]:
        if not self._entries:
            return []
        q_vec = self.embedder.embed(query)
        scored = [(p, cosine(q_vec, v), preview) for p, v, preview in self._entries]
        scored.sort(key=lambda row: row[1], reverse=True)
        return [FileHit(path=p, score=s, preview=prev) for p, s, prev in scored[:k]]

    def __len__(self) -> int:
        return len(self._entries)


def _iter_text_files(root: Path, max_bytes: int) -> Iterable[Path]:
    if root.is_file():
        if root.suffix.lower() in TEXT_EXTENSIONS and root.stat().st_size <= max_bytes:
            yield root
        return
    if not root.is_dir():
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            if path.stat().st_size > max_bytes:
                continue
        except OSError:
            continue
        yield path


__all__ = ["FileHit", "FileIndex", "TEXT_EXTENSIONS"]
