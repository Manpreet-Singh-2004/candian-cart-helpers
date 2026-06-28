import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI_PRODUCTION")
DB_NAME = os.getenv("DB_NAME_IN_PROD")

def update_winners_wallet():
    if not MONGO_URI or not DB_NAME:
        print("Error: MONGO_URI or DB_NAME_IN_DEV not found in .env")
        return

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        customers_collection = db["customers"]

        # 1. Find all customers marked as 'winner'
        query = {"eventParticipant": "winner"}
        winners = list(customers_collection.find(query))

        if not winners:
            print("No customers found with 'eventParticipant' set to 'winner'.")
            return

        print(f"Found {len(winners)} total winners to credit.")
        print("\n--- Current Winners to Receive $50 ---")
        for i, winner in enumerate(winners, 1):
            print(f"{i}. Name: {winner.get('name')}")
            print(f"   Current Gift Wallet: {winner.get('giftWalletBalance', 0) / 100:.2f} $")
            print(f"   ID: {winner.get('_id')}")
            print("-" * 20)

        # 2. Wait for user approval
        choice = input(f"\nApprove incrementing the gift wallet of these {len(winners)} winners by $50.00? (y/n): ").lower().strip()

        if choice == 'y':
            # 3. Perform the increment
            # $inc adds 5000 cents to the existing balance
            winner_ids = [winner["_id"] for winner in winners]
            result = customers_collection.update_many(
                {"_id": {"$in": winner_ids}},
                {"$inc": {"giftWalletBalance": 5000}}
            )
            print(f"\nSuccessfully updated {result.modified_count} winners' wallets.")
        else:
            print("Operation cancelled. No changes made.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    update_winners_wallet()