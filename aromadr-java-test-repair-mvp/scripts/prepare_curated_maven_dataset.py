from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Clone a curated set of Maven projects for dataset scanning."
    )
    parser.add_argument(
        "--manifest",
        default=str(repo_root / "demo" / "config" / "curated_maven_projects.json"),
        help="Path to the curated Maven project manifest.",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory where projects should be cloned. Defaults to the manifest value.",
    )
    parser.add_argument(
        "--tier",
        choices=["starter", "extended", "all"],
        default="starter",
        help="Project tier to clone.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of selected projects to clone.",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Clone only a specific project id. Can be passed more than once.",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Git clone depth. Use 0 for a full clone.",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Run git pull --ff-only in existing project directories.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_dir = _output_dir(args, manifest, manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    projects = _select_projects(manifest["projects"], args.tier, set(args.only), args.limit)
    if not projects:
        print("No projects matched the requested filters.")
        return 1

    failures: list[str] = []
    for project in projects:
        project_id = project["id"]
        destination = output_dir / project_id
        print(f"\n==> {project_id}")
        print(project["repo"])
        if destination.exists():
            if args.update_existing:
                result = _run(["git", "-C", str(destination), "pull", "--ff-only"])
            else:
                print(f"Skipping existing directory: {destination}")
                continue
        else:
            command = ["git", "clone"]
            if args.depth > 0:
                command.extend(["--depth", str(args.depth)])
            command.extend([project["repo"], str(destination)])
            result = _run(command)
        if result.returncode != 0:
            failures.append(project_id)

    print("\nCurated Maven dataset directory:")
    print(output_dir)
    print("\nNext scanner command:")
    print(
        "python -m test_repair_mvp "
        f"--scan-dataset {output_dir} "
        "--dataset-report-dir .mvp_runs/curated-maven-scan"
    )
    print("\nWith AromaDr:")
    print(
        "AROMADR_API_URL=http://localhost:3000 python -m test_repair_mvp "
        f"--scan-dataset {output_dir} "
        "--dataset-report-dir .mvp_runs/curated-maven-scan-aromadr"
    )

    if failures:
        print(f"\nFailed projects: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


def _output_dir(args: argparse.Namespace, manifest: dict[str, Any], manifest_path: Path) -> Path:
    if args.output_dir:
        candidate = Path(args.output_dir)
    else:
        candidate = Path(manifest["default_output_dir"])
    if candidate.is_absolute():
        return candidate
    repo_root = manifest_path.parents[2]
    return (repo_root / candidate).resolve()


def _select_projects(
    projects: list[dict[str, Any]],
    tier: str,
    only: set[str],
    limit: int | None,
) -> list[dict[str, Any]]:
    selected = projects
    if only:
        selected = [project for project in selected if project["id"] in only]
    elif tier != "all":
        selected = [project for project in selected if project.get("tier") == tier]
    if limit is not None:
        selected = selected[:limit]
    return selected


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    print(" ".join(command))
    result = subprocess.run(command, text=True, check=False)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}", file=sys.stderr)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
