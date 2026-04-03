import os
import sys
import json
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("Error: MONGO_URI must be set in the .env file.")
    sys.exit(1)

# Helper to serialize MongoDB specific types (ObjectId) to JSON
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

def main():
    print("--- Fetching Products with Price = 0 to JSON ---")
    print("Connecting to MongoDB...")
    
    try:
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        db = client.get_default_database()
        products_collection = db["products"]
        print(f"Successfully connected to database: {db.name}\n")
        
    except ConnectionFailure:
        print("[!] Error: Could not connect to MongoDB.")
        sys.exit(1)
        
    try:
        # Define the filter query
        query = {"price": 0}
        
        # 1. Get the total count of documents matching the filter
        zero_price_count = products_collection.count_documents(query)
        
        if zero_price_count == 0:
            print("Good news! No products found with a price of 0.")
        else:
            print(f"⚠️ Found {zero_price_count} products with a price of 0.")
            print("Exporting to JSON...")
            
            # 2. Fetch the actual documents and convert cursor to a list
            zero_price_products = list(products_collection.find(query))
            
            # 3. Structure the final data for the JSON file
            output_data = {
                "total_products_with_zero_price": zero_price_count,
                "products": zero_price_products
            }
            
            # 4. Write to a JSON file in the 'products/data' folder
            output_filepath = os.path.join("products/data", "zero_price_products.json")
            
            with open(output_filepath, 'w', encoding='utf-8') as json_file:
                json.dump(output_data, json_file, cls=MongoJSONEncoder, indent=4)
                
            print(f"\n[SUCCESS] Successfully exported data to: {output_filepath}")
            
    except Exception as e:
        print(f"\n[!] An error occurred while querying the database: {e}")
    finally:
        client.close()
        print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()