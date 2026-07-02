import os
import sys
from typing import List, TypeAlias
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import BulkWriteError
from bson.objectid import ObjectId
from bson.errors import InvalidId

# Use a TypeAlias instead of 'Any' to strictly define the MongoDB Document structure
Document: TypeAlias = dict[str, object]

def load_and_validate_env() -> None:
    """Loads variables from .env and ensures all required keys exist."""
    load_dotenv()
    
    required_vars: List[str] = [
        "MONGO_URI_PRODUCTION",
        "MONGO_URI",
        "DB_NAME_IN_PROD",
        "DB_NAME_IN_DEV",
        "STORE_ID_PRODUCTION",
        "STORE_ID"
    ]
    
    missing_vars: List[str] = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

def get_database(uri: str, db_name: str) -> Database[Document]:
    """Creates a MongoDB client and returns the requested database."""
    client: MongoClient[Document] = MongoClient(uri)
    return client[db_name]

def fetch_production_orders(collection: Collection[Document], store_id: ObjectId) -> List[Document]:
    """Fetches orders belonging to the specified production store ID."""
    # Query using the parsed ObjectId
    query: Document = {"storeId": store_id}
    
    # For massive datasets, processing in chunks/cursors is preferred. 
    # List conversion is used here assuming manageable local cloning size.
    return list(collection.find(query))

def transform_orders_for_dev(orders: List[Document], dev_store_id: ObjectId) -> List[Document]:
    """
    Transforms production orders to match the development environment.
    Strips the `_id` so they insert cleanly as new records without duplication errors.
    """
    transformed_orders: List[Document] = []
    
    for order in orders:
        # Shallow copy to avoid mutating the source iteration
        dev_order: Document = order.copy()
        
        # Strip '_id' to allow Mongo to generate new ObjectIds in dev
        if "_id" in dev_order:
            del dev_order["_id"]
            
        # Re-assign the dev store reference as a MongoDB ObjectId
        dev_order["storeId"] = dev_store_id
        
        transformed_orders.append(dev_order)
        
    return transformed_orders

def insert_orders_to_dev(collection: Collection[Document], orders: List[Document]) -> None:
    """Bulk inserts the transformed orders into the development database."""
    if not orders:
        print("⚠️ No orders found to insert.")
        return

    try:
        # ordered=False allows the batch to continue inserting even if a single document fails 
        # (e.g. failing a unique index constraint)
        result = collection.insert_many(orders, ordered=False)
        print(f"✅ Successfully inserted {len(result.inserted_ids)} orders into development.")
        
    except BulkWriteError as bwe:
        n_inserted = bwe.details.get("nInserted", 0)
        print(f"⚠️ Inserted {n_inserted} orders, but encountered some errors (e.g., constraint violations).")
    except Exception as e:
        print(f"❌ An unexpected error occurred during insertion: {e}")

def main() -> None:
    load_and_validate_env()

    # Cast to string safely since `load_and_validate_env` guarantees they exist
    prod_uri: str = str(os.getenv("MONGO_URI_PRODUCTION"))
    dev_uri: str = str(os.getenv("MONGO_URI"))
    prod_db_name: str = str(os.getenv("DB_NAME_IN_PROD"))
    dev_db_name: str = str(os.getenv("DB_NAME_IN_DEV"))
    prod_store_id_str: str = str(os.getenv("STORE_ID_PRODUCTION"))
    dev_store_id_str: str = str(os.getenv("STORE_ID"))

    # Convert strings to MongoDB ObjectIds and validate them early
    try:
        prod_store_id: ObjectId = ObjectId(prod_store_id_str)
        dev_store_id: ObjectId = ObjectId(dev_store_id_str)
    except InvalidId:
        print("❌ Error: STORE_ID or STORE_ID_PRODUCTION in your .env is not a valid 24-character MongoDB ObjectId.")
        sys.exit(1)

    # 1. Connect to both databases
    print(f"🔗 Connecting to Production DB: {prod_db_name}...")
    prod_db = get_database(prod_uri, prod_db_name)
    prod_orders_collection = prod_db["orders"]

    print(f"🔗 Connecting to Development DB: {dev_db_name}...")
    dev_db = get_database(dev_uri, dev_db_name)
    dev_orders_collection = dev_db["orders"]

    # 2. Extract Data
    print(f"📥 Fetching orders for production store ID: {prod_store_id}...")
    prod_orders = fetch_production_orders(prod_orders_collection, prod_store_id)
    print(f"📊 Found {len(prod_orders)} orders in production.")

    if not prod_orders:
        print("🛑 Exiting, no data to clone.")
        return

    # 3. Transform Data
    print("⚙️ Transforming orders for the development environment...")
    dev_orders = transform_orders_for_dev(prod_orders, dev_store_id)

    # 4. Load Data
    print("📤 Inserting orders into development database...")
    insert_orders_to_dev(dev_orders_collection, dev_orders)
    
    print("🚀 Cloning process finished!")

if __name__ == "__main__":
    main()