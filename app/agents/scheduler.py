"""
Scheduler Agent - Manages daily tasks and reschedules when needed.
"""
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from app.services.llm_service import llm_service


SCHEDULER_SYSTEM_PROMPT = """You are a study schedule management agent. Your role is to:
1. Help students manage their daily study tasks
2. Reschedule missed or skipped sessions intelligently
3. Suggest optimal study times based on workload
4. Balance the schedule when changes occur

When rescheduling, consider:
- Upcoming exam dates (prioritize subjects with nearer exams)
- Topic difficulty (harder topics need more time)
- Student's available hours
- Don't overload any single day

Always respond with valid JSON when asked for scheduling decisions."""


class SchedulerAgent:
    """Agent for managing study schedules."""
    
    def __init__(self):
        self.system_prompt = SCHEDULER_SYSTEM_PROMPT
    
    def get_todays_tasks(
        self, plan: Dict, current_date: Optional[str] = None
    ) -> Dict:
        """Get tasks scheduled for today."""
        
        today = datetime.strptime(current_date, "%Y-%m-%d") if current_date else datetime.now()
        day_name = today.strftime("%A").lower()
        
        weekly_schedule = plan.get('weekly_schedule', {})
        todays_tasks = weekly_schedule.get(day_name, [])
        
        return {
            "date": today.strftime("%Y-%m-%d"),
            "day": day_name.capitalize(),
            "tasks": todays_tasks,
            "total_hours": sum(t.get('duration_hours', 0) for t in todays_tasks)
        }
    
    def reschedule_task(
        self, plan: Dict, skipped_task: Dict, 
        reason: str = "missed", 
        available_days: Optional[List[str]] = None
    ) -> Dict:
        """Reschedule a skipped or missed task."""
        
        prompt = f"""A student missed a study session. Please suggest how to reschedule it.

MISSED/SKIPPED TASK:
{json.dumps(skipped_task, indent=2)}

REASON: {reason}

CURRENT WEEKLY SCHEDULE:
{json.dumps(plan.get('weekly_schedule', {}), indent=2)}

AVAILABLE DAYS FOR RESCHEDULING: {available_days or "any day"}

Please suggest:
1. When to reschedule this task
2. If any other tasks need to be adjusted
3. Tips for catching up

Respond with JSON:
{{
    "rescheduled_task": {{
        "original_day": "monday",
        "new_day": "wednesday",
        "subject": "Subject",
        "topic": "Topic",
        "duration_hours": 1.5
    }},
    "adjustments": [
        {{"day": "wednesday", "change": "description of change"}}
    ],
    "catch_up_tips": ["Tip 1", "Tip 2"]
}}"""

        try:
            response = llm_service.simple_completion(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.5
            )
            
            response = response.strip()
            if "```" in response:
                response = response.split("```")[1].replace("json", "").strip()
            
            result = json.loads(response)
            result['success'] = True
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def rebalance_schedule(
        self, plan: Dict, 
        changes: Dict
    ) -> Dict:
        """Rebalance the schedule based on changes (new deadlines, completed topics, etc.)."""
        
        prompt = f"""The student's study plan needs rebalancing due to changes.

CURRENT PLAN SUBJECTS:
{json.dumps(plan.get('subjects', []), indent=2)}

CURRENT WEEKLY SCHEDULE:
{json.dumps(plan.get('weekly_schedule', {}), indent=2)}

CHANGES TO ACCOMMODATE:
{json.dumps(changes, indent=2)}

Please create an updated, balanced schedule. Respond with JSON:
{{
    "updated_weekly_schedule": {{
        "monday": [...],
        "tuesday": [...],
        ...
    }},
    "changes_made": ["Description of change 1", "Description of change 2"],
    "priority_adjustments": ["Any priority changes"],
    "warnings": ["Any concerns about the new schedule"]
}}"""

        try:
            response = llm_service.simple_completion(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.5
            )
            
            response = response.strip()
            if "```" in response:
                response = response.split("```")[1].replace("json", "").strip()
            
            result = json.loads(response)
            result['success'] = True
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def suggest_study_time(
        self, subject: str, topic: str, difficulty: str = "medium"
    ) -> Dict:
        """Suggest optimal study duration for a topic."""
        
        difficulty_multipliers = {
            "easy": 0.75,
            "medium": 1.0,
            "hard": 1.5
        }
        
        base_hours = 1.5
        multiplier = difficulty_multipliers.get(difficulty, 1.0)
        suggested_hours = round(base_hours * multiplier, 1)
        
        return {
            "subject": subject,
            "topic": topic,
            "difficulty": difficulty,
            "suggested_hours": suggested_hours,
            "breakdown": {
                "reading": round(suggested_hours * 0.3, 1),
                "practice": round(suggested_hours * 0.5, 1),
                "review": round(suggested_hours * 0.2, 1)
            },
            "tips": [
                f"For {difficulty} topics, focus on understanding before practice",
                "Take short breaks every 25-30 minutes (Pomodoro technique)",
                "End with a quick self-quiz to test retention"
            ]
        }


scheduler_agent = SchedulerAgent()
