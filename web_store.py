"""
Web Store Module - Mobile Web App Digital Store for Botkeep Domain Integration
Styled like Lynk.id with luxury dark glassmorphism aesthetics.
Seamlessly integrates with Yowes Telegram Bot and Botkeep platform.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import socket
import sys
import threading
import time
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

import qris_engine
import shopeepay_engine

logger = logging.getLogger("web_store")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def _load_env_file() -> None:
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_file):
        return
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

_load_env_file()

# Default metadata
STORE_NAME = os.getenv("STORE_NAME", "Yowes Digital Store")
STORE_TAGLINE = os.getenv("STORE_TAGLINE", "Official Digital Store • Instant Automated Delivery 24/7 • Garansi Aktif")
DEFAULT_SERVER_PORT = int(os.getenv("SERVER_PORT") or os.getenv("PORT") or 8080)
DEFAULT_HOST = "0.0.0.0"

# Category mappings for Lynk.id style tabs
PRODUCT_CATEGORIES: dict[str, str] = {
    "docs": "Edukasi",
    "gemini": "AI Tools",
    "chatgpt_k12": "AI Tools",
    "codex": "AI Tools",
    "claude": "AI Tools",
    "notion": "Produktivitas",
    "office365": "Produktivitas",
    "figma": "Produktivitas",
    "ilovepdf": "Produktivitas",
    "outlook": "Produktivitas",
    "adobe_express": "Produktivitas",
    "capcut": "Produktivitas",
    "spotify": "Hiburan",
    "appletv": "Hiburan",
    "primevideo": "Hiburan",
    "scribd": "Edukasi",
}

# Subtitle / highlights for each product
PRODUCT_HIGHLIGHTS: dict[str, str] = {
    "docs": "Generate Akun & Dokumen Canva Edu",
    "gemini": "18 Bulan Plan • 5TB Cloud Storage • Private",
    "chatgpt_k12": "Akun Edu 2 Tahun • Akses Model Plus",
    "codex": "API Codex 10M Token • 1 Day",
    "claude": "Claude AI Pro Access • Fast API",
    "notion": "Notion Plus 12 Bulan • Unlimited Blocks",
    "office365": "Office 365 Plus 1 Year • 5TB OneDrive",
    "figma": "Figma Pro Edu 2 Years • Unlimited Projects",
    "ilovepdf": "Full Access Web/Mobile/Desktop • AI Tools",
    "outlook": "Full Email Access + OTP Link",
    "appletv": "12 Months Activation Link • 48H Hold Warranty",
    "adobe_express": "12 Months Premium • Direct Redeem Link",
    "capcut": "CapCut Pro Account • All Features",
    "spotify": "Spotify Premium 1 Bulan • Full Warranty",
    "primevideo": "Prime Video 1 Bulan • 4K HDR",
    "scribd": "Scribd Premium 1 Bulan • Full Warranty",
}

# Modern 3D Tactile App Icon Tile Themes (iOS / Squircle theme with rich gradients & crisp white SVGs)
PRODUCT_STYLE_THEMES: dict[str, dict[str, str]] = {
    "docs": {
        "gradient": "linear-gradient(135deg, #00c4cc 0%, #3b82f6 50%, #7c3aed 100%)",
        "shadow": "rgba(0, 196, 204, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>',
    },
    "gemini": {
        "gradient": "linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #2563eb 100%)",
        "shadow": "rgba(99, 102, 241, 0.5)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="#ffffff"><path d="M12 2C12 7.5 7.5 12 2 12C7.5 12 12 16.5 12 22C12 16.5 16.5 12 22 12C16.5 12 12 7.5 12 2Z"/></svg>',
    },
    "chatgpt_k12": {
        "gradient": "linear-gradient(135deg, #10a37f 0%, #059669 100%)",
        "shadow": "rgba(16, 163, 127, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="#ffffff"><path d="M12 2a10 10 0 0 0-7.07 17.07l.07.07L12 22l7-2.86.07-.07A10 10 0 0 0 12 2zm0 3.5a6.5 6.5 0 0 1 5.3 10.27l-5.3 2.16-5.3-2.16A6.5 6.5 0 0 1 12 5.5z"/></svg>',
    },
    "codex": {
        "gradient": "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
        "shadow": "rgba(2, 132, 199, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="#ffffff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    },
    "claude": {
        "gradient": "linear-gradient(135deg, #d97706 0%, #b45309 100%)",
        "shadow": "rgba(217, 119, 6, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="#ffffff"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round"/></svg>',
    },
    "notion": {
        "gradient": "linear-gradient(135deg, #334155 0%, #0f172a 100%)",
        "shadow": "rgba(51, 65, 85, 0.5)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="#ffffff"><path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H18a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6.5A2.5 2.5 0 0 1 4 19.5v-15zM7 6v12l5.5-6.5V18h2V6l-5.5 6.5V6H7z"/></svg>',
    },
    "office365": {
        "gradient": "linear-gradient(135deg, #ea580c 0%, #c2410c 100%)",
        "shadow": "rgba(234, 88, 12, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="#ffffff"><rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/></svg>',
    },
    "figma": {
        "gradient": "linear-gradient(135deg, #a855f7 0%, #ec4899 50%, #f97316 100%)",
        "shadow": "rgba(236, 72, 153, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="#ffffff"><path d="M8 2h8a4 4 0 0 1 0 8H8a4 4 0 0 1 0-8zm0 8h4a4 4 0 0 1 0 8H8a4 4 0 0 1 0-8zm4 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8z"/></svg>',
    },
    "ilovepdf": {
        "gradient": "linear-gradient(135deg, #e11d48 0%, #be123c 100%)",
        "shadow": "rgba(225, 29, 72, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M12 18v-4M9 16h6"/></svg>',
    },
    "outlook": {
        "gradient": "linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%)",
        "shadow": "rgba(29, 78, 216, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
    },
    "adobe_express": {
        "gradient": "linear-gradient(135deg, #8b5cf6 0%, #d946ef 100%)",
        "shadow": "rgba(217, 70, 239, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="#ffffff"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
    },
    "capcut": {
        "gradient": "linear-gradient(135deg, #06b6d4 0%, #0284c7 50%, #1e1b4b 100%)",
        "shadow": "rgba(6, 182, 212, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="8" cy="8" r="2.2" fill="#ffffff"/><circle cx="16" cy="16" r="2.2" fill="#ffffff"/><path d="M9.4 9.4l5.2 5.2"/></svg>',
    },
    "spotify": {
        "gradient": "linear-gradient(135deg, #10b981 0%, #059669 100%)",
        "shadow": "rgba(16, 185, 129, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="#ffffff"><circle cx="12" cy="12" r="10"/><path d="M8 9.5c3-1 6-1 9 1M9 12.8c2.5-.7 5-.7 7 .5M10 15.8c2-.5 4-.5 5.5.5" stroke="#10b981" stroke-width="2" stroke-linecap="round" fill="none"/></svg>',
    },
    "appletv": {
        "gradient": "linear-gradient(135deg, #64748b 0%, #334155 50%, #0f172a 100%)",
        "shadow": "rgba(100, 116, 139, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="#ffffff"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83zM15.97 6.84c.62-.75 1.04-1.8 1.01-2.84-.95.04-2.09.63-2.76 1.41-.58.68-1.09 1.74-.96 2.78 1.06.08 2.09-.6 2.71-1.35z"/></svg>',
    },
    "primevideo": {
        "gradient": "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
        "shadow": "rgba(2, 132, 199, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="#ffffff"><path d="M6 4l15 8-15 8V4z"/></svg>',
    },
    "scribd": {
        "gradient": "linear-gradient(135deg, #0d9488 0%, #0f766e 100%)",
        "shadow": "rgba(13, 148, 136, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    },
}

_cached_bot_username: str | None = None


def _get_bot_username() -> str:
    """Return verified Telegram Bot username. Prioritizes BOT_USERNAME env or fallback."""
    global _cached_bot_username
    if _cached_bot_username:
        return _cached_bot_username

    raw = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
    if raw:
        _cached_bot_username = raw
        return raw

    token = os.getenv("BOT_TOKEN", "").strip()
    if token:
        try:
            req = Request(f"https://api.telegram.org/bot{token}/getMe", headers={"User-Agent": "YowesBot/1.0"})
            with urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok") and data.get("result", {}).get("username"):
                    _cached_bot_username = data["result"]["username"]
                    return _cached_bot_username
        except Exception as exc:
            logger.warning("Could not resolve bot username via Telegram getMe: %s", exc)

    _cached_bot_username = "Jio_NoBot"
    return _cached_bot_username


def _get_support_url() -> str:
    raw = os.getenv("SUPPORT_URL", "https://t.me/TeamPr0_07").strip()
    if raw.startswith("@"):
        return f"https://t.me/{raw.lstrip('@')}"
    return raw


def _get_channel_url() -> str:
    """Return official update channel URL."""
    return os.getenv("OFFICIAL_CHANNEL_URL", "https://t.me/canvaproteam04").strip()


_last_prodseller_refresh: float = 0.0


def ensure_prodseller_cache_sync(force: bool = False) -> list[dict]:
    """Ensure ProdSeller products cache in telegram_bot is populated with live API data."""
    global _last_prodseller_refresh
    now = time.time()
    try:
        import telegram_bot
        expires_at, cached = getattr(telegram_bot, "_prodseller_products_cache", (0.0, []))
        if not force and cached and now < expires_at:
            return cached

        if hasattr(telegram_bot, "_prodseller_request_sync") and hasattr(telegram_bot, "_prodseller_configured"):
            if telegram_bot._prodseller_configured():
                payload = telegram_bot._prodseller_request_sync("GET", "/products")
                products = payload.get("products", [])
                if products:
                    telegram_bot._prodseller_products_cache = (now + 60, products)
                    _last_prodseller_refresh = now
                    logger.info("ProdSeller live stock cache updated: %d products available", len(products))
                    return products
        return cached or []
    except Exception as exc:
        logger.warning("Error refreshing ProdSeller cache: %s", exc)
        return []


def get_all_products_data() -> list[dict[str, Any]]:
    """Retrieve full product list, live prices, descriptions, and stock statuses."""
    ensure_prodseller_cache_sync()
    products: list[dict[str, Any]] = []
    bot_username = _get_bot_username()

    # Import bot helpers dynamically to avoid circular dependencies
    try:
        import telegram_bot
        is_active_func = getattr(telegram_bot, "_is_product_active", lambda k: True)
        stock_status_func = getattr(telegram_bot, "_get_product_stock_status", lambda k: True)
        setting_func = getattr(telegram_bot, "_setting", lambda k, d: d)
        setting_text_func = getattr(telegram_bot, "_setting_text", lambda k, d: d)
        format_idr_func = getattr(telegram_bot, "_format_idr", lambda v: f"Rp {v:,}".replace(",", "."))
        catalog = getattr(telegram_bot, "_PRODUCT_CATALOG", {})
        get_catalog_price_func = getattr(telegram_bot, "_get_catalog_product_price", None)
    except Exception as exc:
        logger.warning("Could not import telegram_bot helpers: %s", exc)
        is_active_func = lambda k: True
        stock_status_func = lambda k: True
        setting_func = lambda k, d: d
        setting_text_func = lambda k, d: d
        format_idr_func = lambda v: f"Rp {v:,}".replace(",", ".")
        catalog = {}
        get_catalog_price_func = None

    # 1. Canva Doc Education
    if is_active_func("docs"):
        doc_price_coins = setting_func("doc_price", 3)
        theme_docs = PRODUCT_STYLE_THEMES.get("docs", {})
        products.append({
            "key": "docs",
            "name": "Canva Doc Education",
            "category": PRODUCT_CATEGORIES.get("docs", "Edukasi"),
            "emoji": "🎓",
            "icon_svg": theme_docs.get("svg", ""),
            "gradient": theme_docs.get("gradient", "linear-gradient(135deg, #00c4cc 0%, #7d2ae8 100%)"),
            "shadow": theme_docs.get("shadow", "rgba(0, 196, 204, 0.45)"),
            "highlight": PRODUCT_HIGHLIGHTS.get("docs", "Generate Akun & Dokumen"),
            "is_coin_price": True,
            "coins": doc_price_coins,
            "price_coins_formatted": f"{doc_price_coins} Koin",
            "price_idr": doc_price_coins * 5000,
            "price_idr_formatted": f"{doc_price_coins} Koin",
            "price_usdt": f"{doc_price_coins} Koin",
            "price_note": f"{doc_price_coins} Koin",
            "in_stock": stock_status_func("docs"),
            "description": (
                "Layanan generate dokumen pengajar dan verifikasi akun Canva Education secara profesional, cepat, dan legal.\n"
                f"• Biaya generate: {doc_price_coins} Koin per akun / dokumen\n"
                "• Mendukung berbagai negara (Indonesia, Filipina, Malaysia, USA, dll)\n"
                "• Proses instan otomatis via bot Telegram\n"
                "• Garansi dokumen valid dan terverifikasi"
            ),
            "buy_url": f"https://t.me/{bot_username}?start=buy_docs",
        })

    # 2. Gemini Pro 18 Months
    if is_active_func("gemini"):
        gemini_p = setting_func("gemini_price_idr", 20000)
        gemini_u = setting_text_func("gemini_binance_price_usdt", "0.60")
        gemini_info = setting_text_func("gemini_info", "").strip()
        if not gemini_info:
            gemini_info = (
                "🤖 Gemini Pro 18 Months (Link Redeem)\n\n"
                "• 18 Months Plan 🤖\n"
                "• 5TB cloud storage included 🛴\n"
                "• You can add 5 users ⚡️\n"
                "• Not Shared ❌\n"
                "• 100% Private 🔐\n"
                "• NO NEED ANY CARD 💳\n"
                "• 24 Hours Hold warranty ✔️\n"
                "• Works in any country no verification 🛫\n\n"
                "Cara Aktivasi: Buka link redeem di browser dan klik 'Activate Offer'!"
            )
        theme_gemini = PRODUCT_STYLE_THEMES.get("gemini", {})
        products.append({
            "key": "gemini",
            "name": "Gemini Pro 18 Bulan",
            "category": PRODUCT_CATEGORIES.get("gemini", "AI Tools"),
            "emoji": "✨",
            "icon_svg": theme_gemini.get("svg", ""),
            "gradient": theme_gemini.get("gradient", "linear-gradient(135deg, #2563eb 0%, #7c3aed 50%, #db2777 100%)"),
            "shadow": theme_gemini.get("shadow", "rgba(124, 58, 237, 0.45)"),
            "highlight": PRODUCT_HIGHLIGHTS.get("gemini", "18 Bulan • 5TB Cloud • Private"),
            "price_idr": gemini_p,
            "price_idr_formatted": format_idr_func(gemini_p),
            "price_usdt": gemini_u,
            "price_note": "18 Bulan Plan",
            "in_stock": stock_status_func("gemini"),
            "description": gemini_info,
            "buy_url": f"https://t.me/{bot_username}?start=buy_gemini",
        })

    # 3. All Catalog Products
    default_theme = {
        "gradient": "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
        "shadow": "rgba(99, 102, 241, 0.45)",
        "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>',
    }

    for c_key, c_cfg in catalog.items():
        if not is_active_func(c_key):
            continue

        if get_catalog_price_func:
            p_idr, p_usdt = get_catalog_price_func(c_key)
        else:
            p_idr = c_cfg.get("default_idr", 20000)
            p_usdt = c_cfg.get("default_binance_usdt", "1.00")

        # Description
        info_custom = setting_text_func(c_cfg.get("info_key", ""), "").strip()
        desc = info_custom if info_custom else c_cfg.get("default_info_id", c_cfg.get("default_info_en", ""))
        theme_item = PRODUCT_STYLE_THEMES.get(c_key, default_theme)

        products.append({
            "key": c_key,
            "name": c_cfg.get("label_id", c_key.title()),
            "category": PRODUCT_CATEGORIES.get(c_key, "Produktivitas"),
            "emoji": c_cfg.get("emoji", "📦"),
            "icon_svg": theme_item.get("svg", default_theme["svg"]),
            "gradient": theme_item.get("gradient", default_theme["gradient"]),
            "shadow": theme_item.get("shadow", default_theme["shadow"]),
            "highlight": PRODUCT_HIGHLIGHTS.get(c_key, "Lisensi Resmi • Garansi"),
            "price_idr": p_idr,
            "price_idr_formatted": format_idr_func(p_idr),
            "price_usdt": p_usdt,
            "price_note": f"+0.5 USDT Markup",
            "in_stock": stock_status_func(c_key),
            "description": desc,
            "buy_url": f"https://t.me/{bot_username}?start=buy_{c_key}",
        })

    return products


def create_web_qris_order(product_key: str, contact: str = "") -> dict[str, Any]:
    """Create a new pending dynamic QRIS order for direct Web Store checkout."""
    ensure_prodseller_cache_sync()

    if product_key == "docs":
        return {
            "status": "error",
            "message": "Produk Canva Doc Education memerlukan pemilihan negara & verifikasi khusus via Bot Telegram.",
        }

    try:
        import telegram_bot
        is_active_func = getattr(telegram_bot, "_is_product_active", lambda k: True)
        stock_status_func = getattr(telegram_bot, "_get_product_stock_status", lambda k: True)
        setting_func = getattr(telegram_bot, "_setting", lambda k, d: d)
        catalog = getattr(telegram_bot, "_PRODUCT_CATALOG", {})
        get_catalog_price_func = getattr(telegram_bot, "_get_catalog_product_price", None)
        allocator = getattr(telegram_bot, "_amount_allocator", None)
        db_func = getattr(telegram_bot, "_db", None)
    except Exception as exc:
        logger.error("Failed to import telegram_bot helpers: %s", exc)
        return {"status": "error", "message": f"Server database error: {exc}"}

    if not is_active_func(product_key):
        return {"status": "error", "message": "Produk ini sedang dinonaktifkan oleh admin."}

    if not stock_status_func(product_key):
        return {"status": "error", "message": "Maaf, stok produk ini sedang habis saat ini. Silakan coba kembali nanti."}

    # Resolve product name and base price in Rupiah
    product_name = ""
    base_price = 20000

    if product_key == "gemini":
        product_name = "Gemini Pro 18 Bulan"
        base_price = setting_func("gemini_qris_price_idr", setting_func("gemini_price_idr", 20000))
    elif product_key in catalog:
        c_cfg = catalog[product_key]
        product_name = c_cfg.get("label_id", product_key.title())
        if get_catalog_price_func:
            base_price = get_catalog_price_func(product_key)[0]
        else:
            base_price = c_cfg.get("default_qris_idr", c_cfg.get("default_idr", 20000))
    else:
        return {"status": "error", "message": "Produk tidak dikenali."}

    if base_price <= 0:
        base_price = 20000

    # Ensure allocator is available
    if allocator is None:
        allocator = shopeepay_engine.UniqueAmountAllocator()
        if "telegram_bot" in sys.modules:
            setattr(sys.modules["telegram_bot"], "_amount_allocator", allocator)

    # Query currently active pending amounts from DB to prevent collisions
    reserved_set: set[int] = set()
    cutoff_time = (datetime.now() - timedelta(minutes=15)).isoformat()
    try:
        with db_func() as conn:
            rows = conn.execute(
                "SELECT raw_amount FROM payment_requests WHERE method = 'qris' AND status = 'pending' AND raw_amount > 0 AND created_at >= ?",
                (cutoff_time,),
            ).fetchall()
            for r in rows:
                if r[0]:
                    reserved_set.add(int(r[0]))
    except Exception as exc:
        logger.warning("Could not query reserved amounts from DB: %s", exc)

    total_amount, unique_code = allocator.allocate(base_price, ttl_seconds=900, reserved_amounts=reserved_set)

    # Dynamic QRIS generation via qris_engine
    raw_static_qris = os.getenv("SHOPEE_MERCHANT_QRIS_RAW", "").strip()
    if not raw_static_qris and hasattr(telegram_bot, "_setting_text"):
        raw_static_qris = telegram_bot._setting_text("shopee_qris_raw", "").strip()

    dynamic_qris_str = ""
    qr_image_url = ""

    if raw_static_qris:
        try:
            dynamic_qris_str = qris_engine.static_to_dynamic_qris(raw_static_qris, total_amount)
            qr_image_url = qris_engine.get_qris_qr_image_url(dynamic_qris_str, size=420)
        except Exception as exc:
            logger.warning("Failed to generate dynamic QRIS: %s", exc)

    if not qr_image_url:
        qr_image_url = os.getenv("QRIS_IMAGE_URL", "https://quickchart.io/qr?text=QRIS_PAYMENT&size=400")

    order_token = secrets.token_hex(16)
    formatted_amount = f"Rp {total_amount:,}".replace(",", ".")
    now_iso = datetime.now().isoformat()

    try:
        with db_func() as conn:
            cur = conn.execute(
                """
                INSERT INTO payment_requests (
                    user_id, method, amount, reference, email, status,
                    created_at, product_key, raw_amount, qris_payload, order_token
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    0,
                    "qris",
                    formatted_amount,
                    f"WEB-{order_token[:8].upper()}",
                    contact.strip() if contact else "Web Guest",
                    "pending",
                    now_iso,
                    product_key,
                    total_amount,
                    dynamic_qris_str,
                    order_token,
                ),
            )
            order_id = cur.lastrowid
    except Exception as exc:
        logger.error("Failed to insert web QRIS order: %s", exc)
        allocator.cancel(total_amount)
        return {"status": "error", "message": "Gagal mencatat pesanan di database."}

    logger.info("⚡ Web QRIS Order created: #%s for %s (%s, Total: %s)", order_id, product_name, contact, formatted_amount)

    return {
        "ok": True,
        "status": "success",
        "order_id": order_id,
        "order_token": order_token,
        "token": order_token,
        "product_key": product_key,
        "product_name": product_name,
        "base_amount": base_price,
        "unique_code": unique_code,
        "total_amount": total_amount,
        "allocated_amount": total_amount,
        "total_amount_formatted": formatted_amount,
        "formatted_amount": formatted_amount,
        "dynamic_qris": dynamic_qris_str,
        "qr_image_url": qr_image_url,
        "expires_in_seconds": 900,
        "created_at": now_iso,
    }


def get_web_order_status(order_token: str) -> dict[str, Any]:
    """Retrieve live order status and delivered credentials for Web Store polling."""
    if not order_token or len(order_token) < 16:
        return {"ok": False, "status": "error", "message": "Token pesanan tidak valid", "error": "Token tidak valid"}

    try:
        import telegram_bot
        db_func = getattr(telegram_bot, "_db", None)
        allocator = getattr(telegram_bot, "_amount_allocator", None)
        settle_func = getattr(telegram_bot, "_check_and_settle_qris_payment_sync", None)
    except Exception as exc:
        return {"ok": False, "status": "error", "message": str(exc), "error": str(exc)}

    try:
        with db_func() as conn:
            row = conn.execute(
                "SELECT * FROM payment_requests WHERE order_token = ?", (order_token,)
            ).fetchone()
            if not row:
                return {"ok": False, "status": "not_found", "message": "Pesanan tidak ditemukan"}

            p = dict(row)

            # Check if pending order has exceeded 15 minutes TTL
            if p["status"] == "pending":
                created_dt = datetime.fromisoformat(p["created_at"])
                elapsed = (datetime.now() - created_dt).total_seconds()
                if elapsed > 900:
                    conn.execute(
                        "UPDATE payment_requests SET status = 'expired', reviewed_at = ? WHERE id = ?",
                        (datetime.now().isoformat(), p["id"]),
                    )
                    if allocator and p.get("raw_amount"):
                        allocator.cancel(p["raw_amount"])
                    return {"ok": True, "status": "expired", "message": "Batas waktu pembayaran 15 menit telah habis"}

                # On-demand live verification against ShopeePay mutations
                if settle_func:
                    try:
                        settled, msg = settle_func(p["id"])
                        if settled:
                            updated_row = conn.execute(
                                "SELECT * FROM payment_requests WHERE id = ?", (p["id"],)
                            ).fetchone()
                            if updated_row:
                                p = dict(updated_row)
                    except Exception as poll_err:
                        logger.debug("On-demand ShopeePay check for order #%s error: %s", p["id"], poll_err)

                if p["status"] == "pending":
                    return {
                        "ok": True,
                        "status": "pending",
                        "order_id": p["id"],
                        "amount": p["amount"],
                        "expires_in_seconds": max(0, int(900 - elapsed)),
                    }

            if p["status"] == "approved":
                return {
                    "ok": True,
                    "status": "approved",
                    "order_id": p["id"],
                    "product_key": p.get("product_key", ""),
                    "amount": p["amount"],
                    "provider_order_id": p.get("provider_order_id", ""),
                    "delivered_data": p.get("delivered_data", ""),
                    "approved_at": p.get("reviewed_at", ""),
                }

            return {
                "ok": True,
                "status": p["status"],
                "order_id": p["id"],
                "message": f"Status pesanan: {p['status']}",
            }
    except Exception as exc:
        logger.error("Error checking web order status: %s", exc)
        return {"ok": False, "status": "error", "message": str(exc)}


def cancel_web_order(order_token: str) -> dict[str, Any]:
    """User cancels active pending QRIS order, freeing unique amount immediately."""
    if not order_token:
        return {"ok": False, "status": "error", "message": "Token tidak valid"}

    try:
        import telegram_bot
        db_func = getattr(telegram_bot, "_db", None)
        allocator = getattr(telegram_bot, "_amount_allocator", None)
        with db_func() as conn:
            row = conn.execute(
                "SELECT id, status, raw_amount FROM payment_requests WHERE order_token = ?", (order_token,)
            ).fetchone()
            if not row:
                return {"ok": False, "status": "not_found", "message": "Pesanan tidak ditemukan"}
            if row["status"] != "pending":
                return {"ok": False, "status": "error", "message": f"Pesanan sudah berstatus '{row['status']}'"}

            conn.execute(
                "UPDATE payment_requests SET status = 'cancelled', reviewed_at = ? WHERE id = ?",
                (datetime.now().isoformat(), row["id"]),
            )
            if allocator and row["raw_amount"]:
                allocator.cancel(row["raw_amount"])
            return {"ok": True, "status": "success", "message": "Pesanan berhasil dibatalkan"}
    except Exception as exc:
        return {"ok": False, "status": "error", "message": str(exc)}


def render_html_page() -> str:
    """Generate the complete luxury glassmorphic HTML page inspired by Lynk.id."""
    bot_username = _get_bot_username()
    support_url = _get_support_url()
    channel_url = _get_channel_url()
    products = get_all_products_data()
    products_json = json.dumps(products, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>{STORE_NAME} • Official Digital Store</title>
  <meta name="description" content="Toko digital otomatis 24 jam. Beli Canva Edu, Gemini Pro, ChatGPT Plus, Spotify, iLovePdf, dan lisensi premium legal bergaransi.">
  <meta name="theme-color" content="#07090e">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-dark: #07090e;
      --bg-card: rgba(255, 255, 255, 0.035);
      --bg-card-hover: rgba(255, 255, 255, 0.06);
      --glass-border: rgba(255, 255, 255, 0.08);
      --glass-border-focus: rgba(99, 102, 241, 0.4);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --primary: #6366f1;
      --primary-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
      --accent-emerald: #10b981;
      --accent-rose: #f43f5e;
      --accent-gold: #f59e0b;
      --shadow-glass: 0 16px 36px -10px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.08);
      --radius-sm: 10px;
      --radius-md: 16px;
      --radius-lg: 22px;
      --radius-xl: 30px;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
    }}

    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-main);
      min-height: 100vh;
      overflow-x: hidden;
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: env(safe-area-inset-top, 16px) 16px env(safe-area-inset-bottom, 32px);
    }}

    /* Ambient luxury light orbs */
    .ambient-mesh {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      pointer-events: none;
      z-index: 0;
      overflow: hidden;
    }}
    .orb-1 {{
      position: absolute;
      top: -150px;
      left: 50%;
      transform: translateX(-50%);
      width: 550px;
      height: 550px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(99, 102, 241, 0.16) 0%, rgba(99, 102, 241, 0) 70%);
      filter: blur(80px);
    }}
    .orb-2 {{
      position: absolute;
      top: 35%;
      right: -100px;
      width: 400px;
      height: 400px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(236, 72, 153, 0.08) 0%, rgba(236, 72, 153, 0) 70%);
      filter: blur(80px);
    }}
    .orb-3 {{
      position: absolute;
      bottom: 5%;
      left: -100px;
      width: 450px;
      height: 450px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(16, 185, 129, 0.08) 0%, rgba(16, 185, 129, 0) 70%);
      filter: blur(80px);
    }}

    /* Mobile Container like Lynk.id */
    .app-container {{
      position: relative;
      z-index: 1;
      width: 100%;
      max-width: 460px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}

    /* Profile / Header Section */
    .header-card {{
      background: var(--bg-card);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid var(--glass-border);
      border-radius: var(--radius-xl);
      padding: 24px 20px 20px;
      text-align: center;
      box-shadow: var(--shadow-glass);
      position: relative;
      overflow: hidden;
    }}
    .header-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 10%;
      right: 10%;
      height: 1px;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
    }}

    .avatar-wrapper {{
      position: relative;
      display: inline-block;
      margin-bottom: 14px;
    }}
    .avatar {{
      width: 82px;
      height: 82px;
      border-radius: 26px;
      background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #db2777 100%);
      border: 1.5px solid rgba(255, 255, 255, 0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 12px 28px -6px rgba(124, 58, 237, 0.55), inset 0 2px 2px rgba(255, 255, 255, 0.6), inset 0 -2px 3px rgba(0, 0, 0, 0.25);
    }}
    .avatar svg {{
      display: block;
      filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
    }}
    .avatar-ring {{
      position: absolute;
      inset: -5px;
      border-radius: 30px;
      border: 2px solid var(--primary);
      opacity: 0.5;
      animation: pulse-ring 3s infinite;
    }}
    @keyframes pulse-ring {{
      0% {{ transform: scale(0.96); opacity: 0.6; }}
      50% {{ transform: scale(1.05); opacity: 0.2; }}
      100% {{ transform: scale(0.96); opacity: 0.6; }}
    }}

    .store-title {{
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      margin-bottom: 6px;
    }}
    .verified-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      background: #3b82f6;
      color: #fff;
      border-radius: 50%;
      font-size: 11px;
      font-weight: bold;
    }}

    .store-tagline {{
      font-size: 13px;
      color: var(--text-muted);
      line-height: 1.5;
      margin-bottom: 14px;
      padding: 0 8px;
    }}

    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 5px 12px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 600;
      color: #34d399;
      margin-bottom: 16px;
    }}
    .status-dot {{
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
      animation: blink 2s infinite ease-in-out;
    }}
    @keyframes blink {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.3; }}
    }}

    /* 3D Tactile Icon Tiles (Inspired by Reference Design) */
    .tactile-tile {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(255, 255, 255, 0.3);
      box-shadow: 0 6px 14px -2px var(--tile-shadow, rgba(0, 0, 0, 0.3)), inset 0 1.5px 1.5px rgba(255, 255, 255, 0.55), inset 0 -1.5px 2px rgba(0, 0, 0, 0.2);
      flex-shrink: 0;
      position: relative;
      overflow: hidden;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .tactile-tile svg {{
      display: block;
      filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.25));
    }}
    .btn-tile {{
      width: 38px;
      height: 38px;
      border-radius: 12px;
    }}
    .trust-tile {{
      width: 42px;
      height: 42px;
      border-radius: 14px;
      margin: 0 auto 6px;
    }}

    /* Action Links (Lynk.id Style Buttons) */
    .link-group {{
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .lynk-btn {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 16px 10px 12px;
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.07);
      color: var(--text-main);
      text-decoration: none;
      font-size: 13.5px;
      font-weight: 600;
      transition: all 0.2s ease;
      cursor: pointer;
    }}
    .lynk-btn:hover, .lynk-btn:active {{
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.15);
      transform: translateY(-1px);
    }}
    .btn-left {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .btn-chevron {{
      color: var(--text-dim);
      font-size: 13px;
    }}

    .lynk-btn-primary {{
      background: rgba(99, 102, 241, 0.12);
      border-color: rgba(99, 102, 241, 0.35);
      box-shadow: 0 8px 20px -4px rgba(99, 102, 241, 0.3);
    }}
    .lynk-btn-primary:hover, .lynk-btn-primary:active {{
      background: rgba(99, 102, 241, 0.2);
      border-color: rgba(99, 102, 241, 0.5);
      box-shadow: 0 10px 24px -4px rgba(99, 102, 241, 0.45);
      transform: translateY(-1px);
    }}

    /* Trust / Features Bar */
    .trust-bar {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin: 4px 0;
    }}
    .trust-item {{
      background: var(--bg-card);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--glass-border);
      border-radius: var(--radius-md);
      padding: 12px 6px 10px;
      text-align: center;
      box-shadow: var(--shadow-glass);
    }}
    .trust-title {{
      font-size: 11px;
      font-weight: 700;
      color: var(--text-main);
    }}
    .trust-desc {{
      font-size: 9.5px;
      color: var(--text-muted);
    }}

    /* Sticky Search & Filter Controls */
    .controls-wrapper {{
      position: sticky;
      top: 10px;
      z-index: 10;
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: rgba(7, 9, 14, 0.75);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      padding: 10px 0 6px;
      border-radius: var(--radius-lg);
    }}

    .search-box {{
      position: relative;
      width: 100%;
    }}
    .search-input {{
      width: 100%;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--glass-border);
      border-radius: var(--radius-md);
      padding: 12px 14px 12px 40px;
      color: var(--text-main);
      font-size: 13.5px;
      font-family: inherit;
      outline: none;
      transition: all 0.2s ease;
    }}
    .search-input:focus {{
      border-color: var(--primary);
      background: rgba(255, 255, 255, 0.08);
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
    }}
    .search-input::placeholder {{
      color: var(--text-dim);
    }}
    .search-icon {{
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-dim);
      font-size: 14px;
      pointer-events: none;
    }}

    /* Row for Currency & Categories */
    .filter-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      justify-content: space-between;
    }}

    .category-scroll {{
      display: flex;
      gap: 6px;
      overflow-x: auto;
      scrollbar-width: none;
      padding-bottom: 2px;
      flex: 1;
    }}
    .category-scroll::-webkit-scrollbar {{
      display: none;
    }}

    .cat-chip {{
      white-space: nowrap;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--glass-border);
      color: var(--text-muted);
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    .cat-chip.active {{
      background: rgba(99, 102, 241, 0.2);
      border-color: rgba(99, 102, 241, 0.6);
      color: #fff;
    }}

    .currency-switch {{
      display: flex;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--glass-border);
      border-radius: 999px;
      padding: 2px;
      flex-shrink: 0;
    }}
    .curr-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 4px 8px;
      font-size: 10.5px;
      font-weight: 700;
      border-radius: 999px;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    .curr-btn.active {{
      background: var(--primary);
      color: #fff;
    }}

    /* Product Cards Grid / List */
    .products-list {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .product-card {{
      background: var(--bg-card);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border);
      border-radius: var(--radius-lg);
      padding: 16px;
      box-shadow: var(--shadow-glass);
      transition: all 0.2s ease;
      cursor: pointer;
      position: relative;
      overflow: hidden;
    }}
    .product-card:hover, .product-card:active {{
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.16);
      transform: translateY(-2px);
    }}

    .card-top {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .prod-icon-box {{
      width: 48px;
      height: 48px;
      border-radius: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      border: 1px solid rgba(255, 255, 255, 0.28);
      box-shadow: 0 8px 18px -3px var(--tile-shadow, rgba(99, 102, 241, 0.4)), inset 0 1.8px 1.8px rgba(255, 255, 255, 0.55), inset 0 -1.8px 2px rgba(0, 0, 0, 0.2);
      position: relative;
      overflow: hidden;
      transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
    }}
    .prod-icon-box svg {{
      display: block;
      filter: drop-shadow(0 1.5px 3px rgba(0, 0, 0, 0.3));
    }}
    .prod-meta {{
      flex: 1;
      min-width: 0;
    }}
    .prod-title {{
      font-size: 15px;
      font-weight: 700;
      color: var(--text-main);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-bottom: 2px;
    }}
    .prod-badge {{
      display: inline-block;
      font-size: 10px;
      font-weight: 600;
      color: var(--primary);
      background: rgba(99, 102, 241, 0.1);
      border: 1px solid rgba(99, 102, 241, 0.25);
      border-radius: 6px;
      padding: 1px 6px;
    }}

    .card-highlight {{
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.4;
      margin-bottom: 14px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .card-footer {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      padding-top: 12px;
    }}
    .price-wrap {{
      display: flex;
      flex-direction: column;
    }}
    .price-label {{
      font-size: 10px;
      color: var(--text-dim);
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.04em;
    }}
    .price-value {{
      font-size: 16px;
      font-weight: 800;
      color: #fff;
    }}

    .stock-tag {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 700;
      border-radius: 999px;
      padding: 4px 10px;
    }}
    .stock-ready {{
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
    }}
    .stock-out {{
      background: rgba(244, 63, 94, 0.12);
      border: 1px solid rgba(244, 63, 94, 0.3);
      color: #fb7185;
    }}
    .stock-dot-pill {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
      display: inline-block;
    }}
    .stock-ready .stock-dot-pill {{
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
    }}
    .stock-out .stock-dot-pill {{
      background: #f43f5e;
      box-shadow: 0 0 8px #f43f5e;
    }}

    .card-btn {{
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #fff;
      padding: 6px 14px;
      border-radius: var(--radius-md);
      font-size: 12px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 4px;
    }}

    /* Empty state */
    .empty-state {{
      text-align: center;
      padding: 40px 20px;
      color: var(--text-muted);
      font-size: 13.5px;
      display: none;
    }}

    /* Modal / Bottom Sheet Detail */
    .modal-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      z-index: 100;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s ease;
      display: flex;
      align-items: flex-end;
      justify-content: center;
    }}
    .modal-backdrop.open {{
      opacity: 1;
      pointer-events: auto;
    }}

    .modal-drawer {{
      width: 100%;
      max-width: 480px;
      background: #0f1422;
      border: 1px solid var(--glass-border);
      border-radius: 28px 28px 0 0;
      padding: 24px 20px 32px;
      box-shadow: 0 -10px 40px rgba(0, 0, 0, 0.8);
      transform: translateY(100%);
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      max-height: 85vh;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .modal-backdrop.open .modal-drawer {{
      transform: translateY(0);
    }}

    .drawer-handle {{
      width: 38px;
      height: 4px;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 999px;
      margin: 0 auto 8px;
    }}

    .drawer-header {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}
    .drawer-icon {{
      width: 58px;
      height: 58px;
      border-radius: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      border: 1.5px solid rgba(255, 255, 255, 0.3);
      box-shadow: 0 10px 24px -4px var(--tile-shadow, rgba(99, 102, 241, 0.45)), inset 0 2px 2px rgba(255, 255, 255, 0.6), inset 0 -2px 3px rgba(0, 0, 0, 0.25);
      position: relative;
      overflow: hidden;
    }}
    .drawer-icon svg {{
      display: block;
      width: 28px;
      height: 28px;
      filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.35));
    }}
    .drawer-info {{
      flex: 1;
    }}
    .drawer-title {{
      font-size: 18px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 4px;
    }}
    .drawer-close {{
      background: rgba(255, 255, 255, 0.08);
      border: none;
      color: #fff;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      font-size: 14px;
      cursor: pointer;
    }}

    .price-box {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--glass-border);
      border-radius: var(--radius-md);
      padding: 14px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .modal-price-idr {{
      font-size: 20px;
      font-weight: 800;
      color: #fff;
    }}
    .modal-price-usdt {{
      font-size: 13px;
      color: #a5b4fc;
      font-weight: 600;
    }}

    .desc-box {{
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: var(--radius-md);
      padding: 14px 16px;
      font-size: 12.5px;
      line-height: 1.6;
      color: var(--text-muted);
      white-space: pre-line;
      max-height: 220px;
      overflow-y: auto;
    }}

    .modal-actions {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 6px;
    }}
    .cta-btn {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 14px;
      border-radius: var(--radius-md);
      font-size: 14px;
      font-weight: 700;
      text-decoration: none;
      transition: all 0.2s ease;
      cursor: pointer;
      border: none;
    }}
    .cta-primary {{
      background: var(--primary-gradient);
      color: #fff;
      box-shadow: 0 8px 24px -4px rgba(99, 102, 241, 0.6);
    }}
    .cta-primary:hover, .cta-primary:active {{
      box-shadow: 0 12px 28px -4px rgba(99, 102, 241, 0.8);
      transform: translateY(-1px);
    }}
    .cta-secondary {{
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--glass-border);
      color: var(--text-main);
    }}
    .cta-qris {{
      background: linear-gradient(135deg, #059669 0%, #10b981 50%, #06b6d4 100%);
      color: #fff;
      box-shadow: 0 8px 24px -4px rgba(16, 185, 129, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.25);
    }}
    .cta-qris:hover, .cta-qris:active {{
      box-shadow: 0 12px 28px -4px rgba(16, 185, 129, 0.85);
      transform: translateY(-1px);
    }}

    /* QRIS Direct Checkout Modal Styles */
    .qris-drawer {{
      max-width: 460px;
    }}
    .qris-notice-box {{
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.25);
      border-radius: var(--radius-md);
      padding: 12px 14px;
      margin-top: 10px;
    }}
    .qris-card-wrap {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      margin-top: 10px;
    }}
    .qris-img-container {{
      background: #ffffff;
      padding: 14px;
      border-radius: 20px;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5);
      text-align: center;
      display: inline-block;
      max-width: 260px;
    }}
    .qris-img {{
      width: 220px;
      height: 220px;
      display: block;
      margin: 0 auto;
      border-radius: 8px;
    }}
    .qris-scan-guide {{
      font-size: 10px;
      font-weight: 700;
      color: #0f172a;
      margin-top: 8px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .qris-amount-card {{
      width: 100%;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--glass-border);
      border-radius: var(--radius-md);
      padding: 12px 14px;
      text-align: center;
    }}
    .qris-total-amount {{
      font-size: 26px;
      font-weight: 800;
      color: #34d399;
      letter-spacing: -0.02em;
    }}
    .copy-badge-btn {{
      background: rgba(16, 185, 129, 0.2);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: #a7f3d0;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    .copy-badge-btn:hover, .copy-badge-btn:active {{
      background: #10b981;
      color: #fff;
    }}
    .qris-code-warn {{
      font-size: 11px;
      color: #fbbf24;
      line-height: 1.45;
      margin-top: 6px;
    }}
    .timer-bar {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(244, 63, 94, 0.1);
      border: 1px solid rgba(244, 63, 94, 0.25);
      border-radius: 999px;
      padding: 5px 14px;
      font-size: 12px;
      font-weight: 700;
      color: #f87171;
    }}
    .success-icon-squircle {{
      width: 68px;
      height: 68px;
      border-radius: 22px;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      border: 1.5px solid rgba(255, 255, 255, 0.4);
      box-shadow: 0 12px 28px -4px rgba(16, 185, 129, 0.6), inset 0 2px 2px rgba(255, 255, 255, 0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 32px;
      font-weight: bold;
      color: #ffffff;
      margin: 0 auto;
    }}
    .delivered-box {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--glass-border);
      border-radius: var(--radius-md);
      padding: 14px 16px;
      margin-top: 8px;
    }}
    .credentials-pre {{
      background: #020617;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      padding: 12px 14px;
      color: #38bdf8;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12.5px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-all;
      max-height: 200px;
      overflow-y: auto;
      text-align: left;
    }}
    .history-card {{
      background: rgba(255, 255, 255, 0.035);
      border: 1px solid var(--glass-border);
      border-radius: 14px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: all 0.2s ease;
    }}
    .history-card:hover {{
      background: rgba(255, 255, 255, 0.055);
      border-color: rgba(99, 102, 241, 0.3);
    }}
    .history-badge-pending {{
      font-size: 10px;
      font-weight: 700;
      color: #fbbf24;
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.3);
      padding: 2px 7px;
      border-radius: 6px;
    }}
    .history-badge-approved {{
      font-size: 10px;
      font-weight: 700;
      color: #34d399;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 2px 7px;
      border-radius: 6px;
    }}
    .history-btn-sm {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--glass-border);
      color: var(--text-main);
      border-radius: 8px;
      padding: 6px 10px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      text-decoration: none;
      transition: all 0.15s;
    }}
    .history-btn-sm:hover {{
      background: rgba(255, 255, 255, 0.15);
      transform: translateY(-1px);
    }}
    .history-btn-resume {{
      background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
      color: #fff;
      border: none;
    }}

    /* Toast Alert */
    .toast {{
      position: fixed;
      bottom: 24px;
      left: 50%;
      transform: translateX(-50%) translateY(100px);
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid rgba(255, 255, 255, 0.15);
      backdrop-filter: blur(20px);
      color: #fff;
      padding: 10px 20px;
      border-radius: 999px;
      font-size: 12.5px;
      font-weight: 600;
      z-index: 200;
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }}
    .toast.show {{
      transform: translateX(-50%) translateY(0);
    }}

    /* FAQ Accordion Section */
    .faq-card {{
      background: var(--bg-card);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border);
      border-radius: var(--radius-xl);
      padding: 18px 20px;
      box-shadow: var(--shadow-glass);
    }}
    .faq-title {{
      font-size: 14px;
      font-weight: 700;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .faq-item {{
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      padding: 10px 0;
    }}
    .faq-item:last-child {{
      border-bottom: none;
      padding-bottom: 0;
    }}
    .faq-q {{
      font-size: 12.5px;
      font-weight: 600;
      color: var(--text-main);
      margin-bottom: 4px;
    }}
    .faq-a {{
      font-size: 11.5px;
      color: var(--text-muted);
      line-height: 1.5;
    }}

    /* Footer */
    .footer {{
      text-align: center;
      font-size: 11px;
      color: var(--text-dim);
      padding: 16px 0 24px;
      line-height: 1.6;
    }}
    .footer a {{
      color: var(--primary);
      text-decoration: none;
    }}

    /* Floating Support FAB */
    .fab-support {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 52px;
      height: 52px;
      border-radius: 17px;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      border: 1.5px solid rgba(255, 255, 255, 0.35);
      box-shadow: 0 10px 24px -4px rgba(16, 185, 129, 0.6), inset 0 2px 2px rgba(255, 255, 255, 0.5), inset 0 -2px 2px rgba(0, 0, 0, 0.2);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      text-decoration: none;
      z-index: 50;
      transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
    }}
    .fab-support svg {{
      display: block;
      filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.3));
    }}
    .fab-support:hover, .fab-support:active {{
      transform: scale(1.08) translateY(-2px);
      box-shadow: 0 14px 28px -2px rgba(16, 185, 129, 0.75);
    }}
  </style>
</head>
<body>

  <!-- Ambient glowing luxury aura -->
  <div class="ambient-mesh">
    <div class="orb-1"></div>
    <div class="orb-2"></div>
    <div class="orb-3"></div>
  </div>

  <div class="app-container">

    <!-- Profile Header Card (Lynk.id style) -->
    <header class="header-card">
      <div class="avatar-wrapper">
        <div class="avatar-ring"></div>
        <div class="avatar" title="{STORE_NAME}">
          <svg viewBox="0 0 24 24" width="38" height="38" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
            <line x1="3" y1="6" x2="21" y2="6"/>
            <path d="M16 10a4 4 0 0 1-8 0"/>
          </svg>
        </div>
      </div>
      <h1 class="store-title">
        {STORE_NAME}
        <span class="verified-badge" title="Verified Store">✓</span>
      </h1>
      <p class="store-tagline">{STORE_TAGLINE}</p>
      
      <div class="status-pill">
        <span class="status-dot"></span>
        <span>Online 24 Jam • Sistem Otomatis</span>
      </div>

      <!-- Quick Action Buttons with 3D Tactile Icons -->
      <div class="link-group">
        <a href="https://t.me/{bot_username}" target="_blank" class="lynk-btn lynk-btn-primary">
          <div class="btn-left">
            <div class="tactile-tile btn-tile" style="background: linear-gradient(135deg, #0088cc 0%, #00b4d8 100%); --tile-shadow: rgba(0, 180, 216, 0.45);">
              <div style="width: 24px; height: 24px; border-radius: 50%; background: #ffffff; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.18);">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="#0088cc"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 0 0-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>
              </div>
            </div>
            <span>Buka Bot Telegram</span>
          </div>
          <span class="btn-chevron">➜</span>
        </a>
        <a href="{support_url}" target="_blank" class="lynk-btn">
          <div class="btn-left">
            <div class="tactile-tile btn-tile" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); --tile-shadow: rgba(16, 185, 129, 0.45);">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
            </div>
            <span>Hubungi Customer Service</span>
          </div>
          <span class="btn-chevron">➜</span>
        </a>
        <a href="{channel_url}" target="_blank" class="lynk-btn">
          <div class="btn-left">
            <div class="tactile-tile btn-tile" style="background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%); --tile-shadow: rgba(245, 158, 11, 0.45);">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="#ffffff"><path d="M18 11v-4c0-1.1-.9-2-2-2h-3l-5-4v16l5-4h3c1.1 0 2-.9 2-2v-4zm-8-3.17L12.83 10H16v4h-3.17L10 16.17V7.83zM20 7v10c1.3-.84 2-2.3 2-4s-.7-3.16-2-4z"/></svg>
            </div>
            <span>Official Update Channel</span>
          </div>
          <span class="btn-chevron">➜</span>
        </a>
      </div>
    </header>

    <!-- Trust & Highlights Bar with 3D Tactile Icons -->
    <section class="trust-bar">
      <div class="trust-item">
        <div class="tactile-tile trust-tile" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); --tile-shadow: rgba(59, 130, 246, 0.45);">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="#ffffff"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
        </div>
        <div class="trust-title">Auto Instant</div>
        <div class="trust-desc">Kirim Otomatis</div>
      </div>
      <div class="trust-item">
        <div class="tactile-tile trust-tile" style="background: linear-gradient(135deg, #10b981 0%, #047857 100%); --tile-shadow: rgba(16, 185, 129, 0.45);">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
        </div>
        <div class="trust-title">Garansi Aktif</div>
        <div class="trust-desc">Sesuai Produk</div>
      </div>
      <div class="trust-item">
        <div class="tactile-tile trust-tile" style="background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); --tile-shadow: rgba(139, 92, 246, 0.45);">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="3"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
        </div>
        <div class="trust-title">QRIS & USDT</div>
        <div class="trust-desc">Payment Realtime</div>
      </div>
    </section>

    <!-- History & Order Status Action Card (Telegram Bot Button Theme) -->
    <div style="width: 100%; margin: 12px 0 10px;">
      <button id="btnOrderHistory" type="button" class="lynk-btn lynk-btn-primary" style="width: 100%; text-align: left; padding: 10px 18px 10px 12px; border-radius: var(--radius-md);">
        <div class="btn-left">
          <div class="tactile-tile btn-tile" style="background: linear-gradient(135deg, #0088cc 0%, #00b4d8 100%); --tile-shadow: rgba(0, 180, 216, 0.45); box-shadow: 0 4px 14px rgba(0, 180, 216, 0.4);">
            <div style="width: 24px; height: 24px; border-radius: 50%; background: #ffffff; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.18);">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#0088cc" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                <path d="M3 3v5h5"/>
                <path d="M12 7v5l4 2"/>
              </svg>
            </div>
          </div>
          <span style="font-weight: 700; font-size: 14.5px; color: #ffffff; letter-spacing: -0.2px;">Riwayat Pesanan</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span id="historyBadgeCount" style="display: none; font-size: 11px; font-weight: 800; color: #ffffff; background: #0088cc; padding: 2px 8px; border-radius: 999px; box-shadow: 0 2px 8px rgba(0, 136, 204, 0.45);">0</span>
          <span class="btn-chevron" style="color: rgba(255, 255, 255, 0.65); font-size: 14px;">➜</span>
        </div>
      </button>
    </div>

    <!-- Sticky Search and Filter Controls -->
    <div class="controls-wrapper">
      <div class="search-box">
        <span class="search-icon">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        </span>
        <input type="text" id="searchInput" class="search-input" placeholder="Cari produk (Gemini, Canva, Office, dll)..." autocomplete="off">
      </div>

      <div class="filter-row">
        <div class="category-scroll" id="categoryChips">
          <button class="cat-chip active" data-cat="all">⚡ Semua</button>
          <button class="cat-chip" data-cat="AI Tools">🤖 AI</button>
          <button class="cat-chip" data-cat="Produktivitas">💼 Produktivitas</button>
          <button class="cat-chip" data-cat="Hiburan">🎬 Hiburan</button>
          <button class="cat-chip" data-cat="Edukasi">🎓 Edukasi</button>
        </div>

        <div class="currency-switch">
          <button id="currIdr" class="curr-btn active">IDR</button>
          <button id="currUsdt" class="curr-btn">USDT</button>
        </div>
      </div>

      <!-- Pending Order Recovery Banner -->
      <div id="pendingOrderBanner" style="display: none; width: 100%; margin-top: 10px; background: linear-gradient(135deg, rgba(245, 158, 11, 0.16) 0%, rgba(239, 68, 68, 0.14) 100%); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 14px; padding: 10px 14px; cursor: pointer;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="status-dot" style="background: #f59e0b; box-shadow: 0 0 8px #f59e0b;"></span>
            <div style="font-size: 11.5px; font-weight: 700; color: #fde68a;">
              Ada Pesanan QRIS Berjalan (<span id="bannerOrderAmount">Rp 0</span>)
            </div>
          </div>
          <span style="font-size: 11px; font-weight: 800; color: #fbbf24; background: rgba(245, 158, 11, 0.2); padding: 4px 8px; border-radius: 8px;">Buka QRIS ➜</span>
        </div>
      </div>
    </div>

    <!-- Products List -->
    <main class="products-list" id="productsList">
      <!-- Product cards populated dynamically by JS -->
    </main>

    <!-- Empty State -->
    <div class="empty-state" id="emptyState">
      🔍 Tidak ada produk yang sesuai dengan pencarian.
    </div>

    <!-- FAQ & Info Section -->
    <section class="faq-card">
      <h3 class="faq-title">💡 Panduan & Tanya Jawab</h3>
      <div class="faq-item">
        <div class="faq-q">1. Bagaimana cara membeli produk?</div>
        <div class="faq-a">Klik produk yang Anda inginkan, lalu pilih <b>"Beli di Bot Telegram"</b>. Bot akan langsung membuka menu pembayaran otomatis via QRIS (Rupiah) atau Binance Pay (USDT).</div>
      </div>
      <div class="faq-item">
        <div class="faq-q">2. Kapan akun/lisensi dikirimkan?</div>
        <div class="faq-a">Sistem kami terintegrasi 24 jam. Begitu pembayaran terverifikasi otomatis, data akun/link aktivasi langsung dikirim ke chat Telegram Anda dalam hitungan detik.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q">3. Apakah ada garansi?</div>
        <div class="faq-a">Ya, seluruh produk kami memiliki garansi hold dan replacement. Jika terjadi kendala, customer service kami siap membantu via Telegram.</div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <p>© 2026 {STORE_NAME} • All Rights Reserved</p>
      <p>Integrated with Botkeep Hosting • <a href="https://t.me/{bot_username}" target="_blank">@{bot_username}</a></p>
    </footer>

  </div>

  <!-- Product Detail Drawer / Modal -->
  <div class="modal-backdrop" id="productModal">
    <div class="modal-drawer">
      <div class="drawer-handle"></div>
      <div class="drawer-header">
        <div class="drawer-icon" id="modalEmoji">✨</div>
        <div class="drawer-info">
          <h2 class="drawer-title" id="modalTitle">Product Title</h2>
          <div class="prod-badge" id="modalCategory">Category</div>
        </div>
        <button class="drawer-close" id="modalClose">✕</button>
      </div>

      <div class="price-box">
        <div>
          <div class="price-label">Harga Produk</div>
          <div class="modal-price-idr" id="modalPrice">Rp 0</div>
        </div>
        <div id="modalStockTag"></div>
      </div>

      <div>
        <div class="price-label" style="margin-bottom: 6px;">Detail & Petunjuk Penggunaan:</div>
        <div class="desc-box" id="modalDesc"></div>
      </div>

      <div class="modal-actions">
        <button id="modalQrisPayBtn" class="cta-btn cta-qris" style="display: none;">
          <div class="tactile-tile" style="background: rgba(255, 255, 255, 0.2); width: 28px; height: 28px; border-radius: 8px;">
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#ffffff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
          </div>
          <span>⚡ Bayar Langsung via QRIS (Web)</span>
          <span>➜</span>
        </button>
        <a id="modalBuyLink" href="#" target="_blank" class="cta-btn cta-primary">
          <span>🛒 Beli di Bot Telegram</span>
          <span>➜</span>
        </a>
        <button id="modalCopyBtn" class="cta-btn cta-secondary">
          <span>🔗 Salin Link Produk</span>
        </button>
        <a href="{support_url}" target="_blank" class="cta-btn cta-secondary">
          <span>💬 Tanya Customer Service</span>
        </a>
      </div>
    </div>
  </div>

  <!-- QRIS Direct Web Checkout Modal -->
  <div class="modal-backdrop" id="qrisCheckoutModal">
    <div class="modal-drawer qris-drawer">
      <div class="drawer-handle"></div>
      
      <!-- View 1: Initiate / Input Contact -->
      <div id="qrisViewInit" style="display: block;">
        <div class="drawer-header">
          <div class="drawer-icon" id="qrisProdIcon">⚡</div>
          <div class="drawer-info">
            <h2 class="drawer-title" id="qrisProdTitle">Nama Produk</h2>
            <div class="prod-badge" id="qrisProdPrice">Rp 0</div>
          </div>
          <button class="drawer-close" id="qrisCloseBtn">✕</button>
        </div>

        <div class="qris-notice-box">
          <div style="display: flex; gap: 8px; align-items: flex-start;">
            <span style="font-size: 16px;">💡</span>
            <div style="font-size: 12px; line-height: 1.5; color: var(--text-main);">
              <b>Pembayaran Otomatis & Terverifikasi Real-time</b><br>
              <span style="color: var(--text-muted);">Mendukung semua m-Banking (BCA, Mandiri, BRI, BNI) & E-Wallet (GoPay, OVO, DANA, ShopeePay). Kredensial akun akan langsung dikirim di layar setelah pembayaran berhasil.</span>
            </div>
          </div>
        </div>

        <div style="margin-top: 14px;">
          <label style="font-size: 11.5px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.04em; display: block; margin-bottom: 6px;">
            Email atau No. WhatsApp (Opsional):
          </label>
          <input type="text" id="qrisContactInput" class="search-input" style="padding: 12px 14px;" placeholder="cth: pembeli@gmail.com atau 0812xxxx">
          <div style="font-size: 10.5px; color: var(--text-dim); margin-top: 4px;">
            Digunakan sebagai arsip & backup bukti pembelian Anda.
          </div>
        </div>

        <div class="modal-actions" style="margin-top: 18px;">
          <button id="qrisConfirmPayBtn" class="cta-btn cta-qris" style="padding: 15px;">
            <span>Lanjut Tampilkan QRIS ➜</span>
          </button>
          <button id="qrisCancelInitBtn" class="cta-btn cta-secondary">
            <span>Kembali</span>
          </button>
        </div>
      </div>

      <!-- View 2: Live QRIS & Timer & Auto-Polling -->
      <div id="qrisViewPaying" style="display: none;">
        <div class="drawer-header">
          <div class="drawer-info">
            <h2 class="drawer-title" style="font-size: 17px;" id="qrisPayingProdTitle">Pembayaran QRIS</h2>
            <div style="display: flex; align-items: center; gap: 6px; margin-top: 2px;">
              <span class="status-dot"></span>
              <span style="font-size: 11px; font-weight: 600; color: #34d399;" id="qrisPollStatusText">Mengecek mutasi otomatis...</span>
            </div>
          </div>
          <button class="drawer-close" id="qrisClosePayingBtn">✕</button>
        </div>

        <div class="qris-card-wrap">
          <div class="qris-img-container">
            <img id="qrisImgTag" src="" alt="Scan QRIS Dinamis" class="qris-img">
            <div class="qris-scan-guide">Scan via m-Banking atau E-Wallet apa saja</div>
          </div>

          <div class="qris-amount-card">
            <div style="font-size: 10.5px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.04em;">TOTAL PEMBAYARAN PAS:</div>
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin: 4px 0;">
              <span class="qris-total-amount" id="qrisTotalAmountText">Rp 0</span>
              <button class="copy-badge-btn" id="qrisCopyAmountBtn" title="Salin Nominal">Salin</button>
            </div>
            <div class="qris-code-warn">
              ⚠️ Wajib transfer persis <b><span id="qrisExactWarn">Rp 0</span></b> (termasuk 3 digit kode unik) agar pesanan otomatis diproses dalam hitungan detik!
            </div>
          </div>

          <div class="timer-bar">
            <span>⏱️ Batas Waktu Pembayaran:</span>
            <span id="qrisTimerCountdown" style="font-weight: 800; color: #fb7185;">14:59</span>
          </div>
        </div>

        <div class="modal-actions" style="margin-top: 14px;">
          <button id="qrisDownloadQrBtn" type="button" class="cta-btn cta-secondary" style="font-size: 12.5px;">
            <span>📥 Simpan Gambar QR ke Galeri</span>
          </button>
          <button id="qrisCancelOrderBtn" class="cta-btn cta-secondary" style="color: #fb7185; border-color: rgba(244, 63, 94, 0.3); font-size: 12.5px;">
            <span>❌ Batalkan Pesanan</span>
          </button>
        </div>
      </div>

      <!-- View 3: Success & Immediate Account Delivery -->
      <div id="qrisViewSuccess" style="display: none;">
        <div style="text-align: center; padding: 10px 0 16px;">
          <div class="success-icon-squircle">✓</div>
          <h2 style="font-size: 20px; font-weight: 800; color: #fff; margin-top: 10px;">Pembayaran Berhasil!</h2>
          <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px;">Terima kasih, akun & lisensi Anda telah aktif seketika.</p>
        </div>

        <div class="delivered-box">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 11px; font-weight: 700; color: #34d399; text-transform: uppercase;">🔑 KREDENSIAL AKUN / LISENSI:</span>
            <span style="font-size: 10px; color: var(--text-dim);" id="qrisSuccessOrderId">Order #0</span>
          </div>
          <pre class="credentials-pre" id="qrisCredentialsText"></pre>
        </div>

        <div class="modal-actions" style="margin-top: 16px;">
          <button id="qrisCopyCredsBtn" class="cta-btn cta-primary">
            <span>📋 Salin Data Akun / Lisensi</span>
          </button>
          <button id="qrisDownloadTxtBtn" class="cta-btn cta-secondary">
            <span>📥 Unduh File Lisensi (.txt)</span>
          </button>
          <button id="qrisFinishBtn" class="cta-btn cta-secondary">
            <span>Selesai / Tutup</span>
          </button>
        </div>
      </div>

    </div>
  </div>

  <!-- Order History Modal Drawer -->
  <div class="modal-backdrop" id="historyModal">
    <div class="modal-drawer qris-drawer">
      <div class="drawer-handle"></div>
      <div class="drawer-header">
        <div class="drawer-icon" style="background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);">🕒</div>
        <div class="drawer-info">
          <h2 class="drawer-title">Riwayat Pesanan Anda</h2>
          <div style="font-size: 11px; color: var(--text-muted);">Akses kredensial & cek status pesanan web</div>
        </div>
        <button class="drawer-close" id="historyCloseBtn">✕</button>
      </div>

      <div id="historyListContainer" style="margin-top: 14px; display: flex; flex-direction: column; gap: 10px; max-height: 52vh; overflow-y: auto; padding-right: 2px;">
        <!-- Populated by JS -->
      </div>

      <div class="modal-actions" style="margin-top: 16px;">
        <button id="historyDoneBtn" class="cta-btn cta-secondary">
          <span>Tutup</span>
        </button>
      </div>
    </div>
  </div>

  <!-- Toast Notification -->
  <div class="toast" id="toastMsg">Tautan berhasil disalin!</div>

  <!-- Floating Customer Service Button -->
  <a href="{support_url}" target="_blank" class="fab-support" title="Chat CS Telegram">
    <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
    </svg>
  </a>

  <script>
    const PRODUCTS_DATA = {products_json};
    let currentCurrency = 'IDR';
    let currentCategory = 'all';
    let currentSearch = '';
    let selectedProduct = null;

    const listEl = document.getElementById('productsList');
    const emptyEl = document.getElementById('emptyState');
    const searchInput = document.getElementById('searchInput');
    const catChips = document.querySelectorAll('.cat-chip');
    const currIdrBtn = document.getElementById('currIdr');
    const currUsdtBtn = document.getElementById('currUsdt');

    const modal = document.getElementById('productModal');
    const modalClose = document.getElementById('modalClose');
    const modalEmoji = document.getElementById('modalEmoji');
    const modalTitle = document.getElementById('modalTitle');
    const modalCategory = document.getElementById('modalCategory');
    const modalPrice = document.getElementById('modalPrice');
    const modalStockTag = document.getElementById('modalStockTag');
    const modalDesc = document.getElementById('modalDesc');
    const modalBuyLink = document.getElementById('modalBuyLink');
    const modalCopyBtn = document.getElementById('modalCopyBtn');
    const modalQrisPayBtn = document.getElementById('modalQrisPayBtn');
    const toast = document.getElementById('toastMsg');

    // QRIS Checkout Modal DOM Elements
    const qrisCheckoutModal = document.getElementById('qrisCheckoutModal');
    const qrisViewInit = document.getElementById('qrisViewInit');
    const qrisViewPaying = document.getElementById('qrisViewPaying');
    const qrisViewSuccess = document.getElementById('qrisViewSuccess');

    const qrisProdIcon = document.getElementById('qrisProdIcon');
    const qrisProdTitle = document.getElementById('qrisProdTitle');
    const qrisProdPrice = document.getElementById('qrisProdPrice');
    const qrisContactInput = document.getElementById('qrisContactInput');
    const qrisConfirmPayBtn = document.getElementById('qrisConfirmPayBtn');
    const qrisCancelInitBtn = document.getElementById('qrisCancelInitBtn');
    const qrisCloseBtn = document.getElementById('qrisCloseBtn');

    const qrisPayingProdTitle = document.getElementById('qrisPayingProdTitle');
    const qrisPollStatusText = document.getElementById('qrisPollStatusText');
    const qrisClosePayingBtn = document.getElementById('qrisClosePayingBtn');
    const qrisImgTag = document.getElementById('qrisImgTag');
    const qrisDownloadQrBtn = document.getElementById('qrisDownloadQrBtn');
    const qrisTotalAmountText = document.getElementById('qrisTotalAmountText');
    const qrisCopyAmountBtn = document.getElementById('qrisCopyAmountBtn');
    const qrisExactWarn = document.getElementById('qrisExactWarn');
    const qrisTimerCountdown = document.getElementById('qrisTimerCountdown');
    const qrisCancelOrderBtn = document.getElementById('qrisCancelOrderBtn');

    const qrisSuccessOrderId = document.getElementById('qrisSuccessOrderId');
    const qrisCredentialsText = document.getElementById('qrisCredentialsText');
    const qrisCopyCredsBtn = document.getElementById('qrisCopyCredsBtn');
    const qrisDownloadTxtBtn = document.getElementById('qrisDownloadTxtBtn');
    const qrisFinishBtn = document.getElementById('qrisFinishBtn');

    // Order History & Recovery Elements
    const btnOrderHistory = document.getElementById('btnOrderHistory');
    const pendingOrderBanner = document.getElementById('pendingOrderBanner');
    const bannerOrderAmount = document.getElementById('bannerOrderAmount');
    const historyModal = document.getElementById('historyModal');
    const historyCloseBtn = document.getElementById('historyCloseBtn');
    const historyDoneBtn = document.getElementById('historyDoneBtn');
    const historyListContainer = document.getElementById('historyListContainer');

    let activeOrder = null;
    let pollInterval = null;
    let countdownInterval = null;

    function showToast(msg) {{
      toast.textContent = msg;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2400);
    }}

    // --- Order History LocalStorage Management ---
    function getStoredOrders() {{
      try {{
        return JSON.parse(localStorage.getItem('yowes_orders') || '[]');
      }} catch (e) {{
        return [];
      }}
    }}

    function saveOrderToHistory(order) {{
      if (!order || !order.token) return;
      try {{
        let list = getStoredOrders();
        const existingIdx = list.findIndex(item => item.token === order.token);
        if (existingIdx >= 0) {{
          list[existingIdx] = Object.assign(list[existingIdx], order);
        }} else {{
          list.unshift(order);
        }}
        localStorage.setItem('yowes_orders', JSON.stringify(list.slice(0, 15)));
        updatePendingBanner();
      }} catch (e) {{}}
    }}

    function updatePendingBanner() {{
      const list = getStoredOrders();
      // Find latest pending order that is less than 15 minutes old
      const pending = list.find(item => {{
        if (item.status !== 'pending') return false;
        const created = new Date(item.created_at || 0).getTime();
        return (Date.now() - created) < 900000;
      }});

      if (pending) {{
        bannerOrderAmount.textContent = pending.amount_formatted || 'QRIS';
        pendingOrderBanner.style.display = 'block';
        pendingOrderBanner.onclick = () => resumePendingOrder(pending);
      }} else {{
        pendingOrderBanner.style.display = 'none';
      }}

      const countEl = document.getElementById('historyBadgeCount');
      if (countEl) {{
        if (list.length > 0) {{
          countEl.textContent = list.length;
          countEl.style.display = 'inline-block';
        }} else {{
          countEl.style.display = 'none';
        }}
      }}
    }}

    function renderProducts() {{
      const query = currentSearch.toLowerCase().trim();
      const filtered = PRODUCTS_DATA.filter(p => {{
        const matchCat = (currentCategory === 'all') || (p.category === currentCategory);
        const matchSearch = (!query) || (p.name.toLowerCase().includes(query)) || (p.highlight.toLowerCase().includes(query));
        return matchCat && matchSearch;
      }});

      listEl.innerHTML = '';
      if (filtered.length === 0) {{
        emptyEl.style.display = 'block';
        return;
      }}
      emptyEl.style.display = 'none';

      filtered.forEach(p => {{
        const card = document.createElement('article');
        card.className = 'product-card';
        card.setAttribute('role', 'button');
        card.setAttribute('tabindex', '0');

        const priceDisplay = p.is_coin_price
          ? (p.price_coins_formatted || `${{p.coins || 3}} Koin`)
          : ((currentCurrency === 'IDR') ? p.price_idr_formatted : `${{p.price_usdt}} USDT`);

        const stockClass = p.in_stock ? 'stock-ready' : 'stock-out';
        const stockText = p.in_stock ? 'Ready' : 'Habis';

        card.innerHTML = `
          <div class="card-top">
            <div class="prod-icon-box" style="background: ${{p.gradient}}; --tile-shadow: ${{p.shadow}};">
              ${{p.icon_svg}}
            </div>
            <div class="prod-meta">
              <h2 class="prod-title">${{p.name}}</h2>
              <span class="prod-badge">${{p.category}}</span>
            </div>
          </div>
          <p class="card-highlight">${{p.highlight}}</p>
          <div class="card-footer">
            <div class="price-wrap">
              <span class="price-label">Harga</span>
              <span class="price-value">${{priceDisplay}}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="stock-tag ${{stockClass}}">
                <span class="stock-dot-pill"></span>
                <span>${{stockText}}</span>
              </span>
              <span class="card-btn">Pesan ➜</span>
            </div>
          </div>
        `;

        card.addEventListener('click', () => openModal(p));
        listEl.appendChild(card);
      }});
    }}

    function openModal(p) {{
      selectedProduct = p;
      modalEmoji.style.background = p.gradient;
      modalEmoji.style.setProperty('--tile-shadow', p.shadow);
      modalEmoji.innerHTML = p.icon_svg;
      modalTitle.textContent = p.name;
      modalCategory.textContent = p.category;

      const priceDisplay = p.is_coin_price
        ? (p.price_coins_formatted || `${{p.coins || 3}} Koin`)
        : ((currentCurrency === 'IDR') 
            ? p.price_idr_formatted 
            : `${{p.price_usdt}} USDT`);
      modalPrice.textContent = priceDisplay;

      const stockClass = p.in_stock ? 'stock-ready' : 'stock-out';
      const stockText = p.in_stock ? 'Stok Tersedia' : 'Stok Habis';
      modalStockTag.innerHTML = `
        <span class="stock-tag ${{stockClass}}">
          <span class="stock-dot-pill"></span>
          <span>${{stockText}}</span>
        </span>
      `;

      modalDesc.textContent = p.description || p.highlight || 'Tidak ada petunjuk khusus.';
      modalBuyLink.href = p.buy_url;

      // QRIS payment button visibility: hide for doc builder or out-of-stock
      if (p.key !== 'docs' && p.in_stock) {{
        modalQrisPayBtn.style.display = 'flex';
      }} else {{
        modalQrisPayBtn.style.display = 'none';
      }}

      modal.classList.add('open');
    }}

    function closeModal() {{
      modal.classList.remove('open');
    }}

    modalClose.addEventListener('click', () => {{
      closeModal();
      selectedProduct = null;
    }});
    modal.addEventListener('click', (e) => {{
      if (e.target === modal) {{
        closeModal();
        selectedProduct = null;
      }}
    }});

    modalCopyBtn.addEventListener('click', () => {{
      if (!selectedProduct) return;
      const shareUrl = `${{window.location.origin}}?product=${{selectedProduct.key}}`;
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(shareUrl).then(() => {{
          showToast('Tautan produk berhasil disalin!');
        }});
      }} else {{
        showToast('Link: ' + shareUrl);
      }}
    }});

    // --- QRIS Direct Checkout Flow ---
    function openQrisCheckout(p) {{
      if (!p) return;
      closeModal();

      qrisProdIcon.innerHTML = p.icon_svg;
      qrisProdIcon.style.background = p.gradient;
      qrisProdTitle.textContent = p.name;
      qrisProdPrice.textContent = p.price_idr_formatted;

      const savedContact = localStorage.getItem('yowes_contact') || '';
      qrisContactInput.value = savedContact;

      qrisViewInit.style.display = 'block';
      qrisViewPaying.style.display = 'none';
      qrisViewSuccess.style.display = 'none';
      qrisCheckoutModal.classList.add('open');
    }}

    function closeQrisCheckout() {{
      qrisCheckoutModal.classList.remove('open');
      stopPolling();
      stopCountdown();
      updatePendingBanner();
    }}

    function stopPolling() {{
      if (pollInterval) {{
        clearInterval(pollInterval);
        pollInterval = null;
      }}
    }}

    function stopCountdown() {{
      if (countdownInterval) {{
        clearInterval(countdownInterval);
        countdownInterval = null;
      }}
    }}

    function formatTime(seconds) {{
      const m = Math.floor(seconds / 60);
      const s = seconds % 60;
      return `${{m.toString().padStart(2, '0')}}:${{s.toString().padStart(2, '0')}}`;
    }}

    async function handleCreateOrder() {{
      if (!selectedProduct) return;
      const contactVal = qrisContactInput.value.trim();
      if (contactVal) {{
        localStorage.setItem('yowes_contact', contactVal);
      }}

      qrisConfirmPayBtn.disabled = true;
      const origHtml = qrisConfirmPayBtn.innerHTML;
      qrisConfirmPayBtn.innerHTML = '<span>Membuat QRIS Dinamis...</span>';

      try {{
        const resp = await fetch('/api/order/create', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            product_key: selectedProduct.key,
            contact: contactVal
          }})
        }});

        const result = await resp.json();
        if (!resp.ok || (result.status !== 'success' && !result.ok)) {{
          showToast(result.message || result.error || 'Gagal membuat pesanan QRIS.');
          qrisConfirmPayBtn.disabled = false;
          qrisConfirmPayBtn.innerHTML = origHtml;
          return;
        }}

        activeOrder = result;
        showPayingView(result);

      }} catch (err) {{
        showToast('Koneksi terputus. Silakan coba lagi.');
      }} finally {{
        qrisConfirmPayBtn.disabled = false;
        qrisConfirmPayBtn.innerHTML = origHtml;
      }}
    }}

    function showPayingView(order) {{
      qrisViewInit.style.display = 'none';
      qrisViewPaying.style.display = 'block';
      qrisViewSuccess.style.display = 'none';

      const prodName = selectedProduct ? selectedProduct.name : (order.product_name || 'Pembayaran QRIS');
      qrisPayingProdTitle.textContent = prodName;
      qrisImgTag.src = order.qr_image_url;
      const fmtAmount = order.total_amount_formatted || order.formatted_amount || `Rp ${{Number(order.total_amount || order.allocated_amount).toLocaleString('id-ID')}}`;
      qrisTotalAmountText.textContent = fmtAmount;
      qrisExactWarn.textContent = fmtAmount;
      qrisCopyAmountBtn.dataset.amount = order.total_amount || order.allocated_amount;
      qrisPollStatusText.textContent = 'Mengecek mutasi otomatis...';

      // Save to localStorage history
      saveOrderToHistory({{
        token: order.token || order.order_token,
        product_name: prodName,
        product_key: selectedProduct ? selectedProduct.key : (order.product_key || ''),
        amount_formatted: fmtAmount,
        amount_raw: order.total_amount || order.allocated_amount,
        qr_image_url: order.qr_image_url,
        status: 'pending',
        created_at: order.created_at || new Date().toISOString()
      }});

      let remaining = order.expires_in_seconds || 900;
      qrisTimerCountdown.textContent = formatTime(remaining);
      stopCountdown();
      countdownInterval = setInterval(() => {{
        remaining--;
        if (remaining <= 0) {{
          stopCountdown();
          stopPolling();
          qrisTimerCountdown.textContent = '00:00';
          qrisPollStatusText.textContent = 'Batas waktu pembayaran berakhir.';
          showToast('Waktu pembayaran QRIS telah habis.');
          saveOrderToHistory({{
            token: order.token || order.order_token,
            status: 'expired'
          }});
        }} else {{
          qrisTimerCountdown.textContent = formatTime(remaining);
        }}
      }}, 1000);

      stopPolling();
      pollInterval = setInterval(pollOrderStatus, 3500);
      // Run immediate poll check once
      setTimeout(pollOrderStatus, 800);
    }}

    async function pollOrderStatus() {{
      const token = activeOrder ? (activeOrder.token || activeOrder.order_token) : null;
      if (!token) return;
      try {{
        const resp = await fetch(`/api/order/status?token=${{encodeURIComponent(token)}}`);
        if (!resp.ok) return;
        const data = await resp.json();

        if (data.status === 'approved') {{
          stopPolling();
          stopCountdown();
          showSuccessView(data);
        }} else if (data.status === 'expired' || data.status === 'cancelled') {{
          stopPolling();
          stopCountdown();
          saveOrderToHistory({{
            token: token,
            status: data.status
          }});
          showToast('Pesanan telah kedaluwarsa atau dibatalkan.');
          closeQrisCheckout();
        }}
      }} catch (e) {{
        // Retry silently next loop
      }}
    }}

    function showSuccessView(data) {{
      qrisViewInit.style.display = 'none';
      qrisViewPaying.style.display = 'none';
      qrisViewSuccess.style.display = 'block';

      const token = activeOrder ? (activeOrder.token || activeOrder.order_token) : '';
      qrisSuccessOrderId.textContent = `Order #${{data.order_id || (token ? token.slice(0, 8) : '0')}}`;
      qrisCredentialsText.textContent = data.delivered_data || 'Pesanan berhasil diverifikasi. Terima kasih!';

      saveOrderToHistory({{
        token: token,
        status: 'approved',
        delivered_data: data.delivered_data,
        order_id: data.order_id,
        completed_at: new Date().toISOString()
      }});

      showToast('🎉 Pembayaran berhasil diterima!');
    }}

    async function cancelCurrentOrder() {{
      const token = activeOrder ? (activeOrder.token || activeOrder.order_token) : null;
      if (!token) {{
        closeQrisCheckout();
        return;
      }}
      if (!confirm('Yakin ingin membatalkan pesanan pembayaran ini?')) return;

      try {{
        await fetch('/api/order/cancel', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ token: token }})
        }});
      }} catch (e) {{}}

      saveOrderToHistory({{
        token: token,
        status: 'cancelled'
      }});

      stopPolling();
      stopCountdown();
      activeOrder = null;
      closeQrisCheckout();
      showToast('Pesanan berhasil dibatalkan.');
    }}

    // --- Order History UI Modal Flow ---
    function openHistoryModal() {{
      renderHistoryModal();
      historyModal.classList.add('open');
    }}

    function closeHistoryModal() {{
      historyModal.classList.remove('open');
    }}

    function renderHistoryModal() {{
      const list = getStoredOrders();
      if (!list || list.length === 0) {{
        historyListContainer.innerHTML = `
          <div style="text-align: center; padding: 28px 16px; color: var(--text-muted); font-size: 13px;">
            <div style="font-size: 28px; margin-bottom: 8px;">📭</div>
            Belum ada riwayat pesanan di perangkat ini.
          </div>
        `;
        return;
      }}

      historyListContainer.innerHTML = '';
      list.forEach(item => {{
        const card = document.createElement('div');
        card.className = 'history-card';

        const isApproved = (item.status === 'approved');
        const isPending = (item.status === 'pending');
        const badgeClass = isApproved ? 'history-badge-approved' : (isPending ? 'history-badge-pending' : 'history-badge-pending');
        const badgeText = isApproved ? '✓ Berhasil' : (isPending ? '⏳ Menunggu Bayar' : item.status);
        const dateStr = item.created_at ? new Date(item.created_at).toLocaleString('id-ID', {{ dateStyle: 'medium', timeStyle: 'short' }}) : '-';

        let actionBtns = '';
        if (isApproved) {{
          actionBtns = `
            <button class="history-btn-sm" onclick="viewHistoryCredentials('${{item.token}}')">
              <span>🔑 Lihat Akun</span>
            </button>
            <button class="history-btn-sm" onclick="downloadHistoryTxt('${{item.token}}')">
              <span>📥 Unduh .txt</span>
            </button>
          `;
        }} else if (isPending) {{
          actionBtns = `
            <button class="history-btn-sm history-btn-resume" onclick="resumePendingOrderFromToken('${{item.token}}')">
              <span>⚡ Buka QRIS / Cek Status ➜</span>
            </button>
          `;
        }}

        card.innerHTML = `
          <div class="history-card-top">
            <div>
              <div style="font-size: 13.5px; font-weight: 700; color: #fff;">${{item.product_name || 'Produk Digital'}}</div>
              <div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">${{dateStr}} • ${{item.amount_formatted || ''}}</div>
            </div>
            <span class="${{badgeClass}}">${{badgeText}}</span>
          </div>
          <div style="display: flex; gap: 8px; margin-top: 4px; flex-wrap: wrap;">
            ${{actionBtns}}
          </div>
        `;
        historyListContainer.appendChild(card);
      }});
    }}

    window.viewHistoryCredentials = function(token) {{
      const list = getStoredOrders();
      const found = list.find(it => it.token === token);
      if (!found || !found.delivered_data) {{
        showToast('Kredensial belum tersedia.');
        return;
      }}
      closeHistoryModal();
      activeOrder = found;
      showSuccessView({{
        order_id: found.order_id,
        delivered_data: found.delivered_data
      }});
      qrisCheckoutModal.classList.add('open');
    }};

    window.downloadHistoryTxt = function(token) {{
      const list = getStoredOrders();
      const found = list.find(it => it.token === token);
      if (!found || !found.delivered_data) return;
      const blob = new Blob([found.delivered_data], {{ type: 'text/plain;charset=utf-8' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `lisensi_${{found.product_key || 'order'}}_${{Date.now()}}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('File lisensi (.txt) berhasil diunduh!');
    }};

    window.resumePendingOrderFromToken = function(token) {{
      const list = getStoredOrders();
      const found = list.find(it => it.token === token);
      if (found) {{
        closeHistoryModal();
        resumePendingOrder(found);
      }}
    }};

    function resumePendingOrder(order) {{
      activeOrder = order;
      // Calculate remaining seconds
      const created = new Date(order.created_at || Date.now()).getTime();
      const elapsed = Math.floor((Date.now() - created) / 1000);
      const remaining = Math.max(10, 900 - elapsed);
      order.expires_in_seconds = remaining;

      showPayingView(order);
      qrisCheckoutModal.classList.add('open');
    }}

    btnOrderHistory.addEventListener('click', openHistoryModal);
    historyCloseBtn.addEventListener('click', closeHistoryModal);
    historyDoneBtn.addEventListener('click', closeHistoryModal);
    historyModal.addEventListener('click', (e) => {{
      if (e.target === historyModal) closeHistoryModal();
    }});

    // Safe Download QR Without Page Navigation
    qrisDownloadQrBtn.addEventListener('click', async () => {{
      const qrSrc = qrisImgTag.src;
      if (!qrSrc) return;
      const originalText = qrisDownloadQrBtn.innerHTML;
      qrisDownloadQrBtn.innerHTML = '<span>⏳ Memproses Gambar QR...</span>';

      try {{
        const response = await fetch(qrSrc);
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);

        if (navigator.share && navigator.canShare) {{
          try {{
            const file = new File([blob], 'qris_yowes_digital.png', {{ type: 'image/png' }});
            if (navigator.canShare({{ files: [file] }})) {{
              await navigator.share({{
                title: 'QRIS Pembayaran Yowes Digital',
                text: `QRIS Pembayaran ${{selectedProduct ? selectedProduct.name : ''}}`,
                files: [file]
              }});
              showToast('Gambar QR berhasil dibagikan / disimpan!');
              qrisDownloadQrBtn.innerHTML = originalText;
              return;
            }}
          }} catch (shareErr) {{}}
        }}

        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `qris_yowes_${{Date.now()}}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(blobUrl), 2000);
        showToast('Gambar QR berhasil diunduh ke galeri!');
      }} catch (e) {{
        // Fallback: open in new tab with _blank so web store tab stays completely alive!
        window.open(qrSrc, '_blank');
        showToast('Gambar QR dibuka di tab baru. Tekan lama gambar untuk simpan ke galeri.');
      }} finally {{
        qrisDownloadQrBtn.innerHTML = originalText;
      }}
    }});

    modalQrisPayBtn.addEventListener('click', () => {{
      if (selectedProduct) openQrisCheckout(selectedProduct);
    }});

    qrisConfirmPayBtn.addEventListener('click', handleCreateOrder);
    qrisCloseBtn.addEventListener('click', closeQrisCheckout);
    qrisCancelInitBtn.addEventListener('click', () => {{
      closeQrisCheckout();
      if (selectedProduct) openModal(selectedProduct);
    }});

    qrisClosePayingBtn.addEventListener('click', () => {{
      if (confirm('Tutup tampilan? Verifikasi mutasi QRIS Anda tetap berjalan dan dapat dicek di menu Riwayat.')) {{
        closeQrisCheckout();
      }}
    }});

    qrisCancelOrderBtn.addEventListener('click', cancelCurrentOrder);

    qrisCopyAmountBtn.addEventListener('click', () => {{
      const amt = qrisCopyAmountBtn.dataset.amount;
      if (!amt) return;
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(amt).then(() => {{
          showToast(`Nominal Rp ${{Number(amt).toLocaleString('id-ID')}} disalin!`);
        }});
      }} else {{
        showToast(`Nominal: Rp ${{amt}}`);
      }}
    }});

    qrisCopyCredsBtn.addEventListener('click', () => {{
      const text = qrisCredentialsText.textContent;
      if (!text) return;
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(text).then(() => {{
          showToast('Kredensial lisensi berhasil disalin!');
        }});
      }} else {{
        showToast('Kredensial berhasil disalin.');
      }}
    }});

    qrisDownloadTxtBtn.addEventListener('click', () => {{
      const text = qrisCredentialsText.textContent;
      if (!text) return;
      const blob = new Blob([text], {{ type: 'text/plain;charset=utf-8' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const prodName = selectedProduct ? selectedProduct.key : 'pesanan';
      a.download = `lisensi_${{prodName}}_${{Date.now()}}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('File lisensi (.txt) berhasil diunduh!');
    }});

    qrisFinishBtn.addEventListener('click', () => {{
      closeQrisCheckout();
      selectedProduct = null;
    }});

    qrisCheckoutModal.addEventListener('click', (e) => {{
      if (e.target === qrisCheckoutModal) {{
        if (qrisViewPaying.style.display === 'block') {{
          if (confirm('Tutup tampilan? Verifikasi mutasi QRIS Anda tetap berjalan dan dapat dicek di menu Riwayat.')) {{
            closeQrisCheckout();
          }}
        }} else {{
          closeQrisCheckout();
        }}
      }}
    }});

    // Category Filter Chips
    catChips.forEach(chip => {{
      chip.addEventListener('click', () => {{
        catChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentCategory = chip.dataset.cat;
        renderProducts();
      }});
    }});

    // Search Input reactive listener
    searchInput.addEventListener('input', (e) => {{
      currentSearch = e.target.value;
      renderProducts();
    }});

    // Currency Switcher
    currIdrBtn.addEventListener('click', () => {{
      if (currentCurrency === 'IDR') return;
      currentCurrency = 'IDR';
      currIdrBtn.classList.add('active');
      currUsdtBtn.classList.remove('active');
      renderProducts();
      if (selectedProduct && modal.classList.contains('open')) openModal(selectedProduct);
    }});

    currUsdtBtn.addEventListener('click', () => {{
      if (currentCurrency === 'USDT') return;
      currentCurrency = 'USDT';
      currUsdtBtn.classList.add('active');
      currIdrBtn.classList.remove('active');
      renderProducts();
      if (selectedProduct && modal.classList.contains('open')) openModal(selectedProduct);
    }});

    // Deep link open on load (?product=key) & check active pending banner
    window.addEventListener('DOMContentLoaded', () => {{
      updatePendingBanner();
      const params = new URLSearchParams(window.location.search);
      const targetKey = params.get('product') || params.get('buy');
      if (targetKey) {{
        const found = PRODUCTS_DATA.find(p => p.key === targetKey);
        if (found) {{
          openModal(found);
        }}
      }}
    }});

    // Initial render
    renderProducts();
    updatePendingBanner();
  </script>
</body>
</html>
"""


class WebStoreRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Botkeep Domain and Web Store Clients."""

    def log_message(self, format: str, *args: Any) -> None:
        # Keep logs clean; suppress favicon spam
        if "favicon.ico" not in str(args[0]):
            logger.info("%s - - [%s] %s", self.client_address[0], self.log_date_time_string(), format % args)

    def _send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        resp = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(resp)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(resp)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_HEAD(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Healthcheck for Botkeep uptime monitoring
        if path in ("/health", "/ping", "/status"):
            self._send_json({
                "status": "ok",
                "app": "yowes-digital-store",
                "uptime": time.time(),
                "bot": _get_bot_username(),
            })
            return

        # 2. JSON API for Products
        if path in ("/api/products", "/api/catalog"):
            prods = get_all_products_data()
            self._send_json({"status": "success", "count": len(prods), "products": prods})
            return

        # 3. Check Live QRIS Order Status: GET /api/order/status?token=...
        if path == "/api/order/status":
            token = parse_qs(parsed.query).get("token", [""])[0]
            res = get_web_order_status(token)
            self._send_json(res)
            return

        # 4. Main Web App Store Page
        if path in ("/", "/index.html", "/store"):
            try:
                html_content = render_html_page().encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_content)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(html_content)
                return
            except Exception as exc:
                logger.error("Error rendering web store page: %s", exc)
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.end_headers()
                self.wfile.write(b"Internal Server Error")
                return

        # 5. Fallback 404
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
        payload: dict[str, Any] = {}
        if body_bytes:
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                payload = {}

        # 1. Create Web QRIS Order: POST /api/order/create
        if path == "/api/order/create":
            prod_key = payload.get("product_key", "").strip()
            contact = payload.get("contact", "").strip()
            res = create_web_qris_order(prod_key, contact)
            self._send_json(res)
            return

        # 2. Cancel Web QRIS Order: POST /api/order/cancel
        if path == "/api/order/cancel":
            token = payload.get("token", "").strip()
            res = cancel_web_order(token)
            self._send_json(res)
            return

        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_SERVER_PORT) -> None:
    """Run the Threading HTTPServer synchronously."""
    server_address = (host, port)
    try:
        httpd = ThreadingHTTPServer(server_address, WebStoreRequestHandler)
        logger.info("⚡ Web App Store active on http://%s:%d (Botkeep Ready)", host, port)
        httpd.serve_forever()
    except Exception as exc:
        logger.error("Failed to start Web Store on port %d: %s", port, exc)


def _prodseller_cache_worker() -> None:
    """Continuously refresh ProdSeller stock cache every 50 seconds in the background."""
    while True:
        try:
            ensure_prodseller_cache_sync(force=True)
        except Exception as exc:
            logger.debug("Background ProdSeller stock worker error: %s", exc)
        time.sleep(50)


def _web_shopeepay_poller_worker() -> None:
    """Continuously check and auto-settle pending QRIS orders against ShopeePay mutations in the background."""
    logger.info("⚡ Web Store ShopeePay background mutation worker started")
    while True:
        try:
            import telegram_bot
            db_func = getattr(telegram_bot, "_db", None)
            settle_func = getattr(telegram_bot, "_check_and_settle_qris_payment_sync", None)
            if db_func and settle_func:
                cutoff = (datetime.now() - timedelta(minutes=16)).isoformat()
                with db_func() as conn:
                    pending_rows = conn.execute(
                        "SELECT id FROM payment_requests WHERE method = 'qris' AND status = 'pending' AND created_at >= ?",
                        (cutoff,),
                    ).fetchall()
                for prow in pending_rows:
                    pid = prow[0]
                    try:
                        settled, msg = settle_func(pid)
                        if settled:
                            logger.info("🎉 Web QRIS order #%s auto-settled by background poller!", pid)
                    except Exception as err:
                        logger.debug("Error settling order #%s in web poller: %s", pid, err)
        except Exception as exc:
            logger.debug("Web ShopeePay poller worker error: %s", exc)
        time.sleep(8)


def start_web_server_thread(host: str = DEFAULT_HOST, port: int | None = None) -> threading.Thread:
    """Start the web server in a daemon background thread (safe for bot concurrent runtime)."""
    # Start background workers
    threading.Thread(target=_prodseller_cache_worker, daemon=True, name="ProdSellerWorker").start()
    threading.Thread(target=_web_shopeepay_poller_worker, daemon=True, name="ShopeePayWebPoller").start()

    if port is None:
        port = int(os.getenv("SERVER_PORT") or os.getenv("PORT") or DEFAULT_SERVER_PORT)
    t = threading.Thread(target=run_server, args=(host, port), daemon=True, name="WebStoreThread")
    t.start()
    return t


if __name__ == "__main__":
    threading.Thread(target=_prodseller_cache_worker, daemon=True, name="ProdSellerWorker").start()
    threading.Thread(target=_web_shopeepay_poller_worker, daemon=True, name="ShopeePayWebPoller").start()
    cli_port = DEFAULT_SERVER_PORT
    if len(sys.argv) > 1:
        try:
            cli_port = int(sys.argv[1])
        except ValueError:
            pass
    logger.info("Starting standalone Web Store on port %d...", cli_port)
    run_server(port=cli_port)
