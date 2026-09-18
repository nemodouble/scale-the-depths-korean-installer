"""Validate the public Korean translation dataset without source game text."""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCALE = ROOT / "locales" / "ko"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate():
    manifest = read_json(LOCALE / "manifest.json")
    errors = []
    seen = set()
    total = translated = pending = review = 0

    if manifest.get("schema_version") != 1:
        errors.append("unsupported manifest schema")
    if manifest.get("language") != "ko":
        errors.append("manifest language must be ko")
    if manifest.get("identity") != "table:id":
        errors.append("manifest identity must be table:id")

    for table_record in manifest.get("tables", []):
        path = LOCALE / table_record["file"]
        if not path.exists():
            errors.append(f"missing table file: {table_record['file']}")
            continue
        document = read_json(path)
        table = document.get("table")
        entries = document.get("entries", [])
        if table != table_record["name"]:
            errors.append(f"table name mismatch: {table_record['file']}")
        if len(entries) != table_record["entries"]:
            errors.append(f"entry count mismatch: {table_record['file']}")

        for entry in entries:
            total += 1
            identity = (table, str(entry.get("id")))
            if identity in seen:
                errors.append(f"duplicate identity: {identity[0]}:{identity[1]}")
            seen.add(identity)
            target = entry.get("target")
            if not isinstance(target, str):
                errors.append(f"non-string target: {identity[0]}:{identity[1]}")
                continue
            source_hash = entry.get("source_sha256", "")
            if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
                errors.append(f"invalid source hash: {identity[0]}:{identity[1]}")
            placeholders = entry.get("placeholders")
            if not isinstance(placeholders, list) or not all(
                isinstance(value, str) for value in placeholders
            ):
                errors.append(f"invalid placeholders: {identity[0]}:{identity[1]}")
            elif collections.Counter(re.findall(r"\{[^{}]*\}", target)) != collections.Counter(placeholders):
                errors.append(f"placeholder mismatch: {identity[0]}:{identity[1]}")
            if entry.get("needs_review"):
                review += 1
            if target.strip():
                translated += 1
            elif not entry.get("source_empty"):
                pending += 1

    expected = {
        "total_entries": total,
        "translated_entries": translated,
        "pending_entries": pending,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            errors.append(f"manifest {key} mismatch: {manifest.get(key)} != {value}")
    if pending:
        errors.append(f"{pending} non-empty source entries are untranslated")
    if review:
        errors.append(f"{review} entries need review")

    report = {
        "total": total,
        "translated": translated,
        "pending": pending,
        "needs_review": review,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False))
    return not errors


if __name__ == "__main__":
    raise SystemExit(0 if validate() else 1)

