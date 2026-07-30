from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_repair_mvp.candidate_selection import (
    select_aromadr_candidates,
    summarize_selection,
)
from test_repair_mvp.utils import write_json


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select a deterministic, project-diverse AromaDr repair subset."
    )
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--max-per-project", type=int, default=2)
    args = parser.parse_args()

    rows = select_aromadr_candidates(
        args.input_csv.resolve(),
        args.output_csv.resolve(),
        limit=args.limit,
        max_per_project=args.max_per_project,
    )
    summary = summarize_selection(rows)
    write_json(args.output_csv.resolve().with_suffix(".summary.json"), summary)
    print(f"Selected candidates: {summary['candidate_count']}")
    print(f"Projects represented: {summary['project_count']}")
    print(f"AromaDr findings represented: {summary['aromadr_smell_count']}")
    print(f"Output: {args.output_csv.resolve()}")


if __name__ == "__main__":
    main()
