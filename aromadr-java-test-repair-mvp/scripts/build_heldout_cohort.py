from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def relative_test_path(row: dict[str, str]) -> str:
    full = row["test_file"].replace("\\", "/")
    marker = f"/{row['project_id']}/"
    index = full.casefold().find(marker.casefold())
    return full[index + len(marker) :] if index >= 0 else Path(full).name


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze eligible held-out candidates.")
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("output_manifest", type=Path)
    parser.add_argument(
        "--source",
        nargs=2,
        action="append",
        metavar=("CANDIDATE_CSV", "BASELINE_RESULTS_CSV"),
        required=True,
    )
    args = parser.parse_args()

    selected: list[dict[str, str]] = []
    manifest: list[dict[str, object]] = []
    for candidate_text, results_text in args.source:
        candidates = load_csv(Path(candidate_text))
        by_test = {row["test_file"].casefold(): row for row in candidates}
        for result in load_csv(Path(results_text)):
            if result.get("eligible", "").casefold() != "true":
                continue
            row = by_test[result["source_test_file"].casefold()]
            selected.append(row)
            source_path = Path(row["test_file"])
            manifest.append(
                {
                    "cohort_index": len(selected),
                    "project_id": row["project_id"],
                    "relative_test_file": relative_test_path(row),
                    "source_sha256": file_sha256(source_path),
                    "aromadr_smell_types": row.get("aromadr_smell_types", ""),
                }
            )

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(selected[0].keys()))
        writer.writeheader()
        writer.writerows(selected)
    args.output_manifest.write_text(
        json.dumps(
            {
                "protocol": "deepseek-v1",
                "development_rows_excluded": 10,
                "candidate_count": len(selected),
                "candidates": manifest,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Frozen held-out candidates: {len(selected)}")
    print(f"Runnable CSV: {args.output_csv.resolve()}")
    print(f"Path-neutral manifest: {args.output_manifest.resolve()}")


if __name__ == "__main__":
    main()
