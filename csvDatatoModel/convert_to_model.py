import os
import sys
import csv
import re
from typing import Dict, List, Set, TypedDict, Union
from dotenv import load_dotenv

# Define TypedDict to completely avoid 'Any' type
class ProductData(TypedDict):
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
    primaryUPC: int
    UOM: str
    isMeasuredInWeight: bool

# O(1) Dictionary for fast category mapping
CATEGORY_MAP: Dict[str, str] = {
    "BEARD PRODUCTS": "Personal Care",
    "BODY SOAP": "Personal Care",
    "BODY SPRAY & POWDER": "Personal Care",
    "FACE CREAM": "Personal Care",
    "FACE WASH": "Personal Care",
    "FACIAL PRODUCTS": "Personal Care",
    "HAIR DYE": "Personal Care",
    "HAIR OIL": "Personal Care",
    "SHAMPOO": "Personal Care",
    "WAX & BLEACH": "Personal Care",
    "PERFUME PRODUCTS": "Personal Care",
    "CHANA AND PEANUTS": "Snacks",
    "SNACKS": "Snacks",
    "COOKIES": "Snacks",
    "POHA AND MUMRA": "Snacks",
    "DRINKS & JUICE": "Beverages",
    "TEA & COFFEE": "Tea & Coffee",
    "COOKING MIXES": "Instant Foods",
    "INSTANT MIX": "Instant Foods",
    "SPICES": "Spices",
    "DRY MASALA": "Spices",
    "REGULAR SPICES": "Spices",
    "HERBS": "Spices",
    "PICKLE, CHUTNEY & PASTE": "Pickles & Chutneys",
    "SAUCES": "Sauces & Condiments",
    "PASTES & CHUTNEY": "Pickles & Chutneys",
    "DRY FRUITS": "Dry Fruits & Nuts",
    "MILK POWDER": "Dairy",
    "DAIRY": "Dairy",
    "FROZEN APPETIZER": "Frozen Foods",
    "FROZEN NAAN AND PARATHA": "Frozen Foods",
    "FROZEN PRODUCTS": "Frozen Foods",
    "GENERAL": "Household",
    "HOME USE PRODUCTS": "Household",
    "BAR CODED": "Pooja / Religious Items",
    "RELEGIOUS": "Pooja / Religious Items",
    "GOD STUFF": "Pooja / Religious Items",
    "POOJA ITEMS": "Pooja / Religious Items",
    "JK RELIGIOUS ITEMS": "Pooja / Religious Items",
    "PAN PRODUCTS": "Other",
    "MOUTH FRESHNER": "Other",
    "FOOD SERVICE": "Instant Foods",
    "UTENSILS": "Utensils",
    "KITCHEN UTENSILS": "Utensils",
    "FLOUR": "Flour & Atta",
    "OIL": "Oil & Ghee",
    "EDIBLE OIL": "Oil & Ghee",
    "CANDY": "Sweets & Mithai",
    "CONFECTIONERY": "Sweets & Mithai",
    "PRODUCE": "Vegetables",
    "RADHE STORE": "Vegetables"
}

# Categories eligible for subsidies
SUBSIDISED_CATEGORIES: Set[str] = {"Fruits", "Vegetables", "Dairy"}

def get_tax_rate(tax_code_name: str) -> float:
    """Returns correct float for Tax based on string matching the Mongoose enum."""
    tax = tax_code_name.upper().strip()
    if tax == "GST":
        return 0.05
    if tax == "HST":
        return 0.12
    if tax == "PST":
        return 0.07
    if tax in ["GST+PST", "GST + PST"]:
        return 0.12
    return 0.0  # Captures "no" or anything else

def convert_to_cents(amount_str: str) -> int:
    """Safely converts string price representations to integer cents."""
    try:
        if not amount_str:
            return 0
        return int(round(float(amount_str) * 100))
    except (ValueError, TypeError):
        return 0

def is_measured_in_weight(uom_str: str) -> bool:
    """
    Determines if a product is measured in weight based on its UOM string.
    Accounts for Pieces (PC/PCS) and Volume (ML/LTR) not being weight.
    """
    if not uom_str:
        return False
    
    uom_upper = uom_str.upper().strip()
    
    # 1. Explicitly filter out volume and item counts
    non_weight_flags = ["PC", "PCS", "PIECE", "CASE", "ML", "LTR", "LTS"]
    for flag in non_weight_flags:
        if flag in uom_upper:
            return False
            
    # Safely handle standalone "L" for Liters (e.g. "1 L", "2L" vs "LB")
    if re.search(r'\bL\b', uom_upper) or re.search(r'\d+L\b', uom_upper):
        return False

    # 2. Check for actual weight terminology
    weight_flags = ["KG", "LB", "LBS", "GM", "GMS", "OZ"]
    for flag in weight_flags:
        if flag in uom_upper:
            return True
            
    # Safely handle standalone "G" for Grams (e.g. "100 G", "200G")
    if re.search(r'\bG\b', uom_upper) or re.search(r'\d+G\b', uom_upper):
        return True
        
    return False

def process_csv(input_filepath: str, output_filepath: str, store_id: str, markup_percentage: int) -> None:
    print("\n🚀 Beginning process now...")

    headers: List[str] = [
        "storeId", "name", "description", "category", "markup",
        "tax", "disposableFee", "price", "stock", "subsidised",
        "isFeatured", "primaryUPC", "UOM", "isMeasuredInWeight"
    ]

    valid_products: List[ProductData] = []

    # Tracking metrics
    total_rows: int = 0
    error_count: int = 0
    missed_categories: Set[str] = set()

    try:
        with open(input_filepath, mode='r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                total_rows += 1

                try:
                    name = row.get('ItemName', '').strip()

                    # Early exit if there is no name
                    if not name:
                        error_count += 1
                        continue

                    # 1. Category Mapping Tracking
                    raw_category = row.get('CategoryName', '').strip()
                    mapped_category = CATEGORY_MAP.get(raw_category.upper())
                    
                    if not mapped_category:
                        mapped_category = "Other"
                        if raw_category:
                            missed_categories.add(raw_category)

                    # 2. Subsidised check
                    is_subsidised = mapped_category in SUBSIDISED_CATEGORIES

                    # 3. Extract Core Data
                    try:
                        primary_upc = int(row.get('PrimaryUpc', '0'))
                    except ValueError:
                        primary_upc = 0

                    # Utilize Cost as the primary price base
                    cost_cents = convert_to_cents(row.get('Cost', '0'))
                    disposable_fee_cents = convert_to_cents(row.get('BtlDeposit', '0'))

                    # 4. Stock & Price Logic
                    sts_status = row.get('STS', '').strip().upper()
                    is_in_stock = (sts_status == 'ACTIVE')

                    # If cost is 0, forcibly set stock to False
                    if cost_cents == 0:
                        is_in_stock = False

                    # 5. Extract UOM & Use the new Regex to determine weight
                    uom_val = row.get('UOM', '').strip()
                    is_weight = is_measured_in_weight(uom_val)

                    # 6. Construct Product Mapping utilizing TypedDict
                    product: ProductData = {
                        "storeId": store_id,
                        "name": name,
                        "description": row.get('ItemDesc', '').strip(),
                        "category": mapped_category,
                        "markup": markup_percentage, 
                        "tax": get_tax_rate(row.get('TaxCodeName', '')),
                        "disposableFee": disposable_fee_cents if disposable_fee_cents > 0 else "",
                        "price": cost_cents, # This stores the 'Cost' mapped from the CSV
                        "stock": is_in_stock,
                        "subsidised": is_subsidised,
                        "isFeatured": False,
                        "primaryUPC": primary_upc,
                        "UOM": uom_val,
                        "isMeasuredInWeight": is_weight
                    }

                    valid_products.append(product)

                except Exception as row_error:
                    print(f"⚠️ Error on row {total_rows}: {row_error}")
                    error_count += 1

        # Write output to CSV
        with open(output_filepath, mode='w', encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(valid_products) # type: ignore

        # --- LOGGING OUTPUT ---
        print("-" * 40)
        print("📊 Processing Summary:")
        print(f"  Total entities found:       {total_rows}")
        print(f"  ✅ Successfully processed: {len(valid_products)}")
        print(f"  ❌ Errors/Skipped items:   {error_count}")

        if missed_categories:
            print(f"\n⚠️  Missed Classifications (Defaulted to 'Other'):")
            for cat in missed_categories:
                print(f"    - {cat}")
        else:
            print("\n✨ All categories mapped successfully!")

        print("-" * 40)
        print(f"Output saved to: {output_filepath}\n")

    except FileNotFoundError:
        print(f"❌ ERROR: Could not find the input file: {input_filepath}")
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")

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
            markup_val = int(float(MARKUP_ENV) * 100)
        except ValueError:
            print(f"⚠️ WARNING: Invalid MARKUP_PERCENTAGE format '{MARKUP_ENV}'. Defaulting to 30%.")
            markup_val = 30

    process_csv(
        input_filepath='csvDatatoModel/data/Item_List.csv',
        output_filepath='csvDatatoModel/data/mapped_products.csv',
        store_id=STORE_ID,
        markup_percentage=markup_val
    )