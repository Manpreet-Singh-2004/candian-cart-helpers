import os
import sys
from typing import Optional, List, Tuple, TypedDict

from dotenv import load_dotenv, find_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database

# Load .env by searching upward from this script's location
dotenv_path = find_dotenv(usecwd=True)

if dotenv_path:
    load_dotenv(dotenv_path)
else:
    print("Warning: No .env file found.")

# ---------------------------------------------------------
# 1. Typing
# ---------------------------------------------------------
class OrderDocument(TypedDict, total=False):
    _id: object
    cartTotal: int
    BaseTotal: int
    TotalGST: int
    TotalPST: int
    TotalDisposableFee: int
    subsidy: int
    subsidyUsed: int
    storeProfit: Optional[int]
    platformProfit: Optional[int]


# ---------------------------------------------------------
# 2. Calculation logic
# ---------------------------------------------------------
def round_(n: float) -> int:
    return round(n)


def calculate_profits(order: OrderDocument) -> Tuple[int, int]:
    cart_total: float = order.get("cartTotal", 0) or 0
    base_total: float = order.get("BaseTotal", 0) or 0
    total_gst: float = order.get("TotalGST", 0) or 0
    total_pst: float = order.get("TotalPST", 0) or 0
    disposable_fee: float = order.get("TotalDisposableFee", 0) or 0
    subsidy: float = order.get("subsidy", 0) or 0
    subsidy_used: float = order.get("subsidyUsed", 0) or 0

    if cart_total <= 0:
        return 0, 0

    paid_after_subsidy = cart_total - (subsidy - subsidy_used)
    total_tax = total_gst + total_pst
    profit_margin = paid_after_subsidy - base_total - total_tax - disposable_fee

    store_profit_raw = profit_margin / 2
    platform_profit_raw = profit_margin / 2

    return round_(store_profit_raw), round_(platform_profit_raw)


# ---------------------------------------------------------
# 3. Migration runner
# ---------------------------------------------------------
def migrate_orders(dry_run: bool = False) -> None:
    mongo_uri: Optional[str] = os.getenv("MONGO_URI_PRODUCTION")
    db_name: Optional[str] = os.getenv("DB_NAME_IN_PROD")

    if not mongo_uri:
        print("Error: MONGO_URI environment variable is not set.")
        print(f".env found: {dotenv_path if dotenv_path else 'No'}")
        sys.exit(1)

    if not db_name:
        print("Error: DB_NAME_IN_PROD environment variable is not set.")
        print(f".env found: {dotenv_path if dotenv_path else 'No'}")
        sys.exit(1)

    client: MongoClient = MongoClient(mongo_uri)
    db: Database = client[db_name]
    orders_collection: Collection = db["orders"]

    query = {
        "status": "completed",
        "$or": [
            {"storeProfit": {"$exists": False}},
            {"platformProfit": {"$exists": False}},
            {"storeProfit": None},
            {"platformProfit": None},
        ],
    }

    total_matching = orders_collection.count_documents(query)
    print(f"Found {total_matching} completed orders needing a storeProfit/platformProfit backfill.")

    if total_matching == 0:
        client.close()
        return

    bulk_updates: List[UpdateOne] = []
    total_updated = 0
    batch_size = 500

    for order_data in orders_collection.find(query):
        order: OrderDocument = order_data  # type: ignore

        store_profit, platform_profit = calculate_profits(order)

        if dry_run:
            print(
                f"[dry-run] _id={order['_id']} "
                f"storeProfit={store_profit} "
                f"platformProfit={platform_profit}"
            )
            continue

        bulk_updates.append(
            UpdateOne(
                {"_id": order["_id"]},
                {
                    "$set": {
                        "storeProfit": store_profit,
                        "platformProfit": platform_profit,
                    }
                },
            )
        )

        if len(bulk_updates) >= batch_size:
            result = orders_collection.bulk_write(bulk_updates)
            total_updated += result.modified_count
            print(f"Processed batch. Total updated so far: {total_updated}")
            bulk_updates.clear()

    if bulk_updates:
        result = orders_collection.bulk_write(bulk_updates)
        total_updated += result.modified_count

    print(f"Migration completed. Total records updated: {total_updated}")

    client.close()


if __name__ == "__main__":
    dry_run_flag = "--dry-run" in sys.argv
    migrate_orders(dry_run=dry_run_flag)