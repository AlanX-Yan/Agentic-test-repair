from __future__ import annotations

import json
import os
import re
import shlex
import urllib.error
import urllib.request
from pathlib import Path

from .models import ProjectTask, SmellFinding, SmellReport
from .utils import run_command


class AromaDrDetector:
    """External AromaDr adapter.

    Set AROMADR_CMD to the command that runs AromaDr. The command can contain
    placeholders: {project_root} and {test_file}. For the AromaDr HTTP API,
    set AROMADR_API_URL, for example http://localhost:3000.
    """

    def detect(self, task: ProjectTask) -> SmellReport:
        api_url = os.environ.get("AROMADR_API_URL")
        if api_url:
            return self._detect_with_http_api(api_url.rstrip("/"), task)

        command_template = os.environ.get("AROMADR_CMD")
        if not command_template:
            return SmellReport(detector="AromaDr", aroma_dr_available=False)

        command = shlex.split(
            command_template.format(project_root=task.project_root, test_file=task.test_file)
        )
        result = run_command(command, task.project_root, timeout_seconds=60)
        if not result.ok:
            raw = result.stdout + result.stderr
            return SmellReport(detector="AromaDr", raw_output=raw, aroma_dr_available=False)

        findings = self._parse_output(result.stdout, task.test_file)
        return SmellReport(
            findings=findings,
            detector="AromaDr",
            raw_output=result.stdout,
            aroma_dr_available=True,
        )

    def _detect_with_http_api(self, api_url: str, task: ProjectTask) -> SmellReport:
        endpoint = f"{api_url}/file-test-smells/detect"
        payload = {
            "language": "java",
            "framework": "junit",
            "testFileContent": task.test_file.read_text(encoding="utf-8"),
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            return SmellReport(
                detector="AromaDr HTTP",
                raw_output=str(error),
                aroma_dr_available=False,
            )

        findings = self._parse_output(raw, task.test_file)
        return SmellReport(
            findings=findings,
            detector="AromaDr HTTP",
            raw_output=raw,
            aroma_dr_available=True,
        )

    def _parse_output(self, output: str, default_file: Path) -> list[SmellFinding]:
        stripped = output.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            return self._parse_json_output(stripped, default_file)
        return self._parse_csv_output(output, default_file)

    def _parse_csv_output(self, output: str, default_file: Path) -> list[SmellFinding]:
        findings: list[SmellFinding] = []
        for line in output.splitlines():
            # Accept a simple CSV-like format: file,line,smell,message.
            parts = [part.strip() for part in line.split(",", 3)]
            if len(parts) != 4 or not parts[1].isdigit():
                continue
            file_text, line_text, smell_type, message = parts
            findings.append(
                SmellFinding(
                    smell_type=smell_type,
                    file=Path(file_text) if file_text else default_file,
                    line=int(line_text),
                    message=message,
                    source="AromaDr",
                )
            )
        return findings

    def _parse_json_output(self, output: str, default_file: Path) -> list[SmellFinding]:
        try:
            payload = json.loads(output)
        except json.JSONDecodeError:
            return []

        if isinstance(payload, dict):
            if isinstance(payload.get("findings"), list):
                records = payload["findings"]
            elif isinstance(payload.get("smells"), list):
                records = payload["smells"]
            elif isinstance(payload.get("results"), list):
                records = payload["results"]
            else:
                records = [payload]
        elif isinstance(payload, list):
            records = payload
        else:
            records = []

        findings: list[SmellFinding] = []
        aromadr_findings = self._parse_aromadr_file_response(payload, default_file)
        if aromadr_findings:
            return aromadr_findings

        for record in records:
            if not isinstance(record, dict):
                continue
            smell_type = record.get("smell_type") or record.get("type") or record.get("smell")
            if not smell_type:
                continue
            file_text = record.get("file") or record.get("path") or record.get("source")
            line_value = record.get("line") or record.get("startLine") or record.get("line_number") or 1
            message = record.get("message") or record.get("description") or str(smell_type)
            try:
                line = int(line_value)
            except (TypeError, ValueError):
                line = 1
            findings.append(
                SmellFinding(
                    smell_type=str(smell_type),
                    file=Path(file_text) if file_text else default_file,
                    line=line,
                    message=str(message),
                    source="AromaDr",
                )
            )
        return findings

    def _parse_aromadr_file_response(self, payload: object, default_file: Path) -> list[SmellFinding]:
        if not isinstance(payload, dict):
            return []

        findings: list[SmellFinding] = []
        test_suites = payload.get("testSuites")
        if not isinstance(test_suites, list):
            return []

        for suite in test_suites:
            if not isinstance(suite, dict):
                continue
            tests = suite.get("tests")
            if not isinstance(tests, list):
                continue
            for test_entry in tests:
                if not isinstance(test_entry, dict):
                    continue
                test = test_entry.get("test")
                test_name = test.get("name") if isinstance(test, dict) else "unknown test"
                test_smells = test_entry.get("testSmells")
                if not isinstance(test_smells, list):
                    continue
                for smell in test_smells:
                    if not isinstance(smell, dict):
                        continue
                    smell_name = smell.get("name")
                    if not smell_name:
                        continue
                    line = self._safe_int(smell.get("startLine"), default=1)
                    findings.append(
                        SmellFinding(
                            smell_type=str(smell_name),
                            file=default_file,
                            line=line,
                            message=f"AromaDr reported {smell_name} in {test_name}.",
                            source="AromaDr",
                        )
                    )
        return findings

    def _safe_int(self, value: object, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


class LightweightJUnitDetector:
    """Small deterministic detector for the local MVP demo.

    This is not a replacement for AromaDr. It keeps the demo runnable while the
    external detector is unavailable and mirrors the same report contract.
    """

    TEST_METHOD_RE = re.compile(r"(?:public\s+|private\s+|protected\s+)?(?:static\s+)?void\s+(\w+)\s*\(")

    def detect(self, task: ProjectTask) -> SmellReport:
        source = task.test_file.read_text(encoding="utf-8")
        lines = source.splitlines()
        findings: list[SmellFinding] = []

        findings.extend(self._find_generic_names(lines, task.test_file))
        findings.extend(self._find_missing_assertions(lines, task.test_file))
        findings.extend(self._find_overly_broad_tests(lines, task.test_file))
        findings.extend(self._find_missing_exception_case(source, task.test_file))
        findings.extend(self._find_mockito_overuse(lines, task.test_file))

        return SmellReport(findings=findings, detector="lightweight", aroma_dr_available=False)

    def _find_generic_names(self, lines: list[str], file: Path) -> list[SmellFinding]:
        findings: list[SmellFinding] = []
        for method in self._test_methods(lines):
            if method["name"] in {"testBasic", "testCase", "test1", "test2"}:
                findings.append(
                    SmellFinding(
                        "GenericTestName",
                        file,
                        int(method["line"]),
                        f"Test method '{method['name']}' does not describe behavior.",
                    )
                )
        return findings

    def _find_missing_assertions(self, lines: list[str], file: Path) -> list[SmellFinding]:
        findings: list[SmellFinding] = []
        for method in self._test_methods(lines):
            body_text = "\n".join(method["body"])
            has_assertion = bool(
                re.search(r"\bassert(?:Equals|Throws|True|False|Null|NotNull|That)\s*\(", body_text)
            )
            if not has_assertion:
                findings.append(
                    SmellFinding(
                        "MissingAssertion",
                        file,
                        int(method["line"]),
                        f"Test method '{method['name']}' exercises code without a meaningful assertion.",
                        severity="high",
                    )
                )
        return findings

    def _find_overly_broad_tests(self, lines: list[str], file: Path) -> list[SmellFinding]:
        findings: list[SmellFinding] = []
        for method in self._test_methods(lines):
            body_text = "\n".join(method["body"])
            method_calls = len(
                re.findall(r"\b(?!assert\w*\b)(?:calc|sanitizer|subject|sut)\.\w+\s*\(", body_text)
            )
            if method_calls >= 3:
                findings.append(
                    SmellFinding(
                        "OverlyBroadTest",
                        file,
                        int(method["line"]),
                        f"Test method '{method['name']}' checks multiple behaviors in one case.",
                    )
                )
        return findings

    def _find_missing_exception_case(self, source: str, file: Path) -> list[SmellFinding]:
        if "divide(" in source and "assertThrows" not in source and "ArithmeticException" not in source:
            return [
                SmellFinding(
                    "MissingExceptionCase",
                    file,
                    1,
                    "Tests cover division but do not verify divide-by-zero behavior.",
                )
            ]
        if "normalize(null)" in source and "assertThrows" not in source and "NullPointerException" not in source:
            return [
                SmellFinding(
                    "MissingExceptionCase",
                    file,
                    1,
                    "Tests pass null to normalize but do not verify the expected exception behavior.",
                )
            ]
        return []

    def _find_mockito_overuse(self, lines: list[str], file: Path) -> list[SmellFinding]:
        mock_lines = [idx for idx, line in enumerate(lines, start=1) if "Mockito." in line or "mock(" in line]
        if len(mock_lines) >= 3:
            return [
                SmellFinding(
                    "ExcessiveMocking",
                    file,
                    mock_lines[0],
                    "Test contains several mock calls; verify real behavior when possible.",
                )
            ]
        return []

    def _test_methods(self, lines: list[str]) -> list[dict[str, object]]:
        methods: list[dict[str, object]] = []
        pending_test_annotation = False
        current_name = ""
        current_start = 0
        current_body: list[str] = []
        depth = 0

        for number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("@Test"):
                pending_test_annotation = True
                continue

            match = self.TEST_METHOD_RE.search(line)
            is_test_by_name = bool(match and match.group(1).startswith("test"))
            if match and (pending_test_annotation or is_test_by_name):
                current_name = match.group(1)
                current_start = number
                current_body = [line]
                depth = line.count("{") - line.count("}")
                pending_test_annotation = False
                if depth <= 0:
                    methods.append({"name": current_name, "line": current_start, "body": current_body})
                    current_name = ""
                continue

            pending_test_annotation = False if stripped and not stripped.startswith("@") else pending_test_annotation
            if current_name:
                current_body.append(line)
                depth += line.count("{") - line.count("}")
                if depth <= 0:
                    methods.append({"name": current_name, "line": current_start, "body": current_body})
                    current_name = ""

        return methods


class CompositeDetector:
    """Prefer AromaDr when configured, then add lightweight checks for the MVP."""

    def __init__(self) -> None:
        self.aromadr = AromaDrDetector()
        self.lightweight = LightweightJUnitDetector()

    def detect(self, task: ProjectTask) -> SmellReport:
        aroma_report = self.aromadr.detect(task)
        lightweight_report = self.lightweight.detect(task)
        if aroma_report.aroma_dr_available:
            return SmellReport(
                findings=aroma_report.findings + lightweight_report.findings,
                detector="AromaDr+lightweight",
                raw_output=aroma_report.raw_output,
                aroma_dr_available=True,
            )
        return lightweight_report
