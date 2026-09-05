"""Keep every test away from a developer's demo/integration database."""
import os

os.environ["BCOLLECTION_MODE"] = "test"

import pytest


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch, tmp_path):
    import database
    import cbr_engine
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("BCOLLECTION_MODE", "test")
    monkeypatch.setenv("BCOLLECTION_DB_PATH", str(path))
    for name in ("CORE_BANKING_MODE", "LOS_MODE", "CIC_MODE", "MESSAGING_MODE"):
        monkeypatch.setenv(name, "mock")
    monkeypatch.setattr(database, "DB_FILE_PATH", str(path))
    monkeypatch.setattr(cbr_engine, "_CBR_MATRIX_CACHE", None)
    monkeypatch.setattr(cbr_engine, "_CBR_METADATA_CACHE", None)
