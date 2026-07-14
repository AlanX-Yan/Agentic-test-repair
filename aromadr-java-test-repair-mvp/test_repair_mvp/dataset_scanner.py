from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .detectors import CompositeDetector
from .harness import JavaExecutionHarness
from .models import CommandResult, ProjectTask, SmellReport
from .utils import run_command, write_json


TEST_FILE_SUFFIXES = ("Test.java", "Tests.java", "TestCase.java")
IGNORED_DIR_NAMES = {
    ".git",
    ".gradle",
    ".idea",
    ".m2",
    ".settings",
    "build",
    "node_modules",
    "target",
}


@dataclass(frozen=True)
class MavenProjectScan:
    project_id: str
    project_root: Path
    pom_file: Path
    test_files: list[Path]
    test_compile: CommandResult | None
    test_run: CommandResult | None

    @property
    def has_tests(self) -> bool:
        return bool(self.test_files)

    @property
    def test_compiles(self) -> bool:
        return bool(self.test_compile and self.test_compile.ok)

    @property
    def tests_pass(self) -> bool:
        return bool(self.test_run and self.test_run.ok)


@dataclass(frozen=True)
class TestFileScan:
    project_id: str
    project_root: Path
    test_file: Path
    smell_report: SmellReport
    project_test_compiles: bool
    project_tests_pass: bool

    @property
    def is_candidate(self) -> bool:
        return self.project_test_compiles and self.project_tests_pass and self.smell_report.count > 0


def scan_maven_dataset(
    dataset_root: Path,
    output_dir: Path,
    *,
    run_maven: bool = True,
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    """Scan a directory of Maven projects and write candidate reports.

    The scanner is intentionally dataset-oriented: it treats each directory that
    contains a pom.xml as one Maven project, evaluates whether its tests compile
    and pass, scans every Java test file with the configured detector pipeline,
    and reports candidate files that are ready for the repair loop.
    """

    dataset_root = dataset_root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    detector = CompositeDetector()
    project_scans: list[MavenProjectScan] = []
    test_scans: list[TestFileScan] = []

    for pom_file in discover_maven_projects(dataset_root):
        project_root = pom_file.parent
        project_scan = _scan_project(project_root, dataset_root, run_maven, timeout_seconds)
        project_scans.append(project_scan)
        for test_file in project_scan.test_files:
            smell_report = detector.detect(_task_for_test_file(project_scan, test_file))
            test_scans.append(
                TestFileScan(
                    project_id=project_scan.project_id,
                    project_root=project_scan.project_root,
                    test_file=test_file,
                    smell_report=smell_report,
                    project_test_compiles=project_scan.test_compiles,
                    project_tests_pass=project_scan.tests_pass,
                )
            )

    summary = _build_summary(project_scans, test_scans, output_dir)
    write_json(output_dir / "dataset_scan_summary.json", summary)
    _write_projects_csv(output_dir / "projects.csv", project_scans)
    _write_test_files_csv(output_dir / "test_files.csv", test_scans)
    _write_candidates_csv(output_dir / "candidate_tests.csv", test_scans)
    _write_markdown_report(output_dir / "dataset_candidate_report.md", summary, test_scans)
    return summary


def discover_maven_projects(dataset_root: Path) -> list[Path]:
    pom_files: list[Path] = []
    for path in sorted(dataset_root.rglob("pom.xml")):
        if _is_ignored(path.relative_to(dataset_root)):
            continue
        pom_files.append(path)
    return pom_files


def _scan_project(
    project_root: Path,
    dataset_root: Path,
    run_maven: bool,
    timeout_seconds: int,
) -> MavenProjectScan:
    test_files = _discover_test_files(project_root)
    test_compile = None
    test_run = None
    if run_maven and test_files:
        test_compile = _run_maven(project_root, "test-compile", timeout_seconds)
        if test_compile.ok:
            test_run = _run_maven(project_root, "test", timeout_seconds)
    return MavenProjectScan(
        project_id=_project_id(project_root, dataset_root),
        project_root=project_root,
        pom_file=project_root / "pom.xml",
        test_files=test_files,
        test_compile=test_compile,
        test_run=test_run,
    )


def _run_maven(project_root: Path, goal: str, timeout_seconds: int) -> CommandResult:
    maven_bin = JavaExecutionHarness()._maven_bin()
    local_repo = project_root / ".m2" / "repository"
    command = [maven_bin, f"-Dmaven.repo.local={local_repo}", goal]
    return run_command(command, project_root, timeout_seconds=timeout_seconds)


def _discover_test_files(project_root: Path) -> list[Path]:
    test_root = project_root / "src" / "test" / "java"
    if not test_root.exists():
        return []
    return [
        path
        for path in sorted(test_root.rglob("*.java"))
        if path.name.endswith(TEST_FILE_SUFFIXES) and not _is_ignored(path.relative_to(project_root))
    ]


def _task_for_test_file(project_scan: MavenProjectScan, test_file: Path) -> ProjectTask:
    return ProjectTask(
        task_id=f"{project_scan.project_id}:{test_file.stem}",
        project_root=project_scan.project_root,
        source_under_test=project_scan.pom_file,
        test_file=test_file,
        target_description="Dataset test-smell scan target.",
        build_tool="maven",
        max_iterations=0,
        source_roots=(
            project_scan.project_root / "src" / "main" / "java",
            project_scan.project_root / "src" / "test" / "java",
        ),
    )


def _project_id(project_root: Path, dataset_root: Path) -> str:
    relative = project_root.resolve().relative_to(dataset_root.resolve())
    text = str(relative) if str(relative) != "." else project_root.name
    return text.replace("/", "__")


def _is_ignored(relative_path: Path) -> bool:
    return any(part in IGNORED_DIR_NAMES for part in relative_path.parts)


def _build_summary(
    project_scans: list[MavenProjectScan],
    test_scans: list[TestFileScan],
    output_dir: Path,
) -> dict[str, Any]:
    candidates = [scan for scan in test_scans if scan.is_candidate]
    smell_types: dict[str, int] = {}
    for scan in test_scans:
        for smell_type, count in scan.smell_report.by_type().items():
            smell_types[smell_type] = smell_types.get(smell_type, 0) + count

    return {
        "project_count": len(project_scans),
        "projects_with_tests": sum(1 for scan in project_scans if scan.has_tests),
        "projects_test_compile": sum(1 for scan in project_scans if scan.test_compiles),
        "projects_tests_pass": sum(1 for scan in project_scans if scan.tests_pass),
        "test_file_count": len(test_scans),
        "smelly_test_file_count": sum(1 for scan in test_scans if scan.smell_report.count > 0),
        "candidate_test_count": len(candidates),
        "total_smells": sum(scan.smell_report.count for scan in test_scans),
        "smell_types": dict(sorted(smell_types.items(), key=lambda item: (-item[1], item[0]))),
        "aromadr_available_files": sum(1 for scan in test_scans if scan.smell_report.aroma_dr_available),
        "artifacts_dir": str(output_dir),
    }


def _write_projects_csv(path: Path, project_scans: list[MavenProjectScan]) -> None:
    fieldnames = [
        "project_id",
        "project_root",
        "test_file_count",
        "test_compile_ok",
        "test_ok",
        "test_compile_return_code",
        "test_return_code",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for scan in project_scans:
            writer.writerow(
                {
                    "project_id": scan.project_id,
                    "project_root": str(scan.project_root),
                    "test_file_count": len(scan.test_files),
                    "test_compile_ok": scan.test_compiles,
                    "test_ok": scan.tests_pass,
                    "test_compile_return_code": (
                        scan.test_compile.return_code if scan.test_compile else ""
                    ),
                    "test_return_code": scan.test_run.return_code if scan.test_run else "",
                }
            )


def _write_test_files_csv(path: Path, test_scans: list[TestFileScan]) -> None:
    fieldnames = [
        "project_id",
        "test_file",
        "test_compile_ok",
        "test_ok",
        "detector",
        "aromadr_available",
        "smell_count",
        "smell_types",
        "candidate",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for scan in test_scans:
            writer.writerow(_test_scan_row(scan))


def _write_candidates_csv(path: Path, test_scans: list[TestFileScan]) -> None:
    fieldnames = [
        "project_id",
        "test_file",
        "test_compile_ok",
        "test_ok",
        "detector",
        "aromadr_available",
        "smell_count",
        "smell_types",
        "candidate",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for scan in test_scans:
            if scan.is_candidate:
                writer.writerow(_test_scan_row(scan))


def _test_scan_row(scan: TestFileScan) -> dict[str, Any]:
    smell_types = "; ".join(
        f"{name}={count}" for name, count in sorted(scan.smell_report.by_type().items())
    )
    return {
        "project_id": scan.project_id,
        "test_file": str(scan.test_file),
        "test_compile_ok": scan.project_test_compiles,
        "test_ok": scan.project_tests_pass,
        "detector": scan.smell_report.detector,
        "aromadr_available": scan.smell_report.aroma_dr_available,
        "smell_count": scan.smell_report.count,
        "smell_types": smell_types,
        "candidate": scan.is_candidate,
    }


def _write_markdown_report(path: Path, summary: dict[str, Any], test_scans: list[TestFileScan]) -> None:
    lines = [
        "# Dataset Candidate Report",
        "",
        f"- Maven projects scanned: `{summary['project_count']}`",
        f"- Projects with Java tests: `{summary['projects_with_tests']}`",
        f"- Projects where tests compile: `{summary['projects_test_compile']}`",
        f"- Projects where tests pass: `{summary['projects_tests_pass']}`",
        f"- Test files scanned: `{summary['test_file_count']}`",
        f"- Smelly test files: `{summary['smelly_test_file_count']}`",
        f"- Candidate repair tests: `{summary['candidate_test_count']}`",
        f"- AromaDr available for files: `{summary['aromadr_available_files']}`",
        "",
        "## Smell Types",
        "",
    ]
    if summary["smell_types"]:
        for smell_type, count in summary["smell_types"].items():
            lines.append(f"- `{smell_type}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Candidate Tests",
            "",
            "| Project | Test File | Smells | Smell Types | Detector |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    candidates = [scan for scan in test_scans if scan.is_candidate]
    if candidates:
        for scan in candidates:
            smell_types = ", ".join(
                f"{name}={count}" for name, count in sorted(scan.smell_report.by_type().items())
            )
            lines.append(
                f"| `{scan.project_id}` | `{scan.test_file}` | "
                f"{scan.smell_report.count} | {smell_types} | `{scan.smell_report.detector}` |"
            )
    else:
        lines.append("| none | none | 0 | none | none |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
