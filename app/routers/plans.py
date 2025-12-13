"""
Study plans API routes.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from app.models.session import get_session
from app.models.database import User, StudyPlan, Subject, Topic
from app.agents.planner import planner_agent
import json

router = APIRouter(prefix="/api/plans", tags=["plans"])


class SubjectInput(BaseModel):
    name: str
    priority: int = 2
    exam_date: Optional[str] = None


class CreatePlanRequest(BaseModel):
    subjects: List[SubjectInput]
    hours_per_day: float = 4.0
    goals: Optional[str] = None
    start_date: Optional[str] = None


class PlanResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    is_active: bool
    plan_data: dict


@router.post("/create")
async def create_study_plan(
    request: CreatePlanRequest,
    db: Session = Depends(get_session)
):
    """Create a new study plan using the AI planner agent."""
    
    # Get or create default user
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        user = User(email="demo@example.com", name="Demo User")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Prepare subjects for planner
    subjects_data = [
        {"name": s.name, "priority": s.priority, "exam_date": s.exam_date}
        for s in request.subjects
    ]
    
    exam_dates = {s.name: s.exam_date for s in request.subjects if s.exam_date}
    
    # Generate plan using AI agent
    result = planner_agent.create_plan(
        subjects=subjects_data,
        available_hours_per_day=request.hours_per_day,
        exam_dates=exam_dates if exam_dates else None,
        study_goals=request.goals,
        start_date=request.start_date
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to create plan'))
    
    plan_data = result['plan']
    
    # Save to database
    study_plan = StudyPlan(
        user_id=user.id,
        name=f"Study Plan - {datetime.now().strftime('%Y-%m-%d')}",
        description=request.goals or "AI-generated study plan",
        total_hours=request.hours_per_day * 7,
        weekly_hours=request.hours_per_day * 7,
        is_active=True
    )
    db.add(study_plan)
    db.commit()
    db.refresh(study_plan)
    
    # Save subjects and topics
    for subj_data in plan_data.get('subjects', []):
        subject = Subject(
            plan_id=study_plan.id,
            name=subj_data['name'],
            priority=subj_data.get('priority', 2),
            exam_date=datetime.strptime(subj_data['exam_date'], '%Y-%m-%d') if subj_data.get('exam_date') else None
        )
        db.add(subject)
        db.commit()
        db.refresh(subject)
        
        for topic_data in subj_data.get('topics', []):
            topic = Topic(
                subject_id=subject.id,
                name=topic_data['name'],
                estimated_hours=topic_data.get('estimated_hours', 1.0),
                difficulty=topic_data.get('difficulty', 'medium'),
                resources=json.dumps(topic_data.get('resources', []))
            )
            db.add(topic)
    
    db.commit()
    
    return {
        "success": True,
        "plan_id": study_plan.id,
        "plan_name": study_plan.name,
        "plan_data": plan_data
    }


@router.get("/")
async def list_plans(db: Session = Depends(get_session)):
    """List all study plans."""
    
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        return {"plans": []}
    
    plans = db.exec(select(StudyPlan).where(StudyPlan.user_id == user.id)).all()
    
    return {
        "plans": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat()
            }
            for p in plans
        ]
    }


@router.get("/{plan_id}")
async def get_plan(plan_id: int, db: Session = Depends(get_session)):
    """Get a specific study plan with all details."""
    
    plan = db.get(StudyPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    subjects = db.exec(select(Subject).where(Subject.plan_id == plan_id)).all()
    
    subjects_data = []
    for subj in subjects:
        topics = db.exec(select(Topic).where(Topic.subject_id == subj.id)).all()
        subjects_data.append({
            "id": subj.id,
            "name": subj.name,
            "priority": subj.priority,
            "exam_date": subj.exam_date.isoformat() if subj.exam_date else None,
            "topics": [
                {
                    "id": t.id,
                    "name": t.name,
                    "estimated_hours": t.estimated_hours,
                    "difficulty": t.difficulty,
                    "is_completed": t.is_completed
                }
                for t in topics
            ]
        })
    
    return {
        "id": plan.id,
        "name": plan.name,
        "description": plan.description,
        "is_active": plan.is_active,
        "created_at": plan.created_at.isoformat(),
        "subjects": subjects_data
    }


@router.post("/suggest-topics")
async def suggest_topics(subject: str, level: str = "undergraduate"):
    """Get AI-suggested topics for a subject."""
    
    result = planner_agent.suggest_topics(subject=subject, level=level)
    return result


@router.delete("/{plan_id}")
async def delete_plan(plan_id: int, db: Session = Depends(get_session)):
    """Delete a study plan."""
    
    plan = db.get(StudyPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    db.delete(plan)
    db.commit()
    
    return {"success": True, "message": "Plan deleted"}
