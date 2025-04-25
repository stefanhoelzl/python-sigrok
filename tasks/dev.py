from __future__ import annotations

import json
import sys
import urllib.request

import pytest
import tomlkit
from invoke import Context, task

from tasks.common import ProjectPath, PyProjectPath, TestsPath


@task
def format_and_lint(
    ctx: Context, single_file: str | None = None, *, ci: bool = False
) -> None:
    """formatting and linting"""
    fmt_flags = "--diff" if ci else ""
    chk_flags = (
        "--diff"
        if ci
        else ("--fix" + (" --unfixable=F401,F841" if single_file else ""))
    )

    failed = ctx.run(
        f"uv run ruff format {fmt_flags} {single_file or ProjectPath}", warn=True
    ).failed
    failed |= ctx.run(
        f"uv run ruff check {chk_flags} {single_file or ProjectPath}", warn=True
    ).failed

    if not single_file:
        failed |= ctx.run(f"uv run mypy {ProjectPath}", warn=True).failed

    if failed:
        sys.exit(1)


@task
def tests(_: Context) -> None:
    sys.exit(pytest.main(TestsPath))


@task
def update_version(_: Context) -> None:
    with PyProjectPath.open(mode="rb") as fh:
        pyproject = tomlkit.load(fh)

    name = pyproject["project"]["name"]  # type: ignore[index]
    version = pyproject["project"]["version"]  # type: ignore[index]

    with urllib.request.urlopen(f"https://test.pypi.org/pypi/{name}/json") as f:
        releases = set(json.load(f).get("releases", {}).keys())

    build_nr = sum(
        1
        for release in releases
        if release == version or release.startswith(f"{version}.post")
    )

    pyproject["project"]["version"] = f"{version}.post{build_nr}"  # type: ignore[index]

    with PyProjectPath.open(mode="w") as fh:
        tomlkit.dump(pyproject, fh)
