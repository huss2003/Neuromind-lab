"""NeuroMind API shell (T04): health, request IDs, CORS, structured errors."""
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.errors import ApiError
from app.logging_setup import setup_logging
from app.repository import Repository, get_repository
from app import http
from app.routers import admin, admin_content, admin_ops, checkpoints, content, dashboard, exercises, learner, sessions, teacher, teacher_tools, worker
from app.auth import CurrentUser, current_user, require_roles
from starlette.exceptions import HTTPException as StarletteHTTPException

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

CODES = {400: "INVALID_STATE", 401: "UNAUTHENTICATED", 429: "RATE_LIMITED", 503: "DEPENDENCY_UNAVAILABLE", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT"}

REQUIRED_ENV = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY")
setup_logging()
log = logging.getLogger("neuromind.api")


def missing_config() -> list[str]:
    return [name for name in REQUIRED_ENV if not os.getenv(name)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    if missing_config():  # §17: validate required config at startup (names only, never values)
        log.error("missing required configuration", extra={"ctx": {"missing": missing_config()}})
    yield


app = FastAPI(title="NeuroMind API", version="0.2.0", lifespan=lifespan)

for _r in (content.router, sessions.router, checkpoints.router, exercises.router, teacher.router, dashboard.router, admin.router, admin_ops.router, admin_content.router, learner.router, teacher_tools.router, worker.router):
    app.include_router(_r)

origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = (request.headers.get("x-request-id") or uuid.uuid4().hex)[:64]
    started = time.monotonic()
    calls: list[float] = []
    http.upstream.set(calls)
    response = await call_next(request)
    total = (time.monotonic() - started) * 1000
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Server-Timing"] = f'total;dur={total:.0f}, upstream;dur={sum(calls):.0f};desc="{len(calls)} calls"'
    log.info("request", extra={"ctx": {"request_id": request.state.request_id, "method": request.method,
                                       "path": request.url.path, "status": response.status_code,
                                       "ms": int(total), "upstream_calls": len(calls), "upstream_ms": int(sum(calls))}})
    return response


def _error(request: Request, status: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details or [],
                      "request_id": getattr(request.state, "request_id", "unknown")}}
    return JSONResponse(status_code=status, content=body)


@app.exception_handler(StarletteHTTPException)
async def http_exc(request: Request, exc: StarletteHTTPException):
    if isinstance(exc, ApiError):
        return _error(request, exc.status_code, exc.code, exc.message, exc.details)
    return _error(request, exc.status_code, CODES.get(exc.status_code, "ERROR"), "Request could not be processed")


@app.exception_handler(RequestValidationError)
async def validation_exc(request: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "issue": e["msg"]} for e in exc.errors()]
    return _error(request, 422, "VALIDATION_ERROR", "Request could not be processed", details)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.error("unhandled exception", extra={"ctx": {"request_id": getattr(request.state, "request_id", None),
                                                    "error_type": type(exc).__name__}})
    return _error(request, 500, "INTERNAL_ERROR", "Unexpected error")


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/ready")
async def ready(repo: Repository = Depends(get_repository)) -> JSONResponse:
    """Readiness: reports which checks pass without disclosing any value."""
    config_ok = not missing_config()
    db_ok = config_ok and await repo.ping()
    body = {"status": "ready" if config_ok and db_ok else "degraded", "checks": {"config": config_ok, "database": db_ok}}
    return JSONResponse(status_code=200 if body["status"] == "ready" else 503, content=body)


@app.get("/api/v1/me")
def me(user: CurrentUser = Depends(current_user)) -> dict:
    return {"id": user.id, "role": user.role, "email": user.email, "display_name": user.display_name}


@app.get("/api/v1/teacher/ping")
def teacher_ping(user: CurrentUser = Depends(require_roles("teacher", "admin"))) -> dict:
    return {"ok": True}
