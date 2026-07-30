from pathlib import Path
from unittest import TestCase

from test_repair_mvp.dataset_scanner import (
    TestFileScan,
    _build_summary,
    _command_problem,
)
from test_repair_mvp.models import CommandResult, SmellFinding, SmellReport


class DatasetScannerSourceMetricsTest(TestCase):
    def test_command_problem_accepts_missing_captured_output(self) -> None:
        result = CommandResult(
            command=["mvn", "test"],
            cwd=Path("."),
            return_code=1,
            stdout=None,
            stderr=None,
        )

        self.assertEqual("", _command_problem(result))

    def test_source_metrics_and_candidate_flags_are_separate(self) -> None:
        report = SmellReport(
            findings=[
                SmellFinding(
                    "UnknownTest",
                    Path("ExampleTest.java"),
                    1,
                    "AromaDr finding.",
                    source="AromaDr",
                ),
                SmellFinding(
                    "MissingAssertion",
                    Path("ExampleTest.java"),
                    2,
                    "Lightweight finding.",
                    source="lightweight",
                ),
            ],
            detector="AromaDr+lightweight",
            aroma_dr_available=True,
        )
        scan = TestFileScan(
            project_id="example",
            project_root=Path("."),
            test_file=Path("ExampleTest.java"),
            smell_report=report,
            project_test_compiles=True,
            project_tests_pass=False,
            candidate_mode="test-compile",
        )

        self.assertEqual(2, report.count)
        self.assertEqual(1, report.count_from("AromaDr"))
        self.assertEqual({"UnknownTest": 1}, report.by_type_from("AromaDr"))
        self.assertEqual(1, report.count_from("lightweight"))
        self.assertTrue(scan.is_candidate)
        self.assertTrue(scan.is_aromadr_candidate)
        self.assertTrue(scan.is_lightweight_candidate)

        summary = _build_summary([], [scan], Path("."))
        self.assertEqual(2, summary["total_smells"])
        self.assertEqual(1, summary["aromadr_total_smells"])
        self.assertEqual(1, summary["lightweight_total_smells"])
        self.assertEqual(1, summary["aromadr_candidate_test_count"])
        self.assertEqual(1, summary["lightweight_candidate_test_count"])

    def test_lightweight_only_finding_is_not_an_aromadr_candidate(self) -> None:
        report = SmellReport(
            findings=[
                SmellFinding(
                    "MissingAssertion",
                    Path("ExampleTest.java"),
                    2,
                    "Lightweight finding.",
                    source="lightweight",
                )
            ]
        )
        scan = TestFileScan(
            project_id="example",
            project_root=Path("."),
            test_file=Path("ExampleTest.java"),
            smell_report=report,
            project_test_compiles=True,
            project_tests_pass=True,
            candidate_mode="test-compile",
        )

        self.assertTrue(scan.is_candidate)
        self.assertFalse(scan.is_aromadr_candidate)
        self.assertTrue(scan.is_lightweight_candidate)
