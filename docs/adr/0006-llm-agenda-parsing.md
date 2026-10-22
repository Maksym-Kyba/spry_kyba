# 0006. LLM agenda parsing with Claude on Amazon Bedrock

Status: Accepted. Date: 2026-10-22.

## Context

Agendas reach users as free text: an email from a manager, a chat message, a few lines of notes, in
Ukrainian or English. Typing them into the meeting form by hand is slow. The feature "Paste an
agenda" lets the user paste such text, an LLM turns it into a structured agenda, the form is
pre-filled, and the user checks it and presses Save. The model suggests and the person decides.

Constraints:

- **No NAT gateway.** The API Lambda runs in the VPC to reach Aurora and has no route to the internet
  (Lab 4). A call to Bedrock from there would need a VPC interface endpoint (about $7.30 a month).
- **Cost.** The stack must cost close to $0 when idle, and every model call costs money, so the
  endpoint needs authentication, an input limit and a budget alarm.
- **Text from outside.** The pasted text may contain instructions (prompt injection). It is data,
  never instructions.
- **Model access.** On this AWS account the Claude 5.x models are not available
  (`AccessDeniedException: ... is not available for this account`). Claude Haiku 4.5, Sonnet 4.5/4.6
  and Opus 4.5/4.6 work through the Bedrock runtime API.

## Decision

- **Model:** Claude Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`) through the Bedrock
  runtime API (`anthropic.AnthropicBedrock`). It is the cheapest working model and fast enough for
  a form that waits 2 to 8 seconds. The client (`PARSER_API=runtime|mantle`) and the model
  (`PARSER_MODEL`) are configuration, so moving to a 5.x model on `bedrock-mantle` needs no code change.
- **A separate Lambda function outside the VPC** (`meetings-ai`, `infra/ai.yaml`). It receives text and
  returns JSON, so it needs no database. It reaches Bedrock over the internet without a NAT
  gateway or a VPC endpoint and costs nothing while idle.
- **The model never writes.** The parser only returns a suggestion. Saving goes through the existing
  `POST /api/meetings` with its usual validation and database access. The browser also sends the
  suggestion, the model and the prompt version, and the API stores them in `meetings.ai_suggestion`
  (JSONB, capped at 50 KB) next to the final agenda. The difference between what the model suggested
  and what the user saved is the quality signal.
- **The contract is a schema.** The model answers by calling the tool `record_agenda`. The result is
  validated with Pydantic. On a validation error the model sees the error once and retries, then the
  parser returns an error (422). Values the text does not state stay empty (`minutes`, `owner`, `due`).
- **Authentication.** The function URL is public (`AuthType NONE`), but the code verifies the Cognito
  *access* token (signature against the user pool JWKS, expiry, issuer, `token_use`, `client_id`) and
  answers 401 otherwise. Text longer than 10,000 characters gets 413 before any model call.
- **Logging.** One JSON line per parse: user (`sub`), model, prompt version, input and output tokens,
  latency and cost in dollars. The pasted text is never logged.

## Alternatives considered

- **Call Bedrock from the API Lambda through a VPC interface endpoint.** Rejected: about $7.30 a
  month for one endpoint whether anyone parses or not, which breaks "$0 when idle", and the API
  would need a second network path. For a product with many parses a day it would become reasonable.
- **Use the Claude API directly instead of Bedrock.** Rejected: it needs an API key to store and rotate
  (Bedrock uses the function's IAM role), the usage is billed outside AWS, and it breaks
  the budget alarm and tags that cover the rest of the stack.
- **A regular-expression parser.** Rejected: real agendas are free text in several languages with
  relative dates ("by Friday"). A regular expression covers only the formats it was written for, and
  every new format is more code. It would be cheaper and fully deterministic, so it stays a fallback.

## Consequences

- **Cost.** One parse is about 1,400 input and 310 output tokens, about $0.003 on Haiku 4.5 (the log
  line: 1414 / 310 tokens, $0.002964). Prices for the 4.x models are estimates, so verify them on the
  Bedrock price page. 20 organisations parsing 30 agendas a week each is about 2,600 parses a month,
  about $7 at the measured average of $0.0026 per parse: the same order as one VPC endpoint, and it scales with use, not with time.
- **Latency.** A parse takes 1.6 to 5.3 seconds on the server (six logged calls, the first one after a cold start was the slowest). The screen shows progress
  and a Cancel button. The parser does not stream, because the answer is a JSON object that is only
  useful whole.
- **What is logged and stored.** Token counts, latency and cost in CloudWatch (14 days). The
  suggestion in the database. Not the pasted text.
- **When Bedrock is down or throttled.** The user sees a clear message (429 or 503) and types the
  agenda by hand. Everything else in Spry keeps working, because the parser is a separate function
  and the save path does not call Bedrock.
- **Prompt injection.** The pasted text is delimited and the system prompt says it is data. The
  damage is limited by the design: the model has no tools that change anything, the output is
  validated, and the user checks every field before Save.
- **Abuse.** A public URL with real accounts is limited by the token check, the input cap and the
  $5 monthly budget alarm. Per-user rate limits are not implemented and would be the next step.
- **IAM.** `bedrock:InvokeModel` is limited to Anthropic models and this account's inference
  profiles. `bedrock-mantle:CreateInference` is allowed on `*` and should be narrowed.

## Deviations from the lab text

- Haiku 4.5 on the runtime API instead of Claude 5.x on `bedrock-mantle` (not available for this account).
- The parser is a FastAPI app behind the AWS Lambda Web Adapter, like the API and the report builder, because
  the backend image has no Lambda runtime interface client for a plain `handler(event, context)`.
  `parse_agenda` itself is a plain function with no AWS code in it.
- The template is `infra/ai.yaml`, like all other templates, so that `make infra-lint` covers it.
- Prompt versions: `agenda-v1` gave weekday errors and invented minutes, `agenda-v2` fixed both,
  `agenda-v3` returns local time without a UTC offset (the offset was wrong across the daylight-saving change).
