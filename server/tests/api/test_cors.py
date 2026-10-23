"""CORS defaults must not authorize arbitrary credentialed browser origins."""
import httpx
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.main import app


def settings(origins=""):
    return Settings(_env_file=None, SUPABASE_URL="https://example.supabase.co",
                    SUPABASE_SERVICE_KEY="sb_secret_fixture", CORS_ORIGINS=origins)


def test_default_origins_are_local_and_deployments_are_explicit():
    origins = settings().cors_origins_list()
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3001" in origins
    assert not any(origin.startswith("https://") for origin in origins)
    assert "https://dashboard.example.com" in settings(" https://dashboard.example.com ").cors_origins_list()


def test_application_has_no_permissive_origin_regex():
    middleware = next(m for m in app.user_middleware if m.cls is CORSMiddleware)
    assert not middleware.kwargs.get("allow_origin_regex")
    assert "*" not in middleware.kwargs["allow_origins"]


@pytest.mark.anyio
@pytest.mark.parametrize("origin,status", [
    ("http://localhost:3000", 200),
    ("https://dashboard.example.com", 200),
    ("https://untrusted.example.com", 400),
    ("https://flowsync.vercel.app", 400),
])
async def test_credentialed_preflight_requires_an_allowed_origin(origin, status):
    fixture = FastAPI()
    fixture.add_middleware(CORSMiddleware, allow_origins=settings("https://dashboard.example.com").cors_origins_list(),
                           allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=fixture), base_url="http://fixture") as client:
        response = await client.options("/", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
    assert response.status_code == status
    if status == 200:
        assert response.headers["access-control-allow-origin"] == origin
    else:
        assert "access-control-allow-origin" not in response.headers
