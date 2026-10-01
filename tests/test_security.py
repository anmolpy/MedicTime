"""No model downloads, provider calls, or real patient data in these regressions."""
import asyncio
import importlib
import io
import sys
import types
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from starlette.datastructures import UploadFile, Headers

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Stub only expensive integrations; exercise the real ASGI app and upload helper.
for name in ['audio', 'llm']:
    module = types.ModuleType('backend.app.' + name)
    for fn in ['transcribe_file', 'transcribe_segments', 'receptionist_response', 'generate_soap_note']:
        setattr(module, fn, lambda *args: 'synthetic response')
    sys.modules[module.__name__] = module
main = importlib.import_module('backend.app.main')
from backend.app.security import DemoGuard


def run(coro):
    return asyncio.run(coro)


def test_failed_oversized_upload_is_removed_and_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'settings', types.SimpleNamespace(max_upload_mb=0))
    monkeypatch.setattr(main.tempfile, 'tempdir', str(tmp_path))
    upload = UploadFile(io.BytesIO(b'audio'), filename='voice.wav', headers=Headers({'content-type': 'audio/wav'}))
    with pytest.raises(main.HTTPException) as error:
        run(main.save_upload(upload))
    assert error.value.status_code == 413
    assert list(tmp_path.iterdir()) == []
    assert upload.file.closed


def test_read_failure_also_removes_partial_upload(tmp_path, monkeypatch):
    monkeypatch.setattr(main.tempfile, 'tempdir', str(tmp_path))
    upload = UploadFile(io.BytesIO(b'audio'), filename='voice.wav')
    async def fail(*args):
        raise OSError('synthetic read error')
    upload.read = fail
    with pytest.raises(OSError):
        run(main.save_upload(upload))
    assert not list(tmp_path.iterdir())
    assert upload.file.closed


def test_static_route_does_not_expose_project_files():
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
            for path in ['/static/.env', '/static/main.py', '/.env', '/backend/app/config.py']:
                assert (await client.get(path)).status_code == 404
            assert (await client.get('/')).status_code == 200
            assert (await client.get('/config.js')).status_code == 200
    run(check())


def test_errors_do_not_echo_sensitive_exception_details():
    response = main.internal_error('test', RuntimeError('synthetic-secret-patient-text'))
    assert response.status_code == 500
    assert b'synthetic-secret' not in response.body
    assert b'traceback' not in response.body
    assert b'error_id' in response.body


def test_quota_counts_same_peer_and_has_global_budget(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.delenv('UPSTASH_REDIS_REST_URL', raising=False)
    monkeypatch.delenv('UPSTASH_REDIS_REST_TOKEN', raising=False)
    async def check():
        guard = DemoGuard(None)
        for _ in range(6): assert await guard.allowed('same-peer')
        assert not await guard.allowed('same-peer')
        for i in range(94): assert await guard.allowed(f'peer-{i}')
        assert not await guard.allowed('new-peer')
    run(check())


def test_production_requires_shared_quota_storage(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.delenv('UPSTASH_REDIS_REST_URL', raising=False)
    monkeypatch.delenv('UPSTASH_REDIS_REST_TOKEN', raising=False)
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=DemoGuard(main.app)), base_url='http://test') as client:
            response = await client.post('/api/agent-chat', data={'message': 'test'})
            assert response.status_code == 503
    run(check())


def test_chunked_request_size_enforced_before_downstream(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.delenv('UPSTASH_REDIS_REST_URL', raising=False)
    monkeypatch.delenv('UPSTASH_REDIS_REST_TOKEN', raising=False)
    async def check():
        called = False
        async def downstream(*args):
            nonlocal called
            called = True
        sent = []
        async def receive(): return {'type': 'http.request', 'body': b'x' * (17 * 1024 * 1024), 'more_body': False}
        async def send(message): sent.append(message)
        await DemoGuard(downstream)({'type': 'http', 'method': 'POST', 'path': '/api/voice-chat', 'client': ('peer', 1)}, receive, send)
        assert not called
        assert sent[0]['status'] == 413
    run(check())
