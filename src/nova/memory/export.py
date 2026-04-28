"""Memory export — JSON + Markdown for GDPR-grade data portability.

The user can request all stored memories at any time via these helpers.
JSON is the canonical, lossless format; Markdown is a human-readable
companion document.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any


def to_json(memories: Iterable[Mapping[str, Any]]) -> str:
    """Serialize memories as a stable, indented JSON document."""
    payload = {
        "exported_at": datetime.now().isoformat(),
        "schema_version": 1,
        "memories": [dict(m) for m in memories],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def to_markdown(memories: Iterable[Mapping[str, Any]], title: str = "Nova memory export") -> str:
    """Render memories as a Markdown document."""
    items = list(memories)
    lines = [
        f"# {title}",
        "",
        f"Exported {datetime.now().isoformat()}",
        f"Total memories: {len(items)}",
        "",
        "---",
        "",
    ]
    for i, m in enumerate(items, 1):
        lines.append(f"## {i}. {m.get('content', '(no content)')}")
        for key in sorted(k for k in m if k != "content"):
            lines.append(f"- **{key}**: {m[key]}")
        lines.append("")
    return "\n".join(lines)


def export_to_files(
    memories: Iterable[Mapping[str, Any]],
    out_dir: Path,
    *,
    base_name: str = "memory",
) -> tuple[Path, Path]:
    """Write JSON + Markdown to ``out_dir``, return ``(json_path, md_path)``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    items = list(memories)
    json_path = out_dir / f"{base_name}.json"
    md_path = out_dir / f"{base_name}.md"
    json_path.write_text(to_json(items), encoding="utf-8")
    md_path.write_text(to_markdown(items), encoding="utf-8")
    return json_path, md_path


__all__ = ["export_to_files", "to_json", "to_markdown"]
