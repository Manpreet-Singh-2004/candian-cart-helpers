import os
import json
import random
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

# 1. Load the environment configuration
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME_IN_DEV")
STORE_ID = os.getenv("STORE_ID")

if not DB_NAME:
    print("⚠️  Warning: 'DB_NAME_IN_DEV' not found in your .env file. Falling back to default.")
    DB_NAME = "test"

if not STORE_ID:
    print("⚠️  Warning: 'STORE_ID' not found in your .env file. Generating a random one for fallback.")
    STORE_ID = str(ObjectId())

# 2. Initialize MongoDB Client with a fast timeout fallback
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
db = client[DB_NAME]

def get_mock_products(limit=3):
    """
    Attempts to pull genuine product IDs from the database.
    Falls back to generating safe, mock ObjectIds if the connection times out.
    """
    try:
        products_collection = db["products"]
        real_products = list(products_collection.find({}, {"_id": 1}).limit(10))
        
        if real_products:
            sampled = random.sample(real_products, min(len(real_products), limit))
            return [str(p["_id"]) for p in sampled]
            
    except Exception as e:
        print(f"⚠️  Could not fetch from DB '{DB_NAME}' ({e}). Using mock fallback IDs.")
        
    return [str(ObjectId()) for _ in range(limit)]

def generate_boundary_orders():
    """
    Generates 8 custom order payloads matching the specified boundary test cases.
    """
    product_ids = get_mock_products(limit=3)
    
    # Precise edge-case UTC dates from your specification
    test_cases = [
        {"utc": "2026-07-02T12:00:00.000Z", "desc": "Today, this month"},
        {"utc": "2026-07-02T06:59:59.999Z", "desc": "Yesterday — NOT today"},
        {"utc": "2026-07-02T07:00:00.001Z", "desc": "Today — first instant of the day"},
        {"utc": "2026-07-01T06:59:59.999Z", "desc": "Last month (June) — NOT this month"},
        {"utc": "2026-07-01T07:00:00.001Z", "desc": "This month — first instant of July"},
        {"utc": "2026-06-25T06:59:59.999Z", "desc": "Outside rolling-7-days window"},
        {"utc": "2026-06-25T07:00:00.001Z", "desc": "Inside rolling-7-days window (boundary)"},
        {"utc": "2026-05-30T19:24:33.316Z", "desc": "Two months back — shouldn't show"}
    ]
    
    orders = []
    
    for i, case in enumerate(test_cases, start=1):
        products_array = []
        base_total = 0
        total_gst = 0

        for pid in product_ids:
            qty = random.randint(1, 2)
            markup = round(random.uniform(10, 50), 2)
            tax_rate = 0.05 if random.choice([True, False]) else 0
            
            item_total = int((1000 + (markup * 10)) * qty) 
            base_total += item_total
            total_gst += int(item_total * tax_rate)

            products_array.append({
                "productId": pid,
                "quantity": qty,
                "markup": markup,
                "tax": tax_rate,
                "disposableFee": 0,
                "total": item_total,
                "subsidy": 0
            })

        payload = {
            "_id": str(ObjectId()),
            "testCaseNumber": i,
            "testCaseDescription": case["desc"],
            "products": products_array,
            "subsidyItems": [],
            "miscItems": [],
            "TotalGST": total_gst,
            "TotalPST": 0,
            "TotalDisposableFee": 0,
            "BaseTotal": base_total,
            "cartTotal": base_total + total_gst,
            "subsidy": 695,
            "subsidyLeft": 695,
            "subsidyUsed": 0,
            "userId": str(ObjectId()),       
            "storeId": STORE_ID,             # Loaded from your .env environment context
            "status": "completed",
            "paymentMode": "wallet",
            "cashierId": str(ObjectId()),    
            "createdAt": case["utc"],        # String format for the JSON file output
            "updatedAt": case["utc"],
            "__v": 0,
            "platformProfit": 135,
            "storeProfit": 250
        }
        orders.append(payload)
        
    return orders

if __name__ == "__main__":
    print(f"Connecting using URI config parameters targeting DB: '{DB_NAME}'...")
    print(f"Target Store ID configuration: '{STORE_ID}'\n")

    # 1. Generate the edge-case payloads
    print("Generating 8 specific boundary testing payloads...")
    fake_orders = generate_boundary_orders()

    # 2. Ensure 'data' directory exists and export payloads to data/fakeOrders.json
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    json_filepath = os.path.join(output_dir, "fakeOrders.json")
    
    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(fake_orders, f, indent=2)
    print(f"✅ Successfully wrote {len(fake_orders)} payloads to '{json_filepath}'")

    # 3. Halt and request explicit confirmation before writing to DB
    print("\n------------------------------------------------------------")
    user_input = input("❓ Would you like to seed these 8 orders into MongoDB now? (yes/no): ").strip().lower()
    print("------------------------------------------------------------")

    if user_input in ["yes", "y"]:
        try:
            orders_collection = db["orders"]
            
            db_payloads = []
            for order in fake_orders:
                db_order = order.copy()
                
                # Convert string ID representations back to BSON ObjectIds for proper insertion[cite: 1]
                db_order["_id"] = ObjectId(db_order["_id"])
                db_order["userId"] = ObjectId(db_order["userId"])
                db_order["storeId"] = ObjectId(db_order["storeId"])
                db_order["cashierId"] = ObjectId(db_order["cashierId"])
                for item in db_order["products"]:
                    item["productId"] = ObjectId(item["productId"])
                
                # Convert ISO string timestamp to BSON native Date objects[cite: 1]
                clean_created_at = db_order["createdAt"].replace("Z", "+00:00")
                clean_updated_at = db_order["updatedAt"].replace("Z", "+00:00")
                
                db_order["createdAt"] = datetime.fromisoformat(clean_created_at)
                db_order["updatedAt"] = datetime.fromisoformat(clean_updated_at)
                
                db_payloads.append(db_order)

            result = orders_collection.insert_many(db_payloads)
            print(f"🚀 Success! Inserted {len(result.inserted_ids)} records with native BSON Date objects into '{DB_NAME}.orders'.")
        except Exception as e:
            print(f"❌ Database insertion failed: {e}")
    else:
        print("❌ Operation canceled. Records were saved locally to JSON but not written to MongoDB.")