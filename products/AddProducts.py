import os
import sys
import random
from datetime import datetime, timezone
from typing import Dict, List, Union
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

# Define a strict type alias for our document structure
ProductDocument = Dict[str, Union[str, int, float, bool, ObjectId, datetime, List[Dict[str, str]]]]

def get_products() -> List[ProductDocument]:
    """Returns the list of 20 product dictionaries mapped to the full MongoDB schema."""
    now = datetime.now(timezone.utc)
    
    # Generate mock ObjectIds for related collections to populate all schema fields
    mock_invoice_id = ObjectId()
    mock_vendor_id = ObjectId()
    
    # Base product template to ensure all schema fields are present
    def create_product(data: ProductDocument) -> ProductDocument:
        base: ProductDocument = {
            "createdAt": now,
            "updatedAt": now,
            "isFeatured": False,
            "subsidised": False,
            "description": "Premium quality product.", # Default fallback description
            "disposableFee": 0,                      # Default to 0 cents
            "primaryUPC": random.randint(100000000000, 999999999999), # Random 12-digit UPC
            "InvoiceId": mock_invoice_id,
            "vendorId": mock_vendor_id,
            "images": [] # Default empty image array if not provided
        }
        base.update(data)
        return base

    return [
        # ===== BP 1 (Price: 100 cents) =====
        create_product({"storeId": STORE_ID, "name": "Bread White Loaf", "category": "Bakery", "markup": 35, "tax": 0.05, "price": 100, "stock": True, "images": [{"url": "https://picsum.photos/seed/breadwhite/600/600", "fileId": "breadwhite1"}]}),
        create_product({"storeId": STORE_ID, "name": "Amul Milk 1L", "description": "Fresh toned milk", "category": "Dairy", "markup": 32, "tax": 0.0, "disposableFee": 10, "price": 100, "stock": True}),
        create_product({"storeId": STORE_ID, "name": "Kurkure Masala Munch", "category": "Snacks", "markup": 40, "tax": 0.05, "price": 100, "stock": True}),
        create_product({"storeId": STORE_ID, "name": "Vim Dishwash Bar", "category": "Household", "markup": 33, "tax": 0.12, "price": 100, "stock": True}),
        create_product({"storeId": STORE_ID, "name": "Patanjali Multani Mitti Soap", "category": "Personal Care", "markup": 45, "tax": 0.12, "price": 100, "stock": True}),

        # ===== BP 5 (Price: 500 cents) =====
        create_product({"storeId": STORE_ID, "name": "Bread Whole Wheat", "category": "Bakery", "markup": 30, "tax": 0.05, "price": 500, "stock": True}),
        create_product({"storeId": STORE_ID, "name": "Haldiram Bhujia 400g", "category": "Snacks", "markup": 38, "tax": 0.05, "price": 500, "stock": True}),
        create_product({"storeId": STORE_ID, "name": "Masala Chai Tea Bags", "category": "Beverages", "markup": 35, "tax": 0.05, "price": 500, "stock": True}),
        create_product({"storeId": STORE_ID, "name": "Harpic Toilet Cleaner", "category": "Household", "markup": 45, "tax": 0.12, "price": 500, "stock": True}),
        create_product({"storeId": STORE_ID, "name": "Bananas (1kg)", "category": "Fruits", "markup": 30, "tax": 0.0, "price": 500, "stock": True}),

        # ===== BP 10 (Price: 1000 cents) =====
        create_product({"storeId": STORE_ID, "name": "Mother Dairy Whipped Butter 2x2KG", "category": "Dairy", "markup": 45, "tax": 0.0, "price": 1000, "stock": True}),
        create_product({"storeId": STORE_ID, "name": "Parachute Coconut Oil 500ml", "category": "Personal Care", "markup": 40, "tax": 0.12, "price": 1000, "stock": True}),
        create_product({"storeId": STORE_ID, "name": "Frozen Chicken Nuggets 750g", "category": "Meat", "markup": 30, "tax": 0.05, "price": 1000, "stock": True}),

        # ===== BP 15 (Price: 1500 cents) =====
        create_product({"storeId": STORE_ID, "name": "Alpenliebe Lollipops", "category": "Snacks", "markup": 42, "tax": 0.05, "price": 1500, "stock": True}),
        create_product({"storeId": STORE_ID, "name": "Surf Excel 1kg", "category": "Household", "markup": 35, "tax": 0.12, "price": 1500, "stock": True}),
        create_product({"storeId": STORE_ID, "name": "Mangoes (1kg)", "description": "Seasonal fresh mangoes", "category": "Fruits", "markup": 35, "tax": 0.0, "price": 1500, "stock": False}),
        create_product({"storeId": STORE_ID, "name": "Aashirvaad Atta 10kg", "category": "Other", "markup": 32, "tax": 0.0, "price": 1500, "stock": True}),

        # ===== BP 20 (Price: 2000 cents) =====
        create_product({"storeId": STORE_ID, "name": "Thums Up 2L", "category": "Beverages", "markup": 30, "tax": 0.12, "price": 2000, "stock": True, "disposableFee": 20}),
        create_product({"storeId": STORE_ID, "name": "Frozen Mutton Curry Cut 1kg", "category": "Meat", "markup": 42, "tax": 0.05, "price": 2000, "stock": False}),
        create_product({"storeId": STORE_ID, "name": "India Gate Basmati Rice 5kg", "category": "Other", "markup": 30, "tax": 0.0, "price": 2000, "stock": True}),
    ]

def main() -> None:
    print("Connecting to MongoDB...")
    try:
        # Connect to MongoDB cluster
        client = MongoClient(MONGO_URI)
        
        # Test connection
        client.admin.command('ping')
        
        # Select database
        db = client.get_database() 
        products_collection = db["products"] 

        print(f"Successfully connected to database: {db.name}")

        products = get_products()
        
        print(f"Attempting to insert {len(products)} products for Store ID: {STORE_ID}...")
        
        # Insert the data
        result = products_collection.insert_many(products)
        
        print(f"Successfully inserted {len(result.inserted_ids)} products into the database!")

    except ConnectionFailure:
        print("Error: Could not connect to MongoDB. Check your connection string and network access.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    main()