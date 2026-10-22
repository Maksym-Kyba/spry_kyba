import os
import sys

from app.ai.agenda import get_client


def main() -> None:
    model = os.environ.get("PARSER_MODEL")
    if not model:
        print("Error: PARSER_MODEL environment variable is not set", file=sys.stderr)
        sys.exit(1)

    try:
        client = get_client()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    response = client.messages.create(
        model=model,
        max_tokens=256,
        messages=[{"role": "user", "content": "Hello! Say hi in one short sentence."}],
    )

    answer = ""
    for block in response.content:
        if getattr(block, "type", None) == "text" or hasattr(block, "text"):
            answer += getattr(block, "text", "")

    print(f"Answer: {answer}")
    print(f"Stop reason: {response.stop_reason}")
    print(f"Usage: {response.usage}")


if __name__ == "__main__":
    main()
