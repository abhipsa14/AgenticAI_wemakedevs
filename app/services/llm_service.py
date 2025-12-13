"""
LLM service for interacting with language models.
"""
from typing import Optional, List, Dict
from openai import OpenAI
from app.config import OPENAI_API_KEY, GROQ_API_KEY, DEFAULT_LLM_MODEL


class LLMService:
    """Service for interacting with LLM providers."""
    
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        
        if provider == "groq" and GROQ_API_KEY:
            self.client = OpenAI(
                api_key=GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
            self.default_model = "llama-3.1-70b-versatile"
        else:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            self.default_model = DEFAULT_LLM_MODEL
    
    def chat(
        self, messages: List[Dict[str, str]], model: Optional[str] = None,
        temperature: float = 0.7, max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """Send a chat completion request."""
        model = model or self.default_model
        
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM API error: {str(e)}")
    
    def simple_completion(
        self, prompt: str, system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Simple single-turn completion."""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages=messages, system_prompt=system_prompt, temperature=temperature)


# Global instance
llm_service = LLMService(
    provider="groq" if GROQ_API_KEY and not OPENAI_API_KEY else "openai"
)
