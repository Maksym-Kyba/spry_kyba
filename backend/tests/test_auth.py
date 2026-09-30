import time

from httpx import AsyncClient

from tests.conftest import make_token
from tests.test_api import meeting_payload


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


BOB = bearer(make_token("bob"))


async def test_health_needs_no_token(client: AsyncClient) -> None:
    response = await client.get("/api/health", headers={"Authorization": ""})
    assert response.status_code == 200


async def test_missing_token(client: AsyncClient) -> None:
    for path in ("/api/me", "/api/meetings", "/api/participants"):
        response = await client.get(path, headers={"Authorization": ""})
        assert response.status_code == 401, path
        assert response.headers["www-authenticate"] == "Bearer"


async def test_rejected_tokens(client: AsyncClient) -> None:
    now = int(time.time())
    bad_tokens = {
        "expired": make_token(iat=now - 7200, exp=now - 3600),
        "other client": make_token(aud="someone-else"),
        "other pool": make_token(iss="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Other"),
        "access token": make_token(token_use="access"),
        "garbage": "not-a-jwt",
    }
    for label, token in bad_tokens.items():
        response = await client.get("/api/me", headers=bearer(token))
        assert response.status_code == 401, label


async def test_tampered_token(client: AsyncClient) -> None:
    header, payload, signature = make_token().split(".")
    forged = make_token("mallory").split(".")[1]
    response = await client.get("/api/me", headers=bearer(f"{header}.{forged}.{signature}"))
    assert response.status_code == 401


async def test_first_request_creates_user(client: AsyncClient) -> None:
    first = (await client.get("/api/me")).json()
    assert first["email"] == "alice@example.com"
    assert first["name"] == "Alice"
    assert (await client.get("/api/me")).json()["id"] == first["id"]


async def test_user_details_follow_the_token(client: AsyncClient) -> None:
    first = (await client.get("/api/me")).json()
    renamed = make_token("alice", name="Alice Koval", email="alice@new.example.com")
    body = (await client.get("/api/me", headers=bearer(renamed))).json()
    assert body == {"id": first["id"], "email": "alice@new.example.com", "name": "Alice Koval"}


async def test_name_falls_back_to_email(client: AsyncClient) -> None:
    token = make_token("carol", name=None, email="carol.k@example.com")
    assert (await client.get("/api/me", headers=bearer(token))).json()["name"] == "carol.k"


async def test_meetings_are_private(client: AsyncClient) -> None:
    mine = (await client.post("/api/meetings", json=meeting_payload(title="Alice's"))).json()
    theirs = (
        await client.post("/api/meetings", json=meeting_payload(title="Bob's"), headers=BOB)
    ).json()

    assert [m["title"] for m in (await client.get("/api/meetings")).json()] == ["Alice's"]
    bob_list = (await client.get("/api/meetings", headers=BOB)).json()
    assert [m["title"] for m in bob_list] == ["Bob's"]

    # Someone else's meeting looks missing: no reading, editing or deleting it.
    url = f"/api/meetings/{theirs['id']}"
    assert (await client.get(url)).status_code == 404
    assert (await client.put(url, json=meeting_payload())).status_code == 404
    assert (await client.delete(url)).status_code == 404
    assert (await client.get(url, headers=BOB)).json()["title"] == "Bob's"
    assert (await client.get(f"/api/meetings/{mine['id']}", headers=BOB)).status_code == 404
