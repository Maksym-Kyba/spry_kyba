from httpx import AsyncClient

BASE = "/api/meetings"  # change if the existing tests use another prefix

SUGGESTION = {
    "agenda": {"title": "Pricing sync", "items": [{"topic": "Pro pricing", "minutes": 15}]},
    "model": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "prompt_version": "agenda-v2",
}


def _payload(**extra):
    return {
        "title": "Pricing sync",
        "description": "",
        "starts_at": "2026-10-26T10:00:00+03:00",
        "ends_at": "2026-10-26T10:45:00+03:00",
        "place": "Room 1",
        "participant_ids": [],
        **extra,
    }


async def test_old_requests_still_work(client: AsyncClient):
    r = await client.post(BASE, json=_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["agenda"] == ""
    assert body["ai_suggestion"] is None


async def test_create_with_agenda_and_ai_suggestion(client: AsyncClient):
    r = await client.post(
        BASE, json=_payload(agenda="- Pro pricing (15m)", ai_suggestion=SUGGESTION)
    )
    assert r.status_code == 201
    meeting_id = r.json()["id"]
    got = (await client.get(f"{BASE}/{meeting_id}")).json()
    assert got["agenda"] == "- Pro pricing (15m)"
    assert got["ai_suggestion"] == SUGGESTION


async def test_too_large_ai_suggestion_is_rejected(client: AsyncClient):
    big = {**SUGGESTION, "agenda": {"blob": "x" * 60_000}}
    r = await client.post(BASE, json=_payload(ai_suggestion=big))
    assert r.status_code == 422


async def test_long_model_name_is_rejected(client: AsyncClient):
    bad = {**SUGGESTION, "model": "m" * 101}
    r = await client.post(BASE, json=_payload(ai_suggestion=bad))
    assert r.status_code == 422


async def test_put_keeps_agenda_unless_sent(client: AsyncClient):
    r = await client.post(BASE, json=_payload(agenda="first", ai_suggestion=SUGGESTION))
    meeting_id = r.json()["id"]

    r = await client.put(f"{BASE}/{meeting_id}", json=_payload(title="Renamed"))
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"
    assert r.json()["agenda"] == "first"
    assert r.json()["ai_suggestion"] == SUGGESTION

    r = await client.put(f"{BASE}/{meeting_id}", json=_payload(agenda="second"))
    assert r.json()["agenda"] == "second"
    assert r.json()["ai_suggestion"] == SUGGESTION
