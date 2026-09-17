from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path


def check_wheel(path: Path, release_version: str | None) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        assert any(name.endswith("/METADATA") for name in names), "wheel lacks metadata"
        assert "espeakng_runtime/py.typed" in names, "wheel lacks py.typed"
        assert any(name.endswith("/LICENSE") for name in names), "wheel lacks LICENSE"
        if release_version:
            version = release_version.removeprefix("v")
            assert path.name.startswith(f"espeakng_runtime-{version}-"), (
                f"unexpected release wheel name: {path.name}"
            )


def check_sdist(path: Path, release_version: str | None) -> None:
    with tarfile.open(path) as archive:
        names = archive.getnames()
        assert any(name.endswith("/README.md") for name in names), "sdist lacks README.md"
        assert any(name.endswith("/LICENSE") for name in names), "sdist lacks LICENSE"
        if release_version:
            version = release_version.removeprefix("v")
            assert path.name == f"espeakng_runtime-{version}.tar.gz", (
                f"unexpected release sdist name: {path.name}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument("--release-version")
    args = parser.parse_args()
    check_wheel(args.wheel, args.release_version)
    check_sdist(args.sdist, args.release_version)
    print(f"validated {args.wheel.name} and {args.sdist.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
