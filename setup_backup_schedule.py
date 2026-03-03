#!/usr/bin/env python3
"""
Setup Automated Database Backups
Configure Windows Task Scheduler for hourly backups
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def setup_scheduled_backup():
    """Setup Windows Task Scheduler for automated backups"""
    print("\n" + "="*60)
    print("AUTOMATED BACKUP SCHEDULER SETUP")
    print("="*60 + "\n")
    
    # Get script paths
    project_root = Path(__file__).parent
    backup_script = project_root / "backup_database.py"
    python_exe = project_root / ".venv" / "Scripts" / "python.exe"
    
    if not backup_script.exists():
        print("❌ ERROR: backup_database.py not found")
        return 1
    
    if not python_exe.exists():
        print("❌ ERROR: Python executable not found in .venv")
        return 1
    
    # Task name
    task_name = "TradingBot-DatabaseBackup"
    
    print("Configuration:")
    print(f"  Task Name: {task_name}")
    print(f"  Script: {backup_script}")
    print(f"  Python: {python_exe}")
    print(f"  Frequency: Every hour")
    print(f"  Time: Every hour at :00 (00:00, 01:00, 02:00, etc.)")
    print()
    
    # Build command
    command = f'"{python_exe}" "{backup_script}"'
    
    # Build task scheduler command
    schtasks_cmd = [
        "schtasks",
        "/create",
        "/tn", task_name,
        "/tr", command,
        "/sc", "hourly",
        "/mo", "1",
        "/st", "00:00:00",
        "/f",  # Force create
        "/rl", "highest"  # Run with highest privileges
    ]
    
    print("Creating scheduled task...")
    print()
    
    try:
        result = subprocess.run(
            schtasks_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        print("✅ Scheduled task created successfully!")
        print()
        
        # Verify the task was created
        verify_cmd = ["schtasks", "/query", "/tn", task_name]
        verify_result = subprocess.run(
            verify_cmd,
            capture_output=True,
            text=True
        )
        
        if verify_result.returncode == 0:
            print("Scheduled Task Details:")
            print("-" * 60)
            print(verify_result.stdout)
            print()
            
            print("Backup Schedule:")
            print("  - Runs every hour")
            print("  - Automatic cleanup of backups older than 30 days")
            print("  - Maximum 90 recent backups retained")
            print("  - Compressed storage (gzip format)")
            print()
            
            print("Manual Operations:")
            print("-" * 60)
            print(f"  View task: schtasks /query /tn {task_name}")
            print(f"  Run now: schtasks /run /tn {task_name}")
            print(f"  Delete: schtasks /delete /tn {task_name} /f")
            print()
            
            print("Backup & Recovery:")
            print("-" * 60)
            print(f"  Backup location: {project_root}/backups/")
            print(f"  Manual backup: python backup_database.py")
            print(f"  View backups: ls backups/")
            print(f"  Restore: python restore_database.py <backup_file>")
            print()
            
            print("="*60)
            print("✅ Database Backup System is Ready!")
            print("="*60 + "\n")
            
            return 0
        else:
            print("⚠️  Warning: Could not verify task creation")
            print(verify_result.stderr)
            return 0
            
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: Failed to create scheduled task")
        print(f"  Command: {' '.join(e.cmd)}")
        print(f"  Error: {e.stderr}")
        print()
        print("Manual Alternative:")
        print("  If Task Scheduler fails, you can manually run backups with:")
        print(f"    python backup_database.py")
        print()
        return 1
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = setup_scheduled_backup()
    sys.exit(exit_code)
