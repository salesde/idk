"""Output file management — saves agent-generated content to disk."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

OUTPUT_ROOT = Path("output")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_content(
    department: str,
    content_type: str,  # script | article | site | product | report
    title: str,
    content: str,
    metadata: dict[str, Any] | None = None,
    extension: str = "md",
) -> Path:
    """Save generated content to the output directory."""
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    dir_path = ensure_dir(OUTPUT_ROOT / "content" / department / date_str)

    safe_title = "".join(c if c.isalnum() or c in "- _" else "_" for c in title)[:60]
    filename = f"{content_type}_{safe_title}.{extension}"
    file_path = dir_path / filename

    if extension == "json":
        payload = {"title": title, "content": content, "metadata": metadata or {}}
        file_path.write_text(json.dumps(payload, indent=2, default=str))
    else:
        header = f"# {title}\n\n"
        if metadata:
            header += f"<!-- metadata: {json.dumps(metadata, default=str)} -->\n\n"
        file_path.write_text(header + content)

    logger.info("Saved %s → %s", content_type, file_path)
    return file_path


def save_report(name: str, content: str, department: str = "general") -> Path:
    dir_path = ensure_dir(OUTPUT_ROOT / "reports" / department)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_path = dir_path / f"{ts}_{name}.md"
    file_path.write_text(content)
    logger.info("Report saved → %s", file_path)
    return file_path


def save_code(name: str, code: str, language: str = "python", department: str = "general") -> Path:
    ext_map = {"python": "py", "javascript": "js", "html": "html", "css": "css", "json": "json"}
    ext = ext_map.get(language, "txt")
    dir_path = ensure_dir(OUTPUT_ROOT / "code" / department)
    file_path = dir_path / f"{name}.{ext}"
    file_path.write_text(code)
    logger.info("Code saved → %s", file_path)
    return file_path


def list_outputs(department: str | None = None) -> list[Path]:
    base = OUTPUT_ROOT / "content" / (department or "")
    if not base.exists():
        return []
    return sorted(base.rglob("*.*"), key=os.path.getmtime, reverse=True)
