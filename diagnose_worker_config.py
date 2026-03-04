#!/usr/bin/env python3
"""Check what settings the worker is actually loading."""

import os
import sys
from pathlib import Path

print("="*80)
print("🔍 Environment Variables Check:")
print("="*80)

# Check environment variables
openai_key_env = os.environ.get("OPENAI_API_KEY", "NOT SET")
print(f"OPENAI_API_KEY from os.environ: {openai_key_env[:30]}..." if len(openai_key_env) > 30 else f"OPENAI_API_KEY: {openai_key_env}")

llm_provider_env = os.environ.get("SELECTED_LLM", "NOT SET")
print(f"SELECTED_LLM from os.environ: {llm_provider_env}")

worker_scout_provider_env = os.environ.get("WORKER_AI_SCOUT_PROVIDER", "NOT SET") 
print(f"WORKER_AI_SCOUT_PROVIDER from os.environ: {worker_scout_provider_env}")

# Check .env file
print("\n" + "="*80)
print("🔍 .env File Check:")
print("="*80)

env_file = Path(".env")
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.startswith("OPENAI_API_KEY="):
                value = line.split("=", 1)[1].strip().strip("'\"")
                print(f"Found in .env: OPENAI_API_KEY={value[:30]}...")
            elif line.startswith("SELECTED_LLM="):
                value = line.split("=", 1)[1].strip().strip("'\"")
                print(f"Found in .env: SELECTED_LLM={value}")
            elif line.startswith("WORKER_AI_SCOUT_PROVIDER="):
                value = line.split("=", 1)[1].strip().strip("'\"")
                print(f"Found in .env: WORKER_AI_SCOUT_PROVIDER={value}")
else:
    print("❌ .env file not found!")

# Now load Pydantic Settings and check what it sees
print("\n" + "="*80)
print("🔍 Pydantic Settings Check:")
print("="*80)

try:
    from packages.shared.config import Settings
    settings = Settings()
    
    openai_key_config = settings.openai_api_key
    print(f"settings.openai_api_key: {openai_key_config[:30]}..." if openai_key_config and len(str(openai_key_config)) > 30 else f"settings.openai_api_key: {openai_key_config}")
    
    selected_llm = settings.selected_llm
    print(f"settings.selected_llm: {selected_llm}")
    
    scout_provider = settings.worker_ai_scout_provider
    print(f"settings.worker_ai_scout_provider: {scout_provider}")
    
    verifier_provider = settings.worker_ai_verifier_provider  
    print(f"settings.worker_ai_verifier_provider: {verifier_provider}")
    
    # Check if OpenAI key contains Groq prefix
    if openai_key_config and openai_key_config.startswith("gsk_"):
        print(f"\n⚠️ CRITICAL: OpenAI key starts with 'gsk_' - THIS IS A GROQ KEY!")
    elif openai_key_config and openai_key_config.startswith("sk-proj"):
        print(f"\n✅ GOOD: OpenAI key starts with 'sk-proj' - CORRECT FORMAT!")
 
except Exception as e:
    print(f"❌ Error loading Pydantic Settings: {e}")
    import traceback
    traceback.print_exc()

# Check get_llm_adapter behavior
print("\n" + "="*80)
print("🔍 LLM Adapter Type Check:")
print("="*80)

try:
    from packages.shared.llm_adapter import get_llm_adapter
    
    # Test what would happen with current settings
    from packages.shared.config import Settings
    settings = Settings()
    
    adapter = get_llm_adapter(
        provider=settings.worker_ai_scout_provider,
        api_key=settings.openai_api_key,
        model="gpt-3.5-turbo"
    )
    
    adapter_type = type(adapter).__name__
    print(f"get_llm_adapter() returned: {adapter_type}")
    
    if "Groq" in adapter_type:
        print(f"⚠️ PROBLEM: Auto-detected Groq provider (model has gsk_ prefix?)")
    elif "OpenAI" in adapter_type:
        print(f"✅ GOOD: Using OpenAI provider")
    
except Exception as e:
    print(f"❌ Error creating adapter: {e}")
    import traceback
    traceback.print_exc()
