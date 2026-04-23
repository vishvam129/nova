"""Long-term vector memory.

Protocol + in-memory store + lazy Chroma adapter. Supports per-user
namespaces and metadata-filtered recall.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from nova.tools.filter import Embedder, HashingEmbedder, cosine


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    namespace: str = "default"


@runtime_checkable
class VectorStore(Protocol):
    def add(self, record: MemoryRecord) -> None: ...

    def search(
        self,
        query: str,
        k: int = 5,
        namespace: str = "default",
        where: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]: ...

    def delete(self, record_id: str, namespace: str = "default") -> None: ...

    def __len__(self) -> int: ...


@dataclass
class InMemoryVectorStore:
    embedder: Embedder = field(default_factory=HashingEmbedder)
    _data: list[tuple[MemoryRecord, list[float]]] = field(default_factory=list)

    def add(self, record: MemoryRecord) -> None:
        self._data.append((record, self.embedder.embed(record.text)))

    def search(
        self,
        query: str,
        k: int = 5,
        namespace: str = "default",
        where: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]:
        q = self.embedder.embed(query)

        def keep(rec: MemoryRecord) -> bool:
            if rec.namespace != namespace:
                return False
            if where is None:
                return True
            return all(rec.metadata.get(k) == v for k, v in where.items())

        scored = [(rec, cosine(q, vec)) for rec, vec in self._data if keep(rec)]
        scored.sort(key=lambda row: row[1], reverse=True)
        return [rec for rec, _ in scored[:k]]

    def delete(self, record_id: str, namespace: str = "default") -> None:
        self._data = [
            (rec, vec)
            for rec, vec in self._data
            if not (rec.id == record_id and rec.namespace == namespace)
        ]

    def __len__(self) -> int:
        return len(self._data)


@dataclass
class ChromaStore:
    """Lazy Chroma adapter."""

    path: str = ".nova/chroma"
    collection: str = "nova"
    _client: Any = None
    _col: Any = None

    def _ensure(self) -> Any:
        if self._col is None:
            import chromadb

            self._client = chromadb.PersistentClient(path=self.path)
            self._col = self._client.get_or_create_collection(self.collection)
        return self._col

    def add(self, record: MemoryRecord) -> None:
        col = self._ensure()
        col.add(
            ids=[record.id],
            documents=[record.text],
            metadatas=[{**record.metadata, "namespace": record.namespace}],
        )

    def search(
        self,
        query: str,
        k: int = 5,
        namespace: str = "default",
        where: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]:
        col = self._ensure()
        filter_: dict[str, Any] = {"namespace": namespace}
        if where:
            filter_.update(where)
        result = col.query(query_texts=[query], n_results=k, where=filter_)
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        out: list[MemoryRecord] = []
        for rid, doc, meta in zip(ids, docs, metas, strict=True):
            ns = meta.pop("namespace", namespace) if isinstance(meta, dict) else namespace
            out.append(MemoryRecord(id=rid, text=doc, metadata=dict(meta or {}), namespace=ns))
        return out

    def delete(self, record_id: str, namespace: str = "default") -> None:
        col = self._ensure()
        col.delete(ids=[record_id], where={"namespace": namespace})

    def __len__(self) -> int:
        return int(self._ensure().count())


def records_from_texts(
    texts: Sequence[str],
    *,
    ids: Sequence[str] | None = None,
    namespace: str = "default",
) -> list[MemoryRecord]:
    ids_ = list(ids) if ids is not None else [f"m-{i}" for i in range(len(texts))]
    return [
        MemoryRecord(id=i, text=t, namespace=namespace) for i, t in zip(ids_, texts, strict=True)
    ]


__all__ = [
    "ChromaStore",
    "InMemoryVectorStore",
    "MemoryRecord",
    "VectorStore",
    "records_from_texts",
]
