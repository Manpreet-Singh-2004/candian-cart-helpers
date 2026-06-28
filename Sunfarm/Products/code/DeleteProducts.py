import os
import sys
import csv
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Load environment variables from .env file
load_dotenv()

# Retrieve variables as requested
MONGO_URI = os.getenv("MONGO_URI_PRODUCTION")
DB_NAME = os.getenv("DB_NAME_IN_PROD")

if not MONGO_URI or not DB_NAME:
    print("Error: MONGO_URI and DB_NAME_IN_DEV must be set in the .env file.")
    sys.exit(1)

def main():
    print("Connecting to MongoDB...")
    try:
        # Connect to MongoDB cluster
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        db = client[DB_NAME]
        products_collection = db["products"]

        print(f"Successfully connected to database: {db.name}")

        # --- Define Deletion Criteria ---
        # 1. isAvailable MUST be False.
        # 2. It must NOT have images (the images array is missing, null, or empty).
        delete_query = {
            "isAvailable": False,
            "$or": [
                {"images": {"$exists": False}}, 
                {"images": None},
                {"images": {"$size": 0}}
            ]
        }

        print("\nScanning for products that match the deletion criteria...")
        
        # Fetch all matching documents to extract them to CSV
        products_to_delete = list(products_collection.find(delete_query))
        count = len(products_to_delete)

        if count == 0:
            print("No products found matching the deletion criteria. Nothing to do. Exiting.")
            return

        # --- 1. Extract to CSV ---
        csv_filename = "products_to_delete_backup.csv"
        print(f"Found {count} products. Extracting data to {csv_filename}...")
        
        # Dynamically gather all unique keys to use as CSV headers
        headers = set()
        for p in products_to_delete:
            headers.update(p.keys())
        headers = list(headers)

        with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            
            for p in products_to_delete:
                # Convert complex MongoDB types (like ObjectId and Datetime) to strings so CSV can save them
                row = {key: str(value) for key, value in p.items()}
                writer.writerow(row)
                
        print(f"Successfully saved {count} products to {csv_filename}.")

        # --- 2. Ask for Permission to Delete ---
        print("\n" + "!" * 60)
        print(f"WARNING: You are about to permanently delete {count} products.")
        print("!" * 60)
        
        confirmation = input(f"Are you sure you want to delete these {count} products from the DB? (yes/no): ").strip().lower()

        if confirmation == 'yes':
            print("\nDeleting products...")
            result = products_collection.delete_many(delete_query)
            print(f"Success! Permanently deleted {result.deleted_count} products.")
        else:
            print("\nDeletion cancelled by user. The database was NOT touched.")

    except ConnectionFailure:
        print("Error: Could not connect to MongoDB. Check your connection string and network access.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'client' in locals():
            client.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()