"""Supabase token verification and role guards (T05).

Identity comes from Supabase Auth (token verified server-side); role comes from the
`profiles` table read with the server-only service-role key. Never from client input.
"""
import os
from dataclasses import dataclass

import httpx
from fastapi import Depends, HTTPException, Request

from app.repository import Repository, get_repository
from app.services import audit

ROLES = ("learner", "teacher", "admin")


@dataclass(frozen=True)
class CurrentUser:
    id: str
    role: str
    email: str = ""
    display_name: str = ""


class SupabaseVerifier:
    async def verify(self, token: str) -> CurrentUser:
        url = os.environ["SUPABASE_URL"].rstrip("/")
        anon = os.environ["SUPABASE_ANON_KEY"]
        service = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{url}/auth/v1/user", headers={"apikey": anon, "Authorization": f"Bearer {token}"})
            if r.status_code != 200:
                raise HTTPException(401)
            uid = r.json()["id"]
            p = await c.get(
                f"{url}/rest/v1/profiles", params={"id": f"eq.{uid}", "select": "role,display_name"},
                headers={"apikey": service, "Authorization": f"Bearer {service}"},
            )
            rows = p.json() if p.status_code == 200 else []
            if not rows or rows[0]["role"] not in ROLES:
                raise HTTPException(403)
            return CurrentUser(id=uid, role=rows[0]["role"], email=r.json().get("email", ""),
                               display_name=rows[0].get("display_name") or "")


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
