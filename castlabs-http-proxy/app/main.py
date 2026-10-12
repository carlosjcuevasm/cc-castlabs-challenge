
import os
from contextlib import asynccontextmanager
import time
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

from app.jwt_utils import create_jwt

from pydantic import BaseModel, ConfigDict

class ProxyRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    username: str

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    secret_hex = os.getenv("JWT_SECRET_HEX")
    upstream_url = os.getenv("UPSTREAM_URL")

    if not secret_hex or not upstream_url:
        raise RuntimeError(
            "JWT_SECRET_HEX and UPSTREAM_URL must be configured"
        )

    try:
        bytes.fromhex(secret_hex)
    except ValueError as exc:
        raise RuntimeError(
            "JWT_SECRET_HEX must be a valid hexadecimal string"
        ) from exc

    async with httpx.AsyncClient() as client:
        app.state.http_client = client
        app.state.jwt_secret_hex = secret_hex
        app.state.upstream_url = upstream_url
        app.state.start_time = time.monotonic()
        app.state.request_count = 0
        yield


app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def count_proxy_requests(request: Request, call_next):
    if request.url.path == "/proxy":
        app.state.request_count += 1

    return await call_next(request)


@app.get("/status")
async def status():
    return {
        "uptime_seconds": round(
            time.monotonic() - app.state.start_time, 2
        ),
        "request_count": app.state.request_count,
    }

@app.post("/proxy")
async def proxy(body: ProxyRequest, request: Request):
    username = body.username

    if not username.strip():
        raise HTTPException(
            status_code=422,
            detail="username must be a non-empty string",
        )

    token = create_jwt(username, app.state.jwt_secret_hex)

    try:
        upstream_response = await app.state.http_client.post(
            app.state.upstream_url,
            content=await request.body(),
            headers={
                "content-type": "application/json",
                "x-my-jwt": token,
            },
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach upstream endpoint",
        ) from exc

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        media_type=upstream_response.headers.get("content-type"),
    )
