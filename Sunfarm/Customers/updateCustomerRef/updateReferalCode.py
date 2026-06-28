import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
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
        client.admin.command('ping')
        db = client[DB_NAME] 
        
        customers_collection = db["customers"]
        referral_codes_collection = db["referralcodes"]

        print(f"Successfully connected to database: {db.name}")

        # --- STEP 1: Ensure `myreferralCodeId` exists in all customers ---
        print("\nStep 1: Ensuring `myreferralCodeId` exists in all customer documents...")
        # In MongoDB/Python, setting a field to None translates to 'null' in BSON
        default_my_ref_result = customers_collection.update_many(
            {"myreferralCodeId": {"$exists": False}},
            {"$set": {"myreferralCodeId": None}}
        )
        print(f"Defaulted 'myreferralCodeId' to null for {default_my_ref_result.modified_count} customers.")

        # --- STEP 2: Map string `referralCode` to `referralCodeId` ---
        print("\nStep 2: Migrating string 'referralCode' to ObjectIds...")
        
        # 2A: Fetch all referral codes into a dictionary for fast memory lookup
        # This prevents us from doing a database query for every single customer
        print("Fetching existing referral codes for mapping...")
        all_codes = list(referral_codes_collection.find({}, {"code": 1, "_id": 1}))
        code_to_id_map = {doc["code"]: doc["_id"] for doc in all_codes if "code" in doc}
        
        print(f"Loaded {len(code_to_id_map)} referral codes into memory.")

        # 2B: Find all customers that currently have a string-based referralCode
        customers_cursor = customers_collection.find({"referralCode": {"$type": "string"}})
        
        bulk_operations = []
        unmatched_codes = set()

        for customer in customers_cursor:
            code_str = customer.get("referralCode", "").strip()
            
            if code_str:
                ref_id = code_to_id_map.get(code_str)
                
                if ref_id:
                    # Prepare a bulk update operation for this customer
                    operation = UpdateOne(
                        {"_id": customer["_id"]},
                        {
                            "$set": {"referralCodeId": ref_id},
                            "$unset": {"referralCode": ""} # Removes the old string field
                        }
                    )
                    bulk_operations.append(operation)
                else:
                    unmatched_codes.add(code_str)

        # 2C: Execute the bulk update if we found matches
        if bulk_operations:
            print(f"Found {len(bulk_operations)} customers to update. Executing bulk write...")
            bulk_result = customers_collection.bulk_write(bulk_operations)
            print("-" * 40)
            print("✅ Migration Complete!")
            print(f"Successfully migrated {bulk_result.modified_count} customers.")
            print("-" * 40)
        else:
            print("No customers needed migration (either already migrated or no valid string codes found).")

        # 2D: Log any orphaned string codes that didn't exist in the referralcodes table
        if unmatched_codes:
            print("\n⚠️ WARNING: The following string codes were found on customers but do NOT exist in the 'referralcodes' collection:")
            for orphan_code in unmatched_codes:
                print(f"  - {orphan_code}")

    except ConnectionFailure:
        print("Error: Could not connect to MongoDB. Check your connection string and network access.")
    except PyMongoError as e:
        print(f"Database error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'client' in locals():
            client.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()