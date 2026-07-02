from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProjectTask:
    """A single Java test-generation and repair target."""

    task_id: str
    project_root: Path
    source_under_test: Path
    test_file: Path
    target_description: str
    build_tool: str = "javac-demo"
    max_iterations: int = 3
    source_roots: tuple[Path, ...] = field(default_factory=tuple)
    test_runner_class: str | None = None
    max_accepted_smells: int = 0


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    cwd: Path
    return_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.return_code == 0


@dataclass(frozen=True)
class ExecutionResult:
    compiled: bool
    passed: bool
    command_result: CommandResult
    test_count: int = 0
    failure_count: int = 0
    coverage_percent: float | None = None


@dataclass(frozen=True)
class SmellFinding:
    smell_type: str
    file: Path
    line: int
    message: str
    source: str = "lightweight"
    severity: str = "medium"


@dataclass(frozen=True)
class SmellReport:
    findings: list[SmellFinding] = field(default_factory=list)
    detector: str = "lightweight"
    raw_output: str = ""
    aroma_dr_available: bool = False

    @property
    def count(self) -> int:
        return len(self.findings)

    def by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in self.findings:
            counts[finding.smell_type] = counts.get(finding.smell_type, 0) + 1
        return counts


@dataclass(frozen=True)
class EvaluationDecision:
    accepted: bool
    reasons: list[str]
    feedback_items: list[str]
    criteria: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class IterationRecord:
    iteration: int
    test_file: Path
    execution: ExecutionResult
    smell_report: SmellReport
    decision: EvaluationDecision
    feedback: str


@dataclass(frozen=True)
class RepairRun:
    task: ProjectTask
    iterations: list[IterationRecord]
    final_accepted: bool
    artifacts_dir: Path

    def summary(self) -> dict[str, Any]:
        first = self.iterations[0]
        last = self.iterations[-1]
        return {
            "task_id": self.task.task_id,
            "iterations": len(self.iterations),
            "final_accepted": self.final_accepted,
            "initial_smells": first.smell_report.count,
            "final_smells": last.smell_report.count,
            "initial_passed": first.execution.passed,
            "final_passed": last.execution.passed,
            "artifacts_dir": str(self.artifacts_dir),
        }
