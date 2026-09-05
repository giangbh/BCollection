import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from bc_runtime.settings import RuntimeSettings
import database as db
from main import app

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/bcollection.py"


def command(path, *args, mode="test"):
    return subprocess.run(
        [sys.executable, str(CLI), "--mode", mode, "--database", str(path), *args],
        capture_output=True, text=True, cwd=ROOT, timeout=30,
    )


def dump_data(path):
    with sqlite3.connect(path) as conn:
        return {table: conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
                for table in ("cases", "case_interactions", "cbr_reference_cases")}


def integration_env(monkeypatch):
    monkeypatch.setenv("BCOLLECTION_MODE", "integration")
    for prefix, url in (("CORE_BANKING", "CORE_BANKING_API_URL"), ("LOS", "LOS_API_URL"), ("CIC", "CIC_GATEWAY_URL")):
        monkeypatch.setenv(f"{prefix}_MODE", "http")
        monkeypatch.setenv(url, "https://integration.invalid/api")


def test_import_does_not_create_database(tmp_path):
    path = tmp_path / "no-import-side-effect.sqlite3"
    env = {**os.environ, "BCOLLECTION_DB_PATH": str(path), "PYTHONPATH": str(ROOT / "bcollection-platform/services/collection-api/src")}
    result = subprocess.run([sys.executable, "-c", "import main"], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert not path.exists()


@pytest.mark.parametrize("mode", ["test", "demo"])
def test_startup_creates_schema_without_business_data(monkeypatch, mode):
    monkeypatch.setenv("BCOLLECTION_MODE", mode)
    with TestClient(app) as client:
        assert client.get("/api/cases").json() == []
        for table in ("cases", "case_interactions", "cbr_reference_cases"):
            assert client.get("/api/db/schema").json()["tables"][table]["row_count"] == 0
        response = client.get("/api/runtime")
        assert response.json()["mode"] == mode
        assert response.headers["X-BCollection-Simulation"] == "true"


def test_seed_is_explicit_deterministic_idempotent_and_labelled(tmp_path):
    first, second = tmp_path / "first.sqlite3", tmp_path / "second.sqlite3"
    for path in (first, second):
        result = command(path, "seed-demo")
        assert result.returncode == 0, result.stderr
    original = dump_data(first)
    assert original == dump_data(second)
    assert len(original["cases"]) == 500
    assert len(original["cbr_reference_cases"]) == 1000
    assert all(row[-1] == "SYNTHETIC" for rows in original.values() for row in rows)
    result = command(first, "seed-demo")
    assert result.returncode == 0, result.stderr
    assert dump_data(first) == original
    assert command(first, "seed-demo", "--seed", "43").returncode != 0
    assert dump_data(first) == original


def test_seed_refuses_existing_unclassified_data(tmp_path):
    db.init_db()
    with db.get_connection() as conn:
        conn.execute("INSERT INTO cbr_reference_cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     ("EXISTING", "MORTGAGE", 1, "UNKNOWN", "[]", "Existing user data", 0, 1, "PENDING", "[]", "2026-09-01", "UNKNOWN"))
    before = dump_data(db.DB_FILE_PATH)
    assert command(db.DB_FILE_PATH, "seed-demo").returncode != 0
    assert dump_data(db.DB_FILE_PATH) == before


def test_seeded_api_restart_does_not_reseed_and_restores_mock_obligations():
    result = command(db.DB_FILE_PATH, "seed-demo")
    assert result.returncode == 0, result.stderr
    before = dump_data(db.DB_FILE_PATH)
    for _ in range(2):
        with TestClient(app) as client:
            cases = client.get("/api/cases").json()
            case = cases[0]
            response = client.get(f"/api/cases/{case['case_id']}/persona")
            assert response.status_code == 200, response.text
            import main
            assert main.obl_repo.get_party_obligation(case["loan_id"], case["debtor_cif"])
            assert main.core_banking_adapter.get_realtime_balance(case["loan_id"]).overdue_amount == case["overdue_amount"]
    assert dump_data(db.DB_FILE_PATH) == before


def test_new_demo_interactions_keep_synthetic_provenance():
    assert command(db.DB_FILE_PATH, "seed-demo").returncode == 0
    with TestClient(app) as client:
        case = client.get("/api/cases").json()[0]
        result = client.post(f"/api/cases/{case['case_id']}/call-wrapup", json={
            "guardrail_token": "", "outcome": "BUSY_NO_ANSWER",
        })
        assert result.status_code == 200
        assert all(row["data_origin"] == "SYNTHETIC" for row in client.get(f"/api/cases/{case['case_id']}/history").json())


def test_legacy_migration_preserves_records_without_inventing_provenance(monkeypatch):
    db.init_db()
    with db.get_connection() as conn:
        conn.execute("ALTER TABLE cbr_reference_cases DROP COLUMN data_origin")
        conn.execute("INSERT INTO cbr_reference_cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     ("LEGACY", "MORTGAGE", 1, "UNKNOWN", "[]", "Original", 0, 1, "PENDING", "[]", "2026-09-01"))
    db.init_db()
    with db.get_connection() as conn:
        row = conn.execute("SELECT resolution_playbook, data_origin FROM cbr_reference_cases WHERE reference_id='LEGACY'").fetchone()
        assert tuple(row) == ("Original", "UNKNOWN")
    integration_env(monkeypatch)
    with pytest.raises(ValueError, match="unclassified"):
        with TestClient(app):
            pass


@pytest.mark.parametrize("mode", ["production", "typo", ""])
def test_unknown_profile_fails(monkeypatch, mode):
    monkeypatch.setenv("BCOLLECTION_MODE", mode)
    with pytest.raises(ValueError):
        RuntimeSettings.from_env()


def test_integration_requires_explicit_path(monkeypatch):
    monkeypatch.setenv("BCOLLECTION_MODE", "integration")
    monkeypatch.delenv("BCOLLECTION_DB_PATH")
    with pytest.raises(ValueError, match="explicit"):
        RuntimeSettings.from_env()


def test_demo_rejects_http_clients(monkeypatch):
    monkeypatch.setenv("CORE_BANKING_MODE", "http")
    with pytest.raises(ValueError, match="must be mock"):
        with TestClient(app):
            pass


def test_seed_never_allowed_in_integration(tmp_path):
    path = tmp_path / "integration.sqlite3"
    assert command(path, "seed-demo", mode="integration").returncode != 0
    assert not path.exists()


def test_integration_never_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("BCOLLECTION_MODE", "integration")
    with pytest.raises(ValueError, match="must be http"):
        with TestClient(app):
            pass


def test_integration_blocks_simulations_and_mutations(monkeypatch):
    integration_env(monkeypatch)
    # A startup must not call any backend network endpoint.
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: pytest.fail("Unexpected outbound request"))
    with TestClient(app) as client:
        assert client.get("/api/runtime").json()["integration_read_only"] is True
        assert client.get("/api/cases").json() == []
        for path in ("/api/cases/1/persona", "/api/cases/1/similar-cases"):
            assert client.get(path).status_code == 503
        for path in ("call-intent", "call-wrapup", "balance-check", "call-transcribe"):
            assert client.post(f"/api/cases/1/{path}", json={}).status_code == 503


def test_database_cannot_cross_profiles(monkeypatch):
    assert command(db.DB_FILE_PATH, "seed-demo").returncode == 0
    before = dump_data(db.DB_FILE_PATH)
    integration_env(monkeypatch)
    with pytest.raises(ValueError, match="another runtime profile"):
        with TestClient(app):
            pass
    assert dump_data(db.DB_FILE_PATH) == before


def test_domain_has_one_canonical_definition():
    from bc_domain import CollectionCase
    from bc_domain.models import CollectionCase as CanonicalCase
    assert CollectionCase is CanonicalCase
    assert not (ROOT / "bcollection-platform/libs/bc-domain/models.py").exists()
