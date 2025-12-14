"""
Planner Agent - Creates personalized study plans.
"""
import json
from datetime import datetime, timedelta
from typing import Optional
from app.services.llm_service import llm_service


PLANNER_SYSTEM_PROMPT = """You are an expert study planner agent. Your role is to create personalized, 
realistic study plans for students based on their subjects, available time, exam dates, and goals.

GUIDELINES:
1. If topics are already provided for a subject, USE those topics and estimate hours for each
2. If no topics are provided, break down subjects into manageable topics yourself
3. Distribute study sessions evenly, avoiding overload
4. Include breaks and revision time
5. Prioritize based on exam dates and difficulty
6. Be realistic about time estimates based on the grade level mentioned
7. Include active recall and practice sessions
8. For board exam grades (10, 12), focus more on exam-oriented preparation
9. For competitive exams (JEE, NEET), include problem-solving practice

When creating a plan, you MUST respond with valid JSON in this exact format:
{
    "subjects": [
        {
            "name": "Subject Name",
            "priority": 1,
            "topics": [
                {
                    "name": "Topic Name",
                    "estimated_hours": 2.0,
                    "difficulty": "medium",
                    "resources": ["textbook chapter X", "lecture notes"]
                }
            ],
            "exam_date": "YYYY-MM-DD or null"
        }
    ],
    "weekly_schedule": {
        "monday": [{"subject": "Subject", "topic": "Topic", "duration_hours": 1.5, "type": "study"}],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "saturday": [],
        "sunday": []
    },
    "daily_study_hours": 4,
    "recommendations": ["Tip 1", "Tip 2"]
}"""


class PlannerAgent:
    """Agent for creating study plans."""
    
    def __init__(self):
        self.system_prompt = PLANNER_SYSTEM_PROMPT
    
    def create_plan(
        self, subjects: list, available_hours_per_day: float,
        exam_dates: Optional[dict] = None, study_goals: Optional[str] = None,
        start_date: Optional[str] = None
    ) -> dict:
        """Create a comprehensive study plan."""
        
        start = start_date or datetime.now().strftime("%Y-%m-%d")
        
        # Format subjects with topics information
        subjects_info = ""
        for subj in subjects:
            subjects_info += f"\n- {subj['name']} (Priority: {subj.get('priority', 2)})"
            if subj.get('topics'):
                subjects_info += f"\n  Pre-selected topics: {', '.join(subj['topics'])}"
            if subj.get('exam_date'):
                subjects_info += f"\n  Exam date: {subj['exam_date']}"
        
        prompt = f"""Create a detailed study plan with these parameters:

SUBJECTS TO STUDY:{subjects_info}

CONSTRAINTS:
- Available study hours per day: {available_hours_per_day}
- Start date: {start}
- Exam dates: {json.dumps(exam_dates or {}, indent=2)}

STUDENT'S GOALS/CONTEXT:
{study_goals or 'General mastery of all subjects'}

IMPORTANT: If topics are pre-selected for a subject, use those exact topics in your plan and estimate hours for each.
If no topics are given, create appropriate topics based on the grade level mentioned.

Create a realistic, well-structured study plan. Respond ONLY with valid JSON."""

        try:
            response = llm_service.simple_completion(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.5
            )
            
            # Extract JSON from response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            plan = json.loads(response.strip())
            plan['created_at'] = datetime.now().isoformat()
            plan['start_date'] = start
            
            return {"success": True, "plan": plan}
        
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Failed to parse plan: {str(e)}", "raw_response": response}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def suggest_topics(self, subject: str, level: str = "undergraduate") -> dict:
        """Suggest topics for a given subject."""
        
        prompt = f"""Suggest a comprehensive list of topics for studying {subject} at {level} level.
        
Return JSON format:
{{
    "subject": "{subject}",
    "topics": [
        {{"name": "Topic name", "subtopics": ["Subtopic 1", "Subtopic 2"], "estimated_hours": 2.0, "difficulty": "easy/medium/hard"}}
    ]
}}"""

        try:
            response = llm_service.simple_completion(prompt=prompt, system_prompt=self.system_prompt)
            response = response.strip()
            if "```" in response:
                response = response.split("```")[1].replace("json", "").strip()
            return json.loads(response)
        except Exception as e:
            return {"error": str(e)}


planner_agent = PlannerAgent()
