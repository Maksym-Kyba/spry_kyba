from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import SessionDep
from app.models import Participant
from app.schemas import ParticipantCreate, ParticipantRead

router = APIRouter(prefix="/participants", tags=["participants"])


@router.get("", response_model=list[ParticipantRead])
async def list_participants(session: SessionDep) -> list[Participant]:
    result = await session.scalars(select(Participant).order_by(Participant.name))
    return list(result)


@router.post("", response_model=ParticipantRead, status_code=status.HTTP_201_CREATED)
async def create_participant(payload: ParticipantCreate, session: SessionDep) -> Participant:
    participant = Participant(name=payload.name, email=payload.email.lower())
    session.add(participant)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Participant with this email already exists"
        ) from None
    return participant
