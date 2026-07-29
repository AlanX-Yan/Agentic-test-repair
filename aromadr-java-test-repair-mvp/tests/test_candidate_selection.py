import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from test_repair_mvp.candidate_selection import (
    select_aromadr_candidates,
    summarize_selection,
)


class CandidateSelectionTest(TestCase):
    def test_selects_only_aromadr_candidates_with_project_cap(self) -> None:
        fieldnames = [
            "project_id",
            "test_file",
            "aromadr_candidate",
            "aromadr_smell_count",
            "aromadr_smell_types",
        ]
        rows = [
            {
                "project_id": "alpha",
                "test_file": "A1Test.java",
                "aromadr_candidate": "True",
                "aromadr_smell_count": "3",
                "aromadr_smell_types": "UnknownTest=3",
            },
            {
                "project_id": "alpha",
                "test_file": "A2Test.java",
                "aromadr_candidate": "True",
                "aromadr_smell_count": "1",
                "aromadr_smell_types": "SleepyTest=1",
            },
            {
                "project_id": "beta",
                "test_file": "BTest.java",
                "aromadr_candidate": "True",
                "aromadr_smell_count": "2",
                "aromadr_smell_types": "AssertionRoulette=2",
            },
            {
                "project_id": "gamma",
                "test_file": "CTest.java",
                "aromadr_candidate": "False",
                "aromadr_smell_count": "4",
                "aromadr_smell_types": "UnknownTest=4",
            },
        ]

        with TemporaryDirectory() as temporary_dir:
            input_csv = Path(temporary_dir) / "input.csv"
            output_csv = Path(temporary_dir) / "output.csv"
            with input_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            selected = select_aromadr_candidates(
                input_csv,
                output_csv,
                limit=3,
                max_per_project=1,
            )

        self.assertEqual(2, len(selected))
        self.assertEqual({"alpha", "beta"}, {row["project_id"] for row in selected})
        self.assertTrue(all(row["aromadr_candidate"] == "True" for row in selected))
        summary = summarize_selection(selected)
        self.assertEqual(2, summary["candidate_count"])
        self.assertEqual(2, summary["project_count"])
