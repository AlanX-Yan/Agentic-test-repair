from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aromadr_counts(report: dict) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for finding in report.get("findings", []):
        if finding.get("source", "").casefold() == "aromadr":
            counts[finding["smell_type"]] += 1
    return dict(counts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a repair evaluation run.")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="INDEX=RUN_DIR",
        help="Replace a contaminated 1-based candidate with a one-row rerun.",
    )
    args = parser.parse_args()

    overrides: dict[int, Path] = {}
    for text in args.override:
        index, path = text.split("=", 1)
        overrides[int(index)] = Path(path)

    main_rows = read_csv(args.run_dir / "candidate_repair_results.csv")
    analyzed: list[dict] = []
    smell_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"candidate_attempts": 0, "accepted_candidates": 0, "before": 0, "after": 0}
    )

    for index, main_row in enumerate(main_rows, start=1):
        if index in overrides:
            run_root = overrides[index]
            row = read_csv(run_root / "candidate_repair_results.csv")[0]
            task_dir = run_root / "tasks" / "001"
            rerun = True
        else:
            run_root = args.run_dir
            row = main_row
            task_dir = run_root / "tasks" / f"{index:03d}"
            rerun = False

        attempts = int(row.get("attempts") or 0)
        artifacts = task_dir / "artifacts" / "repair"
        before = aromadr_counts(read_json(artifacts / "iteration-0" / "smell_report.json"))
        after = aromadr_counts(
            read_json(artifacts / f"iteration-{attempts}" / "smell_report.json")
        )
        accepted = row.get("accepted", "").casefold() == "true"
        for smell_type, count in before.items():
            stats = smell_stats[smell_type]
            stats["candidate_attempts"] += 1
            stats["accepted_candidates"] += int(accepted)
            stats["before"] += count
            stats["after"] += after.get(smell_type, 0)

        source = Path(row["source_test_file"])
        snapshot = task_dir / "original_test.java"
        analyzed.append(
            {
                "index": index,
                "project_id": row["project_id"],
                "test_file": source.name,
                "accepted": accepted,
                "attempts": attempts,
                "compiled": row.get("compiled", "").casefold() == "true",
                "tests_pass": row.get("tests_pass", "").casefold() == "true",
                "aromadr_before": sum(before.values()),
                "aromadr_after": sum(after.values()),
                "smell_types_before": "; ".join(
                    f"{key}={value}" for key, value in sorted(before.items())
                ),
                "model_calls": int(row.get("model_calls") or 0),
                "total_tokens": int(row.get("total_tokens") or 0),
                "estimated_cost_usd": float(row.get("estimated_cost_usd") or 0),
                "elapsed_seconds": float(row.get("elapsed_seconds") or 0),
                "status": row.get("status", ""),
                "infrastructure_rerun": rerun,
                "original_datatd_unchanged": (
                    source.exists() and snapshot.exists() and sha256(source) == sha256(snapshot)
                ),
            }
        )

    accepted_count = sum(item["accepted"] for item in analyzed)
    summary = {
        "protocol": "deepseek-v1",
        "candidate_count": len(analyzed),
        "accepted_count": accepted_count,
        "rejected_count": len(analyzed) - accepted_count,
        "success_rate": accepted_count / len(analyzed),
        "first_attempt_accepted": sum(
            item["accepted"] and item["attempts"] == 1 for item in analyzed
        ),
        "feedback_retry_accepted": sum(
            item["accepted"] and item["attempts"] == 2 for item in analyzed
        ),
        "compile_regressions": sum(not item["compiled"] for item in analyzed),
        "test_regressions": sum(
            item["compiled"] and not item["tests_pass"] for item in analyzed
        ),
        "aromadr_before": sum(item["aromadr_before"] for item in analyzed),
        "aromadr_after": sum(item["aromadr_after"] for item in analyzed),
        "model_calls": sum(item["model_calls"] for item in analyzed),
        "total_tokens": sum(item["total_tokens"] for item in analyzed),
        "estimated_cost_usd": sum(item["estimated_cost_usd"] for item in analyzed),
        "elapsed_seconds": sum(item["elapsed_seconds"] for item in analyzed),
        "mean_elapsed_seconds": sum(item["elapsed_seconds"] for item in analyzed)
        / len(analyzed),
        "min_elapsed_seconds": min(item["elapsed_seconds"] for item in analyzed),
        "max_elapsed_seconds": max(item["elapsed_seconds"] for item in analyzed),
        "mean_tokens": sum(item["total_tokens"] for item in analyzed) / len(analyzed),
        "mean_cost_usd": sum(item["estimated_cost_usd"] for item in analyzed)
        / len(analyzed),
        "original_datatd_unchanged": all(
            item["original_datatd_unchanged"] for item in analyzed
        ),
        "infrastructure_reruns": sum(item["infrastructure_rerun"] for item in analyzed),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "heldout_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    with (args.output_dir / "heldout_candidates.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(analyzed[0].keys()))
        writer.writeheader()
        writer.writerows(analyzed)
    with (args.output_dir / "heldout_smell_types.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        fieldnames = [
            "smell_type",
            "candidate_attempts",
            "accepted_candidates",
            "success_rate",
            "before",
            "after",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for smell_type, stats in sorted(smell_stats.items()):
            writer.writerow(
                {
                    "smell_type": smell_type,
                    **stats,
                    "success_rate": (
                        stats["accepted_candidates"] / stats["candidate_attempts"]
                    ),
                }
            )
    project_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"attempts": 0, "accepted": 0}
    )
    for item in analyzed:
        project_stats[item["project_id"]]["attempts"] += 1
        project_stats[item["project_id"]]["accepted"] += int(item["accepted"])
    with (args.output_dir / "heldout_projects.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["project_id", "attempts", "accepted", "success_rate"],
        )
        writer.writeheader()
        for project_id, stats in sorted(project_stats.items()):
            writer.writerow(
                {
                    "project_id": project_id,
                    **stats,
                    "success_rate": stats["accepted"] / stats["attempts"],
                }
            )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
