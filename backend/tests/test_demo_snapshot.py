import gzip
import sqlite3

from app.data.demo import ensure_demo_snapshot


def test_demo_unpack_is_atomic_and_does_not_replace_existing_database(tmp_path):
    source = tmp_path / "source.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE marker (value TEXT)")
        connection.execute("INSERT INTO marker VALUES ('demo')")
    archive = tmp_path / "source.sqlite.gz"
    with gzip.open(archive, "wb") as stream:
        stream.write(source.read_bytes())
    target = tmp_path / "nested" / "snapshot.sqlite"
    ensure_demo_snapshot(target, archive)
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT value FROM marker").fetchone()[0] == "demo"
    before = target.read_bytes()
    archive.write_bytes(b"broken")
    ensure_demo_snapshot(target, archive)
    assert target.read_bytes() == before
