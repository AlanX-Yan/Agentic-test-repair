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
    candidate_mode: str = "tests-pass"

    @property
    def is_candidate(self) -> bool:
        return self._is_candidate_for_count(self.smell_report.count)

    @property
    def is_aromadr_candidate(self) -> bool:
        return self._is_candidate_for_count(self.smell_report.count_from("AromaDr"))

    @property
    def is_lightweight_candidate(self) -> bool:
        return self._is_candidate_for_count(self.smell_report.count_from("lightweight"))

    def _is_candidate_for_count(self, smell_count: int) -> bool:
        if smell_count <= 0:
            return False
        if self.candidate_mode == "smelly-only":
            return True
        if self.candidate_mode == "test-compile":
            return self.project_test_compiles
        return self.project_test_compiles and self.project_tests_pass


def scan_maven_dataset(
    dataset_root: Path,
    output_dir: Path,
    *,
    run_maven: bool = True,
    timeout_seconds: int = 180,
    maven_repo: Path | None = None,
    maven_strategy: str = "lifecycle",
    candidate_mode: str = "tests-pass",
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
    resolved_maven_repo = (maven_repo or output_dir / ".m2" / "repository").resolve()

    detector = CompositeDetector()
    project_scans: list[MavenProjectScan] = []
    test_scans: list[TestFileScan] = []

    for pom_file in discover_maven_projects(dataset_root):
        project_root = pom_file.parent
        project_scan = _scan_project(
            project_root,
            dataset_root,
            run_maven,
            timeout_seconds,
            resolved_maven_repo,
            maven_strategy,
        )
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
                    candidate_mode=candidate_mode,
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
    maven_repo: Path,
    maven_strategy: str,
) -> MavenProjectScan:
    test_files = _discover_test_files(project_root)
    test_compile = None
    test_run = None
    if run_maven and test_files:
        test_compile = _run_maven(
            project_root,
            _maven_goals("test-compile", maven_strategy),
            timeout_seconds,
            maven_repo,
        )
        if test_compile.ok:
            test_run = _run_maven(
                project_root,
                _maven_goals("test", maven_strategy),
                timeout_seconds,
                maven_repo,
            )
    return MavenProjectScan(
        project_id=_project_id(project_root, dataset_root),
        project_root=project_root,
        pom_file=project_root / "pom.xml",
        test_files=test_files,
        test_compile=test_compile,
        test_run=test_run,
    )


def _run_maven(
    project_root: Path,
    goals: list[str],
    timeout_seconds: int,
    maven_repo: Path,
) -> CommandResult:
    maven_bin = JavaExecutionHarness()._maven_bin()
    command = [
        maven_bin,
        "--batch-mode",
        "--no-transfer-progress",
        f"-Dmaven.repo.local={maven_repo}",
        "-DskipITs=true",
        "-Drat.skip=true",
        "-Dcheckstyle.skip=true",
        "-Dspotbugs.skip=true",
        "-Dmaven.javadoc.skip=true",
    ] + goals
    return run_command(command, project_root, timeout_seconds=timeout_seconds)


def _maven_goals(check: str, strategy: str) -> list[str]:
    if strategy == "fast":
        if check == "test-compile":
            return [
                "resources:resources",
                "resources:testResources",
                "compiler:compile",
                "compiler:testCompile",
            ]
        return ["surefire:test"]
    return [check]


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
    aromadr_candidates = [scan for scan in test_scans if scan.is_aromadr_candidate]
    lightweight_candidates = [scan for scan in test_scans if scan.is_lightweight_candidate]
    combined_metrics = _smell_metrics(test_scans)
    aromadr_metrics = _smell_metrics(test_scans, source="AromaDr")
    lightweight_metrics = _smell_metrics(test_scans, source="lightweight")

    return {
        "project_count": len(project_scans),
        "projects_with_tests": sum(1 for scan in project_scans if scan.has_tests),
        "projects_test_compile": sum(1 for scan in project_scans if scan.test_compiles),
        "projects_tests_pass": sum(1 for scan in project_scans if scan.tests_pass),
        "projects_test_compile_timeout": sum(
            1 for scan in project_scans if scan.test_compile and scan.test_compile.return_code == 124
        ),
        "projects_test_timeout": sum(
            1 for scan in project_scans if scan.test_run and scan.test_run.return_code == 124
        ),
        "test_file_count": len(test_scans),
        "smelly_test_file_count": combined_metrics["smelly_file_count"],
        "candidate_test_count": len(candidates),
        "aromadr_smelly_test_file_count": aromadr_metrics["smelly_file_count"],
        "aromadr_candidate_test_count": len(aromadr_candidates),
        "lightweight_smelly_test_file_count": lightweight_metrics["smelly_file_count"],
        "lightweight_candidate_test_count": len(lightweight_candidates),
        "candidate_mode": candidates[0].candidate_mode if candidates else _candidate_mode(test_scans),
        "total_smells": combined_metrics["total"],
        "smell_types": combined_metrics["types"],
        "aromadr_total_smells": aromadr_metrics["total"],
        "aromadr_smell_types": aromadr_metrics["types"],
        "lightweight_total_smells": lightweight_metrics["total"],
        "lightweight_smell_types": lightweight_metrics["types"],
        "aromadr_available_files": sum(1 for scan in test_scans if scan.smell_report.aroma_dr_available),
        "artifacts_dir": str(output_dir),
    }


def _smell_metrics(
    test_scans: list[TestFileScan],
    source: str | None = None,
) -> dict[str, Any]:
    smell_types: dict[str, int] = {}
    total = 0
    smelly_file_count = 0
    for scan in test_scans:
        report = scan.smell_report
        count = report.count if source is None else report.count_from(source)
        by_type = report.by_type() if source is None else report.by_type_from(source)
        total += count
        if count > 0:
            smelly_file_count += 1
        for smell_type, smell_count in by_type.items():
            smell_types[smell_type] = smell_types.get(smell_type, 0) + smell_count
    return {
        "total": total,
        "smelly_file_count": smelly_file_count,
        "types": dict(sorted(smell_types.items(), key=lambda item: (-item[1], item[0]))),
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
        "test_compile_problem",
        "test_problem",
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
                    "test_compile_problem": _command_problem(scan.test_compile),
                    "test_problem": _command_problem(scan.test_run),
                }
            )


def _command_problem(result: CommandResult | None) -> str:
    if result is None or result.ok:
        return ""
    if result.return_code == 124:
        return "timeout"
    text = "\n".join([result.stderr, result.stdout])
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[ERROR]"):
            return stripped[:240]
    return text.strip().replace("\n", " ")[:240]


def _write_test_files_csv(path: Path, test_scans: list[TestFileScan]) -> None:
    fieldnames = [
        "project_id",
        "test_file",
        "test_compile_ok",
        "test_ok",
        "candidate_mode",
        "detector",
        "aromadr_available",
        "smell_count",
        "smell_types",
        "aromadr_smell_count",
        "aromadr_smell_types",
        "lightweight_smell_count",
        "lightweight_smell_types",
        "candidate",
        "aromadr_candidate",
        "lightweight_candidate",
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
        "candidate_mode",
        "detector",
        "aromadr_available",
        "smell_count",
        "smell_types",
        "aromadr_smell_count",
        "aromadr_smell_types",
        "lightweight_smell_count",
        "lightweight_smell_types",
        "candidate",
        "aromadr_candidate",
        "lightweight_candidate",
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
    aromadr_smell_types = "; ".join(
        f"{name}={count}"
        for name, count in sorted(scan.smell_report.by_type_from("AromaDr").items())
    )
    lightweight_smell_types = "; ".join(
        f"{name}={count}"
        for name, count in sorted(scan.smell_report.by_type_from("lightweight").items())
    )
    return {
        "project_id": scan.project_id,
        "test_file": str(scan.test_file),
        "test_compile_ok": scan.project_test_compiles,
        "test_ok": scan.project_tests_pass,
        "candidate_mode": scan.candidate_mode,
        "detector": scan.smell_report.detector,
        "aromadr_available": scan.smell_report.aroma_dr_available,
        "smell_count": scan.smell_report.count,
        "smell_types": smell_types,
        "aromadr_smell_count": scan.smell_report.count_from("AromaDr"),
        "aromadr_smell_types": aromadr_smell_types,
        "lightweight_smell_count": scan.smell_report.count_from("lightweight"),
        "lightweight_smell_types": lightweight_smell_types,
        "candidate": scan.is_candidate,
        "aromadr_candidate": scan.is_aromadr_candidate,
        "lightweight_candidate": scan.is_lightweight_candidate,
    }


def _write_markdown_report(path: Path, summary: dict[str, Any], test_scans: list[TestFileScan]) -> None:
    lines = [
        "# Dataset Candidate Report",
        "",
        f"- Maven projects scanned: `{summary['project_count']}`",
        f"- Projects with Java tests: `{summary['projects_with_tests']}`",
        f"- Projects where tests compile: `{summary['projects_test_compile']}`",
        f"- Projects where tests pass: `{summary['projects_tests_pass']}`",
        f"- Maven test-compile timeouts: `{summary['projects_test_compile_timeout']}`",
        f"- Maven test timeouts: `{summary['projects_test_timeout']}`",
        f"- Test files scanned: `{summary['test_file_count']}`",
        f"- Smelly test files: `{summary['smelly_test_file_count']}`",
        f"- Candidate repair tests: `{summary['candidate_test_count']}`",
        f"- AromaDr-only smelly test files: `{summary['aromadr_smelly_test_file_count']}`",
        f"- AromaDr-only candidate repair tests: `{summary['aromadr_candidate_test_count']}`",
        f"- Lightweight-only smelly test files: `{summary['lightweight_smelly_test_file_count']}`",
        f"- Lightweight-only candidate repair tests: `{summary['lightweight_candidate_test_count']}`",
        f"- Candidate mode: `{summary['candidate_mode']}`",
        f"- AromaDr available for files: `{summary['aromadr_available_files']}`",
        "",
        "## AromaDr-Only Smell Types",
        "",
    ]
    if summary["aromadr_smell_types"]:
        for smell_type, count in summary["aromadr_smell_types"].items():
            lines.append(f"- `{smell_type}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Lightweight-Only Smell Types",
            "",
        ]
    )
    if summary["lightweight_smell_types"]:
        for smell_type, count in summary["lightweight_smell_types"].items():
            lines.append(f"- `{smell_type}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Combined Smell Types",
            "",
        ]
    )
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
            "| Project | Test File | Combined | AromaDr | Lightweight | Smell Types | Detector |",
            "| --- | --- | ---: | ---: | ---: | --- | --- |",
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
                f"{scan.smell_report.count} | {scan.smell_report.count_from('AromaDr')} | "
                f"{scan.smell_report.count_from('lightweight')} | {smell_types} | "
                f"`{scan.smell_report.detector}` |"
            )
    else:
        lines.append("| none | none | 0 | 0 | 0 | none | none |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _candidate_mode(test_scans: list[TestFileScan]) -> str:
    if not test_scans:
        return "tests-pass"
    return test_scans[0].candidate_mode
