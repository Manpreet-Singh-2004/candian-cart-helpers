import os
import sys
import csv
import re
from typing import Dict, List, Set, TypedDict, Union
from dotenv import load_dotenv

class ProductData(TypedDict, total=False):
    storeId: str
    name: str
    description: str
    category: str
    markup: int
    tax: float
    disposableFee: Union[int, str]
    price: int
    stock: bool
    subsidised: bool
    isFeatured: bool
    primaryUPC: str
    UOM: str
    isMeasuredInWeight: bool

SUBSIDISED_CATEGORIES: Set[str] = {"Fruits", "Vegetables", "Dairy"}

def convert_to_cents(amount_str: str) -> int:
    """Safely converts string dollar representations to integer cents."""
    try:
        if not amount_str:
            return 0
        return int(round(float(amount_str) * 100))
    except (ValueError, TypeError):
        return 0

def extract_uom_from_name(name: str) -> dict:
    valid_weight_units = {"KG", "G", "GM", "GMS", "LB", "LBS", "OZ"}
    match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$', name.upper().strip())
    
    result = {"uom": "", "is_weight": False}
    
    if match:
        unit = match.group(2)
        if unit in valid_weight_units:
            if unit in ["GM", "GMS"]: unit = "G"
            if unit == "LBS": unit = "LB"
            
            result["uom"] = unit
            result["is_weight"] = True
            
    return result

def process_csvs(categories_filepath: str, inventory_filepath: str, output_filepath: str, failed_filepath: str, store_id: str, global_markup: int) -> None:
    print("\n🚀 Merging data (Processing ALL items, strict auditing enabled)...")

    headers: List[str] = [
        "storeId", "name", "description", "category", "markup",
        "tax", "disposableFee", "price", "stock", "subsidised",
        "isFeatured", "primaryUPC", "UOM", "isMeasuredInWeight"
    ]
    
    failed_headers: List[str] = ["primaryUPC", "name", "failure_reason", "raw_data"]

    valid_products: List[ProductData] = []
    failed_entities: List[dict] = []
    
    # Step 1: Load Inventory Data with strict row handling
    inventory_data = {}
    try:
        with open(inventory_filepath, mode='r', encoding='utf-8-sig') as inv_file:
            reader = csv.reader(inv_file)
            
            # Skip the garbage title row: "INVENTORY,,,,,,,,,,,,"
            next(reader, None)
            
            # Extract the actual header row
            actual_headers = next(reader, None)
            if not actual_headers or 'Item No' not in actual_headers:
                print("❌ FATAL: Could not find valid headers in inventory file. Check file structure.")
                sys.exit(1)
                
            # Create a DictReader using the explicit headers we just grabbed
            inv_reader = csv.DictReader(inv_file, fieldnames=actual_headers)
            
            for row in inv_reader:
                item_no = row.get('Item No')
                # This check skips sub-headers like "BAG,,,,,,,,,,,," because 'Item No' will be None or empty
                if item_no and item_no.strip():
                    inventory_data[item_no.strip()] = row
                    
    except FileNotFoundError:
        print(f"❌ FATAL: Inventory file not found at {inventory_filepath}")
        sys.exit(1)

    # Step 2: Merge Data
    try:
        with open(categories_filepath, mode='r', encoding='utf-8-sig') as cat_file:
            cat_reader = csv.DictReader(cat_file)

            for row_num, cat_row in enumerate(cat_reader, start=2):
                
                upc = cat_row.get('primaryUPC', '').strip()
                name = cat_row.get('name', '').strip()
                category = cat_row.get('category', '').strip()
                
                try:
                    if not category:
                        failed_entities.append({"primaryUPC": upc, "name": name, "failure_reason": "Missing Category", "raw_data": str(cat_row)})
                        continue

                    if not upc or not name:
                        failed_entities.append({"primaryUPC": upc, "name": name, "failure_reason": "Missing UPC or Name", "raw_data": str(cat_row)})
                        continue

                    inv_row = inventory_data.get(upc)
                    
                    if not inv_row:
                        failed_entities.append({"primaryUPC": upc, "name": name, "failure_reason": "Missing in Inventory File", "raw_data": str(cat_row)})
                        continue

                    # -- Core Pricing Logic Applied Here --
                    cost_cents = convert_to_cents(inv_row.get('Cost', '0'))
                    price_cents = convert_to_cents(inv_row.get('Price', '0'))
                    
                    if cost_cents > 0:
                        final_price = cost_cents
                        is_in_stock = True
                    elif price_cents > 0:
                        final_price = price_cents
                        is_in_stock = True
                    else:
                        final_price = 0
                        is_in_stock = False

                    deposit_cents = convert_to_cents(inv_row.get('Deposit', '0'))
                    
                    try:
                        tax_rate = float(cat_row.get('tax', '0'))
                    except ValueError:
                        tax_rate = 0.0

                    uom_data = extract_uom_from_name(name)

                    product: ProductData = {
                        "storeId": store_id,
                        "name": name,
                        "description": "",
                        "category": category,
                        "markup": global_markup,
                        "tax": tax_rate,
                        "disposableFee": deposit_cents if deposit_cents > 0 else "",
                        "price": final_price,
                        "stock": is_in_stock,
                        "subsidised": category in SUBSIDISED_CATEGORIES,
                        "isFeatured": False,
                        "primaryUPC": upc
                    }

                    if uom_data["is_weight"]:
                        product["UOM"] = uom_data["uom"]
                        product["isMeasuredInWeight"] = True

                    valid_products.append(product)

                except Exception as row_error:
                    failed_entities.append({
                        "primaryUPC": upc, 
                        "name": name, 
                        "failure_reason": f"Exception processing row: {str(row_error)}", 
                        "raw_data": str(cat_row)
                    })

        # Output Valid Products
        with open(output_filepath, mode='w', encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(valid_products)
            
        # Output Failed Entities
        if failed_entities:
            with open(failed_filepath, mode='w', encoding='utf-8', newline='') as failfile:
                fail_writer = csv.DictWriter(failfile, fieldnames=failed_headers)
                fail_writer.writeheader()
                fail_writer.writerows(failed_entities)

        print("-" * 40)
        print("📊 Merge Complete:")
        print(f"  ✅ Successfully processed: {len(valid_products)}")
        print(f"  ❌ Failed entities isolated: {len(failed_entities)} (Check {failed_filepath})")
        print("-" * 40)

    except FileNotFoundError:
        print(f"❌ FATAL: Categories file not found at {categories_filepath}")
        sys.exit(1)


if __name__ == "__main__":
    load_dotenv()

    STORE_ID = os.getenv("STORE_ID")
    MARKUP_ENV = os.getenv("MARKUP_PERCENTAGE")

    if not STORE_ID:
        print("❌ ERROR: STORE_ID must be set in the .env file.")
        sys.exit(1)

    if not MARKUP_ENV:
        print("⚠️ WARNING: MARKUP_PERCENTAGE not found in .env. Defaulting to 30%.")
        markup_val = 30
    else:
        try:
            markup_val = int(float(MARKUP_ENV))
        except ValueError:
            print(f"⚠️ WARNING: Invalid MARKUP_PERCENTAGE format '{MARKUP_ENV}'. Defaulting to 30.")
            markup_val = 30

    process_csvs(
        categories_filepath='csvDatatoModel/sunfarm/data/category.csv', 
        inventory_filepath='csvDatatoModel/sunfarm/data/sunfarm.csv',
        output_filepath='csvDatatoModel/sunfarm/data/final_merged_products.csv',
        failed_filepath='csvDatatoModel/sunfarm/data/failed_entities.csv',
        store_id=STORE_ID,
        global_markup=markup_val
    )