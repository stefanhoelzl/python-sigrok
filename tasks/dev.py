from __future__ import annotations

import sys

import pytest
from invoke import Context, task

from tasks.common import ProjectPath, TestsPath


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
