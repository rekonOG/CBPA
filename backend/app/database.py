from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from .config import Settings

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_DDL_DATASETS = """
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id   TEXT NOT NULL,
    dataset_type TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    updated_at   TEXT,
    payload      TEXT NOT NULL,
    PRIMARY KEY (dataset_id)
);
"""

_DDL_INVENTORY = """
CREATE TABLE IF NOT EXISTS inventory_items (
    id        TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    category  TEXT NOT NULL DEFAULT 'General',
    quantity  INTEGER NOT NULL DEFAULT 0,
    price     REAL NOT NULL DEFAULT 0.0,
    supplier  TEXT NOT NULL DEFAULT 'Unknown',
    status    TEXT NOT NULL DEFAULT 'In Stock'
);
"""

# ---------------------------------------------------------------------------
# Default inventory seed data
# ---------------------------------------------------------------------------

DEFAULT_INVENTORY_ITEMS: list[dict[str, Any]] = [
    {"id": "SKU-1001", "itemName": "Wireless Mouse",               "category": "Electronics", "quantity": 45,  "price": 29.99,  "supplier": "Logitech",   "status": "In Stock"},
    {"id": "SKU-1002", "itemName": "Mechanical Keyboard",          "category": "Electronics", "quantity": 8,   "price": 89.99,  "supplier": "Corsair",    "status": "Low Stock"},
    {"id": "SKU-1003", "itemName": "USB-C Cable (1m)",             "category": "Electronics", "quantity": 120, "price": 9.99,   "supplier": "Anker",      "status": "In Stock"},
    {"id": "SKU-1004", "itemName": "Bluetooth Speaker",            "category": "Electronics", "quantity": 0,   "price": 49.99,  "supplier": "JBL",        "status": "Out of Stock"},
    {"id": "SKU-2001", "itemName": "Ceramic Coffee Mug",           "category": "Kitchenware", "quantity": 34,  "price": 12.50,  "supplier": "MugCo",      "status": "In Stock"},
    {"id": "SKU-2002", "itemName": "Stainless Steel Water Bottle", "category": "Kitchenware", "quantity": 5,   "price": 22.00,  "supplier": "HydroFlask", "status": "Low Stock"},
    {"id": "SKU-3001", "itemName": "Ergonomic Office Chair",       "category": "Furniture",   "quantity": 12,  "price": 189.00, "supplier": "Steelcase",  "status": "In Stock"},
    {"id": "SKU-3002", "itemName": "Adjustable Standing Desk",     "category": "Furniture",   "quantity": 3,   "price": 349.00, "supplier": "Fully",      "status": "Low Stock"},
    {"id": "SKU-4001", "itemName": "Leather Journal",              "category": "Stationery",  "quantity": 50,  "price": 15.00,  "supplier": "Moleskine",  "status": "In Stock"},
    {"id": "SKU-4002", "itemName": "Gel Pen Set (12-pack)",        "category": "Stationery",  "quantity": 80,  "price": 8.50,   "supplier": "Pilot",      "status": "In Stock"},
]


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

@dataclass
class SQLiteRepository:
    """SQLite-backed repository.

    Two tables:
    - ``datasets``        — full JSON blobs for customer / product analysis results.
    - ``inventory_items`` — individual rows for efficient CRUD on inventory.
    """

    db_path: Path

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")  # better concurrency
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_schema(self) -> None:
        with self._cursor() as cur:
            cur.execute(_DDL_DATASETS)
            cur.execute(_DDL_INVENTORY)

        # Seed inventory table only if it is empty
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM inventory_items")
            count = cur.fetchone()[0]

        if count == 0:
            self.replace_inventory(DEFAULT_INVENTORY_ITEMS)

    # ------------------------------------------------------------------
    # Dataset operations (customer / product analysis JSON blobs)
    # ------------------------------------------------------------------

    def save_dataset(self, payload: dict[str, Any]) -> None:
        """Upsert a dataset document (keyed by ``datasetId``)."""
        dataset_id = payload["datasetId"]
        dataset_type = payload.get("datasetType", "unknown")
        now = datetime.now(timezone.utc).isoformat()
        blob = json.dumps(payload, default=str)

        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO datasets (dataset_id, dataset_type, created_at, updated_at, payload)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(dataset_id) DO UPDATE SET
                    dataset_type = excluded.dataset_type,
                    updated_at   = excluded.updated_at,
                    payload      = excluded.payload
                """,
                (dataset_id, dataset_type, now, now, blob),
            )

    def get_dataset(
        self,
        dataset_id: str | None = None,
        dataset_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Return a dataset document by ``dataset_id`` or the latest of a given ``dataset_type``."""
        with self._cursor() as cur:
            if dataset_id:
                cur.execute(
                    "SELECT payload FROM datasets WHERE dataset_id = ?",
                    (dataset_id,),
                )
            elif dataset_type:
                cur.execute(
                    """
                    SELECT payload FROM datasets
                    WHERE dataset_type = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (dataset_type,),
                )
            else:
                cur.execute(
                    "SELECT payload FROM datasets ORDER BY created_at DESC LIMIT 1"
                )

            row = cur.fetchone()

        if row is None:
            return None
        return json.loads(row["payload"])

    # ------------------------------------------------------------------
    # Inventory-specific row-level operations
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id":       row["id"],
            "itemName": row["item_name"],
            "category": row["category"],
            "quantity": row["quantity"],
            "price":    row["price"],
            "supplier": row["supplier"],
            "status":   row["status"],
        }

    def get_inventory_items(self) -> list[dict[str, Any]]:
        """Return all inventory items ordered by id."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM inventory_items ORDER BY id")
            return [self._row_to_item(r) for r in cur.fetchall()]

    def inventory_item_exists(self, item_id: str) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "SELECT 1 FROM inventory_items WHERE LOWER(id) = LOWER(?)",
                (item_id,),
            )
            return cur.fetchone() is not None

    def add_inventory_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Insert a new inventory item. Raises ``ValueError`` if id already exists."""
        if self.inventory_item_exists(item["id"]):
            raise ValueError(f"Item with SKU '{item['id']}' already exists.")
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO inventory_items (id, item_name, category, quantity, price, supplier, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item["itemName"],
                    item.get("category", "General"),
                    int(item.get("quantity", 0)),
                    float(item.get("price", 0.0)),
                    item.get("supplier", "Unknown"),
                    item.get("status", "In Stock"),
                ),
            )
        return item

    def update_inventory_item(
        self, item_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Apply a partial update to an inventory item. Returns updated item or None if not found."""
        col_map = {
            "itemName": "item_name",
            "category": "category",
            "quantity": "quantity",
            "price":    "price",
            "supplier": "supplier",
            "status":   "status",
        }
        set_clauses: list[str] = []
        values: list[Any] = []
        for key, sql_col in col_map.items():
            if key in updates:
                set_clauses.append(f"{sql_col} = ?")
                values.append(updates[key])

        if not set_clauses:
            # Nothing to update; just return the existing item
            with self._cursor() as cur:
                cur.execute(
                    "SELECT * FROM inventory_items WHERE LOWER(id) = LOWER(?)",
                    (item_id,),
                )
                row = cur.fetchone()
            return self._row_to_item(row) if row else None

        values.append(item_id)
        with self._cursor() as cur:
            cur.execute(
                f"UPDATE inventory_items SET {', '.join(set_clauses)} WHERE LOWER(id) = LOWER(?)",
                values,
            )
            if cur.rowcount == 0:
                return None
            cur.execute(
                "SELECT * FROM inventory_items WHERE LOWER(id) = LOWER(?)",
                (item_id,),
            )
            row = cur.fetchone()
        return self._row_to_item(row) if row else None

    def delete_inventory_item(self, item_id: str) -> bool:
        """Delete an inventory item by id. Returns True if deleted, False if not found."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM inventory_items WHERE LOWER(id) = LOWER(?)",
                (item_id,),
            )
            return cur.rowcount > 0

    def replace_inventory(self, items: list[dict[str, Any]]) -> None:
        """Replace all inventory items (used for bulk CSV/Excel upload)."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM inventory_items")
            cur.executemany(
                """
                INSERT OR REPLACE INTO inventory_items
                    (id, item_name, category, quantity, price, supplier, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        i["id"],
                        i["itemName"],
                        i.get("category", "General"),
                        int(i.get("quantity", 0)),
                        float(i.get("price", 0.0)),
                        i.get("supplier", "Unknown"),
                        i.get("status", "In Stock"),
                    )
                    for i in items
                ],
            )

    def upsert_inventory_items(self, items: list[dict[str, Any]]) -> tuple[int, int]:
        """Merge items into inventory: update existing, insert new.

        Returns ``(added_count, updated_count)``.
        """
        with self._cursor() as cur:
            cur.execute("SELECT LOWER(id) FROM inventory_items")
            existing_ids: set[str] = {r[0] for r in cur.fetchall()}

        added = 0
        updated = 0
        for item in items:
            key = item["id"].strip().lower()
            if key in existing_ids:
                # Preserve existing quantity; update metadata only
                with self._cursor() as cur:
                    cur.execute(
                        "SELECT quantity FROM inventory_items WHERE LOWER(id) = ?",
                        (key,),
                    )
                    row = cur.fetchone()
                    existing_qty = row["quantity"] if row else 0

                updates = {
                    "itemName": item["itemName"],
                    "category": item.get("category", "General"),
                    "price":    item.get("price", 0.0),
                    "supplier": item.get("supplier", "Unknown"),
                    "status":   _item_status(existing_qty),
                }
                self.update_inventory_item(item["id"], updates)
                updated += 1
            else:
                qty = int(item.get("quantity", 0))
                item["status"] = _item_status(qty)
                self.add_inventory_item(item)
                added += 1

        return added, updated


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item_status(quantity: int) -> str:
    if quantity <= 0:
        return "Out of Stock"
    if quantity <= 10:
        return "Low Stock"
    return "In Stock"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def initialize_repository(settings: Settings) -> "SQLiteRepository":
    """Create the SQLite db file, run DDL migrations, and return a ready repository."""
    db_path = settings.sqlite_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    repo = SQLiteRepository(db_path=db_path)
    repo._initialize_schema()
    print(f"[DB] SQLite database ready at {db_path}")
    return repo
