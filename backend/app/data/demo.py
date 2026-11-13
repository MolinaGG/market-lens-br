"""Unpack the attributed, frozen public demonstration snapshot."""

import argparse
import gzip
import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


def ensure_demo_snapshot(target: Path, archive: Path) -> Path:
    target = Path(target)
    archive = Path(archive)
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(fd)
    try:
        with gzip.open(archive, "rb") as source, open(temporary, "wb") as output:
            shutil.copyfileobj(source, output)
        with closing(sqlite3.connect(temporary)) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Demo snapshot failed integrity validation")
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unpack the frozen public demo snapshot")
    parser.add_argument("--database", type=Path, default=Path("data/market_lens.db"))
    parser.add_argument("--archive", type=Path, default=Path("demo/open_data_snapshot.sqlite.gz"))
    options = parser.parse_args()
    print(ensure_demo_snapshot(options.database, options.archive))
