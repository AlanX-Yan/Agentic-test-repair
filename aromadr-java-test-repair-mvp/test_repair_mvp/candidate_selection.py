from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


def select_aromadr_candidates(
    input_csv: Path,
    output_csv: Path,
    *,
    limit: int = 40,
    max_per_project: int = 2,
) -> list[dict[str, str]]:
    with input_csv.open(encoding="utf-8", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("aromadr_candidate", "").casefold() == "true"
        ]
    if not rows:
        raise ValueError("No rows with aromadr_candidate=True were found.")

    rows.sort(
        key=lambda row: (
            row["project_id"].casefold(),
            -int(row.get("aromadr_smell_count") or 0),
            row["test_file"].casefold(),
        )
    )
    by_project: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_project[row["project_id"]].append(row)

    selected: list[dict[str, str]] = []
    project_counts: dict[str, int] = defaultdict(int)
    uncovered_types = {
        smell_type
        for row in rows
        for smell_type in _parse_smell_types(row.get("aromadr_smell_types", ""))
    }

    for smell_type in sorted(
        uncovered_types,
        key=lambda name: (
            sum(
                _parse_smell_types(row.get("aromadr_smell_types", "")).get(name, 0)
                for row in rows
            ),
            name,
        ),
    ):
        candidates = [
            row
            for row in rows
            if row not in selected
            and smell_type in _parse_smell_types(row.get("aromadr_smell_types", ""))
            and project_counts[row["project_id"]] < max_per_project
        ]
        if not candidates or len(selected) >= limit:
            continue
        row = min(
            candidates,
            key=lambda item: (
                project_counts[item["project_id"]],
                -int(item.get("aromadr_smell_count") or 0),
                item["project_id"].casefold(),
                item["test_file"].casefold(),
            ),
        )
        selected.append(row)
        project_counts[row["project_id"]] += 1

    project_names = sorted(by_project, key=str.casefold)
    while len(selected) < min(limit, len(rows)):
        added = False
        for project_id in project_names:
            if project_counts[project_id] >= max_per_project:
                continue
            row = next(
                (candidate for candidate in by_project[project_id] if candidate not in selected),
                None,
            )
            if row is None:
                continue
            selected.append(row)
            project_counts[project_id] += 1
            added = True
            if len(selected) >= limit:
                break
        if not added:
            break

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)
    return selected


def summarize_selection(rows: list[dict[str, str]]) -> dict[str, Any]:
    smell_types: dict[str, int] = {}
    for row in rows:
        for smell_type, count in _parse_smell_types(
            row.get("aromadr_smell_types", "")
        ).items():
            smell_types[smell_type] = smell_types.get(smell_type, 0) + count
    return {
        "candidate_count": len(rows),
        "project_count": len({row["project_id"] for row in rows}),
        "aromadr_smell_count": sum(
            int(row.get("aromadr_smell_count") or 0) for row in rows
        ),
        "aromadr_smell_types": dict(
            sorted(smell_types.items(), key=lambda item: (-item[1], item[0]))
        ),
    }


def _parse_smell_types(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for part in text.split(";"):
        name, separator, count_text = part.strip().partition("=")
        if not separator:
            continue
        try:
            result[name] = int(count_text)
        except ValueError:
            continue
    return result
