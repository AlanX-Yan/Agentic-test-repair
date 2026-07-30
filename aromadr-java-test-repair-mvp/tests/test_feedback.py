from pathlib import Path
from unittest import TestCase

from test_repair_mvp.feedback import MasterEvaluator
from test_repair_mvp.models import (
    CommandResult,
    ExecutionResult,
    ProjectTask,
    SmellFinding,
    SmellReport,
)


class MasterEvaluatorTest(TestCase):
    def test_aromadr_is_authoritative_when_available(self) -> None:
        root = Path(".").resolve()
        task = ProjectTask(
            task_id="candidate",
            project_root=root,
            source_under_test=root / "pom.xml",
            test_file=root / "ExampleTest.java",
            target_description="repair",
        )
        execution = ExecutionResult(
            compiled=True,
            passed=True,
            command_result=CommandResult(["mvn", "test"], root, 0, "", ""),
        )
        report = SmellReport(
            findings=[
                SmellFinding(
                    smell_type="ExcessiveMocking",
                    file=task.test_file,
                    line=1,
                    message="local heuristic",
                    source="lightweight",
                )
            ],
            detector="AromaDr+lightweight",
            aroma_dr_available=True,
        )

        decision = MasterEvaluator().evaluate(task, execution, report)

        self.assertTrue(decision.accepted)
        self.assertTrue(decision.criteria["smell_threshold"])

    def test_feedback_ignores_lightweight_findings_when_aromadr_is_available(self) -> None:
        report = SmellReport(
            findings=[
                SmellFinding(
                    smell_type="MagicNumberTest",
                    file=Path("ExampleTest.java"),
                    line=3,
                    message="AromaDr finding",
                    source="AromaDr",
                ),
                SmellFinding(
                    smell_type="ExcessiveMocking",
                    file=Path("ExampleTest.java"),
                    line=4,
                    message="local heuristic",
                    source="lightweight",
                ),
            ],
            detector="AromaDr+lightweight",
            aroma_dr_available=True,
        )

        feedback = MasterEvaluator()._feedback_from_smells(report)

        self.assertEqual(1, len(feedback))
        self.assertIn("numeric literals", feedback[0])
