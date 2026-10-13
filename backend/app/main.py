"""NeuroMind API shell (T04): health, request IDs, CORS, structured errors."""
import os
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routers.content import router as content_router
from app.auth import CurrentUser, current_user, require_roles
from starlette.exceptions import HTTPException as StarletteHTTPException

CODES = {400: "INVALID_STATE", 401: "UNAUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT"}

app = FastAPI(title="NeuroMind API", version="0.1.0")

app.include_router(content_router)

origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


def _error(request: Request, status: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details or [],
                      "request_id": getattr(request.state, "request_id", "unknown")}}
    return JSONResponse(status_code=status, content=body)


@app.exception_handler(StarletteHTTPException)
async def http_exc(request: Request, exc: StarletteHTTPException):
    return _error(request, exc.status_code, CODES.get(exc.status_code, "ERROR"), "Request could not be processed")


@app.exception_handler(RequestValidationError)
async def validation_exc(request: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "issue": e["msg"]} for e in exc.errors()]
    return _error(request, 422, "VALIDATION_ERROR", "Request could not be processed", details)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    return _error(request, 500, "INTERNAL_ERROR", "Unexpected error")


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/me")
def me(user: CurrentUser = Depends(current_user)) -> dict:
    return {"id": user.id, "role": user.role}


@app.get("/api/v1/teacher/ping")
def teacher_ping(user: CurrentUser = Depends(require_roles("teacher", "admin"))) -> dict:
    return {"ok": True}
