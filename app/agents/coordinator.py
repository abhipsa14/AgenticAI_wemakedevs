"""
Coordinator Agent - Routes requests and coordinates between agents.
"""
from typing import Dict, Optional
from app.agents.planner import planner_agent
from app.agents.knowledge import knowledge_agent
from app.agents.scheduler import scheduler_agent
from app.services.llm_service import llm_service


COORDINATOR_SYSTEM_PROMPT = """You are a coordinator agent for a study assistant system.
Your role is to understand the student's request and determine the best way to help them.

You can help with:
1. PLANNING - Creating study plans, suggesting topics, organizing study schedule
2. KNOWLEDGE - Answering questions from notes, explaining topics, generating quizzes
3. SCHEDULING - Managing daily tasks, rescheduling missed sessions, rebalancing plans
4. GENERAL - General study tips, motivation, chat

Analyze the student's message and respond with the appropriate action."""


class CoordinatorAgent:
    """Main coordinator that routes requests to appropriate agents."""
    
    def __init__(self):
        self.system_prompt = COORDINATOR_SYSTEM_PROMPT
        self.planner = planner_agent
        self.knowledge = knowledge_agent
        self.scheduler = scheduler_agent
    
    def classify_intent(self, message: str) -> Dict:
        """Classify the user's intent from their message."""
        
        prompt = f"""Analyze this student message and classify their intent.

MESSAGE: "{message}"

Respond with JSON only:
{{
    "primary_intent": "planning|knowledge|scheduling|general",
    "action": "specific action like create_plan|answer_question|get_tasks|reschedule|chat",
    "entities": {{
        "subject": "extracted subject if any",
        "topic": "extracted topic if any"
    }},
    "confidence": 0.0-1.0
}}"""

        try:
            response = llm_service.simple_completion(prompt=prompt, temperature=0.3)
            response = response.strip()
            if "```" in response:
                response = response.split("```")[1].replace("json", "").strip()
            
            import json
            return json.loads(response)
        except Exception:
            return {
                "primary_intent": "general",
                "action": "chat",
                "entities": {},
                "confidence": 0.5
            }
    
    def handle_request(
        self, user_id: int, message: str, 
        context: Optional[Dict] = None
    ) -> Dict:
        """Main entry point for handling user requests."""
        
        intent = self.classify_intent(message)
        intent_type = intent.get('primary_intent', 'general')
        action = intent.get('action', 'chat')
        entities = intent.get('entities', {})
        
        context = context or {}
        
        # Route to appropriate agent
        if intent_type == 'planning':
            return self._handle_planning(message, action, entities, context)
        
        elif intent_type == 'knowledge':
            return self._handle_knowledge(user_id, message, action, entities)
        
        elif intent_type == 'scheduling':
            return self._handle_scheduling(message, action, entities, context)
        
        else:
            return self._handle_general(message)
    
    def _handle_planning(
        self, message: str, action: str, entities: Dict, context: Dict
    ) -> Dict:
        """Handle planning-related requests."""
        
        if action == 'create_plan' and context.get('subjects'):
            result = self.planner.create_plan(
                subjects=context['subjects'],
                available_hours_per_day=context.get('hours_per_day', 4),
                exam_dates=context.get('exam_dates'),
                study_goals=context.get('goals')
            )
        elif action == 'suggest_topics' and entities.get('subject'):
            result = self.planner.suggest_topics(subject=entities['subject'])
        else:
            result = {
                "type": "planning_help",
                "message": "I can help you create a study plan. Please tell me:\n"
                          "1. What subjects you want to study\n"
                          "2. How many hours per day you can study\n"
                          "3. Any upcoming exam dates"
            }
        
        result['intent_type'] = 'planning'
        return result
    
    def _handle_knowledge(
        self, user_id: int, message: str, action: str, entities: Dict
    ) -> Dict:
        """Handle knowledge/question requests."""
        
        if action in ['answer_question', 'ask']:
            result = self.knowledge.answer_question(
                user_id=user_id,
                question=message,
                subject_filter=entities.get('subject')
            )
        elif action == 'explain':
            result = self.knowledge.explain_topic(
                user_id=user_id,
                topic=entities.get('topic', message)
            )
        elif action == 'quiz':
            result = self.knowledge.generate_quiz(
                user_id=user_id,
                topic=entities.get('topic', entities.get('subject', 'general'))
            )
        else:
            result = self.knowledge.answer_question(
                user_id=user_id,
                question=message
            )
        
        result['intent_type'] = 'knowledge'
        return result
    
    def _handle_scheduling(
        self, message: str, action: str, entities: Dict, context: Dict
    ) -> Dict:
        """Handle scheduling requests."""
        
        plan = context.get('current_plan', {})
        
        if action == 'get_tasks':
            result = self.scheduler.get_todays_tasks(
                plan=plan,
                current_date=context.get('date')
            )
        elif action == 'reschedule':
            result = self.scheduler.reschedule_task(
                plan=plan,
                skipped_task=context.get('skipped_task', {}),
                reason=context.get('reason', 'missed')
            )
        elif action == 'rebalance':
            result = self.scheduler.rebalance_schedule(
                plan=plan,
                changes=context.get('changes', {})
            )
        else:
            result = {
                "type": "scheduling_help",
                "message": "I can help you manage your schedule. I can:\n"
                          "- Show today's tasks\n"
                          "- Reschedule missed sessions\n"
                          "- Rebalance your study plan"
            }
        
        result['intent_type'] = 'scheduling'
        return result
    
    def _handle_general(self, message: str) -> Dict:
        """Handle general chat and study tips."""
        
        response = llm_service.simple_completion(
            prompt=message,
            system_prompt="You are a friendly study assistant. Help the student with their "
                         "question or provide motivation and study tips. Be encouraging and helpful.",
            temperature=0.7
        )
        
        return {
            "intent_type": "general",
            "type": "chat",
            "message": response
        }


coordinator_agent = CoordinatorAgent()
