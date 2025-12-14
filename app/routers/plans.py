"""
Study plans API routes.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from app.models.session import get_session
from app.models.database import User, StudyPlan, Subject, Topic, StudySession, SessionStatus, Priority
from app.agents.planner import planner_agent
import json

router = APIRouter(prefix="/api/plans", tags=["plans"])


class SubjectInput(BaseModel):
    name: str
    priority: int = 2
    exam_date: Optional[str] = None
    topics: Optional[List[str]] = None


class CreatePlanRequest(BaseModel):
    subjects: List[SubjectInput]
    hours_per_day: float = 4.0
    goals: Optional[str] = None
    start_date: Optional[str] = None
    grade: Optional[str] = None
    board: Optional[str] = None


class PlanResponse(BaseModel):
    id: int
    title: str
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
        {
            "name": s.name, 
            "priority": s.priority, 
            "exam_date": s.exam_date,
            "topics": s.topics or []
        }
        for s in request.subjects
    ]
    
    exam_dates = {s.name: s.exam_date for s in request.subjects if s.exam_date}
    
    # Build goals string including grade info
    goals_str = request.goals or ""
    if request.grade:
        goals_str = f"Grade: {request.grade}, Board: {request.board or 'Not specified'}. {goals_str}"
    
    # Generate plan using AI agent
    result = planner_agent.create_plan(
        subjects=subjects_data,
        available_hours_per_day=request.hours_per_day,
        exam_dates=exam_dates if exam_dates else None,
        study_goals=goals_str if goals_str else None,
        start_date=request.start_date
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to create plan'))
    
    plan_data = result['plan']
    
    # Calculate dates
    from datetime import timedelta
    start = datetime.strptime(request.start_date, '%Y-%m-%d').date() if request.start_date else datetime.now().date()
    end = start + timedelta(days=30)  # Default 30 day plan
    
    # Save to database
    study_plan = StudyPlan(
        user_id=user.id,
        title=f"Study Plan - {datetime.now().strftime('%Y-%m-%d')}",
        goal=request.goals or "AI-generated study plan",
        start_date=start,
        end_date=end,
        hours_per_day=request.hours_per_day,
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
            description=f"Priority: {subj_data.get('priority', 2)}"
        )
        db.add(subject)
        db.commit()
        db.refresh(subject)
        
        for topic_data in subj_data.get('topics', []):
            difficulty_map = {'easy': 1, 'medium': 2, 'hard': 3}
            diff_value = difficulty_map.get(topic_data.get('difficulty', 'medium'), 2)
            topic = Topic(
                subject_id=subject.id,
                name=topic_data['name'],
                estimated_hours=topic_data.get('estimated_hours', 1.0),
                difficulty=diff_value
            )
            db.add(topic)
    
    db.commit()
    
    # Create study sessions from weekly schedule
    weekly_schedule = plan_data.get('weekly_schedule', {})
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    # Create sessions for the next 4 weeks
    from datetime import timedelta
    current_date = start
    
    for week in range(4):
        for day_index, day_name in enumerate(day_names):
            # Calculate the date for this day
            days_until_day = (day_index - start.weekday()) % 7
            session_date = start + timedelta(days=days_until_day + (week * 7))
            
            # Skip if before start date
            if session_date < start:
                continue
            
            # Get tasks for this day
            day_tasks = weekly_schedule.get(day_name, [])
            
            session_time_hour = 9  # Start at 9 AM
            
            for task in day_tasks:
                subject_name = task.get('subject', 'Study')
                topic_name = task.get('topic', 'General')
                duration_hours = task.get('duration_hours', 1.0)
                
                session = StudySession(
                    plan_id=study_plan.id,
                    subject_name=subject_name,
                    topic_name=topic_name,
                    scheduled_date=session_date,
                    scheduled_time=f"{session_time_hour:02d}:00",
                    duration_hours=duration_hours,
                    duration_minutes=int(duration_hours * 60),
                    status=SessionStatus.PENDING,
                    priority=Priority.MEDIUM
                )
                db.add(session)
                
                # Increment time for next session
                session_time_hour += int(duration_hours) + 1
                if session_time_hour > 20:  # Don't schedule past 8 PM
                    session_time_hour = 9
    
    db.commit()
    
    return {
        "success": True,
        "plan_id": study_plan.id,
        "plan_name": study_plan.title,
        "plan_data": plan_data,
        "message": "Study plan created with tasks added to your schedule!"
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
                "name": p.title,
                "description": p.goal,
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
            "description": subj.description,
            "topics": [
                {
                    "id": t.id,
                    "name": t.name,
                    "estimated_hours": t.estimated_hours,
                    "difficulty": t.difficulty
                }
                for t in topics
            ]
        })
    
    return {
        "id": plan.id,
        "name": plan.title,
        "description": plan.goal,
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
