import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from shutil import copyfile

import pytest

from agniview.migrations import migrate
from db_support import require_test_database


URL = os.getenv("TEST_DATABASE_URL")
if URL:
    require_test_database(URL)
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL required")
MIGRATIONS = Path(__file__).parents[2] / "database" / "migrations"


@pytest.fixture
def database():
    import psycopg

    with psycopg.connect(URL, autocommit=True) as connection:
        require_test_database(URL, actual_name=connection.info.dbname)
        connection.execute("DROP SCHEMA public CASCADE")
        connection.execute("CREATE SCHEMA public")
        yield connection


def test_clean_install_restart_and_concurrent_runners(database):
    import psycopg

    def run():
        with psycopg.connect(URL, autocommit=True) as connection:
            return migrate(connection, MIGRATIONS)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(map(len, results)) == [0, len(list(MIGRATIONS.glob("*.sql")))]
    assert migrate(database, MIGRATIONS) == []
    assert database.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == len(list(MIGRATIONS.glob("*.sql")))


def test_upgrade_legacy_007_preserves_data(database):
    for file in sorted(MIGRATIONS.glob("*.sql"))[:7]:
        database.execute(file.read_text())
    database.execute("INSERT INTO ingestion_jobs(source, status) VALUES ('upgrade-proof', 'succeeded')")
    with pytest.raises(ValueError, match="baseline"):
        migrate(database, MIGRATIONS)
    assert migrate(database, MIGRATIONS, baseline="007") == [p.name for p in sorted(MIGRATIONS.glob("*.sql"))[7:]]
    assert database.execute("SELECT source FROM ingestion_jobs").fetchone()[0] == "upgrade-proof"
    assert database.execute("SELECT content_hash FROM osm_industrial_zones").fetchall() == []
    assert migrate(database, MIGRATIONS) == []


def test_failed_migration_rolls_back_and_can_restart(database, tmp_path):
    (tmp_path / "001_first.sql").write_text("CREATE TABLE proof(id integer);")
    (tmp_path / "002_failure.sql").write_text("INSERT INTO missing_table VALUES (1);")
    with pytest.raises(Exception):
        migrate(database, tmp_path)
    assert database.execute("SELECT to_regclass('proof'), to_regclass('schema_migrations')").fetchone() == (None, None)
    (tmp_path / "002_failure.sql").write_text("INSERT INTO proof VALUES (1);")
    assert len(migrate(database, tmp_path)) == 2
    assert database.execute("SELECT * FROM proof").fetchall() == [(1,)]


def test_modified_applied_migration_is_rejected(database, tmp_path):
    for file in MIGRATIONS.glob("*.sql"):
        copyfile(file, tmp_path / file.name)
    migrate(database, tmp_path)
    first = sorted(tmp_path.glob("*.sql"))[0]
    first.write_text(first.read_text() + "\n-- altered\n")
    with pytest.raises(ValueError, match="changed"):
        migrate(database, tmp_path)
