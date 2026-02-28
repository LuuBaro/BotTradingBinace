
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import TraderContext
from packages.shared.ai_orchestrator import AIOrchestrator
from packages.shared.llm_adapter import get_llm_adapter
from packages.shared.config import settings

async def check_intent():
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select, desc
        res = await session.execute(select(TraderContext).order_by(desc(TraderContext.timestamp)).limit(1))
        context = res.scalar_one_or_none()
        if not context:
            print("No context")
            return
            
        print(f"--- TRADER PROMPT ---\n{context.prompt}\n")
        
        llm = get_llm_adapter(
            provider=settings.selected_llm,
            api_key=settings.openai_api_key if settings.selected_llm in ('openai', 'groq') else settings.anthropic_api_key,
            model=settings.openai_model if settings.selected_llm in ('openai', 'groq') else settings.anthropic_model
        )
        orchestrator = AIOrchestrator(llm)
        intent = await orchestrator.parse_trader_intent(context.prompt)
        print("--- PARSED INTENT ---")
        import json
        print(json.dumps(intent, indent=2))

if __name__ == "__main__":
    asyncio.run(check_intent())
