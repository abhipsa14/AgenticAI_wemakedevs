"""
Schedule management API routes.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from app.models.session import get_session
from app.models.database import User, StudyPlan, StudySession, SessionStatus
from app.agents.scheduler import scheduler_agent
import json

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


class TaskStatusUpdate(BaseModel):
    session_id: int
    status: str  # completed, skipped, rescheduled
    notes: Optional[str] = None


class RescheduleRequest(BaseModel):
    session_id: int
    reason: str = "missed"


@router.get("/today")
async def get_todays_tasks(
    date: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """Get study tasks for today (or specified date)."""
    
    target_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
    day_name = target_date.strftime("%A").lower()
    
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "day": day_name.capitalize(),
            "tasks": [],
            "total_hours": 0,
            "message": "No active plan found. Create a study plan first!"
        }
    
    # Get active plan
    plan = db.exec(
        select(StudyPlan)
        .where(StudyPlan.user_id == user.id)
        .where(StudyPlan.is_active == True)
    ).first()
    
    if not plan:
        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "day": day_name.capitalize(),
            "tasks": [],
            "total_hours": 0,
            "message": "No active plan found. Create a study plan first!"
        }
    
    # Get sessions for today
    sessions = db.exec(
        select(StudySession)
        .where(StudySession.plan_id == plan.id)
        .where(StudySession.scheduled_date == target_date.date())
    ).all()
    
    tasks = [
        {
            "id": s.id,
            "subject": s.subject_name,
            "topic": s.topic_name,
            "duration_hours": s.duration_hours,
            "status": s.status.value,
            "notes": s.notes
        }
        for s in sessions
    ]
    
    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "day": day_name.capitalize(),
        "tasks": tasks,
        "total_hours": sum(t['duration_hours'] for t in tasks),
        "plan_name": plan.title
    }


@router.post("/update-status")
async def update_task_status(
    update: TaskStatusUpdate,
    db: Session = Depends(get_session)
):
    """Update the status of a study session."""
    
    session = db.get(StudySession, update.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    status_map = {
        "completed": SessionStatus.COMPLETED,
        "skipped": SessionStatus.SKIPPED,
        "rescheduled": SessionStatus.RESCHEDULED,
        "pending": SessionStatus.PENDING
    }
    
    if update.status not in status_map:
        raise HTTPException(status_code=400, detail=f"Invalid status: {update.status}")
    
    session.status = status_map[update.status]
    session.notes = update.notes or session.notes
    
    if update.status == "completed":
        session.actual_duration = session.duration_hours
    
    db.add(session)
    db.commit()
    
    return {"success": True, "message": f"Session marked as {update.status}"}


@router.post("/reschedule")
async def reschedule_session(
    request: RescheduleRequest,
    db: Session = Depends(get_session)
):
    """Reschedule a missed or skipped session using AI."""
    
    session = db.get(StudySession, request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    plan = db.get(StudyPlan, session.plan_id)
    
    skipped_task = {
        "subject": session.subject_name,
        "topic": session.topic_name,
        "duration_hours": session.duration_hours,
        "original_date": session.scheduled_date.isoformat()
    }
    
    # Get AI suggestions for rescheduling
    result = scheduler_agent.reschedule_task(
        plan={},  # Would need to build full plan data
        skipped_task=skipped_task,
        reason=request.reason
    )
    
    # Mark original session as rescheduled
    session.status = SessionStatus.RESCHEDULED
    db.add(session)
    db.commit()
    
    return {
        "success": True,
        "original_session_id": session.id,
        "suggestions": result
    }


@router.get("/week")
async def get_weekly_schedule(
    start_date: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """Get the full weekly schedule."""
    
    start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.now()
    # Get Monday of current week
    start = start - __import__('datetime').timedelta(days=start.weekday())
    
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        return {"week_start": start.strftime("%Y-%m-%d"), "days": {}}
    
    plan = db.exec(
        select(StudyPlan)
        .where(StudyPlan.user_id == user.id)
        .where(StudyPlan.is_active == True)
    ).first()
    
    if not plan:
        return {"week_start": start.strftime("%Y-%m-%d"), "days": {}}
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    week_data = {}
    
    for i, day_name in enumerate(days):
        day_date = start + __import__('datetime').timedelta(days=i)
        
        sessions = db.exec(
            select(StudySession)
            .where(StudySession.plan_id == plan.id)
            .where(StudySession.scheduled_date == day_date.date())
        ).all()
        
        week_data[day_name.lower()] = {
            "date": day_date.strftime("%Y-%m-%d"),
            "tasks": [
                {
                    "id": s.id,
                    "subject": s.subject_name,
                    "topic": s.topic_name,
                    "duration_hours": s.duration_hours,
                    "status": s.status.value
                }
                for s in sessions
            ]
        }
    
    return {
        "week_start": start.strftime("%Y-%m-%d"),
        "plan_name": plan.title,
        "days": week_data
    }


@router.get("/stats")
async def get_study_stats(db: Session = Depends(get_session)):
    """Get study statistics."""
    
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        return {"total_sessions": 0, "completed": 0, "skipped": 0, "hours_studied": 0}
    
    plan = db.exec(
        select(StudyPlan)
        .where(StudyPlan.user_id == user.id)
        .where(StudyPlan.is_active == True)
    ).first()
    
    if not plan:
        return {"total_sessions": 0, "completed": 0, "skipped": 0, "hours_studied": 0}
    
    all_sessions = db.exec(select(StudySession).where(StudySession.plan_id == plan.id)).all()
    
    completed = [s for s in all_sessions if s.status == SessionStatus.COMPLETED]
    skipped = [s for s in all_sessions if s.status == SessionStatus.SKIPPED]
    
    return {
        "total_sessions": len(all_sessions),
        "completed": len(completed),
        "skipped": len(skipped),
        "pending": len(all_sessions) - len(completed) - len(skipped),
        "hours_studied": sum(s.actual_duration or 0 for s in completed),
        "completion_rate": round(len(completed) / len(all_sessions) * 100, 1) if all_sessions else 0
    }
