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
        
        # If your URI doesn't include the DB name, uncomment the line below and specify it:
        # db = client["your_database_name"] 
        
        products_collection = db["products"]

        print(f"Successfully connected to database: {db.name}")
        
        # Count products before deletion for confirmation
        count_before = products_collection.count_documents({"storeId": STORE_ID})
        
        if count_before == 0:
            print(f"No products found for Store ID: {STORE_ID}. Nothing to delete.")
            return

        print(f"Found {count_before} products for Store ID: {STORE_ID}.")
        
        # Confirm before deleting (optional but recommended for destructive actions)
        confirmation = input("Are you sure you want to delete all these products? (yes/no): ")
        
        if confirmation.lower() != 'yes':
            print("Deletion cancelled by user.")
            return

        print("Deleting products...")
        
        # Perform the deletion
        result = products_collection.delete_many({"storeId": STORE_ID})
        
        print(f"Success! Deleted {result.deleted_count} products.")

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