from __future__ import annotations

import argparse
from pathlib import Path

from .benchmark import run_benchmark
from .config import load_task, rebase_task
from .dataset_scanner import scan_maven_dataset
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
    parser.add_argument(
        "--scan-dataset",
        help="Scan a directory of Maven projects and produce dataset candidate reports.",
    )
    parser.add_argument(
        "--dataset-report-dir",
        default=".mvp_runs/dataset-scan",
        help="Output directory for dataset scan reports.",
    )
    parser.add_argument(
        "--dataset-skip-maven",
        action="store_true",
        help="Skip Maven test-compile/test checks during dataset scanning.",
    )
    parser.add_argument(
        "--dataset-timeout-seconds",
        type=int,
        default=180,
        help="Timeout for each Maven command during dataset scanning.",
    )
    parser.add_argument(
        "--dataset-maven-repo",
        help="Shared Maven local repository for dataset scanning. Defaults to <dataset-report-dir>/.m2/repository.",
    )
    parser.add_argument(
        "--dataset-maven-strategy",
        choices=["lifecycle", "fast"],
        default="lifecycle",
        help="Use full Maven lifecycle goals or direct fast screening goals.",
    )
    parser.add_argument(
        "--dataset-candidate-mode",
        choices=["tests-pass", "test-compile", "smelly-only"],
        default="tests-pass",
        help="Criteria for marking a smelly test file as a repair candidate.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    run_dir = (repo_root / args.run_dir).resolve()

    if args.scan_dataset:
        dataset_root = Path(args.scan_dataset)
        if not dataset_root.is_absolute():
            dataset_root = (repo_root / dataset_root).resolve()
        report_dir = Path(args.dataset_report_dir)
        if not report_dir.is_absolute():
            report_dir = (repo_root / report_dir).resolve()
        maven_repo = Path(args.dataset_maven_repo) if args.dataset_maven_repo else None
        if maven_repo and not maven_repo.is_absolute():
            maven_repo = (repo_root / maven_repo).resolve()
        summary = scan_maven_dataset(
            dataset_root,
            report_dir,
            run_maven=not args.dataset_skip_maven,
            timeout_seconds=args.dataset_timeout_seconds,
            maven_repo=maven_repo,
            maven_strategy=args.dataset_maven_strategy,
            candidate_mode=args.dataset_candidate_mode,
        )
        print("Maven dataset scan complete")
        print(f"Maven projects scanned: {summary['project_count']}")
        print(f"Projects with Java tests: {summary['projects_with_tests']}")
        print(f"Projects where tests compile: {summary['projects_test_compile']}")
        print(f"Projects where tests pass: {summary['projects_tests_pass']}")
        print(f"Maven test-compile timeouts: {summary['projects_test_compile_timeout']}")
        print(f"Maven test timeouts: {summary['projects_test_timeout']}")
        print(f"Test files scanned: {summary['test_file_count']}")
        print(f"Smelly test files: {summary['smelly_test_file_count']}")
        print(f"Candidate repair tests: {summary['candidate_test_count']}")
        print(f"Candidate mode: {summary['candidate_mode']}")
        print(f"Artifacts: {summary['artifacts_dir']}")
        return

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
