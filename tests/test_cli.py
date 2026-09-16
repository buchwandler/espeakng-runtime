from __future__ import annotations

import subprocess

import pytest

from espeakng_runtime.backends import cli


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ("/x/espeak-ng-data", "/x"),
        ("/x/espeak-data", "/x"),
        ("/x", "/x"),
        (None, None),
    ],
)
def test_cli_normalizes_data_path(
    monkeypatch: pytest.MonkeyPatch,
    data: str | None,
    expected: str | None,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    backend = cli.CliBackend(
        executable="/bin/espeak",
        data=data,
        timeout=None,
        requested_mode="cli",
    )

    backend._run(["--version"])

    assert commands == [["/bin/espeak", "--version", *([f"--path={expected}"] if expected else [])]]


def test_cli_invocation_does_not_use_a_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    shell_values: list[object] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        shell_values.append(kwargs["shell"] if "shell" in kwargs else False)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    backend = cli.CliBackend(
        executable="/bin/espeak",
        data=None,
        timeout=1,
        requested_mode="cli",
    )

    backend._run(["--version"])

    assert shell_values == [False]
