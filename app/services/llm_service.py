"""
LLM service for interacting with language models.
Uses httpx for direct API calls (no heavy SDK dependencies).
"""
from typing import Optional, List, Dict
import httpx
from app.config import OPENAI_API_KEY, GROQ_API_KEY, DEFAULT_LLM_MODEL


class LLMService:
    """Service for interacting with LLM providers via direct HTTP calls."""
    
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        
        if provider == "groq" and GROQ_API_KEY:
            self.api_key = GROQ_API_KEY
            self.base_url = "https://api.groq.com/openai/v1"
            self.default_model = "llama-3.3-70b-versatile"
        else:
            self.api_key = OPENAI_API_KEY
            self.base_url = "https://api.openai.com/v1"
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
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": full_messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
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
