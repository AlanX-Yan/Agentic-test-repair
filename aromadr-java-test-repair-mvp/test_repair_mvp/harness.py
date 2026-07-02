from __future__ import annotations

import shutil
import re
from pathlib import Path

from .models import CommandResult, ExecutionResult, ProjectTask
from .utils import run_command


class JavaExecutionHarness:
    """Compile and execute generated tests for Java projects."""

    def run_tests(self, task: ProjectTask) -> ExecutionResult:
        if task.build_tool == "maven":
            local_repo = task.project_root / ".m2" / "repository"
            return self._run_build_tool(
                task,
                [self._maven_bin(), f"-Dmaven.repo.local={local_repo}", "test"],
            )
        if task.build_tool == "gradle":
            return self._run_build_tool(task, ["gradle", "test"])
        return self._run_javac_demo(task)

    def _run_build_tool(self, task: ProjectTask, command: list[str]) -> ExecutionResult:
        if not Path(command[0]).exists() and shutil.which(command[0]) is None:
            result = CommandResult(command, task.project_root, 127, "", f"{command[0]} is not installed.")
            return ExecutionResult(compiled=False, passed=False, command_result=result)

        result = run_command(command, task.project_root, timeout_seconds=180)
        return ExecutionResult(
            compiled=result.ok,
            passed=result.ok,
            command_result=result,
            test_count=self._extract_maven_test_count(result.stdout),
            failure_count=self._extract_maven_failure_count(result.stdout, default=0 if result.ok else 1),
        )

    def _maven_bin(self) -> str:
        from os import environ

        configured = environ.get("MAVEN_BIN")
        if configured:
            return configured

        workspace_root = Path(__file__).resolve().parents[2]
        local_maven = workspace_root / "tools" / "apache-maven-3.9.16" / "bin" / "mvn"
        if local_maven.exists():
            return str(local_maven)
        return "mvn"

    def _run_javac_demo(self, task: ProjectTask) -> ExecutionResult:
        classes_dir = task.project_root / "build" / "classes"
        classes_dir.mkdir(parents=True, exist_ok=True)

        source_files = self._java_sources(task)
        compile_cmd = ["javac", "-d", str(classes_dir)] + [str(path) for path in source_files]
        compile_result = run_command(compile_cmd, task.project_root)
        if not compile_result.ok:
            return ExecutionResult(compiled=False, passed=False, command_result=compile_result, failure_count=1)

        runner_class = task.test_runner_class or self._class_name_from_file(task.test_file)
        run_cmd = ["java", "-cp", str(classes_dir), runner_class]
        run_result = run_command(run_cmd, task.project_root)
        test_count = self._extract_test_count(run_result.stdout)
        failure_count = self._extract_failure_count(run_result.stdout, default=0 if run_result.ok else 1)
        return ExecutionResult(
            compiled=True,
            passed=run_result.ok,
            command_result=run_result,
            test_count=test_count,
            failure_count=failure_count,
        )

    def _java_sources(self, task: ProjectTask) -> list[Path]:
        roots = task.source_roots or (
            task.project_root / "src" / "main" / "java",
            task.project_root / "src" / "test" / "java",
        )
        sources: list[Path] = []
        for root in roots:
            if root.exists():
                sources.extend(sorted(root.rglob("*.java")))
        if task.test_file not in sources and task.test_file.exists():
            sources.append(task.test_file)
        return sources

    def _class_name_from_file(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        package = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("package ") and stripped.endswith(";"):
                package = stripped.removeprefix("package ").removesuffix(";")
                break
        class_name = path.stem
        return f"{package}.{class_name}" if package else class_name

    def _extract_test_count(self, stdout: str) -> int:
        for line in stdout.splitlines():
            if line.startswith("TESTS_RUN="):
                try:
                    return int(line.split("=", 1)[1])
                except ValueError:
                    return 0
        return 0

    def _extract_failure_count(self, stdout: str, default: int) -> int:
        for line in stdout.splitlines():
            if line.startswith("TESTS_FAILED="):
                try:
                    return int(line.split("=", 1)[1])
                except ValueError:
                    return default
        return default

    def _extract_maven_test_count(self, stdout: str) -> int:
        last = 0
        for match in re.finditer(r"Tests run:\s*(\d+),", stdout):
            last = int(match.group(1))
        return last

    def _extract_maven_failure_count(self, stdout: str, default: int) -> int:
        last = 0
        seen = False
        for match in re.finditer(r"Failures:\s*(\d+),\s*Errors:\s*(\d+),", stdout):
            seen = True
            last = int(match.group(1)) + int(match.group(2))
        return last if seen else default
