"""API routes for conversation viewing."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from backend.database import get_db
from backend.api.schemas import ConversationSummaryResponse, ConversationResponse
from backend.models.models import Conversation, Simulation

router = APIRouter()


@router.get(
    "/simulations/{simulation_id}/conversations",
    response_model=List[ConversationSummaryResponse],
)
async def get_simulation_conversations(
    simulation_id: int, db: Session = Depends(get_db)
):
    """Get all conversations for a simulation."""
    # Verify simulation exists
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Get all conversations
    conversations = (
        db.query(Conversation)
        .filter(Conversation.simulation_id == simulation_id)
        .order_by(Conversation.started_at)
        .all()
    )

    return conversations


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Get full conversation details including all messages."""
    conversation = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(Conversation.id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation
