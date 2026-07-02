from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .models import ProjectTask
from .utils import read_json


def load_task(config_path: Path) -> ProjectTask:
    data = read_json(config_path)
    base = config_path.parent.parent
    project_root = (base / data["project_root"]).resolve()
    source_roots = tuple((project_root / root).resolve() for root in data.get("source_roots", []))
    return ProjectTask(
        task_id=data["task_id"],
        project_root=project_root,
        source_under_test=(project_root / data["source_under_test"]).resolve(),
        test_file=(project_root / data["test_file"]).resolve(),
        target_description=data["target_description"],
        build_tool=data.get("build_tool", "javac-demo"),
        max_iterations=int(data.get("max_iterations", 3)),
        source_roots=source_roots,
        test_runner_class=data.get("test_runner_class"),
        max_accepted_smells=int(data.get("max_accepted_smells", 0)),
    )


def load_benchmark(config_path: Path) -> list[Path]:
    data = read_json(config_path)
    base = config_path.parent
    return [(base / item).resolve() for item in data["tasks"]]


def rebase_task(task: ProjectTask, working_project: Path) -> ProjectTask:
    return replace(
        task,
        project_root=working_project,
        source_under_test=working_project / task.source_under_test.relative_to(task.project_root),
        test_file=working_project / task.test_file.relative_to(task.project_root),
        source_roots=tuple(working_project / root.relative_to(task.project_root) for root in task.source_roots),
    )
