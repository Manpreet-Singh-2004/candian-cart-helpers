import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from bson.errors import InvalidId

# Load environment variables from .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI_PRODUCTION")
DB_NAME = os.getenv("DB_NAME_IN_PROD")

# The specific product ID you want to remove
TARGET_PRODUCT_ID_STR = "6a08cff8810608954715a30f"

if not MONGO_URI or not DB_NAME:
    print("Error: MONGO_URI_PRODUCTION and DB_NAME_IN_PROD must be set in the .env file.")
    sys.exit(1)

try:
    TARGET_PRODUCT_ID = ObjectId(TARGET_PRODUCT_ID_STR)
except InvalidId as e:
    print(f"Error: Invalid Product ID format. It must be a 24-character hex string. Details: {e}")
    sys.exit(1)

def main():
    print("Connecting to Production MongoDB...")
    try:
        # Connect to MongoDB cluster
        client = MongoClient(MONGO_URI)
        
        # Test connection
        client.admin.command('ping')
        
        # Select the specific production database
        db = client[DB_NAME] 
        
        # Target the orders collection
        orders_collection = db["orders"]

        print(f"Successfully connected to database: {db.name}")
        
        # 1. Find the number of orders that have this product in their 'products' array
        query = {"products.productId": TARGET_PRODUCT_ID}
        count_before = orders_collection.count_documents(query)
        
        if count_before == 0:
            print(f"\nNo orders found containing Product ID: {TARGET_PRODUCT_ID_STR}. Nothing to delete.")
            return

        print(f"\nFound {count_before} order(s) containing Product ID: {TARGET_PRODUCT_ID_STR}.")
        
        # 2. Confirm before modifying (Guardrail)
        print("\n" + "!"*60)
        print("WARNING: This will modify historical orders in PRODUCTION!")
        print("Note: This script removes the item from the array but does NOT")
        print("automatically recalculate cartTotal, TotalGST, BaseTotal, etc.")
        print("!"*60)
        confirmation = input(f"Are you sure you want to remove this product from all {count_before} orders? (yes/no): ").strip()
        
        if confirmation.lower() != 'yes':
            print("\nAction cancelled by user. No orders were modified.")
            return

        print("\nRemoving product from orders...")
        
        # 3. Use $pull to remove the specific product object from the products array
        update_operation = {
            "$pull": {
                "products": {
                    "productId": TARGET_PRODUCT_ID
                }
            }
        }
        
        # Perform the update on all matching documents
        result = orders_collection.update_many(query, update_operation)
        
        print(f"Success! Modified {result.modified_count} orders by removing the product.")

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