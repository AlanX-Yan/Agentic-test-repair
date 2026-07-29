from __future__ import annotations

import argparse
import csv
from pathlib import Path


def normalized_test_id(row: dict[str, str]) -> tuple[str, str]:
    return (
        row.get("project_id", "").casefold(),
        Path(row.get("test_file", "")).name.casefold(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select deterministic AromaDr candidates outside a fixed subset."
    )
    parser.add_argument("candidate_csv", type=Path)
    parser.add_argument("excluded_subset_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-per-project", type=int, default=1)
    args = parser.parse_args()

    with args.excluded_subset_csv.open(encoding="utf-8", newline="") as handle:
        excluded = {normalized_test_id(row) for row in csv.DictReader(handle)}
    with args.candidate_csv.open(encoding="utf-8", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("aromadr_candidate", "").casefold() == "true"
            and normalized_test_id(row) not in excluded
        ]

    selected: list[dict[str, str]] = []
    project_counts: dict[str, int] = {}
    for row in rows:
        project = row.get("project_id", "")
        if project_counts.get(project, 0) >= args.max_per_project:
            continue
        selected.append(row)
        project_counts[project] = project_counts.get(project, 0) + 1
        if len(selected) >= args.limit:
            break

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)

    print(f"Eligible source rows outside fixed subset: {len(rows)}")
    print(f"Selected replacements: {len(selected)}")
    print(f"Projects represented: {len(project_counts)}")
    print(f"Output: {args.output_csv.resolve()}")


if __name__ == "__main__":
    main()
