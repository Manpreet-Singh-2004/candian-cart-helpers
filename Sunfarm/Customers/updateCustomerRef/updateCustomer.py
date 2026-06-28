import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ConnectionFailure

# Load environment variables from .env file
load_dotenv()

# Fetch environment variables
MONGO_URI = os.getenv("MONGO_URI_PRODUCTION")
DB_NAME = os.getenv("DB_NAME_IN_PROD")

if not MONGO_URI or not DB_NAME:
    print("Error: MONGO_URI and DB_NAME_IN_DEV must be set in the .env file.")
    sys.exit(1)

def main():
    print("Connecting to MongoDB...")
    try:
        # Connect to MongoDB cluster
        client = MongoClient(MONGO_URI)
        
        # Test connection
        client.admin.command('ping')
        
        # Select the specific database from the env variable
        db = client[DB_NAME] 
        
        orders_collection = db["orders"]
        customers_collection = db["customers"]

        print(f"Successfully connected to database: {db.name}")
        
        # --- NEW STEP: Apply defaults for missing fields ---
        print("\nChecking for missing fields in the customers collection...")
        
        # 1A. Default 'placedFirstOrder' to False if it doesn't exist
        default_order_result = customers_collection.update_many(
            {"placedFirstOrder": {"$exists": False}},
            {"$set": {"placedFirstOrder": False}}
        )
        
        # 1B. Default 'referralCodeEnabled' to False if it doesn't exist
        default_referral_result = customers_collection.update_many(
            {"referralCodeEnabled": {"$exists": False}},
            {"$set": {"referralCodeEnabled": False}}
        )
        
        print(f"Defaulted 'placedFirstOrder' to False for {default_order_result.modified_count} customers.")
        print(f"Defaulted 'referralCodeEnabled' to False for {default_referral_result.modified_count} customers.")
        print("-" * 40)

        # --- ORIGINAL STEP: Upgrade users with subsidy > 0 ---
        print("\nScanning for orders where subsidy > 0...")
        
        # Query the orders collection for subsidy > 0
        cursor = orders_collection.find(
            {"subsidy": {"$gt": 0}}, 
            {"userId": 1, "_id": 0}
        )
        
        # Extract unique userIds using a set
        user_ids = set()
        for doc in cursor:
            if "userId" in doc:
                user_ids.add(doc["userId"])
                
        user_ids_list = list(user_ids)
        
        if not user_ids_list:
            print("No orders found with a subsidy greater than 0. No customers to upgrade.")
            return

        print(f"Found {len(user_ids_list)} unique customers who used a subsidy.")
        print("Upgrading customer flags (placedFirstOrder, referralCodeEnabled) to True...")
        
        # Bulk update the specific customers who meet the criteria
        result = customers_collection.update_many(
            {"_id": {"$in": user_ids_list}},
            {"$set": {
                "placedFirstOrder": True,
                "referralCodeEnabled": True
            }}
        )
        
        print("-" * 40)
        print("✅ Upgrade Complete!")
        print(f"Customers Matched for Upgrade: {result.matched_count}")
        print(f"Customers Actually Modified: {result.modified_count}")
        print("-" * 40)

    except ConnectionFailure:
        print("Error: Could not connect to MongoDB. Check your connection string and network access.")
    except PyMongoError as e:
        print(f"Database error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'client' in locals():
            client.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()