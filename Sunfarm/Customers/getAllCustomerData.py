import os
import sys
import csv
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

# Load environment variables from .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI_PRODUCTION")
DB_NAME = os.getenv("DB_NAME_IN_PROD")

# Validate required environment variables
if not MONGO_URI:
    print("❌ ERROR: MONGO_URI_PRODUCTION must be set in the .env file.", file=sys.stderr)
    sys.exit(1)

if not DB_NAME:
    print("❌ ERROR: DB_NAME_IN_PROD must be set in the .env file.", file=sys.stderr)
    sys.exit(1)


def sanitize_value(value):
    """Converts MongoDB BSON types (ObjectIds, datetimes) to standard strings for CSV compatibility."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    # Handles ObjectId or other non-string types safely
    return str(value)


def export_customers_to_csv(output_filepath: str) -> None:
    print(f"🔌 Connecting to production MongoDB database: '{DB_NAME}'...")
    client = None
    try:
        # Establish connection with a 5-second timeout limit
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')  # Test connectivity
        
        db = client[DB_NAME]
        customers_collection = db["customers"]
        
        print("🔍 Fetching customer data...")
        # Retrieve all documents from the customers collection
        customers = list(customers_collection.find({}))
        
        if not customers:
            print("⚠️ No customer records found to export.")
            return

        print(f"📊 Found {len(customers)} customers. Determining CSV structure...")

        # Dynamically discover all unique keys across documents to ensure no fields are cut off
        headers = set()
        for doc in customers:
            headers.update(doc.keys())
        
        # Sort headers to ensure consistent column ordering (e.g., keeping '_id' first)
        sorted_headers = sorted(list(headers))
        if "_id" in sorted_headers:
            sorted_headers.remove("_id")
            sorted_headers.insert(0, "_id")

        print(f"💾 Writing data to {output_filepath}...")
        
        # Ensure directory exists if path contains folders
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True) if os.path.dirname(output_filepath) else None

        with open(output_filepath, mode='w', encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=sorted_headers)
            writer.writeheader()
            
            for doc in customers:
                # Sanitize BSON types per row mapping
                row_data = {key: sanitize_value(doc.get(key)) for key in sorted_headers}
                writer.writerow(row_data)

        print(f"✨ Success! Exported {len(customers)} customers successfully to: {output_filepath}")

    except ConnectionFailure:
        print("❌ ERROR: Could not connect to MongoDB. Check your connection string and network/IP access restrictions.", file=sys.stderr)
    except PyMongoError as e:
        print(f"❌ Database error occurred: {e}", file=sys.stderr)
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        if client is not None:
            client.close()
            print("🔌 Database connection closed.")


if __name__ == "__main__":
    # Define destination path
    output_path = os.path.join("data", "exported_customers.csv")
    
    export_customers_to_csv(output_path)