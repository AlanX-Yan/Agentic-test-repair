from __future__ import annotations

import csv
import difflib
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .agents import ApiBudget, create_coding_agent
from .models import ProjectTask
from .orchestrator import GoalDrivenRepairOrchestrator
from .utils import write_json


def run_candidate_baselines(
    candidate_csv: Path,
    output_dir: Path,
    *,
    offset: int = 0,
    limit: int | None = None,
    maven_repo: Path | None = None,
    timeout_seconds: int = 600,
    coding_backend: str = "template",
    repair_max_attempts: int = 0,
    repair_budget_usd: float | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    """Baseline and optionally repair candidate tests in isolated project copies."""

    checkpoint_path = output_dir / "candidate_checkpoint.json"
    if output_dir.exists() and any(output_dir.iterdir()) and not resume:
        raise FileExistsError(f"Candidate repair output is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    environment_path = output_dir / "environment.json"
    if not environment_path.exists():
        write_json(
            environment_path,
            _environment_manifest(
                candidate_csv,
                offset=offset,
                limit=limit,
                timeout_seconds=timeout_seconds,
                coding_backend=coding_backend,
                repair_max_attempts=repair_max_attempts,
                repair_budget_usd=repair_budget_usd,
            ),
        )

    with candidate_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows = rows[offset:]
    if limit is not None:
        rows = rows[:limit]

    results: list[dict[str, Any]] = []
    if resume and checkpoint_path.exists():
        checkpoint = json.loads(
            checkpoint_path.read_text(encoding="utf-8")
        )
        if checkpoint.get("candidate_csv_sha256") != _sha256(candidate_csv):
            raise ValueError("Resume candidate CSV does not match checkpoint.")
        results = checkpoint.get("results", [])
    budget = ApiBudget(
        limit_usd=repair_budget_usd,
        consumed_usd=sum(
            float(result.get("estimated_cost_usd") or 0) for result in results
        ),
    )
    for index, row in enumerate(rows, start=1):
        if index <= len(results):
            continue
        if resume:
            _remove_incomplete_task(output_dir, index)
        started = time.monotonic()
        cost_before = budget.consumed_usd
        try:
            result = _run_candidate_baseline(
                row,
                output_dir,
                index=index,
                maven_repo=maven_repo,
                timeout_seconds=timeout_seconds,
                coding_backend=coding_backend,
                repair_max_attempts=repair_max_attempts,
                budget=budget,
            )
        except Exception as error:
            result = _failed_candidate_result(row, output_dir, index, error)
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        result["estimated_cost_usd"] = round(
            budget.consumed_usd - cost_before, 8
        )
        usage = _candidate_usage(Path(result["artifacts_dir"]))
        result["model_calls"] = usage["model_calls"]
        result["total_tokens"] = usage["total_tokens"]
        result["provider"] = "deepseek" if usage["model_calls"] else ""
        result["model"] = usage["model"]
        results.append(result)
        write_json(
            checkpoint_path,
            {
                "candidate_csv_sha256": _sha256(candidate_csv),
                "offset": offset,
                "limit": limit,
                "results": results,
            },
        )

    summary = _aggregate_results(results, output_dir)
    summary["budget_limit_usd"] = repair_budget_usd
    summary["budget_consumed_usd"] = round(budget.consumed_usd, 8)
    summary["budget_remaining_usd"] = (
        None
        if repair_budget_usd is None
        else round(max(0.0, repair_budget_usd - budget.consumed_usd), 8)
    )
    write_json(output_dir / "candidate_repair_summary.json", summary)
    _write_results_csv(output_dir / "candidate_repair_results.csv", results)
    _write_markdown(output_dir / "candidate_repair_report.md", summary, results)
    return summary


def _remove_incomplete_task(output_dir: Path, index: int) -> None:
    tasks_root = (output_dir / "tasks").resolve()
    task_dir = (tasks_root / f"{index:03d}").resolve()
    if task_dir.parent != tasks_root:
        raise ValueError(f"Unsafe incomplete task path: {task_dir}")
    if task_dir.exists():
        shutil.rmtree(task_dir)


def _environment_manifest(
    candidate_csv: Path,
    **options: Any,
) -> dict[str, Any]:
    workspace_root = Path(__file__).resolve().parents[2]
    local_maven = (
        workspace_root
        / "tools"
        / "apache-maven-3.9.16"
        / "bin"
        / ("mvn.cmd" if os.name == "nt" else "mvn")
    )
    maven_command = str(local_maven) if local_maven.exists() else "mvn"
    return {
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "java_version": _version_output(["java", "-version"]),
        "maven_version": _version_output([maven_command, "-version"]),
        "coding_backend": options["coding_backend"],
        "model": (
            os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")
            if options["coding_backend"] == "deepseek"
            else "template"
        ),
        "aromadr_api_url": os.environ.get("AROMADR_API_URL", ""),
        "candidate_csv_sha256": _sha256(candidate_csv),
        "options": options,
    }


def _version_output(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return output[:2000]


def _candidate_usage(artifacts_dir: Path) -> dict[str, Any]:
    path = artifacts_dir / "api_attempts.json"
    if not path.exists():
        return {"model_calls": 0, "total_tokens": 0, "model": ""}
    attempts = json.loads(path.read_text(encoding="utf-8"))
    completed = [item for item in attempts if item.get("status") == "completed"]
    return {
        "model_calls": len(completed),
        "total_tokens": sum(
            int((item.get("usage") or {}).get("total_tokens") or 0)
            for item in completed
        ),
        "model": completed[-1].get("model", "") if completed else "",
    }


def _failed_candidate_result(
    row: dict[str, str],
    output_dir: Path,
    index: int,
    error: Exception,
) -> dict[str, Any]:
    task_dir = output_dir / "tasks" / f"{index:03d}"
    original_snapshot = task_dir / "original_test.java"
    working_project = task_dir / "project"
    source_test_file = Path(row["test_file"]).resolve()
    source_project = _find_project_root(source_test_file)
    relative_test_file = source_test_file.relative_to(source_project)
    working_test_file = working_project / relative_test_file
    rolled_back = False
    if original_snapshot.exists() and working_test_file.exists():
        shutil.copy2(original_snapshot, working_test_file)
        rolled_back = True
    error_text = f"{type(error).__name__}: {error}"
    baseline_execution = _read_optional_json(
        task_dir / "artifacts" / "baseline" / "iteration-0" / "execution.json"
    )
    baseline_smells = _read_optional_json(
        task_dir / "artifacts" / "baseline" / "iteration-0" / "smell_report.json"
    )
    baseline_aromadr = sum(
        1
        for finding in baseline_smells.get("findings", [])
        if finding.get("source", "").casefold() == "aromadr"
    )
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "candidate_error.txt").write_text(error_text, encoding="utf-8")
    return {
        "task_id": f"dataset:{row['project_id']}:{source_test_file.stem}",
        "project_id": row["project_id"],
        "source_project": str(source_project),
        "source_test_file": str(source_test_file),
        "working_project": str(working_project),
        "working_test_file": str(working_test_file),
        "original_snapshot": str(original_snapshot),
        "original_sha256": (
            _sha256(original_snapshot) if original_snapshot.exists() else ""
        ),
        "final_sha256": (
            _sha256(working_test_file) if working_test_file.exists() else ""
        ),
        "baseline_compiled": bool(baseline_execution.get("compiled", False)),
        "baseline_tests_pass": bool(baseline_execution.get("passed", False)),
        "compiled": False,
        "tests_pass": False,
        "maven_return_code": -1,
        "aromadr_available": bool(
            baseline_smells.get("aroma_dr_available", False)
        ),
        "baseline_aromadr_smells": baseline_aromadr,
        "combined_smells": 0,
        "aromadr_smells": 0,
        "lightweight_smells": 0,
        "aromadr_smell_types": {},
        "changed": rolled_back,
        "rolled_back": rolled_back,
        "unchanged": rolled_back,
        "accepted": False,
        "eligible": False,
        "attempts": 0,
        "status": "candidate-error",
        "error": error_text,
        "diff": str(task_dir / "repair.diff"),
        "artifacts_dir": str(task_dir / "artifacts"),
    }


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _run_candidate_baseline(
    row: dict[str, str],
    output_dir: Path,
    *,
    index: int,
    maven_repo: Path | None,
    timeout_seconds: int,
    coding_backend: str,
    repair_max_attempts: int,
    budget: ApiBudget,
) -> dict[str, Any]:
    source_test_file = Path(row["test_file"]).resolve()
    source_project = _find_project_root(source_test_file)
    relative_test_file = source_test_file.relative_to(source_project)
    task_name = f"{index:03d}"
    task_dir = output_dir / "tasks" / task_name
    working_project = task_dir / "project"
    _copy_project(source_project, working_project)

    working_test_file = working_project / relative_test_file
    original_snapshot = task_dir / "original_test.java"
    original_snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(working_test_file, original_snapshot)
    original_hash = _sha256(working_test_file)

    task = ProjectTask(
        task_id=f"dataset:{row['project_id']}:{source_test_file.stem}",
        project_root=working_project,
        source_under_test=working_project / "pom.xml",
        test_file=working_test_file,
        target_description=(
            "Establish an isolated Maven and AromaDr baseline for a DataTD "
            f"candidate with AromaDr smells: {row.get('aromadr_smell_types', '')}."
        ),
        build_tool="maven",
        max_iterations=0,
        source_roots=(
            working_project / "src" / "main" / "java",
            working_project / "src" / "test" / "java",
        ),
        maven_repo=maven_repo,
        command_timeout_seconds=timeout_seconds,
        maven_test_compile_first=True,
    )
    baseline_artifacts = task_dir / "artifacts" / "baseline"
    baseline_run = GoalDrivenRepairOrchestrator(baseline_artifacts).run(
        task, generate_initial_tests=False
    )
    baseline_record = baseline_run.iterations[0]
    eligible = (
        baseline_record.execution.compiled
        and baseline_record.execution.passed
        and baseline_record.smell_report.aroma_dr_available
        and baseline_record.smell_report.count_from("AromaDr") > 0
    )
    if coding_backend != "template" and repair_max_attempts > 0 and eligible:
        repair_task = ProjectTask(
            **{
                **task.__dict__,
                "max_iterations": repair_max_attempts,
            }
        )
        repair_artifacts = task_dir / "artifacts" / "repair"
        agent = create_coding_agent(
            coding_backend, repair_artifacts, budget=budget
        )
        repair_run = GoalDrivenRepairOrchestrator(
            repair_artifacts, agent=agent
        ).run(repair_task, generate_initial_tests=False)
    else:
        repair_run = baseline_run
    final_record = repair_run.iterations[-1]
    proposed_source = working_test_file.read_text(encoding="utf-8")
    original_source = original_snapshot.read_text(encoding="utf-8")
    changed = original_source != proposed_source
    diff_path = task_dir / "repair.diff"
    diff_path.write_text(
        "".join(
            difflib.unified_diff(
                original_source.splitlines(keepends=True),
                proposed_source.splitlines(keepends=True),
                fromfile=str(relative_test_file),
                tofile=str(relative_test_file),
            )
        ),
        encoding="utf-8",
    )
    rolled_back = changed and not repair_run.final_accepted
    if rolled_back:
        (task_dir / "rejected_test.java").write_text(proposed_source, encoding="utf-8")
        shutil.copy2(original_snapshot, working_test_file)
    final_hash = _sha256(working_test_file)
    if coding_backend == "template" and original_hash != final_hash:
        raise RuntimeError(f"Baseline-only run modified the test file: {source_test_file}")

    return {
        "task_id": task.task_id,
        "project_id": row["project_id"],
        "source_project": str(source_project),
        "source_test_file": str(source_test_file),
        "working_project": str(working_project),
        "working_test_file": str(working_test_file),
        "original_snapshot": str(original_snapshot),
        "original_sha256": original_hash,
        "final_sha256": final_hash,
        "baseline_compiled": baseline_record.execution.compiled,
        "baseline_tests_pass": baseline_record.execution.passed,
        "compiled": final_record.execution.compiled,
        "tests_pass": final_record.execution.passed,
        "maven_return_code": final_record.execution.command_result.return_code,
        "aromadr_available": final_record.smell_report.aroma_dr_available,
        "baseline_aromadr_smells": baseline_record.smell_report.count_from("AromaDr"),
        "combined_smells": final_record.smell_report.count,
        "aromadr_smells": final_record.smell_report.count_from("AromaDr"),
        "lightweight_smells": final_record.smell_report.count_from("lightweight"),
        "aromadr_smell_types": final_record.smell_report.by_type_from("AromaDr"),
        "changed": changed,
        "rolled_back": rolled_back,
        "unchanged": original_hash == final_hash,
        "accepted": repair_run.final_accepted,
        "eligible": eligible,
        "attempts": max(0, len(repair_run.iterations) - 1),
        "status": (
            "accepted" if repair_run.final_accepted
            else "rejected-rolled-back" if rolled_back
            else "baseline-ineligible" if not eligible
            else "baseline-recorded"
        ),
        "diff": str(diff_path),
        "artifacts_dir": str(repair_run.artifacts_dir),
    }


def _find_project_root(test_file: Path) -> Path:
    for parent in test_file.parents:
        if (parent / "pom.xml").exists():
            return parent
    raise ValueError(f"No Maven project root found for candidate: {test_file}")


def _safe_name(text: str, *, max_length: int = 120) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-")
    return cleaned[:max_length] or "candidate"


def _copy_project(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"Isolated project already exists: {destination}")
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            ".gradle",
            ".idea",
            ".m2",
            "build",
            "node_modules",
            "target",
        ),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _aggregate_results(
    results: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    return {
        "candidate_count": len(results),
        "projects_represented": len({result["project_id"] for result in results}),
        "compiled_count": sum(1 for result in results if result["compiled"]),
        "tests_pass_count": sum(1 for result in results if result["tests_pass"]),
        "aromadr_available_count": sum(
            1 for result in results if result["aromadr_available"]
        ),
        "unchanged_count": sum(1 for result in results if result["unchanged"]),
        "accepted_count": sum(1 for result in results if result["accepted"]),
        "eligible_count": sum(1 for result in results if result["eligible"]),
        "rolled_back_count": sum(1 for result in results if result["rolled_back"]),
        "candidate_error_count": sum(
            1 for result in results if result["status"] == "candidate-error"
        ),
        "model_call_count": sum(int(result.get("model_calls") or 0) for result in results),
        "total_tokens": sum(int(result.get("total_tokens") or 0) for result in results),
        "estimated_cost_usd": round(
            sum(float(result.get("estimated_cost_usd") or 0) for result in results),
            8,
        ),
        "elapsed_seconds": round(
            sum(float(result.get("elapsed_seconds") or 0) for result in results),
            3,
        ),
        "aromadr_smell_count": sum(
            int(result["aromadr_smells"]) for result in results
        ),
        "mode": "repair" if any(result["attempts"] for result in results) else "baseline-only",
        "artifacts_dir": str(output_dir),
    }


def _write_results_csv(path: Path, results: list[dict[str, Any]]) -> None:
    fieldnames = [
        "task_id",
        "project_id",
        "source_test_file",
        "original_sha256",
        "final_sha256",
        "baseline_compiled",
        "baseline_tests_pass",
        "compiled",
        "tests_pass",
        "maven_return_code",
        "aromadr_available",
        "baseline_aromadr_smells",
        "combined_smells",
        "aromadr_smells",
        "lightweight_smells",
        "changed",
        "rolled_back",
        "unchanged",
        "accepted",
        "eligible",
        "attempts",
        "provider",
        "model",
        "model_calls",
        "total_tokens",
        "estimated_cost_usd",
        "elapsed_seconds",
        "diff",
        "error",
        "status",
        "artifacts_dir",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({name: result.get(name, "") for name in fieldnames})


def _write_markdown(
    path: Path,
    summary: dict[str, Any],
    results: list[dict[str, Any]],
) -> None:
    lines = [
        "# DataTD Candidate Repair Baseline",
        "",
        f"- Candidates: `{summary['candidate_count']}`",
        f"- Projects represented: `{summary['projects_represented']}`",
        f"- Compiled: `{summary['compiled_count']}`",
        f"- Tests pass: `{summary['tests_pass_count']}`",
        f"- AromaDr available: `{summary['aromadr_available_count']}`",
        f"- Files unchanged: `{summary['unchanged_count']}`",
        f"- Accepted: `{summary['accepted_count']}`",
        f"- Eligible for API repair: `{summary['eligible_count']}`",
        f"- Rolled back: `{summary['rolled_back_count']}`",
        f"- AromaDr findings: `{summary['aromadr_smell_count']}`",
        f"- Mode: `{summary['mode']}`",
        "",
        "| Candidate | Compiled | Tests Pass | AromaDr | AromaDr Smells | Unchanged |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for result in results:
        lines.append(
            f"| `{result['task_id']}` | {result['compiled']} | "
            f"{result['tests_pass']} | {result['aromadr_available']} | "
            f"{result['aromadr_smells']} | {result['unchanged']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
