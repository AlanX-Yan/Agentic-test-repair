from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from test_repair_mvp.candidate_repair import (
    _find_project_root,
    _safe_name,
    run_candidate_baselines,
)
from test_repair_mvp.harness import JavaExecutionHarness
from test_repair_mvp.models import CommandResult, ProjectTask


class CandidateRepairSafetyTest(TestCase):
    def test_finds_nearest_maven_project_root(self) -> None:
        with TemporaryDirectory() as temporary_dir:
            project = Path(temporary_dir) / "project"
            test_file = project / "src" / "test" / "java" / "ExampleTest.java"
            test_file.parent.mkdir(parents=True)
            test_file.write_text("class ExampleTest {}", encoding="utf-8")
            (project / "pom.xml").write_text("<project/>", encoding="utf-8")

            self.assertEqual(project, _find_project_root(test_file))

    def test_safe_name_removes_path_separators_and_limits_length(self) -> None:
        name = _safe_name("../project:test/" + ("x" * 200))
        self.assertNotIn("/", name)
        self.assertNotIn("\\", name)
        self.assertLessEqual(len(name), 120)

    @patch("test_repair_mvp.candidate_repair._run_candidate_baseline")
    def test_resume_skips_checkpointed_candidates(self, run_one) -> None:
        with TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            candidate_csv = root / "candidates.csv"
            candidate_csv.write_text(
                "project_id,test_file\nproject,C:/ExampleTest.java\n",
                encoding="utf-8",
            )
            result = {
                "task_id": "dataset:project:ExampleTest",
                "project_id": "project",
                "compiled": True,
                "tests_pass": True,
                "aromadr_available": True,
                "unchanged": True,
                "accepted": True,
                "eligible": True,
                "rolled_back": False,
                "aromadr_smells": 0,
                "attempts": 0,
                "status": "accepted",
                "artifacts_dir": str(root / "artifacts"),
                "diff": "",
            }
            run_one.return_value = result
            output = root / "output"

            run_candidate_baselines(candidate_csv, output, limit=1)
            run_candidate_baselines(candidate_csv, output, limit=1, resume=True)

            self.assertEqual(1, run_one.call_count)

    @patch("test_repair_mvp.harness.run_command")
    def test_maven_two_stage_mode_separates_compile_and_test_failure(
        self,
        run_command,
    ) -> None:
        project = Path(".").resolve()
        run_command.side_effect = [
            CommandResult(["mvn", "test-compile"], project, 0, "", ""),
            CommandResult(["mvn", "test"], project, 1, "", "tests failed"),
        ]
        task = ProjectTask(
            task_id="dataset:test",
            project_root=project,
            source_under_test=project / "pom.xml",
            test_file=project / "ExampleTest.java",
            target_description="test",
            build_tool="maven",
            maven_test_compile_first=True,
        )

        result = JavaExecutionHarness().run_tests(task)

        self.assertTrue(result.compiled)
        self.assertFalse(result.passed)
        self.assertEqual(2, run_command.call_count)
