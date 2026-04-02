import os
import sys
import pprint
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from bson.errors import InvalidId

# Load environment variables from .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("Error: MONGO_URI must be set in the .env file.")
    sys.exit(1)

def get_customer(customer_id_str: str) -> None:
    """Fetches and displays customer data from MongoDB."""
    print("Connecting to MongoDB...")
    try:
        # Validate the ObjectId format
        try:
            customer_id = ObjectId(customer_id_str)
        except InvalidId:
            print(f"\n[!] Error: Invalid Customer ID format ('{customer_id_str}').")
            print("It must be a 24-character hex string.")
            return

        # Connect to MongoDB cluster
        client = MongoClient(MONGO_URI)
        
        # Test connection
        client.admin.command('ping')
        
        # Select default database
        db = client.get_default_database() 
        
        # NOTE: Change "customers" to "users" if your collection is named differently
        customers_collection = db["customers"] 

        print(f"Successfully connected to database: {db.name}")
        print(f"Searching for Customer ID: {customer_id_str}...\n")

        # Query the database
        customer_data = customers_collection.find_one({"_id": customer_id})

        if customer_data:
            print("-" * 30)
            print("Customer Data Found:")
            print("-" * 30)
            # Use pprint for highly readable formatting of nested JSON/BSON data
            pprint.pprint(customer_data)
            print("-" * 30)
        else:
            print(f"[!] No customer found with ID: {customer_id_str}")

    except ConnectionFailure:
        print("Error: Could not connect to MongoDB. Check your connection string and network access.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'client' in locals():
            client.close()

def main():
    # Allow the ID to be passed directly as a command line parameter
    # e.g., python GetCustomer.py 5f4e3c2b1a0d9e8f7c6b5a4d
    if len(sys.argv) > 1:
        customer_id_str = sys.argv[1]
    else:
        # Fallback to interactive prompt if no parameter was passed
        print("\n--- Fetch Customer Data ---")
        customer_id_str = input("Enter the Customer ID: ").strip()

    if not customer_id_str:
        print("Error: Customer ID cannot be empty.")
        sys.exit(1)

    get_customer(customer_id_str)

if __name__ == "__main__":
    main()