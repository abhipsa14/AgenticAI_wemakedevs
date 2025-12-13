"""
Knowledge Agent - Answers questions using RAG from uploaded notes.
"""
from typing import Optional, List, Dict
from app.services.llm_service import llm_service
from app.services.vector_store import vector_store


KNOWLEDGE_SYSTEM_PROMPT = """You are a helpful study assistant that answers student questions 
using their own notes and study materials. You have been provided with relevant excerpts 
from the student's uploaded documents.

GUIDELINES:
1. Base your answers primarily on the provided context from the student's notes
2. If the context doesn't contain enough information, say so clearly
3. Explain concepts in a clear, student-friendly way
4. Use examples where helpful
5. If you reference information from the notes, mention it
6. Suggest related topics the student might want to review

If no relevant context is found, still try to help but note that this is general knowledge, 
not from their specific notes."""


class KnowledgeAgent:
    """Agent for answering questions using RAG."""
    
    def __init__(self):
        self.system_prompt = KNOWLEDGE_SYSTEM_PROMPT
    
    def answer_question(
        self, user_id: int, question: str, 
        subject_filter: Optional[str] = None,
        include_sources: bool = True
    ) -> Dict:
        """Answer a question using RAG from the user's documents."""
        
        # Search for relevant context
        search_results = vector_store.search(
            user_id=user_id,
            query=question,
            n_results=5,
            subject_filter=subject_filter
        )
        
        # Build context from results
        context_parts = []
        sources = []
        
        for i, result in enumerate(search_results):
            if result.get('relevance_score', 0) > 0.3:
                context_parts.append(f"[Source {i+1}]: {result['text']}")
                sources.append({
                    'filename': result['metadata'].get('filename', 'Unknown'),
                    'subject': result['metadata'].get('subject', 'general'),
                    'relevance': round(result.get('relevance_score', 0), 2)
                })
        
        context = "\n\n".join(context_parts) if context_parts else "No relevant notes found."
        
        prompt = f"""STUDENT'S QUESTION:
{question}

RELEVANT CONTEXT FROM NOTES:
{context}

Please answer the question based on the provided context. If the context doesn't fully 
address the question, supplement with general knowledge but indicate which parts come 
from the notes vs general knowledge."""

        try:
            answer = llm_service.simple_completion(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.5
            )
            
            result = {
                "success": True,
                "answer": answer,
                "context_used": bool(context_parts),
                "num_sources": len(sources)
            }
            
            if include_sources:
                result["sources"] = sources
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def explain_topic(self, user_id: int, topic: str, depth: str = "detailed") -> Dict:
        """Provide an explanation of a topic using the user's notes."""
        
        search_results = vector_store.search(user_id=user_id, query=topic, n_results=5)
        
        context_parts = []
        for result in search_results:
            if result.get('relevance_score', 0) > 0.3:
                context_parts.append(result['text'])
        
        context = "\n\n".join(context_parts) if context_parts else ""
        
        context_section = f"\n\nFROM YOUR NOTES:\n{context}" if context else ""
        
        prompt = f"""Explain the topic: "{topic}"

Depth level: {depth} (brief/moderate/detailed)
{context_section}

Provide a clear, well-structured explanation. Include:
1. Definition/Overview
2. Key concepts
3. Examples if helpful
4. How it connects to related topics"""

        try:
            explanation = llm_service.simple_completion(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.5
            )
            
            return {
                "success": True,
                "explanation": explanation,
                "topic": topic,
                "used_notes": bool(context_parts)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_quiz(self, user_id: int, topic: str, num_questions: int = 5) -> Dict:
        """Generate quiz questions based on the topic and user's notes."""
        
        search_results = vector_store.search(user_id=user_id, query=topic, n_results=5)
        
        context_parts = [r['text'] for r in search_results if r.get('relevance_score', 0) > 0.3]
        context = "\n\n".join(context_parts) if context_parts else ""
        
        prompt = f"""Generate {num_questions} quiz questions about: "{topic}"

{"Based on these notes:\n" + context if context else ""}

Return as JSON:
{{
    "topic": "{topic}",
    "questions": [
        {{
            "question": "Question text",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Why this is correct"
        }}
    ]
}}"""

        try:
            response = llm_service.simple_completion(prompt=prompt, temperature=0.7)
            response = response.strip()
            if "```" in response:
                response = response.split("```")[1].replace("json", "").strip()
            
            import json
            quiz = json.loads(response)
            quiz['success'] = True
            return quiz
        except Exception as e:
            return {"success": False, "error": str(e)}


knowledge_agent = KnowledgeAgent()
