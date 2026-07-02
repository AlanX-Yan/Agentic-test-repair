from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .config import load_benchmark, load_task, rebase_task
from .orchestrator import GoalDrivenRepairOrchestrator
from .utils import copy_tree, ensure_clean_dir, write_json


def run_benchmark(config_path: Path, run_dir: Path) -> dict[str, Any]:
    ensure_clean_dir(run_dir)
    task_configs = load_benchmark(config_path)
    rows: list[dict[str, Any]] = []

    for task_config in task_configs:
        loaded_task = load_task(task_config)
        task_dir = run_dir / "tasks" / loaded_task.task_id
        working_project = task_dir / loaded_task.project_root.name
        copy_tree(loaded_task.project_root, working_project)
        task = rebase_task(loaded_task, working_project)

        orchestrator = GoalDrivenRepairOrchestrator(task_dir / "artifacts")
        repair_run = orchestrator.run(task)
        rows.append(_row_from_run(repair_run))

    report = _aggregate(rows, run_dir)
    write_json(run_dir / "benchmark_summary.json", report)
    _write_csv(run_dir / "benchmark_results.csv", rows)
    _write_markdown(run_dir / "benchmark_report.md", rows, report)
    return report


def _row_from_run(repair_run) -> dict[str, Any]:
    first = repair_run.iterations[0]
    last = repair_run.iterations[-1]
    return {
        "task_id": repair_run.task.task_id,
        "iterations": len(repair_run.iterations),
        "accepted": repair_run.final_accepted,
        "initial_compiled": first.execution.compiled,
        "final_compiled": last.execution.compiled,
        "initial_passed": first.execution.passed,
        "final_passed": last.execution.passed,
        "initial_test_count": first.execution.test_count,
        "final_test_count": last.execution.test_count,
        "initial_smells": first.smell_report.count,
        "final_smells": last.smell_report.count,
        "smell_delta": first.smell_report.count - last.smell_report.count,
        "initial_smell_types": first.smell_report.by_type(),
        "final_smell_types": last.smell_report.by_type(),
        "artifacts_dir": str(repair_run.artifacts_dir),
    }


def _aggregate(rows: list[dict[str, Any]], run_dir: Path) -> dict[str, Any]:
    return {
        "task_count": len(rows),
        "accepted_count": sum(1 for row in rows if row["accepted"]),
        "initial_smells": sum(int(row["initial_smells"]) for row in rows),
        "final_smells": sum(int(row["final_smells"]) for row in rows),
        "smell_delta": sum(int(row["smell_delta"]) for row in rows),
        "initial_passed_count": sum(1 for row in rows if row["initial_passed"]),
        "final_passed_count": sum(1 for row in rows if row["final_passed"]),
        "artifacts_dir": str(run_dir),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "task_id",
        "iterations",
        "accepted",
        "initial_compiled",
        "final_compiled",
        "initial_passed",
        "final_passed",
        "initial_test_count",
        "final_test_count",
        "initial_smells",
        "final_smells",
        "smell_delta",
        "artifacts_dir",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})


def _write_markdown(path: Path, rows: list[dict[str, Any]], report: dict[str, Any]) -> None:
    lines = [
        "# Benchmark Report",
        "",
        f"- Tasks: `{report['task_count']}`",
        f"- Accepted: `{report['accepted_count']}`",
        f"- Initial smells: `{report['initial_smells']}`",
        f"- Final smells: `{report['final_smells']}`",
        f"- Smell delta: `{report['smell_delta']}`",
        f"- Initial passed: `{report['initial_passed_count']}`",
        f"- Final passed: `{report['final_passed_count']}`",
        "",
        "| Task | Accepted | Iterations | Initial Passed | Final Passed | Initial Tests | Final Tests | Initial Smells | Final Smells | Delta |",
        "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['task_id']} | {row['accepted']} | {row['iterations']} | "
            f"{row['initial_passed']} | {row['final_passed']} | "
            f"{row['initial_test_count']} | {row['final_test_count']} | "
            f"{row['initial_smells']} | {row['final_smells']} | {row['smell_delta']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
