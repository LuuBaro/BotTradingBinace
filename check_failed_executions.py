"""
Kiểm tra tại sao execution decisions thất bại
"""
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select, desc
from packages.shared.models import Decision
from datetime import datetime, timedelta

async def check_failed_decisions():
    async with AsyncSessionFactory() as session:
        print("\n" + "="*60)
        print("PHAN TICH DECISIONS THAT BAI")
        print("="*60)
        
        # Get failed decisions from last 2 hours
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        result = await session.execute(
            select(Decision)
            .where(Decision.timestamp >= two_hours_ago)
            .where(Decision.status.in_(['FAILED', 'REJECTED']))
            .order_by(desc(Decision.timestamp))
            .limit(10)
        )
        failed_decisions = result.scalars().all()
        
        print(f"\nFound {len(failed_decisions)} failed/rejected decisions in last 2 hours:\n")
        
        for d in failed_decisions:
            print(f"[{d.timestamp.strftime('%H:%M:%S')}] {d.decision_type} - {d.status}")
            print(f"  Trace ID: {d.trace_id}")
            print(f"  Rationale: {d.rationale[:100] if d.rationale else 'N/A'}...")
            
            # Execution details
            if d.execution_error:
                print(f"  ❌ EXECUTION ERROR: {d.execution_error}")
            
            if d.execution_status:
                print(f"  Execution Status: {d.execution_status}")
            
            if d.order_id:
                print(f"  Order ID: {d.order_id}")
            
            # Risk approval
            if d.risk_passed is False:
                print(f"  ⚠️  RISK FAILED: {d.risk_approval_reason or 'Unknown reason'}")
            
            # Validation errors
            if d.validation_errors:
                print(f"  ⚠️  VALIDATION ERRORS: {d.validation_errors}")
            
            print()
        
        print("\n" + "="*60)
        print("KET LUAN")
        print("="*60)
        
        # Analyze common errors
        execution_errors = [d.execution_error for d in failed_decisions if d.execution_error]
        validation_errors = [d.validation_errors for d in failed_decisions if d.validation_errors]
        risk_failures = [d for d in failed_decisions if d.risk_passed is False]
        
        if execution_errors:
            print(f"\n❌ EXECUTION ERRORS ({len(execution_errors)} cases):")
            for err in set(execution_errors):
                print(f"  - {err}")
        
        if validation_errors:
            print(f"\n❌ VALIDATION ERRORS ({len(validation_errors)} cases):")
            for err in validation_errors:
                print(f"  - {err}")
        
        if risk_failures:
            print(f"\n❌ RISK FAILURES ({len(risk_failures)} cases):")
            for d in risk_failures:
                print(f"  - {d.risk_approval_reason or 'Unknown'}")
        
        if not execution_errors and not validation_errors and not risk_failures:
            print("\n⚠️  NO DETAILED ERROR INFO AVAILABLE")
            print("  Possible causes:")
            print("  1. Worker exception before saving error details")
            print("  2. Execution engine not properly logging failures")
            print("  3. Database not recording full error context")

if __name__ == "__main__":
    asyncio.run(check_failed_decisions())
