import os
import sys
import subprocess

def run_script(script_path: str) -> None:
    """Helper to run a python script using the current virtual environment."""
    if not os.path.exists(script_path):
        print(f"\n[!] Error: Could not find script at '{script_path}'")
        return
    
    print(f"\n>>> Starting {script_path}...\n")
    try:
        # sys.executable ensures we use the Python from the active virtual env
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Script exited with an error code: {e.returncode}")
    except KeyboardInterrupt:
        print("\n[!] Script execution cancelled by user.")
    print("\n" + "="*50)

def products_menu():
    """Sub-menu for managing products."""
    while True:
        print("\n--- Products Menu ---")
        print("1. Add Products")
        print("2. Delete Products")
        print("3. Go Back to Main Menu")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            run_script(os.path.join("products", "AddProducts.py"))
        elif choice == '2':
            run_script(os.path.join("products", "DeleteProducts.py"))
        elif choice == '3':
            break
        else:
            print("\n[!] Invalid choice. Please select 1, 2, or 3.")

def dbBackup_menu():
    """Sub-menu for database backup options."""
    while True:
        print("\n--- DB Backup Menu ---")
        print("1. Backup MongoDB")
        print("2. Delete a MongoDB Local Backup")
        print("3. Go Back to Main Menu")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            run_script(os.path.join("dbBackup", "backup_db.py"))
        elif choice == '2':
            run_script(os.path.join("dbBackup", "delete_backup.py"))
        elif choice == '3':
            break
        else:
            print("\n[!] Invalid choice. Please select 1, 2, or 3.")

def main():
    """Main CLI menu."""
    while True:
        print("\n=== Canadian Cart Helpers - Main Menu ===")
        print("1. DB Backup")
        print("2. Manage Products")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            dbBackup_menu() # Fixed: This now routes to the dbBackup sub-menu
        elif choice == '2':
            products_menu()
        elif choice == '3':
            print("\nExiting. Have a great day!")
            sys.exit(0)
        else:
            print("\n[!] Invalid choice. Please select 1, 2, or 3.")

if __name__ == "__main__":
    # Ensures the script resolves relative paths correctly by changing 
    # the working directory to where menu.py is located.
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting. Have a great day!")
        sys.exit(0)