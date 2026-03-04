#!/usr/bin/env python3
"""
Check actual LLM configuration being loaded
"""
from packages.shared.config import Settings

settings = Settings()

print("=" * 80)
print("🔧 KIỂM TRA CẤU HÌNH LLM THỰC TẾ")
print("=" * 80)
print()

print("📋 ENV Variables:")
print(f"  SELECTED_LLM: {settings.selected_llm}")
print(f"  OPENAI_API_KEY: {settings.openai_api_key[:20] if settings.openai_api_key else 'NOT SET'}...")
print(f"  OPENAI_MODEL: {settings.openai_model}")
print()

print("📋 Worker AI Scout:")
print(f"  Provider: {settings.worker_ai_scout_provider}")
print(f"  Model: {settings.worker_ai_scout_model}")
print()

print("📋 Worker AI Verifier:")
print(f"  Provider: {settings.worker_ai_verifier_provider}")
print(f"  Model: {settings.worker_ai_verifier_model}")
print()

print("📋 API Key Analysis:")
if settings.openai_api_key:
    if settings.openai_api_key.startswith("gsk_"):
        print("  ⚠️  OPENAI_API_KEY starts with 'gsk_' - THIS IS A GROQ KEY!")
        print("  → This will cause auto-switch to Groq adapter!")
    elif settings.openai_api_key.startswith("sk-"):
        print("  ✓ OPENAI_API_KEY starts with 'sk-' - Valid OpenAI key")
    else:
        print(f"  ? Strange key format: {settings.openai_api_key[:10]}...")
else:
    print("  ❌ NO OPENAI_API_KEY SET")

print()
print("=" * 80)
print("🔍 PHÁT HIỆN VẤN ĐỀ:")
print("=" * 80)

# Check if there's a mismatch
if settings.worker_ai_scout_provider == "openai" and settings.openai_api_key and settings.openai_api_key.startswith("gsk_"):
    print("❌ CRITICAL BUG: Provider is 'openai' but key is Groq!")
    print("   → Code will auto-switch to Groq adapter in get_llm_adapter()")
    print("   → This causes 429 rate limit from Groq instead of using OpenAI")
    print()
    print("✅ GIẢI PHÁP:")
    print("   1. Check OPENAI_API_KEY in .env - must start with 'sk-'")
    print("   2. Make sure no GROQ_API_KEY is polluting OPENAI_API_KEY")
elif settings.worker_ai_scout_provider == "openai" and settings.openai_api_key and settings.openai_api_key.startswith("sk-"):
    print("✓ Configuration looks correct!")
    print("  Provider: openai")
    print("  Key: Valid OpenAI format")
else:
    print(f"? Investigate provider='{settings.worker_ai_scout_provider}' with key type")
