
from packages.shared.config import settings
print(f"Selected LLM: {settings.selected_llm}")
print(f"OpenAI Model: {settings.openai_model}")
print(f"Anthropic Model: {settings.anthropic_model}")
import os
print(f"ENV OPENAI_MODEL: {os.getenv('OPENAI_MODEL')}")
