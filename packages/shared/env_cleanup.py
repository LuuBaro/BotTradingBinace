#!/usr/bin/env python3
"""
Utility to clean up environment variables before Pydantic loads settings.
Run this FIRST before importing any settings-dependent modules.
"""

import os

def clean_environment():
    """Remove contaminated environment variables that would override .env settings."""
    
    # Check for Groq key in OPENAI_API_KEY
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key.startswith("gsk_"):
        print("WARNING: Found Groq key in OPENAI_API_KEY environment variable")
        print("  This would override .env settings and cause llm_adapter to fail")
        print("  Removing from os.environ...")
        del os.environ["OPENAI_API_KEY"]
        print("  [DONE] Removed contaminated OPENAI_API_KEY from os.environ")
        print("    Pydantic will now load from .env file instead")
    
    return True

if __name__ == "__main__":
    clean_environment()
    print("\n[OK] Environment cleanup complete!")
    
    # Verify
    from packages.shared.config import Settings
    settings = Settings()
    key_sample = settings.openai_api_key[:20] if settings.openai_api_key else "NOT SET"
    print(f"\nLoaded OPENAI_API_KEY: {key_sample}...")
    if settings.openai_api_key and settings.openai_api_key.startswith("sk-proj"):
        print("[OK] Correct OpenAI key detected!")
    elif settings.openai_api_key and settings.openai_api_key.startswith("gsk_"):
        print("[ERROR] Still has Groq key!")
