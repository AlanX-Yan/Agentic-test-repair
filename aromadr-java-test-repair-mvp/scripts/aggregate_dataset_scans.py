from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


SUMMARY_NAME = "dataset_scan_summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate per-project dataset scan reports.")
    parser.add_argument(
        "scan_dirs",
        nargs="+",
        help="Dataset scan report directories to aggregate.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where aggregate reports should be written.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scan_dirs = [Path(item).resolve() for item in args.scan_dirs]
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = [_row_from_scan_dir(path) for path in scan_dirs]
    summary = _aggregate(rows, output_dir)
    (output_dir / "aggregate_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    _write_csv(output_dir / "aggregate_projects.csv", rows)
    _write_merged_csv(output_dir / "aggregate_candidate_tests.csv", scan_dirs, "candidate_tests.csv")
    _write_merged_csv(output_dir / "aggregate_test_files.csv", scan_dirs, "test_files.csv")
    _write_markdown(output_dir / "aggregate_report.md", rows, summary)

    print("Dataset scan aggregation complete")
    print(f"Projects: {summary['project_count']}")
    print(f"Test files: {summary['test_file_count']}")
    print(f"Smelly test files: {summary['smelly_test_file_count']}")
    print(f"Candidate repair tests: {summary['candidate_test_count']}")
    print(f"Artifacts: {output_dir}")
    return 0


def _row_from_scan_dir(scan_dir: Path) -> dict[str, Any]:
    summary_path = scan_dir / SUMMARY_NAME
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    project_name = scan_dir.name
    if project_name.startswith("curated-"):
        project_name = project_name.removeprefix("curated-")
    if project_name.endswith("-aromadr"):
        project_name = project_name.removesuffix("-aromadr")
    return {
        "project": project_name,
        "scan_dir": str(scan_dir),
        **data,
    }


def _aggregate(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    numeric_keys = [
        "project_count",
        "projects_with_tests",
        "projects_test_compile",
        "projects_tests_pass",
        "projects_test_compile_timeout",
        "projects_test_timeout",
        "test_file_count",
        "smelly_test_file_count",
        "candidate_test_count",
        "total_smells",
        "aromadr_available_files",
    ]
    summary = {key: sum(int(row.get(key, 0)) for row in rows) for key in numeric_keys}
    smell_types: dict[str, int] = {}
    for row in rows:
        for smell_type, count in row.get("smell_types", {}).items():
            smell_types[smell_type] = smell_types.get(smell_type, 0) + int(count)
    summary["smell_types"] = dict(sorted(smell_types.items(), key=lambda item: (-item[1], item[0])))
    summary["artifacts_dir"] = str(output_dir)
    return summary


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "project",
        "project_count",
        "projects_with_tests",
        "projects_test_compile",
        "projects_tests_pass",
        "projects_test_compile_timeout",
        "projects_test_timeout",
        "test_file_count",
        "smelly_test_file_count",
        "candidate_test_count",
        "total_smells",
        "aromadr_available_files",
        "scan_dir",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def _write_merged_csv(path: Path, scan_dirs: list[Path], filename: str) -> None:
    merged_rows: list[dict[str, str]] = []
    fieldnames: list[str] = []
    for scan_dir in scan_dirs:
        source = scan_dir / filename
        if not source.exists():
            continue
        project = _project_name(scan_dir)
        with source.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames and not fieldnames:
                fieldnames = ["aggregate_project", "scan_dir"] + reader.fieldnames
            for row in reader:
                merged_rows.append({"aggregate_project": project, "scan_dir": str(scan_dir), **row})

    if not fieldnames:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_rows)


def _project_name(scan_dir: Path) -> str:
    project_name = scan_dir.name
    if project_name.startswith("curated-"):
        project_name = project_name.removeprefix("curated-")
    if project_name.endswith("-aromadr"):
        project_name = project_name.removesuffix("-aromadr")
    return project_name


def _write_markdown(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines = [
        "# Aggregate Dataset Scan Report",
        "",
        f"- Projects scanned: `{summary['project_count']}`",
        f"- Projects with Java tests: `{summary['projects_with_tests']}`",
        f"- Projects where tests compile: `{summary['projects_test_compile']}`",
        f"- Projects where tests pass: `{summary['projects_tests_pass']}`",
        f"- Test files scanned: `{summary['test_file_count']}`",
        f"- Smelly test files: `{summary['smelly_test_file_count']}`",
        f"- Candidate repair tests: `{summary['candidate_test_count']}`",
        f"- AromaDr available for files: `{summary['aromadr_available_files']}`",
        "",
        "## Projects",
        "",
        "| Project | Test Files | Smelly Files | Candidates | Compile | Tests Pass | Compile Timeouts | Total Smells |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['project']}` | {row['test_file_count']} | {row['smelly_test_file_count']} | "
            f"{row['candidate_test_count']} | {row['projects_test_compile']} | "
            f"{row['projects_tests_pass']} | {row['projects_test_compile_timeout']} | "
            f"{row['total_smells']} |"
        )

    lines.extend(["", "## Smell Types", ""])
    if summary["smell_types"]:
        for smell_type, count in summary["smell_types"].items():
            lines.append(f"- `{smell_type}`: `{count}`")
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
