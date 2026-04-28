"""Agent-callable memory tools (MemGPT-style).

The agent calls these directly:
    memory_add(content, importance=0.5)
    memory_edit(memory_id, new_content)
    memory_forget(memory_id)
    memory_list(query=None, top_k=10)

Backs onto MemoryItem + MemoryDecay so importance/recency drive ranking.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from nova.memory.decay import MemoryDecay, MemoryItem


@dataclass
class _Stored:
    id: str
    item: MemoryItem


@dataclass
class AgentMemoryTool:
    """MemGPT-style memory accessible to the agent as tool calls."""

    decay: MemoryDecay = field(default_factory=MemoryDecay)
    path: Path | None = None
    _items: dict[str, _Stored] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.path and self.path.exists():
            data = json.loads(self.path.read_text() or "[]")
            for entry in data:
                item = MemoryItem(
                    content=entry["content"],
                    importance=entry["importance"],
                    created_at=datetime.fromisoformat(entry["created_at"]),
                    last_accessed=datetime.fromisoformat(entry["last_accessed"]),
                    access_count=entry.get("access_count", 0),
                )
                self._items[entry["id"]] = _Stored(id=entry["id"], item=item)

    def add(self, content: str, importance: float = 0.5) -> str:
        mem_id = uuid4().hex[:12]
        self._items[mem_id] = _Stored(
            id=mem_id, item=MemoryItem(content=content, importance=importance)
        )
        self._save()
        return mem_id

    def edit(self, memory_id: str, new_content: str) -> bool:
        stored = self._items.get(memory_id)
        if stored is None:
            return False
        stored.item.content = new_content
        stored.item.last_accessed = datetime.now()
        self._save()
        return True

    def forget(self, memory_id: str) -> bool:
        if memory_id not in self._items:
            return False
        del self._items[memory_id]
        self._save()
        return True

    def get(self, memory_id: str) -> MemoryItem | None:
        stored = self._items.get(memory_id)
        if stored is None:
            return None
        stored.item.touch()
        return stored.item

    def list(self, query: str | None = None, top_k: int = 10) -> list[tuple[str, MemoryItem]]:
        items = [(sid, s.item) for sid, s in self._items.items()]
        if query:
            q = query.lower()
            items = [(sid, it) for sid, it in items if q in it.content.lower()]
        ranked = self.decay.rank([it for _, it in items])
        ranked_ids = {id(it): score for it, score in ranked}
        items.sort(key=lambda pair: ranked_ids.get(id(pair[1]), 0.0), reverse=True)
        return items[:top_k]

    def __len__(self) -> int:
        return len(self._items)

    def prune_decayed(self) -> int:
        """Drop memories whose decay score is below threshold; return count removed."""
        to_drop = [sid for sid, s in self._items.items() if self.decay.should_prune(s.item)]
        for sid in to_drop:
            del self._items[sid]
        if to_drop:
            self._save()
        return len(to_drop)

    def _save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "id": stored.id,
                "content": stored.item.content,
                "importance": stored.item.importance,
                "created_at": stored.item.created_at.isoformat(),
                "last_accessed": stored.item.last_accessed.isoformat(),
                "access_count": stored.item.access_count,
            }
            for stored in self._items.values()
        ]
        self.path.write_text(json.dumps(data, indent=2))


__all__ = ["AgentMemoryTool"]
