from __future__ import annotations

import gzip
import io
import pathlib
import tarfile

import pytest
from scripts.normalize_sdist import normalize_sdist


def _make_sdist(path: pathlib.Path, *, mtime: int, uid: int) -> None:
    content = b"package metadata\n"
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="different-name", mode="wb", fileobj=raw, mtime=mtime) as gz:
            with tarfile.open(fileobj=gz, mode="w:") as archive:
                directory = tarfile.TarInfo("sample-0.1.0")
                directory.type = tarfile.DIRTYPE
                directory.mode = 0o755
                directory.uid = uid
                directory.gid = uid
                directory.mtime = mtime
                archive.addfile(directory)
                member = tarfile.TarInfo("sample-0.1.0/PKG-INFO")
                member.mode = 0o644
                member.uid = uid
                member.gid = uid
                member.mtime = mtime
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))


def test_normalizer_makes_equivalent_sdists_byte_reproducible(tmp_path: pathlib.Path) -> None:
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    _make_sdist(first, mtime=1_700_000_000, uid=1000)
    _make_sdist(second, mtime=1_800_000_000, uid=2000)

    normalize_sdist(first, 1_750_000_000)
    normalize_sdist(second, 1_750_000_000)

    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first, "r:gz") as archive:
        member = archive.getmember("sample-0.1.0/PKG-INFO")
        assert member.mtime == 1_750_000_000
        assert member.uid == 0
        assert archive.extractfile(member).read() == b"package metadata\n"


@pytest.mark.parametrize("name", ["package.whl", "missing.tar.gz"])
def test_normalizer_rejects_unsupported_or_missing_paths(tmp_path: pathlib.Path, name: str) -> None:
    path = tmp_path / name
    with pytest.raises(ValueError):
        normalize_sdist(path, 1_750_000_000)


def test_normalizer_rejects_negative_epoch(tmp_path: pathlib.Path) -> None:
    archive = tmp_path / "sample.tar.gz"
    _make_sdist(archive, mtime=1_700_000_000, uid=1000)
    with pytest.raises(ValueError, match="non-negative"):
        normalize_sdist(archive, -1)
