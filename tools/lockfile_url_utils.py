# Copyright Iris contributors
#
# This file is part of Iris and is released under the BSD license.
# See LICENSE in the root of the repository for full licensing details.
"""Shared helpers for conda lockfiles on restricted networks.

Intended for use by Nox and by benchmarking.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request


def lockfile_uses_anaconda_org(lockfile: Path) -> bool:
    """Return whether lockfile contains conda.anaconda.org URLs."""
    with lockfile.open() as infile:
        result = any("conda.anaconda.org" in line for line in infile)
    return result


def network_blocks_anaconda_org(timeout: int = 5) -> bool:
    """Return whether anaconda.org access is blocked by network policy."""
    for url in ("https://conda.anaconda.org", "https://anaconda.org"):
        try:
            urllib.request.urlopen(url, timeout=timeout)
        except urllib.error.HTTPError as error:
            if error.code == 403:
                return True
    return False


def _missing_ssstack_error() -> RuntimeError:
    return RuntimeError(
        "anaconda.org is not accessible (HTTP 403 Forbidden). "
        "UK Met Office devs can add the `ssstack` tool to PATH for "
        "automatic URL conversion when running Nox sessions or benchmarking runs."
    )


def convert_lockfile_with_ssstack(in_file: Path, out_file: Path) -> None:
    """Convert a lockfile's URLs using ssstack shareable --invert."""
    ssstack = shutil.which("ssstack")
    if ssstack is None:
        raise _missing_ssstack_error()

    subprocess.run(
        [
            ssstack,
            "shareable",
            "--invert",
            "--out-file",
            str(out_file),
            str(in_file),
        ],
        check=True,
    )


def rewrite_lockfile_with_internal_mirror(lockfile: Path) -> None:
    """Rewrite lockfile in place using internal mirror URLs via ssstack."""
    with tempfile.NamedTemporaryFile(suffix=".lock") as temp_out:
        temp_out_path = Path(temp_out.name)
        convert_lockfile_with_ssstack(lockfile, temp_out_path)
        lockfile.write_text(temp_out_path.read_text())


@contextmanager
def resolved_lockfile_for_conda_install(lockfile: Path) -> Iterator[Path]:
    """Yield an installable lockfile path for conda install.

    If ssstack is available and the lockfile uses anaconda.org URLs, a converted
    temporary lockfile path is yielded.
    """
    if lockfile_uses_anaconda_org(lockfile):
        if shutil.which("ssstack") is not None:
            with tempfile.NamedTemporaryFile(suffix=".lock") as temp_out:
                temp_out_path = Path(temp_out.name)
                convert_lockfile_with_ssstack(lockfile, temp_out_path)
                yield temp_out_path
                return

        if network_blocks_anaconda_org():
            raise _missing_ssstack_error()

    yield lockfile
