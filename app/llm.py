import ollama
from app.config import settings

class LLM:

    @staticmethod
    def chat(messages: list[dict]) -> str:
        response = ollama.chat(
            model=settings.MODEL,
            messages=messages,
            format="json",   # 🔥 FORCE JSON MODE
            options={
                "temperature": settings.TEMPERATURE
            }
        )

        return response["message"]["content"]