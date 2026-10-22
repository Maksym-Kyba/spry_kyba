import json
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
    field_serializer,
    model_validator,
)

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _require_tz(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("datetime must include a time-zone offset")
    return value.astimezone(UTC)


AwareDatetime = Annotated[datetime, AfterValidator(_require_tz)]


class ParticipantCreate(BaseModel):
    name: Annotated[NonEmptyStr, StringConstraints(max_length=100)]
    email: Annotated[EmailStr, StringConstraints(max_length=255)]


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str


MAX_AI_SUGGESTION_BYTES = 50_000


class AiSuggestion(BaseModel):
    """What the model suggested, stored next to the final agenda (the quality signal)."""

    agenda: dict[str, Any]
    model: Annotated[str, StringConstraints(max_length=100)]
    prompt_version: Annotated[str, StringConstraints(max_length=50)]

    @model_validator(mode="after")
    def check_size(self) -> AiSuggestion:
        size = len(json.dumps(self.agenda, ensure_ascii=False).encode("utf-8"))
        if size > MAX_AI_SUGGESTION_BYTES:
            raise ValueError("ai_suggestion is too large")
        return self


class MeetingCreate(BaseModel):
    title: Annotated[NonEmptyStr, StringConstraints(max_length=200)]
    description: str = ""
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    place: Annotated[NonEmptyStr, StringConstraints(max_length=200)]
    participant_ids: list[uuid.UUID] = []
    agenda: Annotated[str, StringConstraints(max_length=20_000)] = ""
    ai_suggestion: AiSuggestion | None = None

    @model_validator(mode="after")
    def check_times(self) -> MeetingCreate:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        # de-duplicate while keeping order
        self.participant_ids = list(dict.fromkeys(self.participant_ids))
        return self


class MeetingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    agenda: str
    starts_at: datetime
    ends_at: datetime
    place: str
    participants: list[ParticipantRead]
    ai_suggestion: dict[str, Any] | None = None
    created_at: datetime

    @field_serializer("starts_at", "ends_at", "created_at")
    def to_utc(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
