"""ADP-02: actual HTTP imports, isolated SQLite, no financial state mutation."""
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

import database as db
from main import app
from legacy_mock import seed, create_app, advance_snapshot
from customer_fixtures import seed_customer360
from customer_ingestion import synchronize
from portfolio_import import import_demo_portfolio
from synthetic.generator import generate_synthetic_delinquent_cases
from test_demo_http_adapters import serve, configure

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sources(tmp_path):
    path = tmp_path / 'source.sqlite3'
    at = datetime.now(timezone.utc).isoformat()
    seed(path, generate_synthetic_delinquent_cases(5, 42, datetime(2026, 9, 1)), {'seed': 42}, at)
    seed_customer360(path)
    with sqlite3.connect(path) as conn:
        cif = conn.execute("SELECT debtor_cif FROM mock_resources WHERE resource='profile' ORDER BY rowid LIMIT 1").fetchone()[0]
    return path, cif


def env(monkeypatch, url):
    configure(monkeypatch, url)
    monkeypatch.setenv('CRM_API_URL', url + '/crm/v1')
    monkeypatch.setenv('DIRECTORY_API_URL', url + '/directory/v1')


def update_source(path, cif, resource, mutate):
    with sqlite3.connect(path) as conn:
        payload = json.loads(conn.execute('SELECT payload FROM mock_resources WHERE debtor_cif=? AND resource=?', (cif, resource)).fetchone()[0])
        mutate(payload)
        conn.execute('UPDATE mock_resources SET payload=? WHERE debtor_cif=? AND resource=?', (json.dumps(payload), cif, resource))


def finance():
    with db.get_connection() as conn:
        return {t: [tuple(r) for r in conn.execute(f'SELECT * FROM {t} ORDER BY 1')]
                for t in ('cases', 'case_exposures', 'ptps', 'payment_ledger', 'case_commands', 'case_transition_log', 'exposure_observations')}


def test_rest_portfolio_bootstrap_customer360_and_restart(monkeypatch, sources):
    path, cif = sources
    with serve(create_app(path)) as url:
        env(monkeypatch, url)
        with TestClient(app) as client:
            assert client.get('/api/cases').json() == []
            imported = import_demo_portfolio()
            assert len(imported['created']) == 5
            assert import_demo_portfolio()['created'] == []
            case = next(c for c in client.get('/api/cases').json() if c['debtor_cif'] == cif)
            from case_service import CaseService
            CaseService().execute(case['case_id'], 'existing-ptp', case['case_version'], 'wrapup',
                                  {'outcome': 'PTP_AGREED', 'ptp_amount': 1000000,
                                   'ptp_date': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()})
            baseline = finance()
            result = client.post(f"/api/cases/{case['case_id']}/sync-customer")
            assert result.status_code == 200, result.text
            assert set(result.json()['resources'].values()) <= {'RECORDED', 'EMPTY'}
            assert finance() == baseline
            workspace = client.get(f"/api/cases/{case['case_id']}/workspace").json()
            assert workspace['customer_profile']['party_type'] == 'ORGANIZATION'
            assert workspace['customer_profile']['rm_name'] == 'RM mô phỏng'
            assert workspace['assigned_collector'] is None
            assert len(workspace['source_data']['loans']['snapshot']['items']) == 2
            assert len(workspace['case_scope']['exposures']) == 1
            assert workspace['customer_scope']['complete_core_portfolio'] is False
            assert all(p['max_dpd'] is not None for p in workspace['dpd_history']['case']['points'])
            assert workspace['dpd_history']['case']['definition'].startswith('SOURCE_')
            assert client.get('/api/customer-search', params={'q': 'DEMO-TAX-' + cif}).json()['items'][0]['case_id'] == case['case_id']
            replay = client.post(f"/api/cases/{case['case_id']}/sync-customer").json()
            assert set(replay['resources'].values()) == {'UNCHANGED'}
            assert finance() == baseline
        with TestClient(app) as client:
            restarted = client.get(f"/api/cases/{case['case_id']}/workspace").json()
            assert restarted['source_data']['profile']['snapshot'] == workspace['source_data']['profile']['snapshot']
            assert finance() == baseline


@pytest.mark.parametrize('change,expected', [
    (lambda p: p.update(debtor_cif='WRONG'), 'INVALID_CONTRACT'),
    (lambda p: p['items'][0].update(debtor_cif='WRONG'), 'INVALID_CONTRACT'),
    (lambda p: p.update(data_origin='EXTERNAL'), 'INVALID_CONTRACT'),
    (lambda p: p['items'][0].update(legal_name='changed-without-version'), 'VERSION_CONFLICT'),
    (lambda p: p.update(source_system='DIFFERENT'), 'SOURCE_CONFLICT'),
    (lambda p: p.update(as_of=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat()), 'INVALID_CONTRACT'),
])
def test_bad_source_keeps_last_valid_snapshot(monkeypatch, sources, change, expected):
    path, cif = sources
    with serve(create_app(path)) as url:
        env(monkeypatch, url)
        with TestClient(app):
            synchronize(cif)
            with db.get_connection() as conn:
                previous = tuple(conn.execute("SELECT * FROM customer_source_snapshots WHERE debtor_cif=? AND resource='profile'", (cif,)).fetchone())
            update_source(path, cif, 'profile', change)
            assert synchronize(cif)['resources']['profile'] == expected
            with db.get_connection() as conn:
                assert tuple(conn.execute("SELECT * FROM customer_source_snapshots WHERE debtor_cif=? AND resource='profile'", (cif,)).fetchone()) == previous


def test_newer_old_order_and_empty_are_distinct(monkeypatch, sources):
    path, cif = sources
    with serve(create_app(path)) as url:
        env(monkeypatch, url)
        with TestClient(app):
            synchronize(cif)
            update_source(path, cif, 'collateral', lambda p: p.update(source_version=2, items=[]))
            assert synchronize(cif)['resources']['collateral'] == 'EMPTY'
            update_source(path, cif, 'collateral', lambda p: p.update(source_version=1))
            assert synchronize(cif)['resources']['collateral'] == 'OUT_OF_ORDER'


def test_missing_source_does_not_remove_cached_data(monkeypatch, sources):
    path, cif = sources
    with serve(create_app(path)) as url:
        env(monkeypatch, url)
        with TestClient(app):
            synchronize(cif)
            with sqlite3.connect(path) as conn:
                conn.execute("DELETE FROM mock_resources WHERE debtor_cif=? AND resource='profile'", (cif,))
            assert synchronize(cif)['resources']['profile'] == 'NOT_FOUND'
            from customer_ingestion import read_sources
            with db.get_connection() as conn:
                source = read_sources(conn, cif, datetime.now(timezone.utc))['profile']
                assert source['status'] == 'NOT_FOUND' and source['snapshot']
                assert read_sources(conn, cif, datetime.now(timezone.utc) + timedelta(days=2))['loans']['status'] == 'STALE'


def test_history_does_not_fill_missing_months(monkeypatch, sources):
    path, cif = sources
    with serve(create_app(path)) as url:
        env(monkeypatch, url)
        with TestClient(app) as client:
            import_demo_portfolio()
            case = next(c for c in client.get('/api/cases').json() if c['debtor_cif'] == cif)
            update_source(path, cif, 'history', lambda p: p.update(items=[]))
            synchronize(cif)
            w = client.get(f"/api/cases/{case['case_id']}/workspace").json()
            assert all(p['max_dpd'] is None for p in w['dpd_history']['case']['points'])


def test_cli_bootstrap_and_sync(monkeypatch, sources):
    path, cif = sources
    with serve(create_app(path)) as url:
        env(monkeypatch, url)
        for tail in (['import-demo-portfolio'], ['sync-customer', '--cif', cif]):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/bcollection.py'), '--mode', 'demo-http',
                                     '--database', db.DB_FILE_PATH, *tail], capture_output=True, text=True, timeout=15)
            assert result.returncode == 0, result.stderr


def test_ingestion_gate_without_http():
    with TestClient(app) as client:
        assert client.post('/api/cases/unknown/sync-customer').status_code == 503
        with pytest.raises(ValueError):
            synchronize('D1')
        with pytest.raises(ValueError):
            import_demo_portfolio()
