import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from .env
load_dotenv()

# MONGO_URI = os.getenv("MONGO_URI")
# DB_NAME = os.getenv("DB_NAME_IN_DEV")

MONGO_URI = os.getenv("MONGO_URI_PRODUCTION")
DB_NAME = os.getenv("DB_NAME_IN_PROD")

def run_lucky_draw():
    if not MONGO_URI or not DB_NAME:
        print("Error: MONGO_URI or DB_NAME_IN_DEV not found in .env")
        return

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        customers_collection = db["customers"]

        # 1. Correct query syntax: Dictionary keys imply AND
        query = {
            "referralCode": "CCEVENT2026",
            "eventParticipant": "participant"
        }

        # OR condition if i want either one of the fields to be active
        # query = {
        #     "$or": [
        #         {"referralCode": "CCEVENT2026"},
        #         {"eventParticipant": "participant"}
        #     ]
        # }
        
        total_matching = customers_collection.count_documents(query)

        if total_matching == 0:
            print("No customers found matching the criteria.")
            return

        print(f"Total customers matching criteria: {total_matching}")

        while True:
            # 2. Randomly select 6 customers
            pipeline = [
                {"$match": query},
                {"$sample": {"size": 6}}
            ]
            winners = list(customers_collection.aggregate(pipeline))

            print("\n--- Selected Winners ---")
            for i, winner in enumerate(winners, 1):
                # Displaying requested fields
                print(f"{i}. Name: {winner.get('name')}")
                print(f"   Email: {winner.get('email')}")
                print(f"   Mobile: {winner.get('mobile')}")
                print(f"   Address: {winner.get('address')}")
                print(f"   ID: {winner.get('_id')}")
                print("-" * 20)
            
            # 3. Wait for user approval
            choice = input("\nConfirm these 6 winners? (y/n/reselect): ").lower().strip()

            if choice == 'y':
                winner_ids = [winner["_id"] for winner in winners]
                result = customers_collection.update_many(
                    {"_id": {"$in": winner_ids}},
                    {"$set": {"eventParticipant": "winner"}}
                )
                print(f"\nSuccessfully updated {result.modified_count} customers to 'winner'.")
                break
            elif choice == 'reselect':
                print("\nReselecting random winners...")
                continue
            else:
                print("Operation cancelled.")
                break

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    run_lucky_draw()