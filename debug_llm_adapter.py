#!/usr/bin/env python
"""Debug script to check LLM adapter initialization"""
import os
import sys
from packages.shared.config import settings
from packages.shared.llm_adapter import get_llm_adapter

print("\n=== DEBUGGING LLM ADAPTER ===\n")

# Check what settings are loaded
print("Settings loaded from .env:")
print(f"  SELECTED_LLM: {settings.selected_llm}")
print(f"  OPENAI_API_KEY: {settings.openai_api_key[:30] if settings.openai_api_key else 'None'}...")
print(f"  OPENAI_MODEL: {settings.openai_model}")
print(f"  WORKER_AI_USE_TWO_TIER: {settings.worker_ai_use_two_tier}")
print(f"  WORKER_AI_SCOUT_PROVIDER: {settings.worker_ai_scout_provider}")
print(f"  WORKER_AI_SCOUT_MODEL: {settings.worker_ai_scout_model}")
print(f"  WORKER_AI_VERIFIER_PROVIDER: {settings.worker_ai_verifier_provider}")
print(f"  WORKER_AI_VERIFIER_MODEL: {settings.worker_ai_verifier_model}")

# Check environment variables
print("\nEnvironment variables:")
print(f"  OPENAI_API_KEY from os.getenv: {os.getenv('OPENAI_API_KEY', 'Not set')[:30]}...")
print(f"  WORKER_AI_SCOUT_PROVIDER from os.getenv: {os.getenv('WORKER_AI_SCOUT_PROVIDER', 'Not set')}")

# Test get_llm_adapter with scout config
print("\nTesting get_llm_adapter for Scout:")
try:
    scout_llm = get_llm_adapter(
        provider=settings.worker_ai_scout_provider,
        api_key=settings.openai_api_key if settings.worker_ai_scout_provider in ('openai', 'groq') else None,
        model=settings.worker_ai_scout_model
    )
    print(f"  ✅ Scout adapter type: {type(scout_llm).__name__}")
    print(f"  Scout model: {scout_llm.model}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test get_llm_adapter with verifier config
print("\nTesting get_llm_adapter for Verifier:")
try:
    verifier_llm = get_llm_adapter(
        provider=settings.worker_ai_verifier_provider,
        api_key=settings.openai_api_key if settings.worker_ai_verifier_provider in ('openai', 'groq') else None,
        model=settings.worker_ai_verifier_model
    )
    print(f"  ✅ Verifier adapter type: {type(verifier_llm).__name__}")
    print(f"  Verifier model: {verifier_llm.model}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n=== END DEBUG ===\n")
