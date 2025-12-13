"""
Chat API routes for coordinator agent.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from app.models.session import get_session
from app.models.database import User, ChatMessage, StudyPlan
from app.agents.coordinator import coordinator_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    success: bool
    response: dict
    intent_type: str


@router.post("/")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_session)
):
    """Send a message to the coordinator agent."""
    
    # Get or create user
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        user = User(email="demo@example.com", name="Demo User")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Get active plan for context
    plan = db.exec(
        select(StudyPlan)
        .where(StudyPlan.user_id == user.id)
        .where(StudyPlan.is_active == True)
    ).first()
    
    # Build context
    context = request.context or {}
    if plan:
        context['has_active_plan'] = True
        context['plan_name'] = plan.name
    
    # Save user message
    user_msg = ChatMessage(
        user_id=user.id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()
    
    # Get response from coordinator
    result = coordinator_agent.handle_request(
        user_id=user.id,
        message=request.message,
        context=context
    )
    
    # Save assistant response
    response_content = result.get('message') or result.get('answer') or str(result)
    assistant_msg = ChatMessage(
        user_id=user.id,
        role="assistant",
        content=response_content if isinstance(response_content, str) else str(response_content)
    )
    db.add(assistant_msg)
    db.commit()
    
    return {
        "success": True,
        "response": result,
        "intent_type": result.get('intent_type', 'general')
    }


@router.get("/history")
async def get_chat_history(
    limit: int = 50,
    db: Session = Depends(get_session)
):
    """Get chat history."""
    
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        return {"messages": []}
    
    messages = db.exec(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    ).all()
    
    return {
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat()
            }
            for m in reversed(messages)
        ]
    }


@router.delete("/history")
async def clear_chat_history(db: Session = Depends(get_session)):
    """Clear chat history."""
    
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        return {"success": True, "message": "No history to clear"}
    
    messages = db.exec(select(ChatMessage).where(ChatMessage.user_id == user.id)).all()
    for m in messages:
        db.delete(m)
    db.commit()
    
    return {"success": True, "message": "Chat history cleared"}
