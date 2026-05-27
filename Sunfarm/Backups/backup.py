import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define environments to map folders to their respective URIs
ENVIRONMENTS = {
    "dev": os.getenv("MONGO_URI"),
    "prod": os.getenv("MONGO_URI_PRODUCTION")
}

# Pre-flight check: ensure both URIs exist before doing anything
missing_vars = [key for key, val in ENVIRONMENTS.items() if not val]
if missing_vars:
    print(f"FATAL ERROR: Missing environment variables for {', '.join(missing_vars)}.")
    print("Ensure MONGO_URI and MONGO_URI_PRODUCTION are set in your .env file.")
    sys.exit(1)

def generate_backup_folder_name() -> str:
    """Generates a synchronized folder name based on the exact UTC date and time."""
    now_utc = datetime.now(timezone.utc)
    # Format: YYYY-MM-DD_HH-MM-SS_UTC
    return now_utc.strftime("%Y-%m-%d_%H-%M-%S_UTC")

def run_backup() -> None:
    """Executes the mongodump command to backup databases sequentially."""
    
    # Generate ONE timestamp so dev and prod backups sync up perfectly
    folder_name = generate_backup_folder_name()
    
    for env_name, uri in ENVIRONMENTS.items():
        print(f"\n--- Starting {env_name.upper()} backup ---")
        
        # Target path: e.g., dev/2026-05-27_12-14-00_UTC
        backup_path = Path(env_name) / folder_name
        
        # exist_ok=True and parents=True ensures the dev/prod folders are created if missing
        backup_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Destination: {backup_path.resolve()}")
        
        # Construct the mongodump command
        command = [
            "mongodump",
            "--uri", uri,
            "--out", str(backup_path)
        ]
        
        try:
            # Execute securely
            result = subprocess.run(
                command, 
                check=True, 
                capture_output=True, 
                text=True
            )
            print(f"SUCCESS: {env_name.upper()} backup completed!")
            print(f"Files saved in: {backup_path}")
            
        except FileNotFoundError:
            print("\nFATAL ERROR: 'mongodump' command not found.")
            print("Ensure MongoDB Database Tools are installed and added to your system's PATH.")
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"\nFATAL ERROR: {env_name.upper()} backup process failed.")
            print(f"Exit code: {e.returncode}")
            print(f"Standard Error output:\n{e.stderr}")
            sys.exit(1)
        except Exception as e:
            print(f"\nFATAL CRASH during {env_name.upper()} backup: {e}")
            sys.exit(1)

if __name__ == "__main__":
    run_backup()