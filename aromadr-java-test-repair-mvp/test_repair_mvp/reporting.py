from __future__ import annotations

import shutil
from pathlib import Path

from .models import IterationRecord, RepairRun
from .utils import write_json


class ArtifactWriter:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def snapshot_iteration(self, record: IterationRecord) -> None:
        iteration_dir = self.artifacts_dir / f"iteration-{record.iteration}"
        iteration_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(record.test_file, iteration_dir / record.test_file.name)
        (iteration_dir / "feedback.txt").write_text(record.feedback, encoding="utf-8")
        write_json(iteration_dir / "smell_report.json", self._smell_report_payload(record))
        write_json(iteration_dir / "execution.json", self._execution_payload(record))

    def write_final_report(self, run: RepairRun) -> None:
        write_json(self.artifacts_dir / "summary.json", run.summary())
        markdown = self._build_markdown_report(run)
        (self.artifacts_dir / "report.md").write_text(markdown, encoding="utf-8")

    def _smell_report_payload(self, record: IterationRecord) -> dict:
        return {
            "detector": record.smell_report.detector,
            "aroma_dr_available": record.smell_report.aroma_dr_available,
            "count": record.smell_report.count,
            "by_type": record.smell_report.by_type(),
            "findings": [
                {
                    "smell_type": finding.smell_type,
                    "file": str(finding.file),
                    "line": finding.line,
                    "message": finding.message,
                    "source": finding.source,
                    "severity": finding.severity,
                }
                for finding in record.smell_report.findings
            ],
        }

    def _execution_payload(self, record: IterationRecord) -> dict:
        result = record.execution.command_result
        return {
            "compiled": record.execution.compiled,
            "passed": record.execution.passed,
            "test_count": record.execution.test_count,
            "failure_count": record.execution.failure_count,
            "command": result.command,
            "cwd": str(result.cwd),
            "return_code": result.return_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "criteria": record.decision.criteria,
        }

    def _build_markdown_report(self, run: RepairRun) -> str:
        lines = [
            "# MVP Repair Run Report",
            "",
            f"- Task: `{run.task.task_id}`",
            f"- Final accepted: `{run.final_accepted}`",
            f"- Iterations: `{len(run.iterations)}`",
            "",
            "| Iteration | Compiled | Passed | Tests | Smells | Smell Types |",
            "| --- | --- | --- | ---: | ---: | --- |",
        ]
        for record in run.iterations:
            smell_types = ", ".join(
                f"{name}={count}" for name, count in sorted(record.smell_report.by_type().items())
            )
            lines.append(
                f"| {record.iteration} | {record.execution.compiled} | {record.execution.passed} | "
                f"{record.execution.test_count} | {record.smell_report.count} | {smell_types or 'none'} |"
            )
        lines.extend(["", "## Final Feedback", "", run.iterations[-1].feedback])
        return "\n".join(lines) + "\n"
