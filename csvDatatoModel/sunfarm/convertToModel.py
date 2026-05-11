import os
import sys
import csv
import re
from typing import Dict, List, Set, TypedDict, Union, Optional
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
    primaryUPC: str  # CHANGED TO STRING - Update your Mongoose schema!
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
    """
    Analyzes the product name to extract weight and UOM.
    Returns a dict with valid UOM and boolean for weight measurement.
    """
    valid_weight_units = {"KG", "G", "GM", "GMS", "LB", "LBS", "OZ"}
    
    # Matches patterns like 1.5KG, 10 KG, 500G
    match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$', name.upper().strip())
    
    result = {"uom": "", "is_weight": False}
    
    if match:
        unit = match.group(2)
        if unit in valid_weight_units:
            # Normalize variations
            if unit in ["GM", "GMS"]: unit = "G"
            if unit == "LBS": unit = "LB"
            
            result["uom"] = unit
            result["is_weight"] = True
            
    return result

def process_csvs(categories_filepath: str, inventory_filepath: str, output_filepath: str, store_id: str) -> None:
    print("\n🚀 Stress-testing and merging data...")

    headers: List[str] = [
        "storeId", "name", "description", "category", "markup",
        "tax", "disposableFee", "price", "stock", "subsidised",
        "isFeatured", "primaryUPC", "UOM", "isMeasuredInWeight"
    ]

    valid_products: List[ProductData] = []
    error_count: int = 0
    
    # Step 1: Load Inventory Data into Memory for O(1) Lookups
    inventory_data = {}
    try:
        with open(inventory_filepath, mode='r', encoding='utf-8-sig') as inv_file:
            # Skip the first two header rows from your specific format
            next(inv_file) 
            next(inv_file)
            
            inv_reader = csv.DictReader(inv_file)
            for row in inv_reader:
                item_no = row.get('Item No', '').strip()
                if item_no:
                    inventory_data[item_no] = row
    except FileNotFoundError:
        print(f"❌ FATAL: Inventory file not found at {inventory_filepath}")
        sys.exit(1)

    # Step 2: Process Categories File and Merge
    try:
        with open(categories_filepath, mode='r', encoding='utf-8-sig') as cat_file:
            cat_reader = csv.DictReader(cat_file)

            for row_num, cat_row in enumerate(cat_reader, start=2):
                try:
                    upc = cat_row.get('primaryUPC', '').strip()
                    name = cat_row.get('name', '').strip()
                    category = cat_row.get('category', '').strip()
                    
                    if not upc or not name:
                        error_count += 1
                        continue

                    # Look up matching inventory record
                    inv_row = inventory_data.get(upc)
                    
                    if not inv_row:
                        print(f"⚠️ Warning: UPC {upc} found in categories but missing in inventory. Skipping.")
                        error_count += 1
                        continue

                    # -- Core Data Extraction --
                    
                    # We take Base Cost as 'price' in cents (Mongoose schema)
                    base_cost_cents = convert_to_cents(inv_row.get('Cost', '0'))
                    
                    # Take Margin as 'markup' integer
                    try:
                        markup = int(round(float(inv_row.get('Margin', '0'))))
                    except ValueError:
                        markup = 30 # Fallback
                        
                    deposit_cents = convert_to_cents(inv_row.get('Deposit', '0'))
                    
                    # Parse tax from categories file
                    try:
                        tax_rate = float(cat_row.get('tax', '0'))
                    except ValueError:
                        tax_rate = 0.0

                    # Parse stock logically: If cost is 0 or stock <= 0, it's False
                    try:
                        stock_qty = float(inv_row.get('Stock', '0'))
                        is_in_stock = stock_qty > 0 and base_cost_cents > 0
                    except ValueError:
                        is_in_stock = False

                    # UOM Extraction
                    uom_data = extract_uom_from_name(name)

                    product: ProductData = {
                        "storeId": store_id,
                        "name": name,
                        "description": "", # Left blank as per new data
                        "category": category,
                        "markup": markup,
                        "tax": tax_rate,
                        "disposableFee": deposit_cents if deposit_cents > 0 else "",
                        "price": base_cost_cents,
                        "stock": is_in_stock,
                        "subsidised": category in SUBSIDISED_CATEGORIES,
                        "isFeatured": False,
                        "primaryUPC": upc # Storing as String to prevent crash!
                    }

                    if uom_data["is_weight"]:
                        product["UOM"] = uom_data["uom"]
                        product["isMeasuredInWeight"] = True

                    valid_products.append(product)

                except Exception as row_error:
                    print(f"⚠️ Error processing row {row_num} (UPC: {cat_row.get('primaryUPC')}): {row_error}")
                    error_count += 1

        # Step 3: Write Output
        with open(output_filepath, mode='w', encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(valid_products)

        print("-" * 40)
        print("📊 Merge Complete:")
        print(f"  ✅ Successfully matched & processed: {len(valid_products)}")
        print(f"  ❌ Errors/Skipped items:           {error_count}")
        print("-" * 40)
        print(f"Output saved to: {output_filepath}\n")

    except FileNotFoundError:
        print(f"❌ FATAL: Categories file not found at {categories_filepath}")
        sys.exit(1)


if __name__ == "__main__":
    load_dotenv()

    STORE_ID = os.getenv("STORE_ID")

    if not STORE_ID:
        print("❌ ERROR: STORE_ID must be set in the .env file.")
        sys.exit(1)

    process_csvs(
        categories_filepath='csvDatatoModel/sunfarm/data/category.csv', 
        inventory_filepath='csvDatatoModel/sunfarm/data/sunfarm.csv',
        output_filepath='csvDatatoModel/sunfarm/data/final_merged_products.csv',
        store_id=STORE_ID
    )