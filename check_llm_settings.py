"""
Check LLM Configuration & Status
"""
import asyncio
from packages.shared.config import settings
from packages.shared.database import init_db


async def check_llm():
    await init_db()
    
    print("="*70)
    print("🤖 LLM CONFIGURATION STATUS")
    print("="*70)
    
    print(f"\n✅ Active LLM: {settings.selected_llm}")
    print(f"✅ LLM Mode: {settings.worker_ai_mode}")
    print(f"✅ Prompt Level: {settings.worker_ai_prompt_level}")
    
    print(f"\n📌 OpenAI Config:")
    print(f"   • API Key: {'SET ✅' if settings.openai_api_key else 'NOT SET ❌'}")
    if settings.openai_api_key:
        key_preview = settings.openai_api_key[:20] + "..." + settings.openai_api_key[-5:]
        print(f"     Preview: {key_preview}")
    print(f"   • Model: {settings.openai_model}")
    
    print(f"\n📌 Anthropic Config:")
    print(f"   • API Key: {'SET ✅' if settings.anthropic_api_key else 'NOT SET ❌'}")
    print(f"   • Model: {settings.anthropic_api_key[:30]}..." if settings.anthropic_api_key else "")
    
    print(f"\n📌 2-Tier Mode:")
    print(f"   • Scout Provider: {settings.worker_ai_scout_provider}")
    print(f"   • Scout Model: {settings.worker_ai_scout_model}")
    print(f"   • Verifier Provider: {settings.worker_ai_verifier_provider}")
    print(f"   • Verifier Model: {settings.worker_ai_verifier_model}")
    print(f"   • Scout Threshold: {settings.worker_ai_scout_confidence_threshold}")
    
    print(f"\n📌 Rate Limiting:")
    print(f"   • Max Symbols/Loop: {settings.worker_ai_max_symbols_per_loop}")
    print(f"   • Min Interval: {settings.worker_ai_min_interval_ms}ms")
    print(f"   • Backoff Base: {settings.worker_ai_backoff_base_sec}s")
    
    print("\n" + "="*70)


asyncio.run(check_llm())
