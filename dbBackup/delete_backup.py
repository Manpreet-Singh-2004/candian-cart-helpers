import os
import shutil
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

def parse_and_convert_time(folder_name: str) -> str:
    """Parses the UTC folder name and converts it to Vancouver time for display."""
    try:
        # Expected format: 2026-03-30_17-50-00_UTC
        time_str = folder_name.replace("_UTC", "")
        
        # 1. Parse string into a datetime object
        dt_unaware = datetime.strptime(time_str, "%Y-%m-%d_%H-%M-%S")
        
        # 2. Assign the UTC timezone to it since we know it was saved in UTC
        dt_utc = dt_unaware.replace(tzinfo=ZoneInfo("UTC"))
        
        # 3. Convert to Vancouver time (handles Daylight Saving Time automatically)
        dt_van = dt_utc.astimezone(ZoneInfo("America/Vancouver"))
        
        # 4. Format nicely (e.g., "March 30, 2026 at 10:50:00 AM")
        return dt_van.strftime("%B %d, %Y at %I:%M:%S %p")
    except Exception:
        # If it doesn't match our specific pattern, ignore the folder
        return None

def main():
    # Because we run this from menu.py, the working directory is the root folder.
    # Therefore, we look inside the 'backups' folder relative to the root.
    base_backup_dir = Path("backups")
    
    if not base_backup_dir.exists() or not base_backup_dir.is_dir():
        print("\n[!] No 'backups' directory found. Have you created a backup yet?")
        return

    # List all directories inside backups/
    folders = [f for f in base_backup_dir.iterdir() if f.is_dir()]
    
    valid_backups = []
    for f in folders:
        display_time = parse_and_convert_time(f.name)
        if display_time:
            valid_backups.append({
                "path": f, 
                "raw_name": f.name, 
                "display": display_time
            })
            
    if not valid_backups:
        print("\n[!] No valid MongoDB backups found in the folder.")
        return

    # Sort backups from newest to oldest
    valid_backups.sort(key=lambda x: x["raw_name"], reverse=True)

    # Print the options
    print("\n=== Select a Backup to Delete ===")
    for idx, backup in enumerate(valid_backups, start=1):
        print(f"[{idx}] {backup['display']} (Vancouver Time)")
        print(f"    Folder: {backup['raw_name']}")
    print("[0] Cancel and go back")

    choice = input("\nEnter the number to delete (or 0 to cancel): ").strip()

    if choice == '0':
        print("\nAction cancelled.")
        return

    try:
        choice_idx = int(choice) - 1
        if choice_idx < 0 or choice_idx >= len(valid_backups):
            print("\n[!] Invalid selection.")
            return
            
        selected_backup = valid_backups[choice_idx]
        
        # Confirmation guardrail
        confirm = input(f"\nAre you SURE you want to delete the backup from '{selected_backup['display']}'? (y/n): ").strip().lower()
        
        if confirm == 'y':
            print(f"\nDeleting '{selected_backup['path']}'...")
            # shutil.rmtree securely removes a folder and all its contents
            shutil.rmtree(selected_backup['path'])
            print("Successfully deleted!")
        else:
            print("\nDeletion cancelled.")
            
    except ValueError:
        print("\n[!] Please enter a valid number.")

if __name__ == "__main__":
    main()