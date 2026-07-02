from __future__ import annotations

import argparse
from pathlib import Path

from .benchmark import run_benchmark
from .config import load_task, rebase_task
from .orchestrator import GoalDrivenRepairOrchestrator
from .utils import copy_tree, ensure_clean_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Java test repair MVP demo.")
    parser.add_argument(
        "--config",
        default="demo/config/demo_task.json",
        help="Path to task config JSON.",
    )
    parser.add_argument(
        "--benchmark",
        help="Optional benchmark config JSON containing a list of task configs.",
    )
    parser.add_argument(
        "--run-dir",
        default=".mvp_runs/latest",
        help="Directory for the isolated demo project and artifacts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    run_dir = (repo_root / args.run_dir).resolve()

    if args.benchmark:
        benchmark_config = (repo_root / args.benchmark).resolve()
        report = run_benchmark(benchmark_config, run_dir)
        print("Goal-driven Java test repair benchmark complete")
        print(f"Tasks: {report['task_count']}")
        print(f"Accepted: {report['accepted_count']}")
        print(f"Initial smells: {report['initial_smells']}")
        print(f"Final smells: {report['final_smells']}")
        print(f"Artifacts: {report['artifacts_dir']}")
        return

    config_path = (repo_root / args.config).resolve()
    ensure_clean_dir(run_dir)

    loaded_task = load_task(config_path)
    template_project = loaded_task.project_root
    working_project = run_dir / "java_project"
    copy_tree(template_project, working_project)

    task = rebase_task(loaded_task, working_project)

    orchestrator = GoalDrivenRepairOrchestrator(run_dir / "artifacts")
    run = orchestrator.run(task)

    summary = run.summary()
    print("Goal-driven Java test repair MVP complete")
    print(f"Task: {summary['task_id']}")
    print(f"Iterations: {summary['iterations']}")
    print(f"Initial smells: {summary['initial_smells']}")
    print(f"Final smells: {summary['final_smells']}")
    print(f"Final accepted: {summary['final_accepted']}")
    print(f"Artifacts: {summary['artifacts_dir']}")


if __name__ == "__main__":
    main()
