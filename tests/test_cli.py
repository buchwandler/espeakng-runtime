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


def test_cli_batch_with_multiline_item_falls_back_to_per_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multiline items trigger per-item phonemize() fallback."""
    backend = cli.CliBackend(
        executable="/bin/espeak",
        data=None,
        timeout=1,
        requested_mode="cli",
    )
    calls: list[str] = []

    def fake_phonemize(
        text: str,
        *,
        voice: str,
        separator: str | None = None,
        use_tie: bool = False,
        tie_char: str = "͡",
    ) -> str:
        assert voice == "en-us"
        assert separator == "|"
        assert use_tie is False
        assert tie_char == "͡"
        calls.append(text)
        return " ".join(text.split())

    monkeypatch.setattr(backend, "phonemize", fake_phonemize)

    values = ["One", "\n\nTwo", "", "Three\r\nFour"]

    assert backend.phonemize_many(
        values,
        voice="en-us",
        separator="|",
    ) == [
        "One",
        "Two",
        "",
        "Three Four",
    ]
    assert calls == ["One", "\n\nTwo", "Three\r\nFour"]


def test_cli_batch_single_line_items_use_single_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Newline-free batches still use one _run() call, not per-item."""
    run_calls: list[str] = []

    def fake_run(
        command: list[str],
        *,
        input_text: str | None = None,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        run_calls.append(input_text or "")
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="wˈɜːɹd\nwˈɜːɹd\nwˈɜːɹd\n",
            stderr="",
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    backend = cli.CliBackend(
        executable="/bin/espeak",
        data=None,
        timeout=1,
        requested_mode="cli",
    )

    result = backend.phonemize_many(
        ["Word", "Word", "Word"],
        voice="en-us",
    )

    assert len(run_calls) == 1
    assert len(result) == 3
