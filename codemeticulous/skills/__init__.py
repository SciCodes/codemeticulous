from __future__ import annotations

import shutil
import subprocess
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

SKILL_NAMES = ("research-software-metadata",)

AGENT_DIRECTORIES = {
    "codex": (Path(".agents/skills"),),
    "copilot": (Path(".agents/skills"),),
    "claude": (Path(".claude/skills"),),
    "all": (
        Path(".agents/skills"),
        Path(".claude/skills"),
    ),
}


def bundled_skill(name: str) -> Traversable:
    if name not in SKILL_NAMES:
        raise ValueError(f"Unknown bundled skill: {name}")

    return files(__package__).joinpath(name)


def _copy_resource_tree(source: Traversable, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)

    for child in source.iterdir():
        target = destination / child.name

        if child.is_dir():
            _copy_resource_tree(child, target)
        else:
            with child.open("rb") as source_file:
                with target.open("wb") as target_file:
                    shutil.copyfileobj(source_file, target_file)


def git_repository_root(start: Path | None = None) -> Path:
    """Return the Git repository root containing *start*."""

    working_directory = (start or Path.cwd()).resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=working_directory,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise ValueError(
            "Skill installation must be run from inside a Git repository"
        ) from exc

    return Path(result.stdout.strip()).resolve()


def install_skill(
    name: str,
    agent: str = "codex",
    force: bool = False,
) -> list[Path]:
    if agent not in AGENT_DIRECTORIES:
        raise ValueError(f"Unsupported coding agent: {agent}")

    bundled_skill(name)
    project = git_repository_root()
    installed: list[Path] = []

    # Deduplicate locations because Codex and Copilot share .agents/skills.
    directories = tuple(dict.fromkeys(AGENT_DIRECTORIES[agent]))

    for relative_directory in directories:
        destination = project / relative_directory / name

        if destination.exists():
            if not force:
                raise FileExistsError(
                    f"{destination} already exists; use --force to replace it"
                )
            shutil.rmtree(destination)

        _copy_resource_tree(bundled_skill(name), destination)
        installed.append(destination)

    return installed
