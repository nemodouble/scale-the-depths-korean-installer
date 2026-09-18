"""Export Korean translations with stable IDs without publishing source text."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import re


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def slug(value):
    value = re.sub(r"[^0-9A-Za-z]+", "-", value).strip("-").lower()
    return value or "table"


def load_private_targets(project_root):
    targets = {}
    for path in sorted((project_root / "translations").glob("*.json")):
        for index, target in read_json(path).items():
            index = int(index)
            if index in targets:
                raise RuntimeError(f"duplicate private translation index: {index}")
            if not isinstance(target, str):
                raise TypeError(f"non-string private translation: {index}")
            targets[index] = target
    return targets


def load_existing(output):
    existing = {}
    manifest_path = output / "manifest.json"
    if not manifest_path.exists():
        return existing
    manifest = read_json(manifest_path)
    for table in manifest.get("tables", []):
        document = read_json(output / table["file"])
        for entry in document["entries"]:
            existing[(document["table"], str(entry["id"]))] = entry
    return existing


def export(project_root, output):
    rows = read_json(project_root / "source" / "english.json")
    private_targets = load_private_targets(project_root)
    existing = load_existing(output)
    grouped = collections.defaultdict(list)

    for row in rows:
        stable_key = (row["table"], str(row["id"]))
        source = row["source"]
        source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        previous = existing.get(stable_key)
        if previous is not None:
            target = previous["target"]
            needs_review = bool(previous.get("needs_review")) or (
                previous.get("source_sha256") != source_hash
            )
        else:
            target = private_targets.get(int(row["index"]))
            if target is None and not source.strip():
                target = source
            if target is None:
                target = ""
            needs_review = bool(source.strip() and not target.strip())

        grouped[row["table"]].append(
            {
                "id": str(row["id"]),
                "key": row["key"],
                "target": target,
                "source_sha256": source_hash,
                "source_empty": not source.strip(),
                "placeholders": re.findall(r"\{[^{}]*\}", source),
                "needs_review": needs_review,
            }
        )

    table_records = []
    translated = 0
    pending = 0
    for table in sorted(grouped):
        entries = sorted(grouped[table], key=lambda entry: int(entry["id"]))
        translated += sum(bool(entry["target"].strip()) for entry in entries)
        pending += sum(
            not entry["source_empty"] and not entry["target"].strip()
            for entry in entries
        )
        filename = f"{slug(table)}.json"
        write_json(
            output / filename,
            {
                "schema_version": 1,
                "language": "ko",
                "table": table,
                "entries": entries,
            },
        )
        table_records.append(
            {"name": table, "file": filename, "entries": len(entries)}
        )

    manifest = {
        "schema_version": 1,
        "game": "Scale the Depths",
        "language": "ko",
        "release": "1.0.0",
        "total_entries": len(rows),
        "translated_entries": translated,
        "pending_entries": pending,
        "translation_license": "CC BY 4.0",
        "identity": "table:id",
        "tables": table_records,
    }
    write_json(output / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root",
        type=pathlib.Path,
        required=True,
        help="Private patch workspace containing source/ and translations/",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1] / "locales" / "ko",
    )
    args = parser.parse_args()
    export(args.project_root.resolve(), args.output.resolve())

