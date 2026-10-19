"""Normalize an sdist tarball's metadata for reproducible release packaging."""

from __future__ import annotations

import gzip
import os
import pathlib
import sys
import tarfile


def normalize_sdist(path: pathlib.Path, source_date_epoch: int) -> None:
    if source_date_epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be a non-negative integer")
    if not path.is_file() or path.suffixes[-2:] != [".tar", ".gz"]:
        raise ValueError("sdist path must identify an existing .tar.gz archive")
    temporary = path.with_name(f".{path.name}.normalized")
    try:
        with tarfile.open(path, mode="r:gz") as source:
            members = sorted(source.getmembers(), key=lambda member: member.name)
            if not members:
                raise ValueError("sdist archive is empty")
            with temporary.open("wb") as raw_output:
                with gzip.GzipFile(
                    filename="",
                    mode="wb",
                    fileobj=raw_output,
                    mtime=source_date_epoch,
                    compresslevel=9,
                ) as gzip_output:
                    with tarfile.open(
                        fileobj=gzip_output, mode="w", format=tarfile.PAX_FORMAT
                    ) as destination:
                        for member in members:
                            if member.name.startswith("/") or ".." in pathlib.PurePosixPath(
                                member.name
                            ).parts:
                                raise ValueError("sdist contains an unsafe member path")
                            member.mtime = source_date_epoch
                            member.uid = 0
                            member.gid = 0
                            member.uname = ""
                            member.gname = ""
                            member.pax_headers = {
                                key: value
                                for key, value in member.pax_headers.items()
                                if key
                                not in {"atime", "ctime", "mtime", "LIBARCHIVE.creationtime"}
                            }
                            if member.isfile():
                                stream = source.extractfile(member)
                                if stream is None:
                                    raise ValueError("sdist regular file has no content")
                                with stream:
                                    destination.addfile(member, stream)
                            elif member.isdir() or member.issym() or member.islnk():
                                destination.addfile(member)
                            else:
                                raise ValueError("sdist contains an unsupported member type")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: normalize_sdist.py ARCHIVE SOURCE_DATE_EPOCH", file=sys.stderr)
        return 2
    try:
        normalize_sdist(pathlib.Path(sys.argv[1]), int(sys.argv[2]))
    except (OSError, tarfile.TarError, ValueError) as exc:
        print(f"sdist normalization failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
