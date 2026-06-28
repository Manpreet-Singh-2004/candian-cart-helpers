import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# 3 criteria -: isAvailable true, Images present and category excluding Fruits, Vegitable and Dairy

# Load environment variables from .env file
load_dotenv()

# Retrieve variables as requested
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME_IN_DEV")

if not MONGO_URI or not DB_NAME:
    print("Error: MONGO_URI and DB_NAME_IN_DEV must be set in the .env file.")
    sys.exit(1)

def count_filtered_products():
    print("Connecting to MongoDB...")
    try:
        # Connect to MongoDB cluster
        client = MongoClient(MONGO_URI)
        
        # Test connection
        client.admin.command('ping')
        
        # Select the specific development database
        db = client[DB_NAME]
        
        # Target the products collection
        products_collection = db["products"]

        print(f"Successfully connected to database: {db.name}")
        
        # Construct the query based on your criteria
        query = {
            # 1. isAvailable must be true
            "isAvailable": True,
            
            # 2. Category should not be fruit, vegetable (or vegitable), or dairy
            # Using $nin (not in) to cover potential capitalization variations from your DB mappings
            "category": {
                "$nin": [
                    "fruit", "vegitable", "dairy", 
                    "Fruits", "Vegetables", "Dairy", "Vegetable", "Fruit"
                ]
            },
            
            # 3. Must have an image (images array exists, is an array, and is not empty)
            "images": {
                "$exists": True, 
                "$type": "array", 
                "$ne": []
            }
        }

        print("\nExecuting query...")
        
        # Count the documents that match the query
        total_count = products_collection.count_documents(query)
        
        print("-" * 50)
        print(f"Total products matching criteria: {total_count}")
        print("-" * 50)

    except ConnectionFailure:
        print("Error: Could not connect to MongoDB. Check your connection string and network access.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'client' in locals():
            client.close()
            print("Database connection closed.")

if __name__ == "__main__":
    count_filtered_products()