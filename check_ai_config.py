#!/usr/bin/env python
"""
🔍 Check Current AI Configuration
Hiển thị mode, level, provider, và thông tin cấu hình hiện tại
"""

import sys
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))

from packages.shared.config import settings
from packages.shared.prompt_manager import PromptConfig, describe_configuration

def print_header(text: str):
    """Print formatted header"""
    print(f"\n╔{'═' * 60}╗")
    print(f"║ {text:<58} ║")
    print(f"╚{'═' * 60}╝")

def print_section(title: str):
    """Print section title"""
    print(f"\n📌 {title}")
    print("─" * 62)

def main():
    print_header("🤖 AI WORKER CONFIGURATION CHECK")

    # Current mode & level
    print_section("Current Configuration")
    print(f"Mode:                 {settings.worker_ai_mode}")
    print(f"Prompt Level:         {settings.worker_ai_prompt_level}")
    print(f"Use 2-Tier:           {settings.worker_ai_use_two_tier}")

    # Provider Info
    print_section("Provider Settings")
    print(f"Scout Provider:       {settings.worker_ai_scout_provider}")
    print(f"Scout Model:          {settings.worker_ai_scout_model}")
    print(f"Scout Confidence:     {settings.worker_ai_scout_confidence_threshold}")
    print()
    print(f"Verifier Provider:    {settings.worker_ai_verifier_provider}")
    print(f"Verifier Model:       {settings.worker_ai_verifier_model}")

    # Mode description
    print_section("What This Means")
    config = PromptConfig(
        mode=settings.worker_ai_mode,  # type: ignore
        prompt_level=settings.worker_ai_prompt_level  # type: ignore
    )

    mode_desc = {
        "two_tier_hybrid": """
🌐 TWO-TIER HYBRID (Cloud)
- Scout scans all symbols quickly (cheap model: gpt-3.5)
- Verifier makes final decision (expensive model: gpt-4)
- Auto-filters weak signals to save tokens
- Token cost: ~1,000-1,500 per run
- Best for: Cloud-based with budget constraints
        """,
        "two_tier_same": """
🖥️ TWO-TIER SAME (Local AI)
- Same local model does both scout & verifier roles
- Scout provides lightweight scanning
- Verifier provides detailed analysis
- Token cost: 0 (all local, no API calls)
- Best for: Local AI deployment, cost-free, privacy-first
        """,
        "single_tier": """
⚙️ SINGLE-TIER (One Model)
- Single model for all decisions
- No filtering, calls model for every symbol
- Higher token cost, simpler logic
- Best for: Simple setup, no multi-tier complexity
        """
    }
    
    level_desc = {
        "lightweight": """
⚡ LIGHTWEIGHT PROMPTS
- Minimal token usage per call
- 4-line market data input
- Fast processing (good for scan)
- Best for: Limited resources, quick scans
        """,
        "standard": """
📊 STANDARD PROMPTS (RECOMMENDED)
- Balanced token usage ↔ decision quality
- Full market context + position info
- Medium processing time
- Best for: Both cloud and local, general use
        """,
        "heavyweight": """
🔥 HEAVYWEIGHT PROMPTS
- Maximum analysis depth, no token limit
- Full trading context + technical analysis
- Longer processing time
- Best for: Powerful local AI, maximum quality
        """
    }

    print(mode_desc.get(settings.worker_ai_mode, "Unknown mode"))  # type: ignore
    print(level_desc.get(settings.worker_ai_prompt_level, "Unknown level"))  # type: ignore

    # Cost estimation
    print_section("Token Cost Estimation")
    
    token_estimates = {
        "two_tier_hybrid": {
            "lightweight": (400, "$0.0005"),
            "standard": (1000, "$0.001"),
            "heavyweight": (2500, "$0.0025"),
        },
        "two_tier_same": {
            "lightweight": (0, "$0.00"),
            "standard": (0, "$0.00"),
            "heavyweight": (0, "$0.00"),
        },
        "single_tier": {
            "lightweight": (600, "$0.0008"),
            "standard": (1500, "$0.002"),
            "heavyweight": (3000, "$0.004"),
        }
    }
    
    tokens, cost = token_estimates.get(settings.worker_ai_mode, {}).get(  # type: ignore
        settings.worker_ai_prompt_level, (0, "$0.00")  # type: ignore
    )
    
    print(f"Estimated tokens:     {tokens:,} per decision")
    print(f"Estimated cost:       {cost}")
    print(f"Cost/day (10 trades): {cost.replace('$', f'${float(cost[1:]) * 10:.2f}')}...")

    # Next steps
    print_section("Quick Actions")
    
    if settings.worker_ai_mode == "two_tier_hybrid":  # type: ignore
        print("""
✅ Current: Cloud 2-Tier (works well)

👉 Next Steps:
1. Continue monitoring token usage
2. When ready for local AI:
   - Set WORKER_AI_MODE=two_tier_same
   - Set WORKER_AI_SCOUT_PROVIDER=local
   - Set WORKER_AI_VERIFIER_PROVIDER=local
   - Restart worker

3. For maximum quality (no token limit):
   - Set WORKER_AI_PROMPT_LEVEL=heavyweight
   - Restart worker
        """)
    
    elif settings.worker_ai_mode == "two_tier_same":  # type: ignore
        print("""
✅ Current: Local 2-Tier (zero cost!)

👉 Next Steps:
1. Monitor decision quality vs cloud version
2. If PROMPT_LEVEL=standard:
   - Try PROMPT_LEVEL=heavyweight for better analysis
   - Monitor GPU/CPU usage
   
3. Fine-tune local model if needed
   - Adjust prompts in prompt_manager.py
   - Test with small batch first
        """)
    
    else:
        print("""
⚙️ Current: Single-Tier

👉 Recommendations:
1. Consider switching to 2-tier for filtering
2. If local AI available:
   - Set WORKER_AI_MODE=two_tier_same
   - Enable filtering to save tokens/resources
        """)

    # Footer
    print_section("Configuration Files")
    print(f".env:                   ~/.env (contains WORKER_AI_MODE, LEVEL)")
    print(f"Config module:          packages/shared/config.py")
    print(f"Prompt manager:         packages/shared/prompt_manager.py")
    print(f"Migration guide:        ./MIGRATION_TO_LOCAL_AI.md")

    print("\n" + "=" * 62)
    print("✅ Configuration check complete!")
    print("=" * 62 + "\n")

if __name__ == "__main__":
    main()
