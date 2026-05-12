import os
import sys
import csv
import pprint
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, BulkWriteError
from bson.objectid import ObjectId

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("❌ Error: MONGO_URI must be set in the .env file.")
    sys.exit(1)

# Ensure this points to the exact output file from our previous merge script
CSV_FILE_PATH = "csvDatatoModel/sunfarm/data/final_merged_products.csv"

def parse_boolean(val: str) -> bool:
    """Helper to convert CSV string to actual Boolean"""
    return str(val).strip().lower() in ['true', '1', 't', 'y', 'yes']

def safe_int(val: str) -> int:
    """Safely converts string to int, handling empty strings and decimals."""
    if not val or not str(val).strip():
        return 0
    try:
        return int(float(str(val).strip()))
    except ValueError:
        return 0

def safe_float(val: str) -> float:
    """Safely converts string to float, handling empty strings."""
    if not val or not str(val).strip():
        return 0.0
    try:
        return float(str(val).strip())
    except ValueError:
        return 0.0

def main():
    print("--- Starting Bulk Import Process ---")
    print("Connecting to MongoDB...")
    
    try:
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        db = client.get_default_database()
        products_collection = db["products"]
        print(f"✅ Successfully connected to database: {db.name}")
        
    except ConnectionFailure:
        print("❌ FATAL: Could not connect to MongoDB.")
        sys.exit(1)

    documents_to_insert = []
    skipped_rows = 0
    
    # Dynamically resolve absolute paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    actual_csv_path = os.path.abspath(CSV_FILE_PATH)
    
    print(f"Reading data from {actual_csv_path}...")
    try:
        with open(actual_csv_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            if reader.fieldnames and 'storeId' not in reader.fieldnames:
                print(f"\n❌ CRITICAL ERROR: The CSV does not have 'storeId' as a header.")
                print(f"Headers found: {reader.fieldnames}")
                sys.exit(1)

            # --- PARSE DATA ---
            for row_num, row in enumerate(reader, start=2):
                try:
                    # primaryUPC MUST stay a string
                    raw_upc = row.get('primaryUPC', '').strip()
                    upc_value = raw_upc if raw_upc else None

                    product_doc = {
                        "storeId": ObjectId(row['storeId'].strip()),
                        "name": row.get('name', '').strip(),
                        "description": row.get('description', '').strip(),
                        "category": row.get('category', '').strip(),
                        "markup": safe_float(row.get('markup')),
                        "tax": safe_float(row.get('tax')),
                        "disposableFee": safe_int(row.get('disposableFee')),
                        "price": safe_int(row.get('price')),
                        "stock": parse_boolean(row.get('stock', 'True')),
                        "subsidised": parse_boolean(row.get('subsidised', 'False')),
                        "isFeatured": parse_boolean(row.get('isFeatured', 'False')),
                        "primaryUPC": upc_value
                    }
                    documents_to_insert.append(product_doc)
                    
                except Exception as e:
                    print(f"⚠️ Warning: Skipping Row {row_num} due to formatting error: {e}")
                    skipped_rows += 1
                    
    except FileNotFoundError:
        print(f"❌ Error: Could not find file '{actual_csv_path}'.")
        sys.exit(1)

    total_docs = len(documents_to_insert)
    if total_docs == 0:
        print("\n🛑 No valid products found to insert. Exiting.")
        sys.exit(0)

    print(f"\n✅ Prepared {total_docs} products for insertion. (Skipped {skipped_rows} bad rows).")

    # --- Test insert the FIRST document to MongoDB ---
    first_doc = documents_to_insert[0]
    print("\n" + "="*50)
    print("--- Testing First Document Insertion ---")
    
    try:
        # Actually push to MongoDB
        test_insert_result = products_collection.insert_one(first_doc)
        print(f"🚀 SUCCESS: Inserted 1 test product into MongoDB. ID: {test_insert_result.inserted_id}")
        print("Here is the exact JSON that was saved to your database:")
        pprint.pprint(first_doc)
    except Exception as e:
        print(f"❌ FATAL: Failed to insert the test document into MongoDB: {e}")
        sys.exit(1)
    
    print("\n" + "="*50)
    user_input = input("Check MongoDB / Compass now. Does it look perfect?\nType 'yes' to insert the REMAINING items, or 'no' to abort (this will delete the test item): ").strip().lower()
    
    if user_input not in ['yes', 'y']:
        print("\n🛑 Aborting batch insertion.")
        print("Rolling back: Deleting the test document from MongoDB...")
        products_collection.delete_one({"_id": test_insert_result.inserted_id})
        print("🧹 Rollback complete. Your database is clean. Exiting.")
        sys.exit(0)

    # --- Perform Bulk Insert for the REST of the items ---
    remaining_docs = documents_to_insert[1:]
    
    if not remaining_docs:
        print("\n✅ Only 1 document existed in the CSV, and it's already inserted. Done!")
        sys.exit(0)
        
    print(f"\nPushing the remaining {len(remaining_docs)} products to MongoDB. This may take a moment...")
    
    try:
        # unordered allows it to keep inserting even if a duplicate key error is hit
        result = products_collection.insert_many(remaining_docs, ordered=False)
        print(f"\n✅ [SUCCESS] Successfully inserted {len(result.inserted_ids)} remaining products!")
        print(f"Total products in this batch now live: {len(result.inserted_ids) + 1}") # +1 for the test doc
    except BulkWriteError as bwe:
        inserted_count = bwe.details['nInserted']
        failed_count = len(bwe.details['writeErrors'])
        print(f"\n⚠️ [PARTIAL SUCCESS] Inserted {inserted_count} products.")
        print(f"❌ Encountered {failed_count} database errors (likely duplicate UPCs).")
        print("\n--- Error Summary (First 5) ---")
        for error in bwe.details['writeErrors'][:5]:
            print(f" - Error at index {error['index']}: {error['errmsg']}")
        if failed_count > 5:
            print(f" ... and {failed_count - 5} more errors.")
    except Exception as e:
        print(f"\n❌ A critical error occurred during bulk insertion: {e}")
    finally:
        client.close()
        print("\n--- Bulk Import Process Complete ---")

if __name__ == "__main__":
    main()