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

PRODUCT_CATEGORIES_EN: dict[str, str] = {
    "docs": "Education",
    "gemini": "AI Tools",
    "chatgpt_k12": "AI Tools",
    "codex": "AI Tools",
    "claude": "AI Tools",
    "notion": "Productivity",
    "office365": "Productivity",
    "figma": "Productivity",
    "ilovepdf": "Productivity",
    "outlook": "Productivity",
    "adobe_express": "Productivity",
    "capcut": "Productivity",
    "spotify": "Entertainment",
    "appletv": "Entertainment",
    "primevideo": "Entertainment",
    "scribd": "Education",
}

# Subtitle / highlights for each product (Indonesian)
PRODUCT_HIGHLIGHTS: dict[str, str] = {
    "docs": "Generate Akun & Dokumen Canva Edu",
    "gemini": "18 Bulan Plan • 5TB Cloud Storage • Private",
    "chatgpt_k12": "Akun Edu 2 Tahun • Akses Model Plus",
    "codex": "API Codex 10M Token • 1 Day",
    "claude": "API CLAUDE 10M Token • 1 Day • All Tools",
    "notion": "Notion Plus 12 Bulan • Unlimited Blocks",
    "office365": "Office 365 Plus 1 Year • 5TB OneDrive",
    "figma": "Figma Pro Edu 2 Years • Unlimited Projects",
    "ilovepdf": "Full Access Web/Mobile/Desktop • AI Tools",
    "outlook": "Full Email Access + OTP Link",
    "appletv": "12 Months Activation Link • 48H Hold Warranty",
    "adobe_express": "12 Months Premium • Direct Redeem Link",
    "capcut": "Capcut Pro 1 Month FW • Full Warranty • 2 Devices",
    "spotify": "Spotify Premium 1 Bulan • Full Warranty",
    "primevideo": "Prime Video 6 Months • Full Private • 180 Days",
    "scribd": "Scribd Premium 1 Bulan • Full Warranty",
}

# Subtitle / highlights for each product (English)
PRODUCT_HIGHLIGHTS_EN: dict[str, str] = {
    "docs": "Generate Teacher Documents & Edu Accounts",
    "gemini": "18 Months Plan • 5TB Cloud Storage • Private",
    "chatgpt_k12": "2-Year Edu Account • Plus Models Access",
    "codex": "API Codex 10M Token • 1 Day Validity",
    "claude": "API CLAUDE 10M Token • 1 Day • All Tools",
    "notion": "Notion Plus 12 Months • Unlimited Blocks",
    "office365": "Office 365 Plus 1 Year • 5TB OneDrive",
    "figma": "Figma Pro Edu 2 Years • Unlimited Projects",
    "ilovepdf": "Full Access Web/Mobile/Desktop • AI Tools",
    "outlook": "Full Email Access + OTP Web Link",
    "appletv": "12 Months Activation Link • 48H Hold Warranty",
    "adobe_express": "12 Months Premium • Direct Redeem Link",
    "capcut": "Capcut Pro 1 Month FW • Full Warranty • 2 Devices",
    "spotify": "Spotify Premium 1 Month • Full Warranty",
    "primevideo": "Prime Video 6 Months • Full Private • 180 Days",
    "scribd": "Scribd Premium 1 Month • Full Warranty",
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


def _get_dynamic_product_theme(key: str, category: str = "", emoji: str = "📦") -> dict[str, str]:
    """Provide a modern tactile squircle tile theme for any dynamically synced product."""
    if category in ("AI Tools", "AI"):
        return {
            "gradient": "linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #ec4899 100%)",
            "shadow": "rgba(124, 58, 237, 0.45)",
            "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 0 1 10 10c0 5.52-4.48 10-10 10S2 17.52 2 12 6.48 2 12 2z"/><path d="m9 12 2 2 4-4"/></svg>',
        }
    elif category in ("Hiburan", "Entertainment"):
        return {
            "gradient": "linear-gradient(135deg, #f59e0b 0%, #ef4444 50%, #db2777 100%)",
            "shadow": "rgba(239, 68, 68, 0.45)",
            "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
        }
    elif category in ("Edukasi", "Education"):
        return {
            "gradient": "linear-gradient(135deg, #06b6d4 0%, #0284c7 50%, #3b82f6 100%)",
            "shadow": "rgba(6, 182, 212, 0.45)",
            "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>',
        }
    else:  # Produktivitas
        return {
            "gradient": "linear-gradient(135deg, #0284c7 0%, #2563eb 50%, #1d4ed8 100%)",
            "shadow": "rgba(37, 99, 235, 0.45)",
            "svg": '<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>',
        }


def ensure_prodseller_cache_sync(force: bool = False) -> list[dict]:
    """Ensure ProdSeller products cache in telegram_bot is populated with live API data."""
    global _last_prodseller_refresh
    now = time.time()
    try:
        import telegram_bot
        expires_at, cached = getattr(telegram_bot, "_prodseller_products_cache", (0.0, []))
        if not force and cached and now < expires_at:
            if hasattr(telegram_bot, "_sync_prodseller_catalog"):
                telegram_bot._sync_prodseller_catalog(cached)
            return cached

        if hasattr(telegram_bot, "_prodseller_request_sync") and hasattr(telegram_bot, "_prodseller_configured"):
            if telegram_bot._prodseller_configured():
                payload = telegram_bot._prodseller_request_sync("GET", "/products")
                products = payload.get("products", [])
                if products:
                    telegram_bot._prodseller_products_cache = (now + 60, products)
                    _last_prodseller_refresh = now
                    if hasattr(telegram_bot, "_sync_prodseller_catalog"):
                        telegram_bot._sync_prodseller_catalog(products)
                    logger.info("ProdSeller live stock cache updated: %d products available", len(products))
                    return products
        if cached and hasattr(telegram_bot, "_sync_prodseller_catalog"):
            telegram_bot._sync_prodseller_catalog(cached)
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
        doc_desc_id = (
            "Layanan generate dokumen pengajar dan verifikasi akun Canva Education secara profesional, cepat, dan legal.\n"
            f"• Biaya generate: {doc_price_coins} Koin per akun / dokumen\n"
            "• Mendukung berbagai negara (Indonesia, Filipina, Malaysia, USA, dll)\n"
            "• Proses instan otomatis via bot Telegram\n"
            "• Garansi dokumen valid dan terverifikasi"
        )
        doc_desc_en = (
            "Professional teacher document generation and Canva Education account verification service.\n"
            f"• Generation fee: {doc_price_coins} Coins per account / document\n"
            "• Supports multiple countries (Indonesia, Philippines, Malaysia, USA, etc.)\n"
            "• Instant automated delivery via Telegram bot\n"
            "• Guaranteed valid and verified documentation"
        )
        products.append({
            "key": "docs",
            "name": "Canva Doc Education",
            "name_id": "Canva Doc Education",
            "name_en": "Canva Doc Education",
            "category": "Edukasi",
            "category_id": "Edukasi",
            "category_en": "Education",
            "emoji": "🎓",
            "icon_svg": theme_docs.get("svg", ""),
            "gradient": theme_docs.get("gradient", "linear-gradient(135deg, #00c4cc 0%, #7d2ae8 100%)"),
            "shadow": theme_docs.get("shadow", "rgba(0, 196, 204, 0.45)"),
            "highlight": PRODUCT_HIGHLIGHTS.get("docs", "Generate Akun & Dokumen"),
            "highlight_id": PRODUCT_HIGHLIGHTS.get("docs", "Generate Akun & Dokumen"),
            "highlight_en": PRODUCT_HIGHLIGHTS_EN.get("docs", "Generate Teacher Documents & Edu Accounts"),
            "is_coin_price": True,
            "coins": doc_price_coins,
            "price_coins_formatted": f"{doc_price_coins} Koin",
            "price_idr": doc_price_coins * 5000,
            "price_idr_formatted": f"{doc_price_coins} Koin",
            "price_usdt": f"{doc_price_coins} Koin",
            "price_note": f"{doc_price_coins} Koin",
            "in_stock": stock_status_func("docs"),
            "description": doc_desc_id,
            "description_id": doc_desc_id,
            "description_en": doc_desc_en,
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
        gemini_desc_en = (
            "🤖 Gemini Pro 18 Months (Redeem Link)\n\n"
            "• 18 Months Plan 🤖\n"
            "• 5TB cloud storage included 🛴\n"
            "• You can add 5 users ⚡️\n"
            "• Not Shared ❌\n"
            "• 100% Private 🔐\n"
            "• NO NEED ANY CARD 💳\n"
            "• 24 Hours Hold warranty ✔️\n"
            "• Works in any country no verification 🛫\n\n"
            "Activation: Open the redeem link in browser and click 'Activate Offer'!"
        )
        theme_gemini = PRODUCT_STYLE_THEMES.get("gemini", {})
        products.append({
            "key": "gemini",
            "name": "Gemini Pro 18 Bulan",
            "name_id": "Gemini Pro 18 Bulan",
            "name_en": "Gemini Pro 18 Months",
            "category": "AI Tools",
            "category_id": "AI Tools",
            "category_en": "AI Tools",
            "emoji": "✨",
            "icon_svg": theme_gemini.get("svg", ""),
            "gradient": theme_gemini.get("gradient", "linear-gradient(135deg, #2563eb 0%, #7c3aed 50%, #db2777 100%)"),
            "shadow": theme_gemini.get("shadow", "rgba(124, 58, 237, 0.45)"),
            "highlight": PRODUCT_HIGHLIGHTS.get("gemini", "18 Bulan • 5TB Cloud • Private"),
            "highlight_id": PRODUCT_HIGHLIGHTS.get("gemini", "18 Bulan • 5TB Cloud • Private"),
            "highlight_en": PRODUCT_HIGHLIGHTS_EN.get("gemini", "18 Months Plan • 5TB Cloud • Private"),
            "price_idr": gemini_p,
            "price_idr_formatted": format_idr_func(gemini_p),
            "price_usdt": gemini_u,
            "price_note": "18 Bulan Plan",
            "in_stock": stock_status_func("gemini"),
            "description": gemini_info,
            "description_id": gemini_info,
            "description_en": gemini_desc_en,
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
        desc_id = info_custom if info_custom else c_cfg.get("default_info_id", "")
        desc_en = info_custom if info_custom else c_cfg.get("default_info_en", desc_id)
        # Dynamic category support
        cat_id = c_cfg.get("category") or PRODUCT_CATEGORIES.get(c_key, "Produktivitas")
        cat_en = c_cfg.get("category_en") or PRODUCT_CATEGORIES_EN.get(c_key, "Productivity")

        # Theme & tactile icon support
        theme_item = PRODUCT_STYLE_THEMES.get(c_key)
        if not theme_item:
            theme_item = _get_dynamic_product_theme(c_key, cat_id, c_cfg.get("emoji", "📦"))

        highlight_id = c_cfg.get("highlight_id") or PRODUCT_HIGHLIGHTS.get(c_key, "Lisensi Resmi • Garansi Aktif")
        highlight_en = c_cfg.get("highlight_en") or PRODUCT_HIGHLIGHTS_EN.get(c_key, "Official License • Full Warranty")

        products.append({
            "key": c_key,
            "name": c_cfg.get("label_id", c_key.title()),
            "name_id": c_cfg.get("label_id", c_key.title()),
            "name_en": c_cfg.get("label_en", c_key.title()),
            "category": cat_id,
            "category_id": cat_id,
            "category_en": cat_en,
            "emoji": c_cfg.get("emoji", "📦"),
            "icon_svg": theme_item.get("svg", default_theme["svg"]),
            "gradient": theme_item.get("gradient", default_theme["gradient"]),
            "shadow": theme_item.get("shadow", default_theme["shadow"]),
            "highlight": highlight_id,
            "highlight_id": highlight_id,
            "highlight_en": highlight_en,
            "price_idr": p_idr,
            "price_idr_formatted": format_idr_func(p_idr),
            "price_usdt": p_usdt,
            "price_note": f"+0.5 USDT Markup",
            "in_stock": stock_status_func(c_key),
            "description": desc_id,
            "description_id": desc_id,
            "description_en": desc_en,
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
    now_dt = datetime.now()
    now_iso = now_dt.isoformat()
    now_ts = int(time.time())

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
        "expires_at_ts": now_ts + 900,
        "created_at": now_iso,
        "created_at_ts": now_ts,
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
                try:
                    created_dt = datetime.fromisoformat(p["created_at"])
                    if created_dt.tzinfo is not None:
                        now_dt = datetime.now(created_dt.tzinfo)
                    else:
                        now_dt = datetime.now()
                    elapsed = max(0.0, (now_dt - created_dt).total_seconds())
                except Exception as parse_err:
                    logger.warning("Could not parse created_at timestamp %s: %s", p.get("created_at"), parse_err)
                    elapsed = 0.0

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
                    dyn_qris = p.get("qris_payload") or ""
                    qr_url = ""
                    if dyn_qris:
                        try:
                            qr_url = qris_engine.get_qris_qr_image_url(dyn_qris, size=420)
                        except Exception:
                            pass
                    rem_sec = max(0, int(900 - elapsed))
                    now_ts = int(time.time())
                    return {
                        "ok": True,
                        "status": "pending",
                        "order_id": p["id"],
                        "product_key": p.get("product_key", ""),
                        "amount": p["amount"],
                        "amount_formatted": p["amount"],
                        "formatted_amount": p["amount"],
                        "total_amount_formatted": p["amount"],
                        "raw_amount": p.get("raw_amount") or 0,
                        "total_amount": p.get("raw_amount") or 0,
                        "allocated_amount": p.get("raw_amount") or 0,
                        "dynamic_qris": dyn_qris,
                        "qr_image_url": qr_url,
                        "created_at": p["created_at"],
                        "expires_in_seconds": rem_sec,
                        "expires_at_ts": now_ts + rem_sec,
                    }

            if p["status"] == "approved":
                return {
                    "ok": True,
                    "status": "approved",
                    "order_id": p["id"],
                    "product_key": p.get("product_key", ""),
                    "amount": p["amount"],
                    "amount_formatted": p["amount"],
                    "formatted_amount": p["amount"],
                    "total_amount_formatted": p["amount"],
                    "raw_amount": p.get("raw_amount") or 0,
                    "total_amount": p.get("raw_amount") or 0,
                    "provider_order_id": p.get("provider_order_id", ""),
                    "delivered_data": p.get("delivered_data", ""),
                    "approved_at": p.get("reviewed_at", ""),
                }

            return {
                "ok": True,
                "status": p["status"],
                "order_id": p["id"],
                "product_key": p.get("product_key", ""),
                "amount": p["amount"],
                "amount_formatted": p["amount"],
                "formatted_amount": p["amount"],
                "total_amount_formatted": p["amount"],
                "raw_amount": p.get("raw_amount") or 0,
                "total_amount": p.get("raw_amount") or 0,
                "delivered_data": p.get("delivered_data", ""),
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
  <script>
    // Silencer for third-party browser extension script errors and external dead CDNs (e.g. static-lib)
    window.addEventListener('error', function(e) {{
      if (!e) return false;
      var f = (e.filename || (e.target && (e.target.src || e.target.href)) || '').toString();
      var m = (e.message || '').toString();
      if (f.indexOf('static-lib') !== -1 || f.indexOf('chrome-extension:') === 0 || f.indexOf('moz-extension:') === 0 || m.indexOf('static-lib') !== -1 || m.indexOf('ERR_ADDRESS_INVALID') !== -1) {{
        if (e.stopImmediatePropagation) e.stopImmediatePropagation();
        if (e.preventDefault) e.preventDefault();
        return true;
      }}
    }}, true);
    window.addEventListener('unhandledrejection', function(e) {{
      if (!e || !e.reason) return;
      var r = (e.reason.message || e.reason || '').toString();
      if (r.indexOf('static-lib') !== -1 || r.indexOf('ERR_ADDRESS_INVALID') !== -1) {{
        if (e.preventDefault) e.preventDefault();
      }}
    }});
  </script>
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
    .history-badge-expired {{
      font-size: 10px;
      font-weight: 700;
      color: #94a3b8;
      background: rgba(148, 163, 184, 0.12);
      border: 1px solid rgba(148, 163, 184, 0.25);
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

    /* Custom In-App Confirmation Dialog (Telegram / Riwayat Button Theme) */
    #confirmDialog {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    #confirmDialog.open {{
      opacity: 1;
      pointer-events: auto;
    }}
    .confirm-dialog-card {{
      background: linear-gradient(145deg, rgba(22, 28, 44, 0.98) 0%, rgba(11, 14, 24, 0.99) 100%);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 24px;
      padding: 26px 22px 22px;
      width: 100%;
      max-width: 380px;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.08);
      text-align: center;
      animation: dialogPop 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    @keyframes dialogPop {{
      0% {{ opacity: 0; transform: scale(0.9) translateY(12px); }}
      100% {{ opacity: 1; transform: scale(1) translateY(0); }}
    }}
    /* 3D Tactile Tile matching Telegram Bot Button and History Button */
    .confirm-dialog-tile {{
      width: 56px;
      height: 56px;
      border-radius: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 16px;
      position: relative;
      border: 1.5px solid rgba(255, 255, 255, 0.35);
      box-shadow: 0 8px 24px -4px rgba(0, 180, 216, 0.5), inset 0 2px 2px rgba(255, 255, 255, 0.6), inset 0 -2px 2px rgba(0, 0, 0, 0.25);
      background: linear-gradient(135deg, #0088cc 0%, #00b4d8 100%);
      transition: all 0.3s ease;
    }}
    .confirm-dialog-tile.danger {{
      background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
      border-color: rgba(255, 255, 255, 0.35);
      box-shadow: 0 8px 24px -4px rgba(239, 68, 68, 0.55), inset 0 2px 2px rgba(255, 255, 255, 0.6), inset 0 -2px 2px rgba(0, 0, 0, 0.25);
    }}
    .confirm-dialog-circle {{
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.22);
    }}
    .confirm-dialog-circle svg {{
      display: block;
    }}
    .confirm-dialog-title {{
      font-size: 16.5px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.2px;
      margin-bottom: 8px;
      line-height: 1.35;
    }}
    .confirm-dialog-desc {{
      font-size: 13px;
      color: var(--text-muted);
      line-height: 1.55;
      margin-bottom: 22px;
      padding: 0 4px;
    }}
    .confirm-dialog-actions {{
      display: flex;
      gap: 10px;
      width: 100%;
    }}
    .confirm-btn {{
      flex: 1;
      padding: 13px 14px;
      border-radius: var(--radius-md);
      font-size: 13.5px;
      font-weight: 700;
      cursor: pointer;
      border: none;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      font-family: inherit;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }}
    .confirm-btn-cancel {{
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-muted);
      border: 1px solid rgba(255, 255, 255, 0.12);
    }}
    .confirm-btn-cancel:hover {{
      background: rgba(255, 255, 255, 0.14);
      color: #ffffff;
      transform: translateY(-1px);
    }}
    .confirm-btn-primary {{
      background: linear-gradient(135deg, #0088cc 0%, #00b4d8 100%);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(0, 180, 216, 0.4);
    }}
    .confirm-btn-primary:hover {{
      opacity: 0.95;
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(0, 180, 216, 0.5);
    }}
    .confirm-btn-danger {{
      background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(239, 68, 68, 0.4);
    }}
    .confirm-btn-danger:hover {{
      opacity: 0.95;
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(239, 68, 68, 0.5);
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
      <p class="store-tagline" id="storeTagline">{STORE_TAGLINE}</p>
      
      <div class="status-pill">
        <span class="status-dot"></span>
        <span id="headerStatusText">Online 24 Jam • Sistem Otomatis</span>
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
            <span id="btnTelegramText">Buka Bot Telegram</span>
          </div>
          <span class="btn-chevron">➜</span>
        </a>
        <a href="{support_url}" target="_blank" class="lynk-btn">
          <div class="btn-left">
            <div class="tactile-tile btn-tile" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); --tile-shadow: rgba(16, 185, 129, 0.45);">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
            </div>
            <span id="btnSupportText">Hubungi Customer Service</span>
          </div>
          <span class="btn-chevron">➜</span>
        </a>
        <a href="{channel_url}" target="_blank" class="lynk-btn">
          <div class="btn-left">
            <div class="tactile-tile btn-tile" style="background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%); --tile-shadow: rgba(245, 158, 11, 0.45);">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="#ffffff"><path d="M18 11v-4c0-1.1-.9-2-2-2h-3l-5-4v16l5-4h3c1.1 0 2-.9 2-2v-4zm-8-3.17L12.83 10H16v4h-3.17L10 16.17V7.83zM20 7v10c1.3-.84 2-2.3 2-4s-.7-3.16-2-4z"/></svg>
            </div>
            <span id="btnChannelText">Official Update Channel</span>
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
        <div class="trust-title" id="trust1Title">Auto Instant</div>
        <div class="trust-desc" id="trust1Desc">Kirim Otomatis</div>
      </div>
      <div class="trust-item">
        <div class="tactile-tile trust-tile" style="background: linear-gradient(135deg, #10b981 0%, #047857 100%); --tile-shadow: rgba(16, 185, 129, 0.45);">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
        </div>
        <div class="trust-title" id="trust2Title">Garansi Aktif</div>
        <div class="trust-desc" id="trust2Desc">Sesuai Produk</div>
      </div>
      <div class="trust-item">
        <div class="tactile-tile trust-tile" style="background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); --tile-shadow: rgba(139, 92, 246, 0.45);">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="3"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
        </div>
        <div class="trust-title" id="trust3Title">QRIS & USDT</div>
        <div class="trust-desc" id="trust3Desc">Payment Realtime</div>
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
          <span id="btnOrderHistoryText" style="font-weight: 700; font-size: 14.5px; color: #ffffff; letter-spacing: -0.2px;">Riwayat Pesanan</span>
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
          <button class="cat-chip active" data-cat="all" id="catChipAll">⚡ Semua</button>
          <button class="cat-chip" data-cat="ai" id="catChipAi">🤖 AI</button>
          <button class="cat-chip" data-cat="productivity" id="catChipProductivity">💼 Produktivitas</button>
          <button class="cat-chip" data-cat="entertainment" id="catChipEntertainment">🎬 Hiburan</button>
          <button class="cat-chip" data-cat="education" id="catChipEducation">🎓 Edukasi</button>
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
              <span id="bannerPendingTitle">Ada Pesanan QRIS Berjalan</span> (<span id="bannerOrderAmount">Rp 0</span>)
            </div>
          </div>
          <span id="bannerPendingAction" style="font-size: 11px; font-weight: 800; color: #fbbf24; background: rgba(245, 158, 11, 0.2); padding: 4px 8px; border-radius: 8px;">Buka QRIS ➜</span>
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
      <h3 class="faq-title" id="faqTitle">💡 Panduan & Tanya Jawab</h3>
      <div class="faq-item">
        <div class="faq-q" id="faqQ1">1. Bagaimana cara membeli produk?</div>
        <div class="faq-a" id="faqA1">Klik produk yang Anda inginkan, lalu pilih <b>"Beli di Bot Telegram"</b> atau <b>"Bayar Langsung via QRIS"</b>. Sistem akan memproses secara otomatis.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q" id="faqQ2">2. Kapan akun/lisensi dikirimkan?</div>
        <div class="faq-a" id="faqA2">Sistem kami terintegrasi 24 jam. Begitu pembayaran terverifikasi otomatis, data akun/link aktivasi langsung dikirim di layar atau chat Telegram Anda dalam hitungan detik.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q" id="faqQ3">3. Apakah ada garansi?</div>
        <div class="faq-a" id="faqA3">Ya, seluruh produk kami memiliki garansi hold dan replacement. Jika terjadi kendala, customer service kami siap membantu via Telegram.</div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <p id="footerRights">© 2026 {STORE_NAME} • Hak Cipta Dilindungi</p>
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
          <div class="price-label" id="modalPriceLabel">Harga Produk</div>
          <div class="modal-price-idr" id="modalPrice">Rp 0</div>
        </div>
        <div id="modalStockTag"></div>
      </div>

      <div>
        <div class="price-label" id="modalDescLabel" style="margin-bottom: 6px;">Detail & Petunjuk Penggunaan:</div>
        <div class="desc-box" id="modalDesc"></div>
      </div>

      <div class="modal-actions">
        <button id="modalQrisPayBtn" class="cta-btn cta-qris" style="display: none;">
          <div class="tactile-tile" style="background: rgba(255, 255, 255, 0.2); width: 28px; height: 28px; border-radius: 8px;">
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#ffffff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
          </div>
          <span id="modalQrisPayText">⚡ Bayar Langsung via QRIS (Web)</span>
          <span>➜</span>
        </button>
        <a id="modalBuyLink" href="#" target="_blank" class="cta-btn cta-primary">
          <span id="modalBuyLinkText">🛒 Beli di Bot Telegram</span>
          <span>➜</span>
        </a>
        <button id="modalCopyBtn" class="cta-btn cta-secondary">
          <span id="modalCopyBtnText">🔗 Salin Link Produk</span>
        </button>
        <a href="{support_url}" target="_blank" class="cta-btn cta-secondary">
          <span id="modalSupportBtnText">💬 Tanya Customer Service</span>
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
              <b id="qrisNoticeTitle">Pembayaran Otomatis & Terverifikasi Real-time</b><br>
              <span id="qrisNoticeDesc" style="color: var(--text-muted);">Mendukung semua m-Banking (BCA, Mandiri, BRI, BNI) & E-Wallet (GoPay, OVO, DANA, ShopeePay). Kredensial akun akan langsung dikirim di layar setelah pembayaran berhasil.</span>
            </div>
          </div>
        </div>

        <div style="margin-top: 14px;">
          <label id="qrisContactLabel" style="font-size: 11.5px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.04em; display: block; margin-bottom: 6px;">
            Email atau No. WhatsApp (Opsional):
          </label>
          <input type="text" id="qrisContactInput" class="search-input" style="padding: 12px 14px;" placeholder="cth: pembeli@gmail.com atau 0812xxxx">
          <div id="qrisContactHelp" style="font-size: 10.5px; color: var(--text-dim); margin-top: 4px;">
            Digunakan sebagai arsip & backup bukti pembelian Anda.
          </div>
        </div>

        <div class="modal-actions" style="margin-top: 18px;">
          <button id="qrisConfirmPayBtn" class="cta-btn cta-qris" style="padding: 15px;">
            <span id="qrisConfirmPayBtnText">Lanjut Tampilkan QRIS ➜</span>
          </button>
          <button id="qrisCancelInitBtn" class="cta-btn cta-secondary">
            <span id="qrisCancelInitBtnText">Kembali</span>
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
            <div class="qris-scan-guide" id="qrisScanGuide">Scan via m-Banking atau E-Wallet apa saja</div>
          </div>

          <div class="qris-amount-card">
            <div id="qrisTotalAmountLabel" style="font-size: 10.5px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.04em;">TOTAL PEMBAYARAN PAS:</div>
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin: 4px 0;">
              <span class="qris-total-amount" id="qrisTotalAmountText">Rp 0</span>
              <button class="copy-badge-btn" id="qrisCopyAmountBtn" title="Salin Nominal">Salin</button>
            </div>
            <div class="qris-code-warn" id="qrisExactWarnBox">
              ⚠️ Wajib transfer persis <b><span id="qrisExactWarn">Rp 0</span></b> (termasuk 3 digit kode unik) agar pesanan otomatis diproses dalam hitungan detik!
            </div>
          </div>

          <div class="timer-bar">
            <span id="qrisTimerLabel">⏱️ Batas Waktu Pembayaran:</span>
            <span id="qrisTimerCountdown" style="font-weight: 800; color: #fb7185;">14:59</span>
          </div>
        </div>

        <div class="modal-actions" style="margin-top: 14px;">
          <button id="qrisDownloadQrBtn" type="button" class="cta-btn cta-secondary" style="font-size: 12.5px;">
            <span id="qrisDownloadQrBtnText">📥 Simpan Gambar QR ke Galeri</span>
          </button>
          <button id="qrisCancelOrderBtn" class="cta-btn cta-secondary" style="color: #fb7185; border-color: rgba(244, 63, 94, 0.3); font-size: 12.5px;">
            <span id="qrisCancelOrderBtnText">❌ Batalkan Pesanan</span>
          </button>
        </div>
      </div>

      <!-- View 3: Success & Immediate Account Delivery -->
      <div id="qrisViewSuccess" style="display: none;">
        <div style="text-align: center; padding: 10px 0 16px;">
          <div class="success-icon-squircle">✓</div>
          <h2 id="qrisSuccessTitle" style="font-size: 20px; font-weight: 800; color: #fff; margin-top: 10px;">Pembayaran Berhasil!</h2>
          <p id="qrisSuccessDesc" style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px;">Terima kasih, akun & lisensi Anda telah aktif seketika.</p>
        </div>

        <div class="delivered-box">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span id="qrisCredsLabel" style="font-size: 11px; font-weight: 700; color: #34d399; text-transform: uppercase;">🔑 KREDENSIAL AKUN / LISENSI:</span>
            <span style="font-size: 10px; color: var(--text-dim);" id="qrisSuccessOrderId">Order #0</span>
          </div>
          <pre class="credentials-pre" id="qrisCredentialsText"></pre>
        </div>

        <div class="modal-actions" style="margin-top: 16px;">
          <a id="qrisOpenLinkBtn" href="#" target="_blank" rel="noopener noreferrer" class="cta-btn cta-primary" style="display: none; background: linear-gradient(135deg, #0284c7 0%, #06b6d4 100%); text-decoration: none;">
            <span id="qrisOpenLinkBtnText">🔗 Buka Link / Tautan Akses</span>
            <span>➜</span>
          </a>
          <button id="qrisCopyCredsBtn" class="cta-btn cta-primary">
            <span id="qrisCopyCredsBtnText">📋 Salin Data Akun / Lisensi</span>
          </button>
          <button id="qrisDownloadTxtBtn" class="cta-btn cta-secondary">
            <span id="qrisDownloadTxtBtnText">📥 Unduh File Lisensi (.txt)</span>
          </button>
          <button id="qrisFinishBtn" class="cta-btn cta-secondary">
            <span id="qrisFinishBtnText">Selesai / Tutup</span>
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
          <h2 class="drawer-title" id="historyModalTitle">Riwayat Pesanan Anda</h2>
          <div id="historyModalSubtitle" style="font-size: 11px; color: var(--text-muted);">Akses kredensial & cek status pesanan web</div>
        </div>
        <button class="drawer-close" id="historyCloseBtn">✕</button>
      </div>

      <div id="historyListContainer" style="margin-top: 14px; display: flex; flex-direction: column; gap: 10px; max-height: 52vh; overflow-y: auto; padding-right: 2px;">
        <!-- Populated by JS -->
      </div>

      <div class="modal-actions" style="margin-top: 16px;">
        <button id="historyDoneBtn" class="cta-btn cta-secondary">
          <span id="historyDoneBtnText">Tutup</span>
        </button>
      </div>
    </div>
  </div>

  <!-- Custom Confirmation Dialog Modal -->
  <div class="modal-backdrop" id="confirmDialog" style="display: none;">
    <div class="confirm-dialog-card">
      <div class="confirm-dialog-tile" id="confirmDialogTile">
        <div class="confirm-dialog-circle" id="confirmDialogCircle">
          <!-- Dynamic SVG injected -->
        </div>
      </div>
      <div class="confirm-dialog-title" id="confirmDialogTitle">Konfirmasi</div>
      <div class="confirm-dialog-desc" id="confirmDialogDesc">Apakah Anda yakin?</div>
      <div class="confirm-dialog-actions">
        <button type="button" class="confirm-btn confirm-btn-cancel" id="confirmDialogCancelBtn">Batal</button>
        <button type="button" class="confirm-btn confirm-btn-primary" id="confirmDialogOkBtn">Lanjutkan</button>
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
    let currentLanguage = 'id';
    let currentCategory = 'all';
    let currentSearch = '';
    let selectedProduct = null;

    const I18N = {{
      id: {{
        tagline: "{STORE_TAGLINE}",
        headerStatus: "Online 24 Jam • Sistem Otomatis",
        btnTelegram: "Buka Bot Telegram",
        btnSupport: "Hubungi Customer Service",
        btnChannel: "Official Update Channel",
        trust1Title: "Auto Instant",
        trust1Desc: "Kirim Otomatis",
        trust2Title: "Garansi Aktif",
        trust2Desc: "Sesuai Produk",
        trust3Title: "QRIS & USDT",
        trust3Desc: "Payment Realtime",
        btnOrderHistory: "Riwayat Pesanan",
        searchPlaceholder: "Cari produk (Gemini, Canva, Office, dll)...",
        catAll: "⚡ Semua",
        catAi: "🤖 AI",
        catProductivity: "💼 Produktivitas",
        catEntertainment: "🎬 Hiburan",
        catEducation: "🎓 Edukasi",
        bannerPending: "Ada Pesanan QRIS Berjalan",
        bannerAction: "Buka QRIS ➜",
        emptyState: "🔍 Tidak ada produk yang sesuai dengan pencarian.",
        faqTitle: "💡 Panduan & Tanya Jawab",
        faqQ1: "1. Bagaimana cara membeli produk?",
        faqA1: 'Klik produk yang Anda inginkan, lalu pilih <b>"Beli di Bot Telegram"</b> atau <b>"Bayar Langsung via QRIS"</b>. Sistem akan memproses secara otomatis.',
        faqQ2: "2. Kapan akun/lisensi dikirimkan?",
        faqA2: "Sistem kami terintegrasi 24 jam. Begitu pembayaran terverifikasi otomatis, data akun/link aktivasi langsung dikirim di layar atau chat Telegram Anda dalam hitungan detik.",
        faqQ3: "3. Apakah ada garansi?",
        faqA3: "Ya, seluruh produk kami memiliki garansi hold dan replacement. Jika terjadi kendala, customer service kami siap membantu via Telegram.",
        footerRights: "© 2026 {STORE_NAME} • Hak Cipta Dilindungi",
        cardPriceLabel: "Harga",
        cardOrderBtn: "Pesan ➜",
        stockReady: "Ready",
        stockOut: "Habis",
        modalPriceLabel: "Harga Produk",
        modalStockReady: "Stok Tersedia",
        modalStockOut: "Stok Habis",
        modalDescLabel: "Detail & Petunjuk Penggunaan:",
        modalQrisBtn: "⚡ Bayar Langsung via QRIS (Web)",
        modalBuyLink: "🛒 Beli di Bot Telegram",
        modalCopyBtn: "🔗 Salin Link Produk",
        modalSupportBtn: "💬 Tanya Customer Service",
        qrisNoticeTitle: "Pembayaran Otomatis & Terverifikasi Real-time",
        qrisNoticeDesc: "Mendukung semua m-Banking (BCA, Mandiri, BRI, BNI) & E-Wallet (GoPay, OVO, DANA, ShopeePay). Kredensial akun akan langsung dikirim di layar setelah pembayaran berhasil.",
        qrisContactLabel: "Email atau No. WhatsApp (Opsional):",
        qrisContactPlaceholder: "cth: pembeli@gmail.com atau 0812xxxx",
        qrisContactHelp: "Digunakan sebagai arsip & backup bukti pembelian Anda.",
        qrisConfirmPayBtn: "Lanjut Tampilkan QRIS ➜",
        qrisCancelInitBtn: "Kembali",
        qrisPayingTitle: "Pembayaran QRIS",
        qrisPollStatus: "Mengecek mutasi otomatis...",
        qrisScanGuide: "Scan via m-Banking atau E-Wallet apa saja",
        qrisTotalAmountLabel: "TOTAL PEMBAYARAN PAS:",
        qrisCopyBadge: "Salin",
        qrisExactWarnPrefix: "⚠️ Wajib transfer persis",
        qrisExactWarnSuffix: "(termasuk 3 digit kode unik) agar pesanan otomatis diproses dalam hitungan detik!",
        qrisTimerLabel: "⏱️ Batas Waktu Pembayaran:",
        qrisDownloadQrBtn: "📥 Simpan Gambar QR ke Galeri",
        qrisCancelOrderBtn: "❌ Batalkan Pesanan",
        qrisSuccessTitle: "Pembayaran Berhasil!",
        qrisSuccessDesc: "Terima kasih, akun & lisensi Anda telah aktif seketika.",
        qrisCredsLabel: "🔑 KREDENSIAL AKUN / LISENSI:",
        qrisOpenLinkBtn: "🔗 Buka Link / Tautan Akses ➜",
        qrisCopyCredsBtn: "📋 Salin Data Akun / Lisensi",
        qrisDownloadTxtBtn: "📥 Unduh File Lisensi (.txt)",
        qrisFinishBtn: "Selesai / Tutup",
        historyTitle: "Riwayat Pesanan Anda",
        historySubtitle: "Akses kredensial & cek status pesanan web",
        historyEmpty: "Belum ada riwayat pesanan di perangkat ini.",
        historyBadgeApproved: "✓ Berhasil",
        historyBadgePending: "⏳ Menunggu Bayar",
        historyBadgeExpired: "⏱ Kedaluwarsa",
        historyBtnView: "🔑 Lihat Akun",
        historyBtnDownload: "📥 Unduh .txt",
        historyBtnResume: "⚡ Buka QRIS / Cek Status ➜",
        historyDoneBtn: "Tutup",
        toastCopied: "Tautan produk berhasil disalin!",
        toastNominalCopied: "Nominal pembayaran disalin!",
        toastCredsCopied: "Kredensial lisensi berhasil disalin!",
        toastTxtDownloaded: "File lisensi (.txt) berhasil diunduh!",
        toastQrDownloaded: "Gambar QR berhasil diunduh ke galeri!",
        toastOrderCancelled: "Pesanan berhasil dibatalkan."
      }},
      en: {{
        tagline: "Official Digital Store • Instant Automated Delivery 24/7 • Active Warranty",
        headerStatus: "Online 24/7 • Automated System",
        btnTelegram: "Open Telegram Bot",
        btnSupport: "Contact Customer Support",
        btnChannel: "Official Channel",
        trust1Title: "Auto Instant",
        trust1Desc: "Instant Delivery",
        trust2Title: "Active Warranty",
        trust2Desc: "Guaranteed",
        trust3Title: "QRIS & USDT",
        trust3Desc: "Realtime Payment",
        btnOrderHistory: "Order History",
        searchPlaceholder: "Search products (Gemini, Canva, Office, etc)...",
        catAll: "⚡ All",
        catAi: "🤖 AI Tools",
        catProductivity: "💼 Productivity",
        catEntertainment: "🎬 Entertainment",
        catEducation: "🎓 Education",
        bannerPending: "Active QRIS Order in Progress",
        bannerAction: "Open QRIS ➜",
        emptyState: "🔍 No products found matching your search.",
        faqTitle: "💡 Guide & FAQ",
        faqQ1: "1. How to purchase products?",
        faqA1: 'Click on your desired product, then choose <b>"Buy in Telegram Bot"</b> or <b>"Pay Directly via QRIS"</b>. The system processes orders automatically.',
        faqQ2: "2. When will the license/account be delivered?",
        faqA2: "Our system runs 24/7. Once payment is verified, your account or activation link is delivered on-screen or in your Telegram chat within seconds.",
        faqQ3: "3. Is there a warranty?",
        faqA3: "Yes, all products include hold and replacement warranties. If you need assistance, our support is ready on Telegram.",
        footerRights: "© 2026 {STORE_NAME} • All Rights Reserved",
        cardPriceLabel: "Price",
        cardOrderBtn: "Order ➜",
        stockReady: "In Stock",
        stockOut: "Sold Out",
        modalPriceLabel: "Product Price",
        modalStockReady: "In Stock",
        modalStockOut: "Out of Stock",
        modalDescLabel: "Details & Instructions:",
        modalQrisBtn: "⚡ Pay Directly via QRIS (Web)",
        modalBuyLink: "🛒 Buy in Telegram Bot",
        modalCopyBtn: "🔗 Copy Product Link",
        modalSupportBtn: "💬 Ask Customer Support",
        qrisNoticeTitle: "Automated & Real-time Verified Payment",
        qrisNoticeDesc: "Supports all m-Banking & E-Wallets. Account credentials will be delivered instantly on-screen upon successful payment.",
        qrisContactLabel: "Email or WhatsApp (Optional):",
        qrisContactPlaceholder: "e.g. buyer@gmail.com or +62812xxxx",
        qrisContactHelp: "Used as an archive & backup for your order receipt.",
        qrisConfirmPayBtn: "Proceed to QRIS ➜",
        qrisCancelInitBtn: "Back",
        qrisPayingTitle: "QRIS Payment",
        qrisPollStatus: "Checking transaction status automatically...",
        qrisScanGuide: "Scan with any m-Banking or E-Wallet app",
        qrisTotalAmountLabel: "EXACT TOTAL AMOUNT:",
        qrisCopyBadge: "Copy",
        qrisExactWarnPrefix: "⚠️ Transfer exact amount of",
        qrisExactWarnSuffix: "(including 3-digit unique code) for instant automated processing!",
        qrisTimerLabel: "⏱️ Payment Time Remaining:",
        qrisDownloadQrBtn: "📥 Save QR Image to Gallery",
        qrisCancelOrderBtn: "❌ Cancel Order",
        qrisSuccessTitle: "Payment Successful!",
        qrisSuccessDesc: "Thank you! Your account & license is now active.",
        qrisCredsLabel: "🔑 ACCOUNT CREDENTIALS / LICENSE:",
        qrisOpenLinkBtn: "🔗 Open Access Link ➜",
        qrisCopyCredsBtn: "📋 Copy Credentials",
        qrisDownloadTxtBtn: "📥 Download License (.txt)",
        qrisFinishBtn: "Done / Close",
        historyTitle: "Your Order History",
        historySubtitle: "Access credentials & check web order status",
        historyEmpty: "No order history found on this device.",
        historyBadgeApproved: "✓ Completed",
        historyBadgePending: "⏳ Awaiting Payment",
        historyBadgeExpired: "⏱ Expired",
        historyBtnView: "🔑 View Account",
        historyBtnDownload: "📥 Download .txt",
        historyBtnResume: "⚡ Open QRIS / Check Status ➜",
        historyDoneBtn: "Close",
        toastCopied: "Product link copied to clipboard!",
        toastNominalCopied: "Payment amount copied!",
        toastCredsCopied: "Credentials copied to clipboard!",
        toastTxtDownloaded: "License file (.txt) downloaded!",
        toastQrDownloaded: "QR image saved to gallery!",
        toastOrderCancelled: "Order successfully cancelled."
      }}
    }};

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
    const qrisExactWarnBox = document.getElementById('qrisExactWarnBox');
    const qrisTimerCountdown = document.getElementById('qrisTimerCountdown');
    const qrisCancelOrderBtn = document.getElementById('qrisCancelOrderBtn');

    const qrisSuccessOrderId = document.getElementById('qrisSuccessOrderId');
    const qrisCredentialsText = document.getElementById('qrisCredentialsText');
    const qrisOpenLinkBtn = document.getElementById('qrisOpenLinkBtn');
    const qrisOpenLinkBtnText = document.getElementById('qrisOpenLinkBtnText');
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

    // Custom Confirmation Dialog Elements
    const confirmDialog = document.getElementById('confirmDialog');
    const confirmDialogTile = document.getElementById('confirmDialogTile');
    const confirmDialogCircle = document.getElementById('confirmDialogCircle');
    const confirmDialogTitle = document.getElementById('confirmDialogTitle');
    const confirmDialogDesc = document.getElementById('confirmDialogDesc');
    const confirmDialogOkBtn = document.getElementById('confirmDialogOkBtn');
    const confirmDialogCancelBtn = document.getElementById('confirmDialogCancelBtn');

    let activeOrder = null;
    let pollInterval = null;
    let countdownInterval = null;

    function showToast(msg) {{
      toast.textContent = msg;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2400);
    }}

    // Custom In-App Confirmation Dialog (Replaces native browser confirm())
    function showCustomConfirm({{ title, message, okText, cancelText, iconSvg, icon, isDanger }}) {{
      return new Promise((resolve) => {{
        const chosenIcon = iconSvg || (typeof icon === 'string' && icon.startsWith('<svg') ? icon : null);
        if (isDanger) {{
          if (confirmDialogTile) confirmDialogTile.classList.add('danger');
          if (confirmDialogOkBtn) confirmDialogOkBtn.className = 'confirm-btn confirm-btn-danger';
          if (confirmDialogCircle) {{
            confirmDialogCircle.innerHTML = chosenIcon || `
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#ef4444" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                <line x1="10" y1="11" x2="10" y2="17"></line>
                <line x1="14" y1="11" x2="14" y2="17"></line>
              </svg>
            `;
          }}
        }} else {{
          if (confirmDialogTile) confirmDialogTile.classList.remove('danger');
          if (confirmDialogOkBtn) confirmDialogOkBtn.className = 'confirm-btn confirm-btn-primary';
          if (confirmDialogCircle) {{
            confirmDialogCircle.innerHTML = chosenIcon || `
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#0088cc" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
            `;
          }}
        }}

        const isEn = (currentLanguage === 'en');
        if (confirmDialogTitle) confirmDialogTitle.textContent = title || (isEn ? 'Confirmation' : 'Konfirmasi');
        if (confirmDialogDesc) confirmDialogDesc.textContent = message || '';
        if (confirmDialogOkBtn) confirmDialogOkBtn.textContent = okText || (isEn ? 'Confirm' : 'Ya, Lanjutkan');
        if (confirmDialogCancelBtn) confirmDialogCancelBtn.textContent = cancelText || (isEn ? 'Cancel' : 'Batal');

        confirmDialog.style.display = 'flex';
        void confirmDialog.offsetWidth;
        confirmDialog.classList.add('open');

        function cleanUp(result) {{
          confirmDialog.classList.remove('open');
          setTimeout(() => {{
            if (!confirmDialog.classList.contains('open')) {{
              confirmDialog.style.display = 'none';
            }}
          }}, 240);
          confirmDialogOkBtn.removeEventListener('click', onOk);
          confirmDialogCancelBtn.removeEventListener('click', onCancel);
          confirmDialog.removeEventListener('click', onBackdrop);
          resolve(result);
        }}

        function onOk(e) {{
          e.stopPropagation();
          cleanUp(true);
        }}
        function onCancel(e) {{
          e.stopPropagation();
          cleanUp(false);
        }}
        function onBackdrop(e) {{
          if (e.target === confirmDialog) {{
            cleanUp(false);
          }}
        }}

        confirmDialogOkBtn.addEventListener('click', onOk);
        confirmDialogCancelBtn.addEventListener('click', onCancel);
        confirmDialog.addEventListener('click', onBackdrop);
      }});
    }}

    // --- Order History LocalStorage Management ---
    function healStoredOrders() {{
      try {{
        let rawList = JSON.parse(localStorage.getItem('yowes_orders') || '[]');
        if (!Array.isArray(rawList)) return [];
        let updated = false;
        rawList.forEach(item => {{
          if (!item) return;
          // Auto-heal NaN in amount_formatted
          if (item.amount_formatted && item.amount_formatted.includes('NaN')) {{
            const raw = Number(item.amount_raw || item.total_amount || item.allocated_amount);
            if (!isNaN(raw) && raw > 0) {{
              item.amount_formatted = `Rp ${{raw.toLocaleString('id-ID')}}`;
              item.formatted_amount = item.amount_formatted;
              item.total_amount_formatted = item.amount_formatted;
              updated = true;
            }} else {{
              delete item.amount_formatted;
              delete item.formatted_amount;
              delete item.total_amount_formatted;
              updated = true;
            }}
          }}
        }});
        if (updated) {{
          localStorage.setItem('yowes_orders', JSON.stringify(rawList));
        }}
        return rawList;
      }} catch (e) {{
        return [];
      }}
    }}

    function getStoredOrders() {{
      return healStoredOrders();
    }}

    function saveOrderToHistory(order) {{
      if (!order || !order.token) return;
      try {{
        // Never allow NaN strings into saved orders
        if (order.amount_formatted && order.amount_formatted.includes('NaN')) {{
          delete order.amount_formatted;
          delete order.formatted_amount;
          delete order.total_amount_formatted;
        }}
        let list = getStoredOrders();
        const existingIdx = list.findIndex(item => item.token === order.token);
        if (existingIdx >= 0) {{
          list[existingIdx] = Object.assign(list[existingIdx], order);
        }} else {{
          list.unshift(order);
        }}
        localStorage.setItem('yowes_orders', JSON.stringify(list.slice(0, 20)));
        updatePendingBanner();
      }} catch (e) {{}}
    }}

    function updatePendingBanner() {{
      const list = getStoredOrders();
      const pending = list.find(item => {{
        if (item.status !== 'pending') return false;
        if (item.expires_at_ms) return (item.expires_at_ms > Date.now());
        if (item.expires_at_ts) return ((item.expires_at_ts * 1000) > Date.now());
        if (item.created_at_ms) return (Date.now() - item.created_at_ms) < 900000;
        if (item.created_at_ts) return (Math.floor(Date.now() / 1000) - item.created_at_ts) < 900;
        try {{
          const created = new Date(item.created_at || 0).getTime();
          if (!isNaN(created)) {{
            const diff = Date.now() - created;
            return diff >= 0 && diff < 900000;
          }}
        }} catch (e) {{}}
        return true;
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
      const isEn = (currentLanguage === 'en');
      const dict = I18N[currentLanguage] || I18N.id;
      const query = currentSearch.toLowerCase().trim();

      const filtered = PRODUCTS_DATA.filter(p => {{
        const prodName = isEn ? (p.name_en || p.name) : (p.name_id || p.name);
        const prodHighlight = isEn ? (p.highlight_en || p.highlight) : (p.highlight_id || p.highlight);

        let matchCat = (currentCategory === 'all');
        if (!matchCat) {{
          if (currentCategory === 'ai') matchCat = (p.category_id === 'AI Tools' || p.category_en === 'AI Tools' || p.category === 'AI Tools');
          else if (currentCategory === 'productivity') matchCat = (p.category_id === 'Produktivitas' || p.category_en === 'Productivity' || p.category === 'Produktivitas');
          else if (currentCategory === 'entertainment') matchCat = (p.category_id === 'Hiburan' || p.category_en === 'Entertainment' || p.category === 'Hiburan');
          else if (currentCategory === 'education') matchCat = (p.category_id === 'Edukasi' || p.category_en === 'Education' || p.category === 'Edukasi');
          else matchCat = (p.category === currentCategory || p.category_id === currentCategory || p.category_en === currentCategory);
        }}

        const matchSearch = (!query) || (prodName.toLowerCase().includes(query)) || (prodHighlight.toLowerCase().includes(query));
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

        const prodName = isEn ? (p.name_en || p.name) : (p.name_id || p.name);
        const prodCat = isEn ? (p.category_en || p.category) : (p.category_id || p.category);
        const prodHighlight = isEn ? (p.highlight_en || p.highlight) : (p.highlight_id || p.highlight);

        const priceDisplay = p.is_coin_price
          ? (isEn ? `${{p.coins || 3}} Coins` : (p.price_coins_formatted || `${{p.coins || 3}} Koin`))
          : ((currentCurrency === 'IDR') ? p.price_idr_formatted : `${{p.price_usdt}} USDT`);

        const stockClass = p.in_stock ? 'stock-ready' : 'stock-out';
        const stockText = p.in_stock ? dict.stockReady : dict.stockOut;

        card.innerHTML = `
          <div class="card-top">
            <div class="prod-icon-box" style="background: ${{p.gradient}}; --tile-shadow: ${{p.shadow}};">
              ${{p.icon_svg}}
            </div>
            <div class="prod-meta">
              <h2 class="prod-title">${{prodName}}</h2>
              <span class="prod-badge">${{prodCat}}</span>
            </div>
          </div>
          <p class="card-highlight">${{prodHighlight}}</p>
          <div class="card-footer">
            <div class="price-wrap">
              <span class="price-label">${{dict.cardPriceLabel}}</span>
              <span class="price-value">${{priceDisplay}}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="stock-tag ${{stockClass}}">
                <span class="stock-dot-pill"></span>
                <span>${{stockText}}</span>
              </span>
              <span class="card-btn">${{dict.cardOrderBtn}}</span>
            </div>
          </div>
        `;

        card.addEventListener('click', () => openModal(p));
        listEl.appendChild(card);
      }});
    }}

    function openModal(p) {{
      selectedProduct = p;
      const isEn = (currentLanguage === 'en');
      const dict = I18N[currentLanguage] || I18N.id;

      modalEmoji.style.background = p.gradient;
      modalEmoji.style.setProperty('--tile-shadow', p.shadow);
      modalEmoji.innerHTML = p.icon_svg;
      modalTitle.textContent = isEn ? (p.name_en || p.name) : (p.name_id || p.name);
      modalCategory.textContent = isEn ? (p.category_en || p.category) : (p.category_id || p.category);

      const priceDisplay = p.is_coin_price
        ? (isEn ? `${{p.coins || 3}} Coins` : (p.price_coins_formatted || `${{p.coins || 3}} Koin`))
        : ((currentCurrency === 'IDR') 
            ? p.price_idr_formatted 
            : `${{p.price_usdt}} USDT`);
      modalPrice.textContent = priceDisplay;

      const stockClass = p.in_stock ? 'stock-ready' : 'stock-out';
      const stockText = p.in_stock ? dict.modalStockReady : dict.modalStockOut;
      modalStockTag.innerHTML = `
        <span class="stock-tag ${{stockClass}}">
          <span class="stock-dot-pill"></span>
          <span>${{stockText}}</span>
        </span>
      `;

      const desc = isEn ? (p.description_en || p.description) : (p.description_id || p.description);
      modalDesc.textContent = desc || (isEn ? 'No specific instructions.' : 'Tidak ada petunjuk khusus.');
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
      const dict = I18N[currentLanguage] || I18N.id;
      const shareUrl = `${{window.location.origin}}?product=${{selectedProduct.key}}`;
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(shareUrl).then(() => {{
          showToast(dict.toastCopied);
        }});
      }} else {{
        showToast('Link: ' + shareUrl);
      }}
    }});

    // --- QRIS Direct Checkout Flow ---
    function openQrisCheckout(p) {{
      if (!p) return;
      closeModal();
      const isEn = (currentLanguage === 'en');

      qrisProdIcon.innerHTML = p.icon_svg;
      qrisProdIcon.style.background = p.gradient;
      qrisProdTitle.textContent = isEn ? (p.name_en || p.name) : (p.name_id || p.name);
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
      const isEn = (currentLanguage === 'en');
      const contactVal = qrisContactInput.value.trim();
      if (contactVal) {{
        localStorage.setItem('yowes_contact', contactVal);
      }}

      qrisConfirmPayBtn.disabled = true;
      const origHtml = qrisConfirmPayBtn.innerHTML;
      qrisConfirmPayBtn.innerHTML = `<span>${{isEn ? 'Generating Dynamic QRIS...' : 'Membuat QRIS Dinamis...'}}</span>`;

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
          showToast(result.message || result.error || (isEn ? 'Failed to create QRIS order.' : 'Gagal membuat pesanan QRIS.'));
          qrisConfirmPayBtn.disabled = false;
          qrisConfirmPayBtn.innerHTML = origHtml;
          return;
        }}

        activeOrder = result;
        showPayingView(result);

      }} catch (err) {{
        showToast(isEn ? 'Network connection lost. Please try again.' : 'Koneksi terputus. Silakan coba lagi.');
      }} finally {{
        qrisConfirmPayBtn.disabled = false;
        qrisConfirmPayBtn.innerHTML = origHtml;
      }}
    }}

    function showPayingView(order) {{
      qrisViewInit.style.display = 'none';
      qrisViewPaying.style.display = 'block';
      qrisViewSuccess.style.display = 'none';

      const isEn = (currentLanguage === 'en');
      const dict = I18N[currentLanguage] || I18N.id;
      const prodName = selectedProduct 
        ? (isEn ? (selectedProduct.name_en || selectedProduct.name) : (selectedProduct.name_id || selectedProduct.name))
        : (order.product_name || (isEn ? 'QRIS Payment' : 'Pembayaran QRIS'));

      qrisPayingProdTitle.textContent = prodName;
      qrisImgTag.src = order.qr_image_url || '';
      let fmtAmount = order.total_amount_formatted || order.formatted_amount || order.amount_formatted || order.amount;
      const rawAmt = Number(order.total_amount || order.allocated_amount || order.amount_raw || order.raw_amount);
      if (!fmtAmount || fmtAmount.includes('NaN')) {{
        if (!isNaN(rawAmt) && rawAmt > 0) {{
          fmtAmount = `Rp ${{rawAmt.toLocaleString('id-ID')}}`;
        }} else {{
          fmtAmount = 'Rp 0';
        }}
      }}

      qrisTotalAmountText.textContent = fmtAmount;
      qrisCopyAmountBtn.dataset.amount = (!isNaN(rawAmt) && rawAmt > 0) ? rawAmt : '';
      qrisPollStatusText.textContent = dict.qrisPollStatus;

      // Update exact amount warning notice card with localized prefix & suffix without doubling
      if (qrisExactWarnBox) {{
        qrisExactWarnBox.innerHTML = `${{dict.qrisExactWarnPrefix}} <b><span id="qrisExactWarn">${{fmtAmount}}</span></b> ${{dict.qrisExactWarnSuffix}}`;
      }} else if (qrisExactWarn) {{
        qrisExactWarn.textContent = fmtAmount;
      }}

      // Calculate remaining seconds and absolute expiration millisecond timestamp
      let remaining = 900;
      if (typeof order.expires_in_seconds === 'number' && order.expires_in_seconds >= 0) {{
        remaining = order.expires_in_seconds;
      }} else if (order.expires_at_ms && order.expires_at_ms > Date.now()) {{
        remaining = Math.round((order.expires_at_ms - Date.now()) / 1000);
      }} else if (order.expires_at_ts && (order.expires_at_ts * 1000) > Date.now()) {{
        remaining = Math.round(((order.expires_at_ts * 1000) - Date.now()) / 1000);
      }} else if (order.created_at_ms) {{
        const elapsed = Math.round((Date.now() - order.created_at_ms) / 1000);
        remaining = Math.max(0, 900 - elapsed);
      }} else if (order.created_at_ts) {{
        const elapsed = Math.round((Date.now() - (order.created_at_ts * 1000)) / 1000);
        remaining = Math.max(0, 900 - elapsed);
      }} else if (order.created_at) {{
        try {{
          const parsed = new Date(order.created_at).getTime();
          if (!isNaN(parsed)) {{
            const elapsed = Math.round((Date.now() - parsed) / 1000);
            if (elapsed >= 0 && elapsed <= 900) {{
              remaining = 900 - elapsed;
            }}
          }}
        }} catch (e) {{}}
      }}

      const expiresAtMs = Date.now() + (remaining * 1000);
      order.expires_at_ms = expiresAtMs;
      order.expires_in_seconds = remaining;
      order.created_at_ms = order.created_at_ms || Date.now();

      // Save to localStorage history with all fields harmonized
      saveOrderToHistory({{
        token: order.token || order.order_token,
        product_name: prodName,
        product_key: selectedProduct ? selectedProduct.key : (order.product_key || ''),
        amount_formatted: fmtAmount,
        formatted_amount: fmtAmount,
        total_amount_formatted: fmtAmount,
        amount_raw: (!isNaN(rawAmt) && rawAmt > 0) ? rawAmt : undefined,
        total_amount: (!isNaN(rawAmt) && rawAmt > 0) ? rawAmt : undefined,
        allocated_amount: (!isNaN(rawAmt) && rawAmt > 0) ? rawAmt : undefined,
        qr_image_url: order.qr_image_url || qrisImgTag.src,
        status: 'pending',
        created_at: order.created_at || new Date().toISOString(),
        created_at_ms: order.created_at_ms,
        expires_at_ms: expiresAtMs,
        expires_in_seconds: remaining
      }});

      qrisTimerCountdown.textContent = formatTime(remaining);
      stopCountdown();
      countdownInterval = setInterval(() => {{
        const secondsLeft = Math.max(0, Math.round((order.expires_at_ms - Date.now()) / 1000));
        if (secondsLeft <= 0) {{
          stopCountdown();
          stopPolling();
          qrisTimerCountdown.textContent = '00:00';
          qrisPollStatusText.textContent = isEn ? 'Payment time limit expired.' : 'Batas waktu pembayaran berakhir.';
          showToast(isEn ? 'QRIS payment session has expired.' : 'Waktu pembayaran QRIS telah habis.');
          saveOrderToHistory({{
            token: order.token || order.order_token,
            status: 'expired'
          }});
        }} else {{
          qrisTimerCountdown.textContent = formatTime(secondsLeft);
        }}
      }}, 1000);

      stopPolling();
      pollInterval = setInterval(pollOrderStatus, 3500);
      setTimeout(pollOrderStatus, 800);
    }}

    async function pollOrderStatus() {{
      const token = activeOrder ? (activeOrder.token || activeOrder.order_token) : null;
      if (!token) return;
      const isEn = (currentLanguage === 'en');
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
          showToast(isEn ? 'Order expired or cancelled.' : 'Pesanan telah kedaluwarsa atau dibatalkan.');
          closeQrisCheckout();
        }} else if (data.status === 'pending' && typeof data.expires_in_seconds === 'number' && activeOrder) {{
          const clientSecs = Math.max(0, Math.round((activeOrder.expires_at_ms - Date.now()) / 1000));
          if (Math.abs(clientSecs - data.expires_in_seconds) > 3) {{
            activeOrder.expires_at_ms = Date.now() + (data.expires_in_seconds * 1000);
            activeOrder.expires_in_seconds = data.expires_in_seconds;
          }}
        }}
      }} catch (e) {{}}
    }}

    function extractFirstUrl(text) {{
      if (!text || typeof text !== 'string') return null;
      let idx = text.indexOf('https://');
      if (idx === -1) idx = text.indexOf('http://');
      if (idx === -1) return null;
      const sub = text.slice(idx).trim();
      const punct = [')', '>', '<', '"', "'", '`'];
      let endIdx = sub.length;
      for (let i = 0; i < sub.length; i++) {{
        const code = sub.charCodeAt(i);
        if (code <= 32 || punct.indexOf(sub[i]) !== -1) {{
          endIdx = i;
          break;
        }}
      }}
      return sub.slice(0, endIdx);
    }}

    function isFileUrl(url) {{
      if (!url) return false;
      const clean = url.split('?')[0].toLowerCase();
      return clean.endsWith('.txt') || clean.endsWith('.pdf') || clean.endsWith('.zip') || clean.endsWith('.json') || clean.endsWith('.doc') || clean.endsWith('.docx');
    }}

    function showSuccessView(data) {{
      qrisViewInit.style.display = 'none';
      qrisViewPaying.style.display = 'none';
      qrisViewSuccess.style.display = 'block';

      const isEn = (currentLanguage === 'en');
      const token = activeOrder ? (activeOrder.token || activeOrder.order_token) : '';
      qrisSuccessOrderId.textContent = `Order #${{data.order_id || (token ? token.slice(0, 8) : '0')}}`;
      const creds = data.delivered_data || (isEn ? 'Order successfully verified. Thank you!' : 'Pesanan berhasil diverifikasi. Terima kasih!');
      qrisCredentialsText.textContent = creds;

      // Link / URL detection and dedicated Open Link button
      const linkUrl = extractFirstUrl(creds);
      if (linkUrl && qrisOpenLinkBtn) {{
        qrisOpenLinkBtn.href = linkUrl;
        qrisOpenLinkBtn.style.display = 'flex';
        const isFile = isFileUrl(linkUrl);
        if (qrisOpenLinkBtnText) {{
          qrisOpenLinkBtnText.textContent = isFile 
            ? (isEn ? '📥 Download Product File ➜' : '📥 Unduh File Produk ➜')
            : (isEn ? '🔗 Open Activation Link ➜' : '🔗 Buka Link / Tautan Akses ➜');
        }}
      }} else if (qrisOpenLinkBtn) {{
        qrisOpenLinkBtn.style.display = 'none';
      }}

      saveOrderToHistory({{
        token: token,
        status: 'approved',
        delivered_data: data.delivered_data,
        order_id: data.order_id,
        amount_formatted: data.amount || (activeOrder ? activeOrder.amount_formatted : undefined),
        amount_raw: data.raw_amount || (activeOrder ? activeOrder.amount_raw : undefined),
        completed_at: new Date().toISOString()
      }});

      showToast(isEn ? '🎉 Payment successfully received!' : '🎉 Pembayaran berhasil diterima!');
    }}

    async function cancelCurrentOrder() {{
      const token = activeOrder ? (activeOrder.token || activeOrder.order_token) : null;
      if (!token) {{
        closeQrisCheckout();
        return;
      }}

      const isEn = (currentLanguage === 'en');
      const dict = I18N[currentLanguage] || I18N.id;

      const confirmed = await showCustomConfirm({{
        title: isEn ? 'Cancel Payment Order?' : 'Batalkan Pesanan Pembayaran?',
        message: isEn 
          ? 'Are you sure you want to cancel this order? The dynamic QRIS code will be deactivated.'
          : 'Yakin ingin membatalkan pesanan pembayaran ini? Kode QRIS ini akan dinonaktifkan.',
        okText: isEn ? 'Yes, Cancel' : 'Ya, Batalkan',
        cancelText: isEn ? 'No, Keep' : 'Tidak',
        icon: '🗑️',
        isDanger: true
      }});

      if (!confirmed) return;

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
      showToast(dict.toastOrderCancelled);
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
      const isEn = (currentLanguage === 'en');
      const dict = I18N[currentLanguage] || I18N.id;
      const list = getStoredOrders();

      if (!list || list.length === 0) {{
        historyListContainer.innerHTML = `
          <div style="text-align: center; padding: 28px 16px; color: var(--text-muted); font-size: 13px;">
            <div style="font-size: 28px; margin-bottom: 8px;">📭</div>
            ${{dict.historyEmpty}}
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
        const isExpired = (item.status === 'expired' || item.status === 'cancelled');
        let badgeClass = 'history-badge-pending';
        let badgeText = dict.historyBadgePending;
        if (isApproved) {{
          badgeClass = 'history-badge-approved';
          badgeText = dict.historyBadgeApproved;
        }} else if (isExpired) {{
          badgeClass = 'history-badge-expired';
          badgeText = (item.status === 'cancelled') 
            ? (isEn ? 'Cancelled' : 'Dibatalkan')
            : (dict.historyBadgeExpired || (isEn ? 'Expired' : 'Kedaluwarsa'));
        }}

        const localeStr = isEn ? 'en-US' : 'id-ID';
        let dateStr = '-';
        if (item.created_at_ms) {{
          dateStr = new Date(item.created_at_ms).toLocaleString(localeStr, {{ dateStyle: 'medium', timeStyle: 'short' }});
        }} else if (item.created_at_ts) {{
          dateStr = new Date(item.created_at_ts * 1000).toLocaleString(localeStr, {{ dateStyle: 'medium', timeStyle: 'short' }});
        }} else if (item.created_at) {{
          try {{
            dateStr = new Date(item.created_at).toLocaleString(localeStr, {{ dateStyle: 'medium', timeStyle: 'short' }});
          }} catch (e) {{
            dateStr = '-';
          }}
        }}

        let displayAmount = item.amount_formatted || item.formatted_amount || item.amount;
        if (!displayAmount || displayAmount.includes('NaN')) {{
          const raw = Number(item.amount_raw || item.total_amount || item.allocated_amount);
          if (!isNaN(raw) && raw > 0) {{
            displayAmount = `Rp ${{raw.toLocaleString('id-ID')}}`;
            item.amount_formatted = displayAmount;
          }} else {{
            displayAmount = '';
          }}
        }}

        // Trigger background sync for items missing price or pending or recent expired (auto-heal) or approved without delivered_data
        const isRecent = item.created_at_ms ? (Date.now() - item.created_at_ms < 1000 * 900) : true;
        if (item.token && ((!displayAmount) || isPending || (isExpired && isRecent) || (isApproved && !item.delivered_data))) {{
          fetch(`/api/order/status?token=${{encodeURIComponent(item.token)}}`)
            .then(res => res.json())
            .then(fresh => {{
              if (fresh && fresh.ok) {{
                let updated = false;
                if (fresh.amount && (!item.amount_formatted || item.amount_formatted.includes('NaN'))) {{
                  item.amount_formatted = fresh.amount;
                  item.formatted_amount = fresh.amount;
                  item.total_amount_formatted = fresh.amount;
                  item.amount_raw = fresh.raw_amount;
                  updated = true;
                }}
                if (fresh.status && fresh.status !== item.status) {{
                  item.status = fresh.status;
                  updated = true;
                }}
                if (typeof fresh.expires_in_seconds === 'number') {{
                  item.expires_in_seconds = fresh.expires_in_seconds;
                  item.expires_at_ms = Date.now() + (fresh.expires_in_seconds * 1000);
                  updated = true;
                }}
                if (fresh.delivered_data && !item.delivered_data) {{
                  item.delivered_data = fresh.delivered_data;
                  item.order_id = fresh.order_id;
                  updated = true;
                }}
                if (updated) {{
                  saveOrderToHistory(item);
                  if (historyModal.classList.contains('open')) {{
                    renderHistoryModal();
                  }}
                }}
              }}
            }}).catch(() => {{}});
        }}

        let actionBtns = '';
        if (isApproved) {{
          const linkUrl = extractFirstUrl(item.delivered_data);
          const directLinkBtn = linkUrl ? `
            <a href="${{linkUrl}}" target="_blank" rel="noopener noreferrer" class="history-btn-sm" style="color: #38bdf8; border-color: rgba(56, 189, 248, 0.4); text-decoration: none;">
              <span>🔗 Buka Link</span>
            </a>
          ` : '';

          actionBtns = `
            <button class="history-btn-sm" onclick="viewHistoryCredentials('${{item.token}}')">
              <span>${{dict.historyBtnView}}</span>
            </button>
            ${{directLinkBtn}}
            <button class="history-btn-sm" onclick="downloadHistoryTxt('${{item.token}}')">
              <span>${{dict.historyBtnDownload}}</span>
            </button>
          `;
        }} else if (isPending) {{
          actionBtns = `
            <button class="history-btn-sm history-btn-resume" onclick="resumePendingOrderFromToken('${{item.token}}')">
              <span>${{dict.historyBtnResume}}</span>
            </button>
          `;
        }}

        card.innerHTML = `
          <div class="history-card-top">
            <div>
              <div style="font-size: 13.5px; font-weight: 700; color: #fff;">${{item.product_name || (isEn ? 'Digital Product' : 'Produk Digital')}}</div>
              <div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">${{dateStr}} • ${{displayAmount}}</div>
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

    window.viewHistoryCredentials = async function(token) {{
      const isEn = (currentLanguage === 'en');
      let list = getStoredOrders();
      let found = list.find(it => it.token === token);
      if (!found || !found.delivered_data) {{
        showToast(isEn ? '⏳ Retrieving credentials from server...' : '⏳ Mengambil kredensial dari server...');
        try {{
          const resp = await fetch(`/api/order/status?token=${{encodeURIComponent(token)}}`);
          if (resp.ok) {{
            const data = await resp.json();
            if (data.status === 'approved' && data.delivered_data) {{
              saveOrderToHistory({{
                token: token,
                status: 'approved',
                delivered_data: data.delivered_data,
                order_id: data.order_id,
                amount_formatted: data.amount,
                amount_raw: data.raw_amount
              }});
              list = getStoredOrders();
              found = list.find(it => it.token === token);
            }}
          }}
        }} catch (e) {{}}
      }}

      if (!found || !found.delivered_data) {{
        showToast(isEn ? 'Credentials are not available yet. Please contact support.' : 'Kredensial belum tersedia. Silakan hubungi CS jika butuh bantuan.');
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

    window.downloadHistoryTxt = async function(token) {{
      const dict = I18N[currentLanguage] || I18N.id;
      let list = getStoredOrders();
      let found = list.find(it => it.token === token);
      if (!found || !found.delivered_data) {{
        try {{
          const resp = await fetch(`/api/order/status?token=${{encodeURIComponent(token)}}`);
          if (resp.ok) {{
            const data = await resp.json();
            if (data.delivered_data) {{
              saveOrderToHistory({{
                token: token,
                delivered_data: data.delivered_data,
                order_id: data.order_id
              }});
              list = getStoredOrders();
              found = list.find(it => it.token === token);
            }}
          }}
        }} catch (e) {{}}
      }}
      if (!found || !found.delivered_data) {{
        showToast(dict.historyEmpty || 'Kredensial belum tersedia.');
        return;
      }}
      const blob = new Blob([found.delivered_data], {{ type: 'text/plain;charset=utf-8' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const pKey = (found.product_key || (selectedProduct ? selectedProduct.key : 'pesanan'));
      a.download = `lisensi_${{pKey}}_${{Date.now()}}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast(dict.toastTxtDownloaded);
    }};

    window.resumePendingOrderFromToken = function(token) {{
      const list = getStoredOrders();
      const found = list.find(it => it.token === token);
      if (found) {{
        closeHistoryModal();
        resumePendingOrder(found);
      }}
    }};

    async function resumePendingOrder(order) {{
      if (!order) return;
      activeOrder = order;

      // 1. Calculate remaining seconds smoothly from epoch timestamps (no arbitrary 10s clamp!)
      let remaining = 900;
      if (order.expires_at_ms && order.expires_at_ms > Date.now()) {{
        remaining = Math.round((order.expires_at_ms - Date.now()) / 1000);
      }} else if (order.expires_at_ts && (order.expires_at_ts * 1000) > Date.now()) {{
        remaining = Math.round(((order.expires_at_ts * 1000) - Date.now()) / 1000);
      }} else if (order.created_at_ms) {{
        const elapsed = Math.round((Date.now() - order.created_at_ms) / 1000);
        remaining = Math.max(0, 900 - elapsed);
      }} else if (order.created_at_ts) {{
        const elapsed = Math.round((Date.now() - (order.created_at_ts * 1000)) / 1000);
        remaining = Math.max(0, 900 - elapsed);
      }} else if (typeof order.expires_in_seconds === 'number' && order.expires_in_seconds > 0) {{
        remaining = order.expires_in_seconds;
      }} else if (order.created_at) {{
        try {{
          const parsed = new Date(order.created_at).getTime();
          if (!isNaN(parsed)) {{
            const diff = Math.round((Date.now() - parsed) / 1000);
            if (diff >= 0 && diff <= 900) {{
              remaining = 900 - diff;
            }}
          }}
        }} catch (e) {{}}
      }}

      order.expires_in_seconds = remaining;
      order.expires_at_ms = Date.now() + (remaining * 1000);

      // 2. Open paying view immediately so user sees instant responsiveness
      showPayingView(order);
      qrisCheckoutModal.classList.add('open');

      // 3. Immediately query authoritative server status in background to synchronize remaining time and payment state
      const token = order.token || order.order_token;
      if (token) {{
        try {{
          const resp = await fetch(`/api/order/status?token=${{encodeURIComponent(token)}}`);
          if (resp.ok) {{
            const data = await resp.json();
            if (data.status === 'approved') {{
              stopPolling();
              stopCountdown();
              showSuccessView(data);
              return;
            }}
            if (data.status === 'expired' || data.status === 'cancelled') {{
              stopPolling();
              stopCountdown();
              qrisTimerCountdown.textContent = '00:00';
              saveOrderToHistory({{ token: token, status: data.status }});
              const isEn = (currentLanguage === 'en');
              const dict = I18N[currentLanguage] || I18N.id;
              showToast(isEn ? 'Order session has expired.' : 'Batas waktu pesanan telah habis.');
              closeQrisCheckout();
              return;
            }}
            if (data.status === 'pending') {{
              let updated = false;
              if (typeof data.expires_in_seconds === 'number') {{
                order.expires_in_seconds = data.expires_in_seconds;
                order.expires_at_ms = Date.now() + (data.expires_in_seconds * 1000);
                showPayingView(order);
                updated = true;
              }}
              if (data.amount && (!order.amount_formatted || order.amount_formatted.includes('NaN'))) {{
                order.amount_formatted = data.amount;
                order.formatted_amount = data.amount;
                order.total_amount_formatted = data.amount;
                updated = true;
              }}
              if (data.raw_amount) {{
                order.amount_raw = data.raw_amount;
                order.total_amount = data.raw_amount;
                order.allocated_amount = data.raw_amount;
                updated = true;
              }}
              if (data.qr_image_url && !order.qr_image_url) {{
                order.qr_image_url = data.qr_image_url;
                updated = true;
              }}
              if (updated) {{
                saveOrderToHistory(order);
              }}
            }}
          }}
        }} catch (e) {{}}
      }}
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
      const isEn = (currentLanguage === 'en');
      const dict = I18N[currentLanguage] || I18N.id;
      const originalText = qrisDownloadQrBtn.innerHTML;
      qrisDownloadQrBtn.innerHTML = `<span>${{isEn ? '⏳ Processing QR Image...' : '⏳ Memproses Gambar QR...'}}</span>`;

      try {{
        const response = await fetch(qrSrc);
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);

        if (navigator.share && navigator.canShare) {{
          try {{
            const file = new File([blob], 'qris_yowes_digital.png', {{ type: 'image/png' }});
            if (navigator.canShare({{ files: [file] }})) {{
              await navigator.share({{
                title: isEn ? 'QRIS Payment Yowes Digital' : 'QRIS Pembayaran Yowes Digital',
                text: `${{isEn ? 'QRIS Payment for' : 'QRIS Pembayaran'}} ${{selectedProduct ? selectedProduct.name : ''}}`,
                files: [file]
              }});
              showToast(isEn ? 'QR Image shared / saved!' : 'Gambar QR berhasil dibagikan / disimpan!');
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
        showToast(dict.toastQrDownloaded);
      }} catch (e) {{
        window.open(qrSrc, '_blank');
        showToast(isEn ? 'QR opened in new tab. Long press to save image.' : 'Gambar QR dibuka di tab baru. Tekan lama gambar untuk simpan ke galeri.');
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

    // Custom In-App Modal confirmation on payment close button
    qrisClosePayingBtn.addEventListener('click', async () => {{
      const isEn = (currentLanguage === 'en');
      const confirmed = await showCustomConfirm({{
        title: isEn ? 'Close Payment View?' : 'Tutup Tampilan Pembayaran?',
        message: isEn 
          ? 'Your QRIS mutation check will keep running in the background. You can check the status and retrieve your credentials anytime in the Order History menu.'
          : 'Verifikasi mutasi QRIS Anda tetap berjalan otomatis dan status pesanan beserta lisensi dapat dicek kapan saja di menu Riwayat.',
        okText: isEn ? 'Close View' : 'Tutup Tampilan',
        cancelText: isEn ? 'Stay Here' : 'Tetap di Sini',
        icon: '🕒',
        isDanger: false
      }});
      if (confirmed) {{
        closeQrisCheckout();
      }}
    }});

    qrisCancelOrderBtn.addEventListener('click', cancelCurrentOrder);

    qrisCopyAmountBtn.addEventListener('click', () => {{
      const amt = qrisCopyAmountBtn.dataset.amount;
      if (!amt) return;
      const dict = I18N[currentLanguage] || I18N.id;
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(amt).then(() => {{
          showToast(`Nominal Rp ${{Number(amt).toLocaleString('id-ID')}} ${{dict.toastNominalCopied}}`);
        }});
      }} else {{
        showToast(`Nominal: Rp ${{amt}}`);
      }}
    }});

    qrisCopyCredsBtn.addEventListener('click', () => {{
      const text = qrisCredentialsText.textContent;
      if (!text) return;
      const dict = I18N[currentLanguage] || I18N.id;
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(text).then(() => {{
          showToast(dict.toastCredsCopied);
        }});
      }} else {{
        showToast(dict.toastCredsCopied);
      }}
    }});

    qrisDownloadTxtBtn.addEventListener('click', () => {{
      const text = qrisCredentialsText.textContent;
      if (!text) return;
      const dict = I18N[currentLanguage] || I18N.id;
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
      showToast(dict.toastTxtDownloaded);
    }});

    qrisFinishBtn.addEventListener('click', () => {{
      closeQrisCheckout();
      selectedProduct = null;
    }});

    // Custom In-App Modal confirmation on backdrop click during payment
    qrisCheckoutModal.addEventListener('click', async (e) => {{
      if (e.target === qrisCheckoutModal) {{
        if (qrisViewPaying.style.display === 'block') {{
          const isEn = (currentLanguage === 'en');
          const confirmed = await showCustomConfirm({{
            title: isEn ? 'Close Payment View?' : 'Tutup Tampilan Pembayaran?',
            message: isEn 
              ? 'Your QRIS mutation check will keep running in the background. You can check the status and retrieve your credentials anytime in the Order History menu.'
              : 'Verifikasi mutasi QRIS Anda tetap berjalan otomatis dan status pesanan beserta lisensi dapat dicek kapan saja di menu Riwayat.',
            okText: isEn ? 'Close View' : 'Tutup Tampilan',
            cancelText: isEn ? 'Stay Here' : 'Tetap di Sini',
            icon: '🕒',
            isDanger: false
          }});
          if (confirmed) {{
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

    // Language switch function
    function applyLanguage(lang) {{
      currentLanguage = lang;
      const dict = I18N[lang] || I18N.id;

      // Header & Links
      const storeTaglineEl = document.getElementById('storeTagline');
      if (storeTaglineEl) storeTaglineEl.textContent = dict.tagline;

      const headerStatusEl = document.getElementById('headerStatusText');
      if (headerStatusEl) headerStatusEl.textContent = dict.headerStatus;

      const btnTelegramText = document.getElementById('btnTelegramText');
      if (btnTelegramText) btnTelegramText.textContent = dict.btnTelegram;

      const btnSupportText = document.getElementById('btnSupportText');
      if (btnSupportText) btnSupportText.textContent = dict.btnSupport;

      const btnChannelText = document.getElementById('btnChannelText');
      if (btnChannelText) btnChannelText.textContent = dict.btnChannel;

      // Trust Bar
      const trust1Title = document.getElementById('trust1Title');
      if (trust1Title) trust1Title.textContent = dict.trust1Title;
      const trust1Desc = document.getElementById('trust1Desc');
      if (trust1Desc) trust1Desc.textContent = dict.trust1Desc;

      const trust2Title = document.getElementById('trust2Title');
      if (trust2Title) trust2Title.textContent = dict.trust2Title;
      const trust2Desc = document.getElementById('trust2Desc');
      if (trust2Desc) trust2Desc.textContent = dict.trust2Desc;

      const trust3Title = document.getElementById('trust3Title');
      if (trust3Title) trust3Title.textContent = dict.trust3Title;
      const trust3Desc = document.getElementById('trust3Desc');
      if (trust3Desc) trust3Desc.textContent = dict.trust3Desc;

      // History Action Button
      const btnOrderHistoryText = document.getElementById('btnOrderHistoryText');
      if (btnOrderHistoryText) btnOrderHistoryText.textContent = dict.btnOrderHistory;

      // Search Box Placeholder
      if (searchInput) searchInput.placeholder = dict.searchPlaceholder;

      // Category Chips
      const chipAll = document.getElementById('catChipAll');
      if (chipAll) chipAll.textContent = dict.catAll;
      const chipAi = document.getElementById('catChipAi');
      if (chipAi) chipAi.textContent = dict.catAi;
      const chipProd = document.getElementById('catChipProductivity');
      if (chipProd) chipProd.textContent = dict.catProductivity;
      const chipEnt = document.getElementById('catChipEntertainment');
      if (chipEnt) chipEnt.textContent = dict.catEntertainment;
      const chipEdu = document.getElementById('catChipEducation');
      if (chipEdu) chipEdu.textContent = dict.catEducation;

      // Recovery Banner
      const bannerPendingTitle = document.getElementById('bannerPendingTitle');
      if (bannerPendingTitle) bannerPendingTitle.textContent = dict.bannerPending;
      const bannerPendingAction = document.getElementById('bannerPendingAction');
      if (bannerPendingAction) bannerPendingAction.textContent = dict.bannerAction;

      // Empty State
      if (emptyEl) emptyEl.textContent = dict.emptyState;

      // FAQ Section
      const faqTitle = document.getElementById('faqTitle');
      if (faqTitle) faqTitle.textContent = dict.faqTitle;
      const faqQ1 = document.getElementById('faqQ1');
      if (faqQ1) faqQ1.textContent = dict.faqQ1;
      const faqA1 = document.getElementById('faqA1');
      if (faqA1) faqA1.innerHTML = dict.faqA1;
      const faqQ2 = document.getElementById('faqQ2');
      if (faqQ2) faqQ2.textContent = dict.faqQ2;
      const faqA2 = document.getElementById('faqA2');
      if (faqA2) faqA2.innerHTML = dict.faqA2;
      const faqQ3 = document.getElementById('faqQ3');
      if (faqQ3) faqQ3.textContent = dict.faqQ3;
      const faqA3 = document.getElementById('faqA3');
      if (faqA3) faqA3.innerHTML = dict.faqA3;

      // Footer
      const footerRights = document.getElementById('footerRights');
      if (footerRights) footerRights.textContent = dict.footerRights;

      // Product Drawer Modal labels & buttons
      const modalPriceLabel = document.getElementById('modalPriceLabel');
      if (modalPriceLabel) modalPriceLabel.textContent = dict.modalPriceLabel;
      const modalDescLabel = document.getElementById('modalDescLabel');
      if (modalDescLabel) modalDescLabel.textContent = dict.modalDescLabel;
      const modalQrisPayText = document.getElementById('modalQrisPayText');
      if (modalQrisPayText) modalQrisPayText.textContent = dict.modalQrisBtn;
      const modalBuyLinkText = document.getElementById('modalBuyLinkText');
      if (modalBuyLinkText) modalBuyLinkText.textContent = dict.modalBuyLink;
      const modalCopyBtnText = document.getElementById('modalCopyBtnText');
      if (modalCopyBtnText) modalCopyBtnText.textContent = dict.modalCopyBtn;
      const modalSupportBtnText = document.getElementById('modalSupportBtnText');
      if (modalSupportBtnText) modalSupportBtnText.textContent = dict.modalSupportBtn;

      // QRIS Checkout Modal labels & buttons
      const qrisNoticeTitle = document.getElementById('qrisNoticeTitle');
      if (qrisNoticeTitle) qrisNoticeTitle.textContent = dict.qrisNoticeTitle;
      const qrisNoticeDesc = document.getElementById('qrisNoticeDesc');
      if (qrisNoticeDesc) qrisNoticeDesc.textContent = dict.qrisNoticeDesc;
      const qrisContactLabel = document.getElementById('qrisContactLabel');
      if (qrisContactLabel) qrisContactLabel.textContent = dict.qrisContactLabel;
      if (qrisContactInput) qrisContactInput.placeholder = dict.qrisContactPlaceholder;
      const qrisContactHelp = document.getElementById('qrisContactHelp');
      if (qrisContactHelp) qrisContactHelp.textContent = dict.qrisContactHelp;
      const qrisConfirmPayBtnText = document.getElementById('qrisConfirmPayBtnText');
      if (qrisConfirmPayBtnText) qrisConfirmPayBtnText.textContent = dict.qrisConfirmPayBtn;
      const qrisCancelInitBtnText = document.getElementById('qrisCancelInitBtnText');
      if (qrisCancelInitBtnText) qrisCancelInitBtnText.textContent = dict.qrisCancelInitBtn;

      const qrisPayingTitle = document.getElementById('qrisPayingProdTitle');
      if (qrisPayingTitle) qrisPayingTitle.textContent = dict.qrisPayingTitle;
      const qrisScanGuide = document.getElementById('qrisScanGuide');
      if (qrisScanGuide) qrisScanGuide.textContent = dict.qrisScanGuide;
      const qrisTotalAmountLabel = document.getElementById('qrisTotalAmountLabel');
      if (qrisTotalAmountLabel) qrisTotalAmountLabel.textContent = dict.qrisTotalAmountLabel;
      if (qrisCopyAmountBtn) qrisCopyAmountBtn.textContent = dict.qrisCopyBadge;
      if (qrisExactWarnBox) {{
        const curAmtSpan = document.getElementById('qrisExactWarn');
        const curAmt = curAmtSpan ? curAmtSpan.textContent : 'Rp 0';
        qrisExactWarnBox.innerHTML = `${{dict.qrisExactWarnPrefix}} <b><span id="qrisExactWarn">${{curAmt}}</span></b> ${{dict.qrisExactWarnSuffix}}`;
      }}
      const qrisTimerLabel = document.getElementById('qrisTimerLabel');
      if (qrisTimerLabel) qrisTimerLabel.textContent = dict.qrisTimerLabel;
      const qrisDownloadQrBtnText = document.getElementById('qrisDownloadQrBtnText');
      if (qrisDownloadQrBtnText) qrisDownloadQrBtnText.textContent = dict.qrisDownloadQrBtn;
      const qrisCancelOrderBtnText = document.getElementById('qrisCancelOrderBtnText');
      if (qrisCancelOrderBtnText) qrisCancelOrderBtnText.textContent = dict.qrisCancelOrderBtn;

      const qrisSuccessTitle = document.getElementById('qrisSuccessTitle');
      if (qrisSuccessTitle) qrisSuccessTitle.textContent = dict.qrisSuccessTitle;
      const qrisSuccessDesc = document.getElementById('qrisSuccessDesc');
      if (qrisSuccessDesc) qrisSuccessDesc.textContent = dict.qrisSuccessDesc;
      const qrisCredsLabel = document.getElementById('qrisCredsLabel');
      if (qrisCredsLabel) qrisCredsLabel.textContent = dict.qrisCredsLabel;
      if (qrisOpenLinkBtnText) qrisOpenLinkBtnText.textContent = dict.qrisOpenLinkBtn;
      const qrisCopyCredsBtnText = document.getElementById('qrisCopyCredsBtnText');
      if (qrisCopyCredsBtnText) qrisCopyCredsBtnText.textContent = dict.qrisCopyCredsBtn;
      const qrisDownloadTxtBtnText = document.getElementById('qrisDownloadTxtBtnText');
      if (qrisDownloadTxtBtnText) qrisDownloadTxtBtnText.textContent = dict.qrisDownloadTxtBtn;
      const qrisFinishBtnText = document.getElementById('qrisFinishBtnText');
      if (qrisFinishBtnText) qrisFinishBtnText.textContent = dict.qrisFinishBtn;

      // History Modal
      const historyModalTitle = document.getElementById('historyModalTitle');
      if (historyModalTitle) historyModalTitle.textContent = dict.historyTitle;
      const historyModalSubtitle = document.getElementById('historyModalSubtitle');
      if (historyModalSubtitle) historyModalSubtitle.textContent = dict.historySubtitle;
      const historyDoneBtnText = document.getElementById('historyDoneBtnText');
      if (historyDoneBtnText) historyDoneBtnText.textContent = dict.historyDoneBtn;

      // Re-render products list with localized cards
      renderProducts();

      // If product modal is open, re-render its details in selected language
      if (selectedProduct && modal.classList.contains('open')) {{
        openModal(selectedProduct);
      }}

      // If history modal is open, re-render history cards
      if (historyModal.classList.contains('open')) {{
        renderHistoryModal();
      }}
    }}

    // Currency Switcher: IDR = Indonesian, USDT = English
    currIdrBtn.addEventListener('click', () => {{
      if (currentCurrency === 'IDR' && currentLanguage === 'id') return;
      currentCurrency = 'IDR';
      currIdrBtn.classList.add('active');
      currUsdtBtn.classList.remove('active');
      applyLanguage('id');
    }});

    currUsdtBtn.addEventListener('click', () => {{
      if (currentCurrency === 'USDT' && currentLanguage === 'en') return;
      currentCurrency = 'USDT';
      currUsdtBtn.classList.add('active');
      currIdrBtn.classList.remove('active');
      applyLanguage('en');
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
            client = getattr(telegram_bot, "_shopeepay_client", None)
            if client and getattr(client, "is_session_expired", False):
                time.sleep(30)
                continue
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
