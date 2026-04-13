from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

KB_PATH = Path(__file__).resolve().parent.parent / "data" / "clinic_kb.json"
TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")


@lru_cache(maxsize=1)
def load_knowledge_base() -> list[dict]:
    with KB_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def retrieve_context(message: str, limit: int = 3) -> str:
    tokens = set(token.lower() for token in TOKEN_RE.findall(message))
    if not tokens:
        return ""

    scored_items: list[tuple[int, dict]] = []
    for item in load_knowledge_base():
        haystack = " ".join(
            [
                item.get("topic", ""),
                item.get("question", ""),
                item.get("answer", ""),
                " ".join(item.get("keywords", [])),
            ]
        ).lower()
        score = sum(1 for token in tokens if token in haystack)
        if score:
            scored_items.append((score, item))

    scored_items.sort(key=lambda item: item[0], reverse=True)
    snippets = []
    for _, item in scored_items[:limit]:
        snippets.append(
            f"Topic: {item['topic']}\n"
            f"Question: {item['question']}\n"
            f"Answer: {item['answer']}"
        )
    return "\n\n".join(snippets)
