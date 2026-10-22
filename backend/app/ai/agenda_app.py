import json
import logging
import os
import time
from datetime import date
from typing import Annotated, Any

import jwt
from fastapi import FastAPI, Header, HTTPException, status
from jwt import PyJWKClient, PyJWTError
from pydantic import BaseModel

from app.ai.agenda import (
    PROMPT_VERSION,
    AgendaParseError,
    ParsedAgenda,
    cost_usd,
    parse_agenda,
    render_agenda_text,
)

logger = logging.getLogger("ai.agenda_app")
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Agenda Parser")

_jwks_client: PyJWKClient | None = None


def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        region = os.environ.get("AWS_REGION", "us-east-1")
        user_pool_id = os.environ.get("COGNITO_USER_POOL_ID", "")
        jwks_url = (
            f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        )
        _jwks_client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
    return _jwks_client


def verify_cognito_access_token(
    auth_header: str | None,
    jwks_client: PyJWKClient | None = None,
    user_pool_id: str | None = None,
    client_id: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token in Authorization header",
        )

    if region is None:
        region = os.environ.get("AWS_REGION", "us-east-1")
    if user_pool_id is None:
        user_pool_id = os.environ.get("COGNITO_USER_POOL_ID", "")
    if client_id is None:
        client_id = os.environ.get("COGNITO_CLIENT_ID", "")

    expected_iss = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"

    if jwks_client is None:
        jwks_client = get_jwks_client()

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=expected_iss,
            options={"verify_aud": False, "verify_iss": True, "verify_exp": True},
        )
    except (PyJWTError, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {exc}",
        ) from exc

    if claims.get("token_use") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token must be a Cognito access token (token_use == 'access')",
        )

    if client_id and claims.get("client_id") != client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token client_id does not match expected client_id",
        )

    return claims


def _tokens(usage: Any, key: str) -> int:
    if isinstance(usage, dict):
        return int(usage.get(key, 0))
    return int(getattr(usage, key, 0))


class ParseRequest(BaseModel):
    text: str
    today: date
    tz: str = "UTC"


class ParseResponse(BaseModel):
    agenda: ParsedAgenda
    rendered_text: str
    model: str
    prompt_version: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/parse", response_model=ParseResponse)
async def parse_endpoint(
    body: ParseRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> ParseResponse:
    # 401 for bad or missing Cognito access token
    claims = verify_cognito_access_token(authorization)

    # 413 if text > 10,000 characters before any model call
    if len(body.text) > 10_000:
        raise HTTPException(
            status_code=413,
            detail="Input text exceeds maximum allowed length of 10,000 characters",
        )

    start_time = time.perf_counter()
    model = os.environ.get("PARSER_MODEL", "")

    try:
        parsed, usage = parse_agenda(
            text=body.text,
            today=body.today,
            tz=body.tz,
        )
    except AgendaParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        error_str = str(exc).lower()
        if (
            "throttling" in error_str
            or "ratelimit" in error_str
            or "too many requests" in error_str
            or "429" in error_str
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Bedrock service throttled the request",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Bedrock service unavailable or failed: {exc}",
        ) from exc

    latency_ms = int((time.perf_counter() - start_time) * 1000)
    cost = cost_usd(model, usage)

    # Log ONE JSON line per parse: event=agenda_parsed (never log the pasted text)
    log_entry = {
        "event": "agenda_parsed",
        "sub": claims.get("sub"),
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "input_tokens": _tokens(usage, "input_tokens"),
        "output_tokens": _tokens(usage, "output_tokens"),
        "latency_ms": latency_ms,
        "cost_usd": cost,
    }
    logger.info(json.dumps(log_entry))

    rendered = render_agenda_text(parsed)
    return ParseResponse(
        agenda=parsed,
        rendered_text=rendered,
        model=model,
        prompt_version=PROMPT_VERSION,
    )
