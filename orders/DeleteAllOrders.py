import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId

# Load environment variables from .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
STORE_ID_STR = os.getenv("STORE_ID")

if not MONGO_URI or not STORE_ID_STR:
    print("Error: MONGO_URI and STORE_ID must be set in the .env file.")
    sys.exit(1)

try:
    STORE_ID = ObjectId(STORE_ID_STR)
except Exception as e:
    print(f"Error: Invalid STORE_ID format. It must be a 24-character hex string. Details: {e}")
    sys.exit(1)

def main():
    print("Connecting to MongoDB...")
    try:
        # Connect to MongoDB cluster
        client = MongoClient(MONGO_URI)
        
        # Test connection
        client.admin.command('ping')
        
        # Select database (it will use the one specified in your MONGO_URI)
        db = client.get_default_database() 
        
        # Target the orders collection
        orders_collection = db["orders"]

        print(f"Successfully connected to database: {db.name}")
        
        # Count orders before deletion for confirmation
        count_before = orders_collection.count_documents({"storeId": STORE_ID})
        
        if count_before == 0:
            print(f"No orders found for Store ID: {STORE_ID}. Nothing to delete.")
            return

        print(f"Found {count_before} orders for Store ID: {STORE_ID}.")
        
        # Confirm before deleting (Destructive action guardrail)
        print("\n" + "!"*50)
        print("WARNING: This action is irreversible!")
        print("!"*50)
        confirmation = input(f"Are you sure you want to delete ALL {count_before} orders? (yes/no): ").strip()
        
        if confirmation.lower() != 'yes':
            print("\nDeletion cancelled by user. No orders were harmed.")
            return

        print("\nDeleting orders...")
        
        # Perform the deletion
        result = orders_collection.delete_many({"storeId": STORE_ID})
        
        print(f"Success! Deleted {result.deleted_count} orders.")

    except ConnectionFailure:
        print("Error: Could not connect to MongoDB. Check your connection string and network access.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'client' in locals():
            client.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()