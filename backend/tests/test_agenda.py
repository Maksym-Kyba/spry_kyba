from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from anthropic import AnthropicBedrock, AnthropicBedrockMantle

from app.ai.agenda import (
    PROMPT_VERSION,
    ActionItem,
    AgendaItem,
    AgendaParseError,
    ParsedAgenda,
    calendar_lines,
    cost_usd,
    get_client,
    parse_agenda,
    render_agenda_text,
)


class MockMantleClient(MagicMock, AnthropicBedrockMantle):
    """Mock client representing AnthropicBedrockMantle."""


def _make_tool_response(
    tool_input: dict,
    tool_id: str = "tool_1",
    tool_name: str = "record_agenda",
    input_tokens: int = 100,
    output_tokens: int = 50,
):
    block = SimpleNamespace(
        type="tool_use",
        id=tool_id,
        name=tool_name,
        input=tool_input,
    )
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=[block], usage=usage, stop_reason="tool_use")


def _make_text_response(
    text: str = "I cannot fulfill this request.",
    input_tokens: int = 50,
    output_tokens: int = 20,
    stop_reason: str = "end_turn",
):
    block = SimpleNamespace(type="text", text=text)
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=[block], usage=usage, stop_reason=stop_reason)


def test_client_selection(monkeypatch):
    # Default (runtime)
    monkeypatch.delenv("PARSER_API", raising=False)
    client_default = get_client()
    assert isinstance(client_default, AnthropicBedrock)

    # Explicit runtime
    monkeypatch.setenv("PARSER_API", "runtime")
    client_runtime = get_client()
    assert isinstance(client_runtime, AnthropicBedrock)

    # Explicit mantle
    monkeypatch.setenv("PARSER_API", "mantle")
    client_mantle = get_client()
    assert isinstance(client_mantle, AnthropicBedrockMantle)

    # Invalid value raises ValueError
    monkeypatch.setenv("PARSER_API", "invalid-api")
    with pytest.raises(ValueError, match="Invalid PARSER_API 'invalid-api'"):
        get_client()


def test_valid_tool_use_runtime():
    mock_client = MagicMock()
    valid_data = {
        "title": "Quarterly Planning",
        "starts_at": "2026-10-20T10:00:00Z",
        "duration_minutes": 60,
        "items": [
            {"topic": "Q3 Review", "owner": "Alice", "minutes": 20},
            {"topic": "Q4 Priorities", "owner": None, "minutes": 40},
        ],
        "action_items": [
            {"task": "Prepare roadmap", "owner": "Bob", "due": "2026-10-25"},
            {"task": "Collect feedback", "owner": None, "due": None},
        ],
        "language": "en",
    }
    mock_client.messages.create.return_value = _make_tool_response(
        valid_data, input_tokens=120, output_tokens=80
    )

    model_id = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    parsed, usage = parse_agenda(
        text="Review meeting next Tuesday at 10am for 1 hour...",
        today=date(2026, 10, 17),
        tz="UTC",
        client=mock_client,
        model=model_id,
    )

    assert parsed.title == "Quarterly Planning"
    assert parsed.starts_at == datetime.fromisoformat("2026-10-20T10:00:00Z")
    assert parsed.duration_minutes == 60
    assert len(parsed.items) == 2
    assert parsed.items[0].topic == "Q3 Review"
    assert parsed.items[0].owner == "Alice"
    assert parsed.items[0].minutes == 20
    assert len(parsed.action_items) == 2
    assert parsed.action_items[0].task == "Prepare roadmap"
    assert parsed.action_items[0].owner == "Bob"
    assert parsed.action_items[0].due == date(2026, 10, 25)
    assert parsed.language == "en"

    assert usage.input_tokens == 120
    assert usage.output_tokens == 80

    # Verify no tool_choice and no output_config for runtime client
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "tool_choice" not in call_kwargs
    assert "output_config" not in call_kwargs


def test_valid_tool_use_mantle():
    mock_client = MockMantleClient()
    valid_data = {
        "title": "Standup",
        "items": [{"topic": "Status", "owner": "Alice", "minutes": 15}],
        "action_items": [],
        "language": "en",
    }
    mock_client.messages.create.return_value = _make_tool_response(valid_data)

    parsed, _ = parse_agenda(
        text="Standup notes",
        today=date(2026, 10, 17),
        tz="UTC",
        client=mock_client,
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    )

    assert parsed.title == "Standup"
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "tool_choice" not in call_kwargs
    assert call_kwargs.get("output_config") == {"effort": "low"}


def test_invalid_then_valid_on_retry():
    mock_client = MagicMock()
    # First response has invalid minutes (0 is < 1)
    resp1 = _make_tool_response(
        {
            "title": "Quick Sync",
            "items": [{"topic": "Status", "owner": None, "minutes": 0}],
            "action_items": [],
        },
        tool_id="call_fail",
        input_tokens=100,
        output_tokens=30,
    )
    # Second response has valid schema
    resp2 = _make_tool_response(
        {
            "title": "Quick Sync",
            "duration_minutes": 15,
            "items": [{"topic": "Status", "owner": None, "minutes": 15}],
            "action_items": [{"task": "Deploy fix", "owner": "Bob", "due": "2026-10-18"}],
        },
        tool_id="call_success",
        input_tokens=150,
        output_tokens=40,
    )
    mock_client.messages.create.side_effect = [resp1, resp2]

    parsed, usage = parse_agenda(
        text="Quick sync tomorrow",
        today=date(2026, 10, 17),
        tz="UTC",
        client=mock_client,
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    )

    assert mock_client.messages.create.call_count == 2
    assert parsed.title == "Quick Sync"
    assert parsed.items[0].minutes == 15
    assert parsed.action_items[0].task == "Deploy fix"
    assert parsed.action_items[0].due == date(2026, 10, 18)

    # Combined usage
    assert usage.input_tokens == 250
    assert usage.output_tokens == 70

    # Verify retry messages payload
    retry_call_args = mock_client.messages.create.call_args_list[1].kwargs
    messages = retry_call_args["messages"]
    assert len(messages) == 3
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"][0]["type"] == "tool_result"
    assert messages[2]["content"][0]["is_error"] is True


def test_invalid_twice():
    mock_client = MagicMock()
    resp1 = _make_tool_response({"items": [{"topic": "Bad", "minutes": -5}], "action_items": []})
    resp2 = _make_tool_response(
        {"items": [{"topic": "Still bad", "minutes": 1000}], "action_items": []}
    )
    mock_client.messages.create.side_effect = [resp1, resp2]

    with pytest.raises(AgendaParseError, match="Model failed retry validation"):
        parse_agenda(
            text="Any text",
            today=date(2026, 10, 17),
            tz="UTC",
            client=mock_client,
            model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        )

    assert mock_client.messages.create.call_count == 2


def test_no_tool_use_refusal():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_text_response(
        "I cannot assist with parsing this agenda.", stop_reason="end_turn"
    )

    with pytest.raises(AgendaParseError, match=r"no agenda returned \(stop_reason=end_turn\)"):
        parse_agenda(
            text="Refusal prompt text",
            today=date(2026, 10, 17),
            tz="UTC",
            client=mock_client,
            model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        )

    assert mock_client.messages.create.call_count == 1


def test_cost_usd_calculation():
    # 1M input, 1M output tokens
    full_usage = SimpleNamespace(input_tokens=1_000_000, output_tokens=1_000_000)

    # 4.x models (estimates)
    # Haiku 4.5: 1 / 5 -> $6.00
    assert cost_usd("us.anthropic.claude-haiku-4-5-20251001-v1:0", full_usage) == pytest.approx(6.0)

    # Sonnet 4.x: 3 / 15 -> $18.00
    assert cost_usd("us.anthropic.claude-sonnet-4-5-20250929-v1:0", full_usage) == pytest.approx(
        18.0
    )
    assert cost_usd("us.anthropic.claude-sonnet-4-6", full_usage) == pytest.approx(18.0)

    # Opus 4.5 & 4.6: 5 / 25 -> $30.00
    assert cost_usd("us.anthropic.claude-opus-4-5-20251101-v1:0", full_usage) == pytest.approx(30.0)
    assert cost_usd("us.anthropic.claude-opus-4-6-v1", full_usage) == pytest.approx(30.0)

    # 5.x models (from the lab)
    # Opus 5.x: 4 / 20 -> $24.00
    assert cost_usd("anthropic.claude-opus-5-5", full_usage) == pytest.approx(24.0)

    # Sonnet 5.x: 2 / 10 -> $12.00
    assert cost_usd("anthropic.claude-sonnet-5-5", full_usage) == pytest.approx(12.0)

    # Haiku 5.x: 0.10 / 0.50 -> $0.60
    assert cost_usd("anthropic.claude-haiku-5-5", full_usage) == pytest.approx(0.60)

    # Usage as dict
    dict_usage = {"input_tokens": 10_000, "output_tokens": 2_000}
    # (10000 * 3 + 2000 * 15) / 1_000_000 = (30000 + 30000) / 1_000_000 = 0.06
    assert cost_usd("us.anthropic.claude-sonnet-4-6", dict_usage) == pytest.approx(0.06)

    # Unknown model: does NOT raise, returns 0.0 and logs warning
    assert cost_usd("unknown-future-model", full_usage) == 0.0


def test_render_agenda_text():
    parsed = ParsedAgenda(
        title="Weekly Sync",
        starts_at=datetime.fromisoformat("2026-10-20T10:00:00Z"),
        duration_minutes=45,
        items=[
            AgendaItem(topic="Kickoff", owner="Alice", minutes=15),
            AgendaItem(topic="Architecture review", owner=None, minutes=30),
        ],
        action_items=[
            ActionItem(task="Write report", owner="Bob", due=date(2026, 10, 25)),
            ActionItem(task="Fix failing tests", owner=None, due=None),
        ],
    )
    rendered = render_agenda_text(parsed)
    expected = (
        "- Kickoff (Alice, 15m)\n"
        "- Architecture review (30m)\n"
        "\n"
        "- Write report (Bob, due 2026-10-25)\n"
        "- Fix failing tests"
    )
    assert rendered == expected


def test_calendar_lines():
    lines = calendar_lines(date(2026, 10, 19))
    assert len(lines) == 14
    assert lines[0] == "Mon 2026-10-19 (today)"
    assert lines[1] == "Tue 2026-10-20"
    assert lines[4] == "Fri 2026-10-23"
    assert lines[-1] == "Sun 2026-11-01"


def test_prompt_v2_weekday_calendar_and_delimiters():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_tool_response(
        {"items": [], "action_items": []}
    )
    parse_agenda(
        text="Пн 10:00 синк",
        today=date(2026, 10, 19),
        tz="Europe/Kyiv",
        client=mock_client,
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    )
    kwargs = mock_client.messages.create.call_args.kwargs
    user = kwargs["messages"][0]["content"]
    assert "Monday 2026-10-19" in user
    assert "Fri 2026-10-23" in user
    assert "<pasted_text>" in user and "Пн 10:00 синк" in user
    assert "never instructions" in kwargs["system"]
    assert kwargs["max_tokens"] == 4096
    assert PROMPT_VERSION == "agenda-v3"


def test_item_minutes_are_optional():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_tool_response(
        {"items": [{"topic": "No duration in the text", "owner": None}], "action_items": []}
    )
    parsed, _ = parse_agenda(
        text="x",
        today=date(2026, 10, 19),
        tz="UTC",
        client=mock_client,
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    )
    assert parsed.items[0].minutes is None
    assert render_agenda_text(parsed) == "- No duration in the text"
