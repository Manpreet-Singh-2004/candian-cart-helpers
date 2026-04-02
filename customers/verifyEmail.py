import os
import sys
import argparse
import json
from datetime import datetime
from typing import Optional, TypedDict
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# 1. Reuse existing types: Mirroring the ICustomer interface from customer.model.ts
class CustomerData(TypedDict):
    _id: ObjectId
    userId: ObjectId
    name: str
    email: str
    address: str
    mobile: str
    city: str
    province: str
    monthlyBudget: float
    associatedStoreId: ObjectId
    referralCode: str
    walletBalance: int
    giftWalletBalance: int
    createdAt: datetime
    updatedAt: datetime

# Helper to serialize MongoDB specific types (ObjectId, datetime) to JSON
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj: object) -> object:
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def get_customer_by_id(customer_id: str, mongo_uri: str) -> Optional[CustomerData]:
    """
    Connects to MongoDB and fetches a customer strictly typed as CustomerData.
    """
    if not ObjectId.is_valid(customer_id):
        print(f"Error: '{customer_id}' is not a valid MongoDB ObjectId.", file=sys.stderr)
        return None

    client: Optional[MongoClient] = None
    try:
        # Connect to the MongoDB cluster
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Mongoose defaults to the db name in the URI, and pluralizes model names
        db = client.get_default_database() 
        customers_collection = db['customers']
        
        # Fetch the document and cast it to our TypedDict
        customer: Optional[CustomerData] = customers_collection.find_one({"_id": ObjectId(customer_id)})
        
        return customer

    except PyMongoError as e:
        print(f"Database error occurred: {e}", file=sys.stderr)
        return None
    finally:
        if client is not None:
            client.close()

def main() -> None:
    # 2. Use explicit argument parsing (Vercel CLI best practices)
    parser = argparse.ArgumentParser(description="Fetch and display customer data from MongoDB.")
    parser.add_argument("customer_id", type=str, help="The ObjectId of the customer to fetch")
    args = parser.add_argument()

    # 3. Environment-driven configuration
    mongo_uri: Optional[str] = os.environ.get("MONGODB_URI")
    if not mongo_uri:
        print("Error: MONGODB_URI environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching data for Customer ID: {args.customer_id}...\n")
    
    customer_data = get_customer_by_id(args.customer_id, mongo_uri)

    if customer_data:
        # Pretty print the dictionary using the custom JSON encoder
        formatted_data: str = json.dumps(customer_data, cls=MongoJSONEncoder, indent=2)
        print("Customer Data Found:")
        print(formatted_data)
    else:
        print("Customer not found or an error occurred.")
        sys.exit(1)

if __name__ == "__main__":
    main()