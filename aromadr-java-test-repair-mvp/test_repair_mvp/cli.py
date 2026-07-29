from __future__ import annotations

import argparse
from pathlib import Path

from .agents import create_coding_agent
from .benchmark import run_benchmark
from .candidate_repair import run_candidate_baselines
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
    parser.add_argument(
        "--repair-candidates",
        help="Run a candidate subset CSV through the isolated dataset baseline adapter.",
    )
    parser.add_argument(
        "--repair-output-dir",
        default=".mvp_runs/datatd-repair-baseline",
        help="Output directory for isolated candidate projects and baseline reports.",
    )
    parser.add_argument(
        "--repair-limit",
        type=int,
        help="Optional maximum number of candidate rows to process.",
    )
    parser.add_argument(
        "--repair-offset",
        type=int,
        default=0,
        help="Skip this many candidate rows before applying --repair-limit.",
    )
    parser.add_argument(
        "--repair-maven-repo",
        help="Shared Maven local repository for candidate baselines.",
    )
    parser.add_argument(
        "--repair-timeout-seconds",
        type=int,
        default=600,
        help="Timeout for each candidate Maven test command.",
    )
    parser.add_argument(
        "--coding-backend",
        choices=["template", "deepseek"],
        default="template",
        help="Coding backend. DeepSeek reads DEEPSEEK_API_KEY and related variables.",
    )
    parser.add_argument(
        "--repair-max-attempts",
        type=int,
        default=1,
        help="Maximum DeepSeek repair attempts after the candidate baseline.",
    )
    parser.add_argument(
        "--repair-budget-usd",
        type=float,
        help="Optional shared DeepSeek budget cap for the candidate batch.",
    )
    parser.add_argument(
        "--repair-resume",
        action="store_true",
        help="Resume from candidate_checkpoint.json without repeating completed rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    run_dir = (repo_root / args.run_dir).resolve()

    if args.repair_candidates:
        candidate_csv = Path(args.repair_candidates)
        if not candidate_csv.is_absolute():
            candidate_csv = (repo_root / candidate_csv).resolve()
        output_dir = Path(args.repair_output_dir)
        if not output_dir.is_absolute():
            output_dir = (repo_root / output_dir).resolve()
        maven_repo = Path(args.repair_maven_repo) if args.repair_maven_repo else None
        if maven_repo and not maven_repo.is_absolute():
            maven_repo = (repo_root / maven_repo).resolve()
        summary = run_candidate_baselines(
            candidate_csv,
            output_dir,
            offset=args.repair_offset,
            limit=args.repair_limit,
            maven_repo=maven_repo,
            timeout_seconds=args.repair_timeout_seconds,
            coding_backend=args.coding_backend,
            repair_max_attempts=args.repair_max_attempts,
            repair_budget_usd=args.repair_budget_usd,
            resume=args.repair_resume,
        )
        print("DataTD candidate repair baseline complete")
        print(f"Candidates: {summary['candidate_count']}")
        print(f"Projects represented: {summary['projects_represented']}")
        print(f"Compiled: {summary['compiled_count']}")
        print(f"Tests pass: {summary['tests_pass_count']}")
        print(f"AromaDr available: {summary['aromadr_available_count']}")
        print(f"Eligible for API repair: {summary['eligible_count']}")
        print(f"Accepted: {summary['accepted_count']}")
        print(f"Rolled back: {summary['rolled_back_count']}")
        print(f"Files unchanged: {summary['unchanged_count']}")
        print(f"Artifacts: {summary['artifacts_dir']}")
        return

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

    artifacts_dir = run_dir / "artifacts"
    agent = create_coding_agent(args.coding_backend, artifacts_dir)
    orchestrator = GoalDrivenRepairOrchestrator(artifacts_dir, agent=agent)
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
