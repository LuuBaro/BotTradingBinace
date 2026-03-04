"""
Check what Python processes are doing
"""
import psutil
import json

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'python' in proc.info['name'].lower():
            cmdline = proc.info['cmdline']
            if cmdline and len(cmdline) > 1:
                # Filter out this check script itself
                cmd_str = ' '.join(cmdline)
                if 'check_processes' not in cmd_str:
                    print(f"\nPID {proc.info['pid']}:")
                    print(f"  Command: {' '.join(cmdline[:3])}")
                    if 'uvicorn' in cmd_str:
                        print("  → BACKEND (API)")
                    elif 'worker' in cmd_str.lower() or 'main.py' in cmd_str:
                        print("  → WORKER")
                    elif 'dashboard' in cmd_str or 'npm' in cmd_str or 'vite' in cmd_str:
                        print("  → FRONTEND")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
