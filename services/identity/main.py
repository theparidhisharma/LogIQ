"""Tenant, user-session, application and API-key management service."""
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text

from shared.common import identity_db as db, make_app
from shared.security import (create_api_key_material, current_user, hash_password,
                             issue_access_token, require_roles, verify_password)

app = make_app('identity', database='identity')



class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=12, max_length=256)
    tenant_name: str = Field(min_length=2, max_length=120)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if len(value) > 254 or '@' not in value or value.startswith('@') or value.endswith('@'):
            raise ValueError('A valid email address is required')
        return value


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if len(value) > 254 or '@' not in value or value.startswith('@') or value.endswith('@'):
            raise ValueError('A valid email address is required')
        return value


class KeyRequest(BaseModel):
    label: str = Field(default='ingestion key', min_length=1, max_length=120)
    application_id: str | None = None
    expires_at: datetime | None = None


class ApplicationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    environment: str = Field(default='development', max_length=40)


@app.post('/v1/auth/register', status_code=201)
def register(body: RegisterRequest):
    user_id, tenant_id = str(uuid.uuid4()), str(uuid.uuid4())
    try:
        password_hash = hash_password(body.password)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with db().begin() as conn:
        try:
            conn.execute(text('INSERT INTO tenants(id,name) VALUES(:id,:name)'),
                         {'id': tenant_id, 'name': body.tenant_name})
            conn.execute(text("""INSERT INTO users(id,email,password_hash,tenant_id,role)
                VALUES(:id,:email,:password,:tenant,'admin')"""),
                {'id': user_id, 'email': body.email.lower(), 'password': password_hash, 'tenant': tenant_id})
        except Exception as exc:
            if 'unique' in str(exc).lower() or 'duplicate' in str(exc).lower():
                raise HTTPException(409, 'An account with this email already exists') from exc
            raise
    token, ttl = issue_access_token(user_id=user_id, tenant_id=tenant_id, role='admin', email=body.email.lower())
    return {'access_token': token, 'token_type': 'bearer', 'expires_in': ttl,
            'user': {'id': user_id, 'email': body.email.lower(), 'tenant_id': tenant_id, 'role': 'admin'}}


@app.post('/v1/auth/login')
def login(body: LoginRequest):
    with db().connect() as conn:
        row = conn.execute(text("""SELECT id,email,password_hash,tenant_id,role,is_active
            FROM users WHERE email=:email"""), {'email': body.email.lower()}).mappings().first()
    if not row or not row['is_active'] or not verify_password(body.password, row['password_hash']):
        raise HTTPException(401, 'Invalid email or password')
    token, ttl = issue_access_token(user_id=row['id'], tenant_id=row['tenant_id'], role=row['role'], email=row['email'])
    return {'access_token': token, 'token_type': 'bearer', 'expires_in': ttl,
            'user': {'id': row['id'], 'email': row['email'], 'tenant_id': row['tenant_id'], 'role': row['role']}}


@app.get('/v1/auth/me')
def me(user=Depends(current_user)):
    return {'id': user['id'], 'email': user['email'], 'tenant_id': user['tenant_id'], 'role': user['role']}


class MemberRequest(BaseModel):
    email: str
    password: str = Field(min_length=12, max_length=256)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if len(value) > 254 or '@' not in value or value.startswith('@') or value.endswith('@'):
            raise ValueError('A valid email address is required')
        return value


@app.post('/v1/users', status_code=201)
def create_member(body: MemberRequest, user=Depends(require_roles('admin'))):
    user_id = str(uuid.uuid4())
    try:
        encoded = hash_password(body.password)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with db().begin() as conn:
        try:
            conn.execute(text("""INSERT INTO users(id,email,password_hash,tenant_id,role)
                VALUES(:id,:email,:password,:tenant,'member')"""),
                {'id': user_id, 'email': body.email, 'password': encoded, 'tenant': user['tenant_id']})
        except Exception as exc:
            if 'unique' in str(exc).lower() or 'duplicate' in str(exc).lower():
                raise HTTPException(409, 'An account with this email already exists') from exc
            raise
    return {'id': user_id, 'email': body.email, 'tenant_id': user['tenant_id'], 'role': 'member'}


@app.post('/v1/applications', status_code=201)
def create_application(body: ApplicationRequest, user=Depends(require_roles('admin'))):
    app_id = str(uuid.uuid4())
    with db().begin() as conn:
        try:
            conn.execute(text("""INSERT INTO applications(id,tenant_id,name,environment)
                VALUES(:id,:tenant,:name,:environment)"""),
                {'id': app_id, 'tenant': user['tenant_id'], 'name': body.name, 'environment': body.environment})
        except Exception as exc:
            if 'unique' in str(exc).lower() or 'duplicate' in str(exc).lower():
                raise HTTPException(409, 'Application name already exists in this tenant') from exc
            raise
    return {'id': app_id, 'name': body.name, 'environment': body.environment}


@app.get('/v1/applications')
def list_applications(user=Depends(current_user)):
    with db().connect() as conn:
        rows = conn.execute(text("""SELECT id,name,environment,created_at FROM applications
            WHERE tenant_id=:tenant ORDER BY created_at DESC"""), {'tenant': user['tenant_id']}).mappings().all()
    return {'items': [dict(row) for row in rows]}


@app.post('/v1/api-keys', status_code=201)
def create_key(body: KeyRequest, user=Depends(require_roles('admin'))):
    if body.application_id:
        with db().connect() as conn:
            exists = conn.execute(text('SELECT 1 FROM applications WHERE id=:id AND tenant_id=:tenant'),
                                  {'id': body.application_id, 'tenant': user['tenant_id']}).scalar()
        if not exists:
            raise HTTPException(404, 'Application not found in this tenant')
    raw, digest = create_api_key_material()
    key_id = str(uuid.uuid4())
    with db().begin() as conn:
        conn.execute(text("""INSERT INTO api_keys(id,key_hash,tenant_id,application_id,label,expires_at)
            VALUES(:id,:hash,:tenant,:application,:label,:expires)"""),
            {'id': key_id, 'hash': digest, 'tenant': user['tenant_id'],
             'application': body.application_id, 'label': body.label, 'expires': body.expires_at})
    return {'id': key_id, 'api_key': raw, 'label': body.label, 'application_id': body.application_id,
            'warning': 'Copy this key now. The secret is stored only as a hash and cannot be retrieved again.'}


@app.get('/v1/api-keys')
def list_keys(user=Depends(require_roles('admin'))):
    with db().connect() as conn:
        rows = conn.execute(text("""SELECT id,label,application_id,created_at,expires_at,revoked_at
            FROM api_keys WHERE tenant_id=:tenant ORDER BY created_at DESC"""),
            {'tenant': user['tenant_id']}).mappings().all()
    return {'items': [dict(row) for row in rows]}


@app.delete('/v1/api-keys/{key_id}')
def revoke_key(key_id: str, user=Depends(require_roles('admin'))):
    with db().begin() as conn:
        result = conn.execute(text("""UPDATE api_keys SET revoked_at=now()
            WHERE id=:id AND tenant_id=:tenant AND revoked_at IS NULL"""),
            {'id': key_id, 'tenant': user['tenant_id']})
    if result.rowcount == 0:
        raise HTTPException(404, 'Active API key not found')
    return {'id': key_id, 'revoked': True}


@app.get('/v1/identity/status')
def status():
    return {'status': 'development', 'authentication': ['JWT bearer sessions', 'hashed, revocable ingestion API keys'],
            'authorization': 'tenant-scoped admin/member roles'}
