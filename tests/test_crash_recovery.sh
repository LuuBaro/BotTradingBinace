#!/bin/bash
# Crash Recovery Test
# Tests that the system can recover from unexpected shutdown without duplicates

echo "🧪 Crash Recovery Test"
echo "======================"
echo ""

# Start worker in background
echo "Starting worker..."
python apps/worker/main.py &
WORKER_PID=$!

# Wait for worker to process some decisions
echo "Worker running (PID: $WORKER_PID)"
echo "Waiting 30 seconds for initial processing..."
sleep 30

# Check initial state
echo ""
echo "Checking initial state..."
python scripts/verify_phase1.py

# Kill worker abruptly (simulate crash)
echo ""
echo "Simulating crash (killing worker)..."
kill -9 $WORKER_PID
sleep 2

# Restart worker
echo ""
echo "Restarting worker..."
python apps/worker/main.py &
WORKER_PID=$!

# Wait for recovery
echo "Worker restarted (PID: $WORKER_PID)"
echo "Waiting 30 seconds for recovery..."
sleep 30

# Verify no duplicates
echo ""
echo "Verifying no duplicates after crash..."
python scripts/verify_phase1.py

# Check for duplicate orders
echo ""
echo "Checking for duplicate client_order_ids..."
python -c "
import asyncio
from sqlalchemy import select, func
from packages.shared.database import AsyncSessionFactory
from packages.shared.models import Order

async def check_duplicates():
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Order.client_order_id, func.count(Order.client_order_id))
            .group_by(Order.client_order_id)
            .having(func.count(Order.client_order_id) > 1)
        )
        duplicates = result.all()
        
        if duplicates:
            print(f'❌ FAIL: Found {len(duplicates)} duplicate orders!')
            for dup in duplicates:
                print(f'  - {dup[0]}: {dup[1]} occurrences')
            return False
        else:
            print('✅ PASS: No duplicate orders found')
            return True

result = asyncio.run(check_duplicates())
exit(0 if result else 1)
"

DUPLICATES_CHECK=$?

# Stop worker
echo ""
echo "Stopping worker..."
kill $WORKER_PID 2>/dev/null
wait $WORKER_PID 2>/dev/null

echo ""
echo "======================"
if [ $DUPLICATES_CHECK -eq 0 ]; then
    echo "✅ Crash Recovery Test PASSED"
    echo "System is crash-safe!"
else
    echo "❌ Crash Recovery Test FAILED"
    echo "Found duplicate orders after crash recovery"
    exit 1
fi
