#!/usr/bin/env python3
"""
Validate all configured LLM API keys and test connections
"""
import asyncio
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages"))

from shared.config import settings
from shared.llm_adapter import get_llm_adapter


async def validate_llm_key(provider: str, api_key: str | None, model: str | None) -> tuple[bool, str]:
    """Test connection for a specific LLM provider"""
    if not api_key:
        return False, f"❌ {provider.upper()}: No API key configured"
    
    try:
        adapter = get_llm_adapter(
            provider=provider,
            api_key=api_key,
            model=model or "gpt-4o-mini",
            temperature=0.3,
            max_tokens=100
        )
        
        if hasattr(adapter, 'validate_connection'):
            is_valid = await adapter.validate_connection()
            if is_valid:
                return True, f"✅ {provider.upper()}: Connection successful (Model: {model})"
            else:
                return False, f"❌ {provider.upper()}: Connection failed"
        else:
            # For adapters without validate_connection, try a test generation
            try:
                result = await adapter.generate(
                    prompt="Test",
                    system_prompt="You are a test.",
                    temperature=0.3,
                    max_tokens=10
                )
                if result:
                    return True, f"✅ {provider.upper()}: Generation successful (Model: {model})"
                return False, f"❌ {provider.upper()}: No response"
            except Exception as e:
                return False, f"❌ {provider.upper()}: {str(e)[:80]}"
    except Exception as e:
        return False, f"❌ {provider.upper()}: {str(e)[:80]}"


async def main():
    """Main validation function"""
    print("\n" + "="*60)
    print("LLM API KEY VALIDATION REPORT")
    print("="*60 + "\n")
    
    # Test all configured providers
    providers = [
        ("gemini", settings.bot_gemini_api_key, settings.gemini_model),
        ("openai", settings.bot_openai_api_key, settings.openai_model),
        ("anthropic", settings.bot_anthropic_api_key, settings.anthropic_model),
        ("groq", settings.bot_groq_api_key, settings.groq_model),
    ]
    
    results = []
    for provider, api_key, model in providers:
        print(f"Testing {provider.upper()}...", end=" ")
        is_valid, message = await validate_llm_key(provider, api_key, model)
        results.append((provider, is_valid, message))
        print(message)
    
    print("\n" + "="*60)
    print(f"SELECTED LLM: {settings.selected_llm.upper()}")
    print("="*60 + "\n")
    
    # Summary
    valid_count = sum(1 for _, is_valid, _ in results if is_valid)
    print(f"Valid Providers: {valid_count}/{len(results)}")
    
    selected = settings.selected_llm.lower()
    selected_msg = None
    for provider, is_valid, msg in results:
        if provider == selected:
            selected_msg = msg
            break
    
    if selected_msg:
        print(f"Current Selection: {selected_msg}")
    else:
        print(f"⚠️  SELECTED_LLM='{selected}' not recognized")
    
    print("\n" + "="*60)
    if valid_count > 0:
        print("✅ System is ready for production use")
        return 0
    else:
        print("❌ No valid LLM providers configured")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
