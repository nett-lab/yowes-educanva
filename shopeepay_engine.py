"""
ShopeePay Merchant Mutation Engine (Python Native)
Adopts the proven logic of hirotomasato/paygateme:
- Connects to ShopeePay Partner/Merchant transaction endpoints
- Fetches incoming credit transactions
- Matches pending orders by unique amount / reference
- Automatically settles orders and triggers fulfillment
"""

from __future__ import annotations
import asyncio
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

PAY_BASE_URL = "https://shopeepay.shopee.co.id"
EP_TRANSACTIONS = "/merchant/v1/partner-web/get-transaction-list"
COMPLETED_STATUS = 3


def parse_shopee_amount(value: Any) -> int:
    """Parses Shopee's Indonesian grouped integer format (e.g. '30.000' or 30000)
    into whole rupiah integer.
    """
    if isinstance(value, (int, float)):
        return int(value)
    if not isinstance(value, str):
        return 0

    s = value.strip().replace("Rp", "").replace(" ", "").replace(".", "")
    if s.isdigit():
        return int(s)
    return 0


class ShopeePayClient:
    def __init__(
        self,
        cookie: str = "",
        token: str = "",
        merchant_id: str = "",
        store_id: str = "",
    ):
        self.cookie = cookie or os.getenv("SHOPEE_MERCHANT_COOKIE", "").strip()
        self.token = token or os.getenv("SHOPEE_MERCHANT_TOKEN", "").strip()
        self.merchant_id = merchant_id or os.getenv("SHOPEE_MERCHANT_ID", "").strip()
        self.store_id = store_id or os.getenv("SHOPEE_STORE_ID", "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.cookie and self.token)

    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://partner.shopee.co.id",
            "Referer": "https://partner.shopee.co.id/",
            "X-Timestamp-Ms": str(int(time.time() * 1000)),
            "Cookie": self.cookie,
        }

    async def fetch_recent_transactions(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Queries the ShopeePay merchant transaction list for incoming payments."""
        if not self.is_configured:
            return []

        now_unix = int(time.time())
        # Look back up to 2 hours
        start_unix = now_unix - (2 * 3600)

        payload = {
            "data": {
                "metadata": {
                    "token": self.token,
                    "language": "id",
                    "timezone": "Asia/Jakarta",
                },
                "pageSize": limit,
                "cursor": "",
                "merchantId": self.merchant_id,
                "storeId": self.store_id,
                "filter": {
                    "startTime": start_unix,
                    "endTime": now_unix,
                    "serviceList": [1, 3],
                },
                "sorter": {"field": "createTime", "order": "descend"},
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    f"{PAY_BASE_URL}{EP_TRANSACTIONS}",
                    headers=self._headers(),
                    json=payload,
                )
                if res.status_code == 200:
                    data = res.json()
                    if data.get("code") == 0 or data.get("error") == 0:
                        inner = data.get("data", {})
                        raw_list = inner.get("list") or inner.get("transactions") or []
                        parsed_txs = []
                        for item in raw_list:
                            status = item.get("status")
                            amount_raw = item.get("amount") or item.get("netSales") or "0"
                            amount = parse_shopee_amount(amount_raw)
                            tx_id = str(item.get("transactionId") or item.get("displayTransactionId") or "")
                            
                            # Normalize
                            parsed_txs.append({
                                "id": tx_id,
                                "amount": amount,
                                "status": status,
                                "is_completed": (status == COMPLETED_STATUS),
                                "create_time": item.get("createTime", 0),
                                "raw": item,
                            })
                        return parsed_txs
                    else:
                        logger.warning("ShopeePay response error: %s", data)
                        return []
                else:
                    logger.warning("ShopeePay poll returned HTTP %s", res.status_code)
                    return []
        except Exception as exc:
            logger.error("Error polling ShopeePay transactions: %s", exc)
            return []


class UniqueAmountAllocator:
    """Allocates unique amounts (Base Amount + 1..999) to easily
    distinguish simultaneous incoming QRIS transfers without conflict.
    Includes active reservation tracking and cooldown period to prevent
    reusing an amount while recent mutations are still in lookback windows.
    """
    def __init__(self, min_code: int = 1, max_code: int = 999, cooldown_seconds: int = 7200):
        self.min_code = min_code
        self.max_code = max_code
        self.cooldown_seconds = cooldown_seconds
        self._active_allocations: Dict[int, float] = {}
        self._cooldown_allocations: Dict[int, float] = {}

    def allocate(
        self,
        base_amount: int,
        ttl_seconds: int = 900,
        reserved_amounts: Optional[set[int]] = None,
    ) -> tuple[int, int]:
        self.clean_expired()
        now = time.time()
        reserved = reserved_amounts or set()

        for code in range(self.min_code, self.max_code + 1):
            candidate = base_amount + code
            if candidate in self._active_allocations:
                continue
            if candidate in self._cooldown_allocations:
                continue
            if candidate in reserved:
                continue

            self._active_allocations[candidate] = now + ttl_seconds
            return candidate, code

        # If all candidates in 1..999 are occupied/cooldown, fallback to code 0
        return base_amount, 0

    def release(self, amount: int, into_cooldown: bool = True) -> None:
        self._active_allocations.pop(amount, None)
        if into_cooldown:
            self._cooldown_allocations[amount] = time.time() + self.cooldown_seconds

    def cancel(self, amount: int) -> None:
        """Cancel allocation without cooldown if cancelled before user payment."""
        self._active_allocations.pop(amount, None)

    def clean_expired(self) -> None:
        now = time.time()
        self._active_allocations = {
            amt: exp for amt, exp in self._active_allocations.items() if exp > now
        }
        self._cooldown_allocations = {
            amt: exp for amt, exp in self._cooldown_allocations.items() if exp > now
        }

    def cleanup(self) -> None:
        self.clean_expired()
