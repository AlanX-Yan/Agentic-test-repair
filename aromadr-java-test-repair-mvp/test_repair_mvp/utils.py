from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .models import CommandResult


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def run_command(command: list[str], cwd: Path, timeout_seconds: int = 30) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return CommandResult(command, cwd, completed.returncode, completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            command,
            cwd,
            124,
            exc.stdout or "",
            (exc.stderr or "") + f"\nTimed out after {timeout_seconds} seconds.",
        )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
