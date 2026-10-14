"""Supabase token verification and role guards (T05).

Identity comes from Supabase Auth (token verified server-side); role comes from the
`profiles` table read with the server-only service-role key. Never from client input.
"""
import hashlib
import os
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request

from app import http
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.services import audit

ROLES = ("learner", "teacher", "admin")


@dataclass(frozen=True)
class CurrentUser:
    id: str
    role: str
    email: str = ""
    display_name: str = ""


AUTH_CACHE_SECONDS = float(os.getenv("AUTH_CACHE_SECONDS", "30"))
_cache: dict[str, tuple[float, CurrentUser]] = {}


class SupabaseVerifier:
    """Token check against Supabase Auth, remembered for a short time per warm instance so one page view does not make
    dozens of identical auth round trips. A signed-out token or a changed role is honoured within AUTH_CACHE_SECONDS."""

    async def verify(self, token: str) -> CurrentUser:
        key = hashlib.sha256(token.encode()).hexdigest()
        hit = _cache.get(key)
        now = time.monotonic()
        if hit and hit[0] > now:
            return hit[1]
        url = os.environ["SUPABASE_URL"].rstrip("/")
        anon = os.environ["SUPABASE_ANON_KEY"]
        service = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        r = await http.request("GET", f"{url}/auth/v1/user", headers={"apikey": anon, "Authorization": f"Bearer {token}"})
        if r.status_code != 200:
            _cache.pop(key, None)
            raise HTTPException(401)
        uid = r.json()["id"]
        p = await http.request("GET", f"{url}/rest/v1/profiles", params={"id": f"eq.{uid}", "select": "role,display_name,deactivated_at"},
                               headers=http.service_headers(service))
        rows = p.json() if p.status_code == 200 else []
        if not rows or rows[0]["role"] not in ROLES:
            raise HTTPException(403)
        if rows[0].get("deactivated_at"):
            _cache.pop(key, None)
            raise ApiError(403, "ACCOUNT_DEACTIVATED", "This account has been deactivated. Contact your course administrator.")
        user = CurrentUser(id=uid, role=rows[0]["role"], email=r.json().get("email", ""), display_name=rows[0].get("display_name") or "")
        if AUTH_CACHE_SECONDS > 0:
            if len(_cache) > 2000:
                _cache.clear()
            _cache[key] = (now + AUTH_CACHE_SECONDS, user)
        return user


def get_verifier() -> SupabaseVerifier:
    return SupabaseVerifier()


async def current_user(request: Request, verifier: SupabaseVerifier = Depends(get_verifier)) -> CurrentUser:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401)
    return await verifier.verify(token)


def require_roles(*allowed: str):
    async def guard(request: Request, user: CurrentUser = Depends(current_user),
                    repo: Repository = Depends(get_repository)) -> CurrentUser:
        if user.role not in allowed:
            await audit.record(repo, request, user.id, "auth.denied", "route", None,
                               {"role": user.role, "path": request.url.path})
            raise HTTPException(403)
        return user

    return guard
