"""
Script to switch user from TESTNET to MAINNET
Run this to connect the bot to your real Binance account
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from packages.shared.database import AsyncSessionFactory
from packages.shared.models import UserCredential
from sqlalchemy import select

async def switch_to_mainnet():
    print("=" * 80)
    print("SWITCH TO MAINNET")
    print("=" * 80)
    
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(UserCredential))
        creds = result.scalars().all()
        
        if not creds:
            print("\n❌ No user credentials found")
            return
        
        print(f"\nFound {len(creds)} users. Switching all to MAINNET...")
        
        for cred in creds:
            print(f"\n  User: {cred.user_id}")
            print(f"  Current: {'TESTNET' if cred.use_testnet else 'MAINNET'}")
            
            if cred.use_testnet:
                cred.use_testnet = False
                print(f"  → Changed to: MAINNET")
            else:
                print(f"  → Already on MAINNET")
        
        await session.commit()
        
        print("\n" + "=" * 80)
        print("✅ ALL USERS SWITCHED TO MAINNET")
        print("=" * 80)
        print("\nIMPORTANT:")
        print("1. Make sure your API keys are for MAINNET (not testnet)")
        print("2. Restart the backend: .\surgical_restart.ps1")
        print("3. Check wallet balance - should now show ~$10k from mainnet")
        print("4. All trades will now be executed on your REAL Binance account")
        print("\n⚠️  WARNING: This uses REAL money. Test carefully!")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(switch_to_mainnet())
