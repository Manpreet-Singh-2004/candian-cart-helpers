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
    print("Error: MONGO_URI must be set in the .env file.")
    sys.exit(1)

CSV_FILE_PATH = "csvDatatoModel/data/mapped_products.csv"

def parse_boolean(val: str) -> bool:
    """Helper to convert CSV string to actual Boolean"""
    return str(val).strip().lower() in ['true', '1', 't', 'y', 'yes']

def main():
    print("--- Starting Bulk Import Process ---")
    print("Connecting to MongoDB...")
    
    try:
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        db = client.get_default_database()
        products_collection = db["products"]
        print(f"Successfully connected to database: {db.name}")
        
    except ConnectionFailure:
        print("[!] Error: Could not connect to MongoDB.")
        sys.exit(1)

    documents_to_insert = []
    skipped_rows = 0
    
    print(f"Reading data from {CSV_FILE_PATH}...")
    try:
        # utf-8-sig automatically strips hidden Byte Order Marks from the header row
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            # Basic safety check to ensure it read the headers properly
            if reader.fieldnames and 'storeId' not in reader.fieldnames:
                print(f"\n[!] CRITICAL ERROR: The CSV does not have 'storeId' as a header.")
                print(f"Headers found: {reader.fieldnames}")
                sys.exit(1)

            # --- PARSE DATA ---
            for row_num, row in enumerate(reader, start=2): # start=2 accounts for header row
                try:
                    product_doc = {
                        "storeId": ObjectId(row['storeId'].strip()),
                        "name": row['name'].strip(),
                        "description": row.get('description', '').strip(),
                        "category": row['category'].strip(),
                        "markup": float(row['markup']) if row['markup'] else 0.0,
                        "tax": float(row['tax']) if row['tax'] else 0.0,
                        "disposableFee": int(row['disposableFee']) if row['disposableFee'] else 0,
                        "price": int(row['price']) if row['price'] else 0,
                        "stock": parse_boolean(row.get('stock', 'True')),
                        "subsidised": parse_boolean(row.get('subsidised', 'False')),
                        "isFeatured": parse_boolean(row.get('isFeatured', 'False')),
                        "primaryUPC": int(row['primaryUPC']) if row.get('primaryUPC') else None,
                        
                        # NEW FIELDS ADDED HERE:
                        "UOM": row.get('UOM', '').strip() if row.get('UOM', '').strip() else None,
                        "isMeasuredInWeight": parse_boolean(row.get('isMeasuredInWeight', 'False'))
                    }
                    documents_to_insert.append(product_doc)
                    
                except Exception as e:
                    print(f"[!] Warning: Skipping Row {row_num} due to formatting error: {e}")
                    skipped_rows += 1
                    
    except FileNotFoundError:
        print(f"[!] Error: Could not find file '{CSV_FILE_PATH}'.")
        sys.exit(1)

    total_docs = len(documents_to_insert)
    if total_docs == 0:
        print("\nNo valid products found to insert. Exiting.")
        sys.exit(0)

    print(f"\nPrepared {total_docs} products for insertion. (Skipped {skipped_rows} bad rows).")

    # --- Test insert the FIRST document ---
    first_doc = documents_to_insert[0]
    print("\n" + "="*50)
    print("--- Testing First Document Insertion ---")
    
    try:
        result = products_collection.insert_one(first_doc)
        print(f"Successfully inserted first product with DB ID: {result.inserted_id}")
        print("\nHere is how the document looks in Python (and MongoDB):")
        pprint.pprint(first_doc)
    except Exception as e:
        print(f"\n[!] Failed to insert the first document. Error: {e}")
        sys.exit(1)

    # --- Pause and wait for user confirmation ---
    print("\n" + "="*50)
    user_input = input("Check the console output above or MongoDB. Does the data look correct? \nType 'yes' to insert the remaining items, or 'no' to abort: ").strip().lower()
    
    if user_input not in ['yes', 'y']:
        print("\nAborting the rest of the batch insertion.")
        print("Note: The first item was still saved. You may want to delete it manually.")
        sys.exit(0)

    # --- Perform Bulk Insert for the rest ---
    remaining_docs = documents_to_insert[1:]
    
    if not remaining_docs:
        print("\nNo more documents to insert.")
        sys.exit(0)

    print(f"\nPushing remaining {len(remaining_docs)} products to MongoDB. This may take a moment...")
    
    try:
        result = products_collection.insert_many(remaining_docs, ordered=False)
        print(f"\n[SUCCESS] Successfully inserted {len(result.inserted_ids)} products!")
    except BulkWriteError as bwe:
        inserted_count = bwe.details['nInserted']
        failed_count = len(bwe.details['writeErrors'])
        print(f"\n[PARTIAL SUCCESS] Inserted {inserted_count} products.")
        print(f"[!] Encountered {failed_count} database errors (likely duplicate UPCs).")
        print("\n--- Error Summary (First 5) ---")
        for error in bwe.details['writeErrors'][:5]:
            print(f" - Error at index {error['index']}: {error['errmsg']}")
        if failed_count > 5:
            print(f" ... and {failed_count - 5} more errors.")
    except Exception as e:
        print(f"\n[!] A critical error occurred during insertion: {e}")
    finally:
        client.close()
        print("\n--- Bulk Import Process Complete ---")

if __name__ == "__main__":
    main()