"""Supabase Auth administration (create, ban, list users). Server-side only: needs the service-role/secret key.
Kept behind a small protocol so routers can be tested without the network."""
import os
from typing import Any, Protocol

from app import http

Row = dict[str, Any]


class AuthAdmin(Protocol):
    async def list_users(self, max_users: int = 1000) -> list[Row]: ...
    async def create_user(self, email: str, password: str, display_name: str) -> Row | None: ...
    async def set_banned(self, user_id: str, banned: bool) -> bool: ...


class SupabaseAuthAdmin:
    def __init__(self) -> None:
        self.url = os.environ["SUPABASE_URL"].rstrip("/") + "/auth/v1/admin"
        self.headers = http.service_headers(os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    async def list_users(self, max_users: int = 1000) -> list[Row]:
        out: list[Row] = []
        page = 1
        while len(out) < max_users:
            r = await http.request("GET", f"{self.url}/users", params={"page": str(page), "per_page": "200"}, headers=self.headers)
            r.raise_for_status()
            batch = r.json().get("users", [])
            out += [{"id": u["id"], "email": u.get("email", ""), "last_sign_in_at": u.get("last_sign_in_at"),
                     "created_at": u.get("created_at"), "banned_until": u.get("banned_until"),
                     "email_confirmed": bool(u.get("email_confirmed_at"))} for u in batch]
            if len(batch) < 200:
                break
            page += 1
        return out[:max_users]

    async def create_user(self, email: str, password: str, display_name: str) -> Row | None:
        r = await http.request("POST", f"{self.url}/users", headers=self.headers, json={
            "email": email, "password": password, "email_confirm": True, "user_metadata": {"display_name": display_name}})
        if r.status_code in (409, 422):
            return None  # already registered (or rejected, e.g. weak password): the caller reports a generic message
        r.raise_for_status()
        return {"id": r.json()["id"], "email": email}

    async def set_banned(self, user_id: str, banned: bool) -> bool:
        r = await http.request("PUT", f"{self.url}/users/{user_id}", headers=self.headers,
                               json={"ban_duration": "876000h" if banned else "none"})
        return r.status_code < 300


def get_auth_admin() -> AuthAdmin:
    return SupabaseAuthAdmin()
