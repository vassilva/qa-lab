"""DEF-016: an environment upgraded from v0.4 must end up with the same schema as a fresh install."""

import sqlite3

from app.db import SETTLEMENT_SCHEMA_FILE, Database


def test_fresh_install_has_exactly_the_expected_tables(tmp_path):
    db = Database(url="", sqlite_path=str(tmp_path / "fresh.db"))
    assert db.schema_check() == {"schema_ok": True, "unexpected_tables": [], "missing_tables": []}
    db2 = Database(url="", sqlite_path=str(tmp_path / "st.db"), schema_file=SETTLEMENT_SCHEMA_FILE)
    assert db2.schema_check()["schema_ok"]


def test_upgrade_from_v04_drops_the_orphan_settlement_table(tmp_path):
    path = str(tmp_path / "old.db")
    old = sqlite3.connect(path)          # a v0.4 Trading database: settlement instructions lived here
    old.execute("CREATE TABLE settlement_instructions (instruction_id VARCHAR(20) PRIMARY KEY, trade_id VARCHAR(20))")
    old.commit()
    old.close()

    db = Database(url="", sqlite_path=path)
    assert "settlement_instructions" not in db.actual_tables()
    assert db.schema_check()["schema_ok"]
    assert [r["version"] for r in db._rows("SELECT version FROM schema_migrations")] == \
        ["001_drop_legacy_settlement_instructions"]


def test_migrations_run_once_and_survive_reset(tmp_path):
    path = str(tmp_path / "db.db")
    db = Database(url="", sqlite_path=path)
    db.reset()                                        # test data is cleared, migration history is kept
    assert Database(url="", sqlite_path=path).apply_migrations() == []


def test_schema_check_reports_a_leftover_table(tmp_path):
    db = Database(url="", sqlite_path=str(tmp_path / "x.db"))
    db.execute("CREATE TABLE old_report (id INTEGER)")
    db.commit()
    assert db.schema_check() == {"schema_ok": False, "unexpected_tables": ["old_report"], "missing_tables": []}
