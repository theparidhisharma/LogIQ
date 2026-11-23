import os
import time

import pytest
from fastapi import HTTPException

from shared import security


def test_password_hash_is_salted_and_verifies():
    one = security.hash_password('correct horse battery staple')
    two = security.hash_password('correct horse battery staple')
    assert one != two
    assert security.verify_password('correct horse battery staple', one)
    assert not security.verify_password('wrong password', one)


def test_password_policy_requires_twelve_characters():
    with pytest.raises(ValueError):
        security.hash_password('short')


def test_jwt_round_trip_and_tamper_detection(monkeypatch):
    monkeypatch.setattr(security, 'JWT_SECRET', 'unit-test-secret')
    token, ttl = security.issue_access_token(user_id='u1', tenant_id='t1', role='admin', email='a@example.com')
    claims = security.decode_access_token(token)
    assert claims['sub'] == 'u1' and claims['tenant_id'] == 't1'
    assert ttl > 0
    with pytest.raises(HTTPException) as error:
        security.decode_access_token(token[:-1] + ('A' if token[-1] != 'A' else 'B'))
    assert error.value.status_code == 401


def test_expired_jwt_is_rejected(monkeypatch):
    monkeypatch.setattr(security, 'JWT_SECRET', 'unit-test-secret')
    monkeypatch.setattr(security, 'JWT_TTL_SECONDS', -1)
    token, _ = security.issue_access_token(user_id='u1', tenant_id='t1', role='member', email='a@example.com')
    with pytest.raises(HTTPException):
        security.decode_access_token(token)


def test_api_key_material_is_not_plaintext(monkeypatch):
    monkeypatch.setenv('LOGIQ_API_KEY_PEPPER', 'pepper')
    raw, digest = security.create_api_key_material()
    assert raw.startswith('lgq_')
    assert raw not in digest and len(digest) == 64


def test_api_key_auth_derives_tenant_from_database(monkeypatch):
    import contextlib
    import hashlib
    import sys
    import types
    from starlette.requests import Request

    raw = 'lgq_example-secret-value'
    monkeypatch.setenv('LOGIQ_API_KEY_PEPPER', 'test-pepper')
    digest = hashlib.sha256(('test-pepper' + raw).encode()).hexdigest()

    class Result:
        def mappings(self):
            return self
        def first(self):
            return {'id': 'key-1', 'tenant_id': 'tenant-9', 'application_id': 'app-3', 'scopes': ['ingest']}

    class Connection:
        def execute(self, *_args, **_kwargs):
            return Result()

    @contextlib.contextmanager
    def connect():
        yield Connection()

    fake_common = types.ModuleType('shared.common')
    fake_common.db = lambda: types.SimpleNamespace(connect=connect)
    fake_common.identity_db = fake_common.db
    monkeypatch.setitem(sys.modules, 'shared.common', fake_common)
    request = Request({'type': 'http', 'method': 'POST', 'path': '/v1/logs', 'headers': [(b'x-api-key', raw.encode())], 'query_string': b'', 'server': ('test', 80), 'client': ('test', 1), 'scheme': 'http'})
    context = security.authenticate_api_key(request)
    assert context['tenant_id'] == 'tenant-9'
    assert request.state.tenant_id == 'tenant-9'
    assert request.state.application_id == 'app-3'


def test_api_key_without_ingest_scope_is_forbidden(monkeypatch):
    import contextlib
    import sys
    import types
    from starlette.requests import Request

    class Result:
        def mappings(self):
            return self
        def first(self):
            return {'id': 'key-1', 'tenant_id': 'tenant-9', 'application_id': None, 'scopes': ['read']}

    class Connection:
        def execute(self, *_args, **_kwargs):
            return Result()

    @contextlib.contextmanager
    def connect():
        yield Connection()

    fake_common = types.ModuleType('shared.common')
    fake_common.db = lambda: types.SimpleNamespace(connect=connect)
    fake_common.identity_db = fake_common.db
    monkeypatch.setitem(sys.modules, 'shared.common', fake_common)
    monkeypatch.setenv('LOGIQ_API_KEY_PEPPER', '')
    raw = 'lgq_wrong-scope-key'
    request = Request({'type': 'http', 'method': 'POST', 'path': '/v1/logs', 'headers': [(b'x-api-key', raw.encode())], 'query_string': b'', 'server': ('test', 80), 'client': ('test', 1), 'scheme': 'http'})
    with pytest.raises(HTTPException) as error:
        security.authenticate_api_key(request)
    assert error.value.status_code == 403
