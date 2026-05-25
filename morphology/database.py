"""Загрузчик базы данных: корни и аффиксы из JSON-файлов."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional


class MorphDatabase:
    """Базы корней и аффиксов кыргызского языка."""

    def __init__(self, data_dir: str | Path = "data"):
        self.data_dir = Path(data_dir)
        self.roots_by_pos: Dict[str, List[dict]] = {}
        self.roots_index: Dict[str, List[dict]] = {}  # form -> list[entry]
        self.affixes_by_pos: Dict[str, List[dict]] = {}
        self.affixes_index: Dict[str, dict] = {}  # id -> entry
        self._load()

    # ---------- загрузка ----------
    def _load(self) -> None:
        self._load_roots()
        self._load_affixes()

    def _read_json(self, name: str) -> dict:
        path = self.data_dir / name
        with open(path, "rb") as f:
            data = f.read()
        # Защита от случайных нулевых байтов после JSON
        last = data.rfind(b"}")
        if last >= 0:
            data = data[: last + 1]
        return json.loads(data.decode("utf-8"))

    def _load_roots(self) -> None:
        raw = self._read_json("roots.json")
        for group, items in raw.items():
            if group.startswith("_"):
                continue
            self.roots_by_pos[group] = items
            for it in items:
                self.roots_index.setdefault(it["root"], []).append(it)

    def _load_affixes(self) -> None:
        raw = self._read_json("affixes.json")
        for group, items in raw.items():
            if group.startswith("_"):
                continue
            self.affixes_by_pos[group] = items
            for it in items:
                self.affixes_index[it["id"]] = it

    # ---------- доступ ----------
    def all_roots(self) -> List[dict]:
        return [it for group in self.roots_by_pos.values() for it in group]

    def get_root(self, form: str) -> List[dict]:
        return self.roots_index.get(form, [])

    def get_affix(self, affix_id: str) -> Optional[dict]:
        return self.affixes_index.get(affix_id)

    def affixes_for_category(self, pos: str) -> List[dict]:
        """Возвращает список аффиксов, применимых к данной части речи."""
        if pos == "N":
            return self.affixes_by_pos.get("noun_affixes", [])
        if pos == "V":
            return self.affixes_by_pos.get("verb_affixes", [])
        if pos == "ADJ":
            return self.affixes_by_pos.get("adjective_affixes", [])
        if pos == "PRON":
            # местоимения склоняются как существительные
            return self.affixes_by_pos.get("noun_affixes", [])
        return []

    def stats(self) -> dict:
        return {
            "roots_total": sum(len(v) for v in self.roots_by_pos.values()),
            "roots_by_pos": {k: len(v) for k, v in self.roots_by_pos.items()},
            "affix_lemmas": sum(len(v) for v in self.affixes_by_pos.values()),
            "affix_groups": {k: len(v) for k, v in self.affixes_by_pos.items()},
        }
