import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("Error: MONGO_URI must be set in the .env file.")
    sys.exit(1)

def generate_backup_folder_name() -> str:
    """Generates a folder name based on the exact UTC date and time."""
    now_utc = datetime.now(timezone.utc)
    # Format: YYYY-MM-DD_HH-MM-SS_UTC
    return now_utc.strftime("%Y-%m-%d_%H-%M-%S_UTC")

def run_backup() -> None:
    """Executes the mongodump command to backup the database."""
    base_backup_dir = Path("backups")
    base_backup_dir.mkdir(exist_ok=True)
    
    folder_name = generate_backup_folder_name()
    backup_path = base_backup_dir / folder_name
    
    print(f"Starting database backup...")
    print(f"Destination: {backup_path.resolve()}")
    
    # Construct the mongodump command
    # Passing the URI directly handles authentication and cluster connection routing
    command = [
        "mongodump",
        "--uri", MONGO_URI,
        "--out", str(backup_path)
    ]
    
    try:
        # Execute the command securely without shell=True to prevent injection
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print("\nBackup completed successfully!")
        print(f"Files are saved in: {backup_path}")
        
    except FileNotFoundError:
        print("\nError: 'mongodump' command not found.")
        print("Please ensure MongoDB Database Tools are installed and added to your system's PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("\nError: Backup process failed.")
        print(f"Exit code: {e.returncode}")
        print(f"Standard Error output:\n{e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_backup()