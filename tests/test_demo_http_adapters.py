"""ADP-01 tests use actual loopback HTTP, not monkeypatched adapter responses."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading
import time

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response, RedirectResponse
from fastapi.testclient import TestClient

import database as db
from main import app
from bc_runtime.settings import RuntimeSettings
from core_banking.http_client import HttpCoreBankingApiClient
from core_banking.adapter import CoreBankingAdapter
from legacy_mock import create_app, seed, advance_snapshot, initialize
from rest_transport import RestTransport, AdapterError, required_list
from synthetic.generator import generate_synthetic_delinquent_cases

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def serve(application):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(application, log_level="error", lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.01)
        assert server.started, "Mock REST did not start"
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
        assert not thread.is_alive(), "Mock server failed to stop"


def configure(monkeypatch, url):
    monkeypatch.setenv("BCOLLECTION_MODE", "demo-http")
    for name, env, suffix in (("CORE_BANKING", "CORE_BANKING_API_URL", "core"),
                              ("LOS", "LOS_API_URL", "los"), ("CIC", "CIC_GATEWAY_URL", "cic")):
        monkeypatch.setenv(f"{name}_MODE", "http")
        monkeypatch.setenv(env, f"{url}/{suffix}/v1")


@pytest.fixture
def scenario(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    rows = generate_synthetic_delinquent_cases(500, 42, datetime(2026, 9, 1, 9))
    at = datetime.now(timezone.utc).isoformat()
    seed(path, rows, {"seed": 42}, at)
    return path, rows, at


def test_http_balance_roundtrip_and_no_reverse_hydration(monkeypatch, scenario):
    path, rows, at = scenario
    with serve(create_app(path)) as url:
        configure(monkeypatch, url)
        RuntimeSettings.from_env().validate_adapters()
        # Seed B.Collection independently with identical scenario identity/amounts.
        result = subprocess.run([sys.executable, str(ROOT / "scripts/bcollection.py"),
            "--mode", "demo-http", "--database", db.DB_FILE_PATH, "seed-demo"],
            capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        with TestClient(app) as client:
            runtime = client.get("/api/runtime").json()
            assert runtime["simulation"] and runtime["adapter_transport"] == "http"
            assert not runtime["production_ready"]
            case = next(c for c in client.get("/api/cases").json() if c["loan_id"] == rows[0]["loan_id"])
            payload = {"command_id": "http-check-1", "expected_version": case["case_version"]}
            response = client.post(f"/api/cases/{case['case_id']}/balance-check", json=payload)
            assert response.status_code == 200, response.text
            workspace = client.get(f"/api/cases/{case['case_id']}/workspace").json()
            assert workspace["case"]["overdue_amount"] == rows[0]["overdue_amount"]
            assert client.post(f"/api/cases/{case['case_id']}/balance-check", json=payload).json()["replayed"]
            readiness = client.get("/api/integrations/readiness").json()
            assert readiness["status"] == "DEGRADED"
            assert readiness["sources"]["core"]["status"] == "READY"
            assert readiness["sources"]["los"]["status"] == "NOT_IMPLEMENTED"
            for action in ("call-intent", "call-wrapup", "call-transcribe"):
                assert client.post(f"/api/cases/{case['case_id']}/{action}", json={}).status_code == 503
            assert client.get(f"/api/cases/{case['case_id']}/persona").status_code == 503
        # Restart B.Collection must not rewrite source data or require set_mock_loan.
        with TestClient(app):
            source = HttpCoreBankingApiClient().fetch_loan_balance(rows[0]["loan_id"])["data"]
            assert source["source_version"] == 1 and source["as_of"] == at


def test_mock_persistence_filter_missing_and_no_get_mutation(monkeypatch, scenario):
    path, rows, at = scenario
    for _ in range(2):
        with serve(create_app(path)) as url:
            configure(monkeypatch, url)
            client = HttpCoreBankingApiClient()
            assert client.fetch_loan_balance(rows[0]["loan_id"]) == client.fetch_loan_balance(rows[0]["loan_id"])
            assert all(0 < r["dpd"] <= 5 for r in client.fetch_overdue_portfolio(5))
            assert client.fetch_recent_payments(rows[0]["loan_id"]) == []
            with pytest.raises(AdapterError) as error:
                client.fetch_loan_balance("missing")
            assert error.value.status == 404
            with pytest.raises(AdapterError) as error:
                client.fetch_customer_inflows(rows[0]["debtor_cif"])
            assert error.value.status == 501
    advance_snapshot(path, (datetime.fromisoformat(at) + timedelta(seconds=1)).isoformat())
    seed(path, rows, {"seed": 42}, at)
    with TestClient(create_app(path)) as client:
        assert client.get(f"/core/v1/loans/{rows[0]['loan_id']}/balance").json()["data"]["source_version"] == 2
    with pytest.raises(ValueError, match="differs"):
        seed(path, rows, {"seed": 43}, at)


@pytest.mark.parametrize("url", ["https://example.com/core", "http://localhost:8099/core", "http://127.0.0.1.evil/core", "http://user:pass@127.0.0.1/core", "http://127.0.0.1/core?secret=x"])
def test_demo_http_rejects_non_loopback_or_ambiguous_urls(monkeypatch, url):
    configure(monkeypatch, "http://127.0.0.1:8099")
    monkeypatch.setenv("CORE_BANKING_API_URL", url)
    with pytest.raises(ValueError):
        RuntimeSettings.from_env().validate_adapters()
    with pytest.raises(ValueError):
        HttpCoreBankingApiClient()


def test_transport_errors_no_redirects_or_silent_empty(monkeypatch):
    fixture = FastAPI()

    @fixture.get("/{kind}")
    def respond(kind):
        if kind == "redirect":
            return RedirectResponse("http://example.invalid/private")
        if kind == "unlabelled":
            return {"loans": []}
        return Response("not-json" if kind == "invalid" else '{}',
                        status_code=503 if kind == "unavailable" else 200,
                        headers={"X-Data-Origin": "SYNTHETIC"})

    with serve(fixture) as url:
        configure(monkeypatch, url)
        transport = RestTransport(url, api_key="production-key-must-not-leak")
        assert transport.api_key == ""
        for kind, code in (("invalid", "INVALID_JSON"), ("unlabelled", "UNTRUSTED_DEMO_SOURCE"),
                           ("redirect", "HTTP_ERROR"), ("unavailable", "HTTP_ERROR")):
            with pytest.raises(AdapterError) as error:
                transport.get(kind)
            assert error.value.code == code
            assert error.value.retryable == (kind == "unavailable")
        with pytest.raises(AdapterError, match="INVALID_CONTRACT"):
            required_list(transport.get("empty"), "loans")


def test_mock_refuses_collection_database():
    db.init_db()
    with pytest.raises(ValueError, match="non-mock"):
        initialize(db.DB_FILE_PATH)


def test_collection_refuses_mock_database_without_mutation(monkeypatch, scenario):
    path, _, _ = scenario
    before = path.read_bytes()
    monkeypatch.setattr(db, "DB_FILE_PATH", str(path))
    with pytest.raises(ValueError, match="legacy mock"):
        db.init_db()
    assert path.read_bytes() == before


@pytest.mark.parametrize("field,value", [("outstanding_principal", 1.5), ("overdue_amount", -1),
                                         ("source_version", True), ("as_of", "2026-09-07T12:00:00"),
                                         ("debtor_cif", ""), ("loan_id", "WRONG")])
def test_http_core_rejects_invalid_contract(monkeypatch, scenario, field, value):
    path, rows, _ = scenario
    with sqlite3.connect(path) as conn:
        data = json.loads(conn.execute("SELECT payload FROM mock_loans WHERE loan_id=?", (rows[0]["loan_id"],)).fetchone()[0])
        data[field] = value
        conn.execute("UPDATE mock_loans SET payload=? WHERE loan_id=?", (json.dumps(data), rows[0]["loan_id"]))
    with serve(create_app(path)) as url:
        configure(monkeypatch, url)
        with pytest.raises(AdapterError, match="INVALID_CONTRACT"):
            HttpCoreBankingApiClient().fetch_loan_balance(rows[0]["loan_id"])


def test_cli_seed_idempotency_and_observe(tmp_path):
    path = tmp_path / "cli-mock.sqlite3"
    command = [sys.executable, str(ROOT / "scripts/legacy_mock.py"), "--database", str(path)]
    for _ in range(2):
        result = subprocess.run([*command, "seed"], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
    result = subprocess.run([*command, "observe"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM mock_loans").fetchone()[0] == 500
        assert json.loads(conn.execute("SELECT payload FROM mock_loans LIMIT 1").fetchone()[0])["source_version"] == 2
