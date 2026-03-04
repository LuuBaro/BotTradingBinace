#!/usr/bin/env python3
"""Test what Pydantic Settings is actually loading."""

import os
import sys

# Check environment BEFORE loading Pydantic
print("="*80)
print("🔍 Environment variables BEFORE Pydantic loads:")
print("="*80)
print(f"WORKER_AI_SCOUT_PROVIDER from os.environ: {os.environ.get('WORKER_AI_SCOUT_PROVIDER', 'NOT SET')}")
print(f"WORKER_AI_SCOUT_MODEL from os.environ: {os.environ.get('WORKER_AI_SCOUT_MODEL', 'NOT SET')}")
print(f"OPENAI_API_KEY from os.environ: {os.environ.get('OPENAI_API_KEY', 'NOT SET')[:30]}...")

# Now load Pydantic Settings
print("\n" + "="*80)
print("🔍 Loading Pydantic Settings:")
print("="*80)

from packages.shared.config import Settings
settings = Settings()

print(f"\nsettings.worker_ai_scout_provider: {settings.worker_ai_scout_provider}")
print(f"settings.worker_ai_scout_model: {settings.worker_ai_scout_model}")
print(f"settings.openai_api_key: {settings.openai_api_key[:30] if settings.openai_api_key else 'NOT SET'}...")

# Compare with defaults
from packages.shared.config import Settings as SettingsClass
import inspect

sig = inspect.signature(SettingsClass)
print("\n" + "="*80)
print("🔍 Defaults in config.py:")
print("="*80)

# Check Field defaults
from packages.shared.config import Settings
fields = Settings.model_fields

if 'worker_ai_scout_provider' in fields:
    field = fields['worker_ai_scout_provider']
    print(f"worker_ai_scout_provider default: {field.default}")
    
if 'worker_ai_scout_model' in fields:
    field = fields['worker_ai_scout_model']
    print(f"worker_ai_scout_model default: {field.default}")
    
if 'openai_api_key' in fields:
    field = fields['openai_api_key']
    print(f"openai_api_key default: {field.default}")
