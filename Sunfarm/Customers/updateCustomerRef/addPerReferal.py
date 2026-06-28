import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

# Load environment variables from .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI_PRODUCTION")
DB_NAME = os.getenv("DB_NAME_IN_PROD")

if not MONGO_URI or not DB_NAME:
    print("Error: MONGO_URI_PRODUCTION and DB_NAME_IN_PROD must be set in the .env file.")
    sys.exit(1)

def main():
    print("Connecting to MongoDB...")
    try:
        # Connect to MongoDB cluster
        client = MongoClient(MONGO_URI)
        
        # Test connection
        client.admin.command('ping')
        
        # Select database specified by the environment variable
        db = client[DB_NAME] 
        customers_collection = db["customers"]

        print(f"Successfully connected to database: {db.name}")
        
        # Define the filter criteria: placedFirstOrder is true AND referralCodeEnabled is true
        query_filter = {
            "placedFirstOrder": True,
            "referralCodeEnabled": True
        }
        
        # 1. Count matching documents before updating
        print("Searching for matching customers...")
        match_count = customers_collection.count_documents(query_filter)
        
        # If no documents match, we can exit early
        if match_count == 0:
            print("No customers found matching the criteria. Nothing to update.")
            return
            
        print(f"\nFound {match_count} customers matching the criteria.")
        
        # 2. Wait for user approval
        confirmation = input(f"Are you sure you want to update all {match_count} documents with 'perReferAmount: 5'? (yes/no): ").strip().lower()
        
        if confirmation != 'yes':
            print("\nUpdate cancelled by user. No documents were modified.")
            return
        
        # Define the update operation: set perReferAmount to 5
        update_operation = {
            "$set": {
                "perReferAmount": 5
            }
        }
        
        print("\nApplying updates...")
        
        # 3. Perform the update across all matching documents
        result = customers_collection.update_many(query_filter, update_operation)
        
        print("-" * 30)
        print("Update Operation Successful!")
        print(f"Documents Matched: {result.matched_count}")
        print(f"Documents Modified: {result.modified_count}")
        print("-" * 30)

    except ConnectionFailure:
        print("Error: Could not connect to MongoDB. Check your connection string and network access.")
    except PyMongoError as e:
        print(f"A database error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'client' in locals() and client is not None:
            client.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()