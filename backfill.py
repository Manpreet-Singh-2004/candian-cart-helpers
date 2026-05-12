import os
import sys
import random
from typing import Optional, List, Dict, Any
from pymongo import MongoClient, UpdateOne
from pymongo.errors import ConnectionFailure, OperationFailure
from pymongo.results import BulkWriteResult
from bson.objectid import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv

def main() -> None:
    # 1. Load configuration
    load_dotenv()

    mongo_uri: Optional[str] = os.getenv("MONGO_URI")
    store_id_str: Optional[str] = os.getenv("STORE_ID")

    # 2. Early exits for missing or invalid config
    if not mongo_uri:
        print("Error: MONGO_URI is missing from the .env file.")
        sys.exit(1)

    if not store_id_str:
        print("Error: STORE_ID is missing from the .env file.")
        sys.exit(1)

    try:
        store_id = ObjectId(store_id_str)
    except InvalidId:
        print(f"Error: STORE_ID '{store_id_str}' is not a valid MongoDB ObjectId.")
        sys.exit(1)

    print("Initializing Candian Cart randomized markup backfill...")

    client: Optional[MongoClient] = None

    try:
        # 3. Establish strict connection with timeout
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Force a call to the server to verify connection
        client.admin.command('ping')
        
        db = client.get_default_database()
        collection = db['products']

        # 4. Construct the precise query payload
        query: Dict[str, Any] = {
            "storeId": store_id,
            "markup": 0
        }

        print(f"Scanning for products in Store ID: {store_id_str}...")

        # 5. Fetch ONLY the _id field to minimize memory usage and network payload
        cursor = collection.find(query, {"_id": 1})
        
        bulk_operations: List[UpdateOne] = []
        
        # 6. Iterate and assign a random markup to each document individually
        for doc in cursor:
            random_markup: int = random.randint(30, 40)
            
            bulk_operations.append(
                UpdateOne(
                    {"_id": doc["_id"]},
                    {"$set": {"markup": random_markup}}
                )
            )

        # 7. Execute bulk write if there are operations to run
        if not bulk_operations:
            print("\n✅ Candian Cart backfill complete.")
            print("No products found with markup = 0.")
            return

        print(f"Executing randomized batch update for {len(bulk_operations)} products...")
        
        # Execute all updates in a single database round-trip
        result: BulkWriteResult = collection.bulk_write(bulk_operations)

        # 8. Report results
        print("\n✅ Candian Cart randomized backfill complete.")
        print(f"Products successfully updated: {result.modified_count}")

    except ConnectionFailure:
        print("Fatal: Failed to connect to MongoDB. Verify your MONGO_URI and network settings.")
    except OperationFailure as e:
        print(f"Fatal: Database operation failed. Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # 9. Safe cleanup
        if client is not None:
            client.close()
            print("Database connection closed safely.")

if __name__ == "__main__":
    main()