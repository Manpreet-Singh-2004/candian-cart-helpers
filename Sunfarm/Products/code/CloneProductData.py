import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from bson.objectid import ObjectId

# 1. Load configuration
load_dotenv()

DEV_STORE_ID_STR = os.getenv("STORE_ID")
DEV_MONGO_URI = os.getenv("MONGO_URI")
PROD_MONGO_URI = os.getenv("MONGO_URI_PRODUCTION")
DEV_DB_NAME = os.getenv("DB_NAME_IN_DEV")
PROD_DB_NAME = os.getenv("DB_NAME_IN_PROD")

# Validate environment variables
required_vars = [DEV_STORE_ID_STR, DEV_MONGO_URI, PROD_MONGO_URI, DEV_DB_NAME, PROD_DB_NAME]
if not all(required_vars):
    print("CRITICAL ERROR: Missing one or more environment variables in .env.")
    sys.exit(1)

# Cast the dev store ID to a BSON ObjectId safely
try:
    DEV_STORE_ID = ObjectId(DEV_STORE_ID_STR)
except Exception as e:
    print(f"CRITICAL ERROR: STORE_ID '{DEV_STORE_ID_STR}' is not a valid 24-character hex string.")
    sys.exit(1)

def main():
    print("Establishing database connections...")
    
    # 2. Connect to both clusters
    try:
        prod_client = MongoClient(PROD_MONGO_URI)
        dev_client = MongoClient(DEV_MONGO_URI)
        
        # Test connections
        prod_client.admin.command('ping')
        dev_client.admin.command('ping')
    except Exception as e:
        print(f"CRITICAL ERROR: Database connection failed. Details: {e}")
        sys.exit(1)

    prod_db = prod_client[PROD_DB_NAME]
    dev_db = dev_client[DEV_DB_NAME]

    prod_collection = prod_db['products']
    dev_collection = dev_db['products']

    # 3. Setup batching logic
    BATCH_SIZE = 500
    operations = []
    processed_count = 0
    updated_count = 0

    print(f"Fetching products from Production ({PROD_DB_NAME})...")
    
    # Use a cursor to stream data, preventing memory overload
    cursor = prod_collection.find({})
    
    for product in cursor:
        # Swap the storeId
        product['storeId'] = DEV_STORE_ID
        
        # Prepare an upsert operation: 
        # Match by _id to avoid duplicates. Overwrite document with new storeId.
        operations.append(
            UpdateOne(
                {'_id': product['_id']}, 
                {'$set': product}, 
                upsert=True
            )
        )

        # 4. Execute in batches
        if len(operations) == BATCH_SIZE:
            try:
                result = dev_collection.bulk_write(operations, ordered=False)
                updated_count += (result.upserted_count + result.modified_count)
                processed_count += len(operations)
                print(f"Processed {processed_count} records...")
                operations = [] # Reset batch
            except BulkWriteError as bwe:
                print(f"WARNING: Batch write encountered errors: {bwe.details}")
                # ordered=False allows the batch to continue even if one document fails

    # 5. Flush remaining operations
    if operations:
        try:
            result = dev_collection.bulk_write(operations, ordered=False)
            updated_count += (result.upserted_count + result.modified_count)
            processed_count += len(operations)
            print(f"Processed {processed_count} records...")
        except BulkWriteError as bwe:
             print(f"WARNING: Final batch write encountered errors: {bwe.details}")

    print("\n--- Clone Complete ---")
    print(f"Total Products Checked: {processed_count}")
    print(f"Successfully Upserted/Updated in Dev: {updated_count}")

    prod_client.close()
    dev_client.close()

if __name__ == "__main__":
    main()