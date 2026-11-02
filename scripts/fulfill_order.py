"""
Fulfill and settle web or bot order manually or via ProdSeller.
Usage:
    python scripts/fulfill_order.py [order_id_or_token] [--credentials "account data"] [--force]
Example:
    python scripts/fulfill_order.py 4f0f3de8a3b197bc6534b8a6edbfca59
"""

import argparse
import asyncio
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from telegram_bot import (
    _load_env_file,
    _prodseller_request_sync,
    _extract_order_delivery,
    _PRODUCT_CATALOG,
    DATABASE_PATH,
)

_load_env_file()


def fulfill(order_target: str, manual_credentials: str | None = None, force: bool = False):
    db_file = DATABASE_PATH
    if not db_file.exists():
        print(f"[!] Database file not found at: {db_file}")
        return

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row

    # Find by ID or order_token
    row = None
    if order_target.isdigit():
        row = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (int(order_target),)).fetchone()
    if not row:
        row = conn.execute("SELECT * FROM payment_requests WHERE order_token = ?", (order_target,)).fetchone()
    if not row:
        # Search by partial token or reference
        row = conn.execute("SELECT * FROM payment_requests WHERE order_token LIKE ? OR reference LIKE ?", 
                           (f"%{order_target}%", f"%{order_target}%")).fetchone()

    if not row:
        print(f"[!] Order not found for target: {order_target}")
        conn.close()
        return

    order = dict(row)
    print("=" * 60)
    print(f"📦 FOUND ORDER #{order['id']}")
    print(f"Token    : {order.get('order_token')}")
    print(f"Product  : {order.get('product_key')}")
    print(f"Amount   : {order.get('amount')} (raw: {order.get('raw_amount')})")
    print(f"Current  : {order.get('status')}")
    print(f"Created  : {order.get('created_at')}")
    print(f"Contact  : {order.get('email')}")
    print("=" * 60)

    if order["status"] == "approved" and not force:
        print("[*] Order is already approved!")
        print("Delivered credentials:")
        print(order.get("delivered_data") or "(No delivered data)")
        conn.close()
        return

    delivered_data = manual_credentials or ""
    provider_order_id = order.get("provider_order_id") or f"MANUAL-{order['id']}"

    if not delivered_data:
        pkey = order.get("product_key") or "primevideo"
        print(f"[*] Ordering product '{pkey}' from ProdSeller...")

        cfg = _PRODUCT_CATALOG.get(pkey, {})
        env_pid = cfg.get("prodseller_id_env")
        product_id = os.getenv(env_pid, "") if env_pid else ""
        if not product_id:
            product_id = cfg.get("prodseller_default_id", "")

        if not product_id:
            print(f"[!] No ProdSeller product ID found for {pkey}")
            conn.close()
            return

        body = {"productId": product_id, "quantity": 1}
        contact_email = order.get("email")
        if contact_email and "@" in contact_email:
            body["email"] = contact_email.strip()

        try:
            res = _prodseller_request_sync("POST", "/orders", json=body)
            print("[+] ProdSeller order created successfully:", res.get("orderId"))
            provider_order_id = str(res.get("orderId") or f"ORD-{order['id']}")
            delivered_text, file_url = _extract_order_delivery(res)
            if file_url and file_url not in delivered_text:
                delivered_text = f"{delivered_text}\n\nLink / Unduh File: {file_url}" if delivered_text else file_url
            delivered_data = delivered_text
        except Exception as exc:
            print(f"[!] Error placing order on ProdSeller: {exc}")
            conn.close()
            return

    # Update database
    now_iso = datetime.now().isoformat()
    conn.execute(
        """
        UPDATE payment_requests
        SET status = 'approved',
            provider_order_id = ?,
            delivered_data = ?,
            reviewed_at = ?
        WHERE id = ?
        """,
        (provider_order_id, delivered_data, now_iso, order["id"]),
    )
    conn.commit()
    conn.close()

    print("\n✅ ORDER SUCCESSFULLY FULFILLED & APPROVED!")
    print(f"Status           : approved")
    print(f"Provider Order ID: {provider_order_id}")
    print("-" * 60)
    print("🔑 DELIVERED CREDENTIALS:")
    print(delivered_data)
    print("-" * 60)
    print(f"🌐 Buyer can now view this instantly at:")
    print(f"https://idasyari.web.id/api/order/status?token={order.get('order_token')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fulfill order manually or via ProdSeller")
    parser.add_argument("target", nargs="?", default="4f0f3de8a3b197bc6534b8a6edbfca59", help="Order ID or token")
    parser.add_argument("--credentials", "-c", default=None, help="Manual account credentials string")
    parser.add_argument("--force", "-f", action="store_true", help="Force fulfill even if already approved")
    args = parser.parse_args()

    fulfill(args.target, manual_credentials=args.credentials, force=args.force)
