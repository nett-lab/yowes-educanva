import asyncio
import io
import json
from html import escape
import logging
import os
import random
import re
import secrets
import shlex
import sqlite3
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.error import RetryAfter, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from countries import get_country, list_countries
from mcp_server import generate_documents

BASE_DIR = Path(__file__).resolve().parent


def _load_env_file() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    try:
        with env_file.open("r", encoding="utf-8") as f:
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
OUTPUT_DIR = BASE_DIR / "output" / "telegram"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATA_DIR / "bot.sqlite3"
REQUIRED_CHANNEL = "@canvaproteam04"
REQUIRED_CHANNEL_URL = "https://t.me/canvaproteam04"
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@TeamPr0_07")
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/TeamPr0_07")
WEB_STORE_URL = os.getenv("WEB_STORE_URL", "https://idasyari.web.id").strip()
MEDIA_RETENTION_SECONDS = 10 * 60
MEDIA_CLEANUP_INTERVAL_SECONDS = 60
_media_cleanup_task: asyncio.Task | None = None
_prodseller_products_cache: tuple[float, list[dict]] = (0.0, [])

import qris_engine
import shopeepay_engine

_shopee_qris_raw = os.getenv("SHOPEE_MERCHANT_QRIS_RAW", "").strip()
_shopeepay_client = shopeepay_engine.ShopeePayClient()
_amount_allocator = shopeepay_engine.UniqueAmountAllocator()
_shopeepay_poller_task: asyncio.Task | None = None

COUNTRY_LABELS = {
    "uk": "🇬🇧 United Kingdom",
    "france": "🇫🇷 France",
    "netherlands": "🇳🇱 Netherlands",
    "indonesia": "🇮🇩 Indonesia",
    "australia": "🇦🇺 Australia",
    "canada": "🇨🇦 Canada",
    "spain": "🇪🇸 Spain",
    "argentina": "🇦🇷 Argentina",
    "slovakia": "🇸🇰 Slovakia",
    "mexico": "🇲🇽 Mexico",
    "philippines": "🇵🇭 Philippines",
    "thailand": "🇹🇭 Thailand",
    "us": "🇺🇸 United States",
}


def _delete_expired_media() -> int:
    cutoff = time.time() - MEDIA_RETENTION_SECONDS
    output_root = OUTPUT_DIR.resolve()
    removed = 0
    for path in OUTPUT_DIR.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        try:
            if not path.resolve().is_relative_to(output_root) or path.stat().st_mtime >= cutoff:
                continue
            path.unlink()
            removed += 1
        except (FileNotFoundError, PermissionError, OSError) as exc:
            logger.warning("Could not remove expired media %s: %s", path, exc)
    return removed


async def _media_cleanup_loop() -> None:
    while True:
        removed = await asyncio.to_thread(_delete_expired_media)
        if removed:
            logger.info("Removed %s expired Telegram media file(s)", removed)
        await asyncio.sleep(MEDIA_CLEANUP_INTERVAL_SECONDS)


async def _start_media_cleanup(application) -> None:
    global _media_cleanup_task, _shopeepay_poller_task
    _delete_expired_media()
    _media_cleanup_task = asyncio.create_task(_media_cleanup_loop())
    _shopeepay_poller_task = asyncio.create_task(_shopeepay_mutation_poller(application))
    if _prodseller_configured():
        asyncio.create_task(_prodseller_products(force_refresh=True))
    logger.info("Telegram API initialized; media cleanup, ShopeePay poller & ProdSeller prefetch are active")


async def _stop_media_cleanup(application) -> None:
    global _media_cleanup_task, _shopeepay_poller_task
    if _media_cleanup_task is not None:
        _media_cleanup_task.cancel()
        try:
            await _media_cleanup_task
        except asyncio.CancelledError:
            pass
        _media_cleanup_task = None

    if _shopeepay_poller_task is not None:
        _shopeepay_poller_task.cancel()
        try:
            await _shopeepay_poller_task
        except asyncio.CancelledError:
            pass
        _shopeepay_poller_task = None

(
    COUNTRY,
    DOC_TYPE,
    FIRST_NAME,
    LAST_NAME,
    GENDER,
    SCHOOL,
    POSITION,
    DOB,
    CONFIRM,
) = range(9)

REDEEM_CODE = 20
ADMIN_ADD_COINS = 21
ADMIN_SET_STOCK = 22
ADMIN_SET_INFO = 23
ADMIN_BROADCAST = 24

# Broadcast category icons & labels
# key: (emoji, indonesian_label, english_label)
_BROADCAST_TYPES: dict[str, tuple[str, str, str]] = {
    "flash":  ("⚡", "Flash Sale",      "Flash Sale"),
    "bonus":  ("🎁", "Bonus / Hadiah",  "Bonus / Gift"),
    "stock":  ("📦", "Update Stok",     "Stock Update"),
    "info":   ("📢", "Info Umum",       "General Info"),
    "promo":  ("🔥", "Promo Spesial",   "Special Promo"),
    "custom": ("✏️", "Pesan Kustom",    "Custom Message"),
}

_BROADCAST_TEMPLATES: dict[str, dict[str, str]] = {
    "flash": {
        "id": (
            "⚡ *FLASH SALE TERBATAS!* ⚡\n\n"
            "Dapatkan penawaran harga hemat spesial hari ini untuk semua akun premium & Canva Edu!\n\n"
            "🔥 *Slot & Kuota Sangat Terbatas!*\n"
            "Segera amankan pesanan Anda melalui menu utama sebelum promo berakhir."
        ),
        "en": (
            "⚡ *LIMITED FLASH SALE ALERT!* ⚡\n\n"
            "Special discounted prices available today for all premium accounts & Canva Edu!\n\n"
            "🔥 *Limited Slots Available!*\n"
            "Order now through the main menu before the flash deal ends."
        ),
    },
    "bonus": {
        "id": (
            "🎁 *KLAIM BONUS & HADIAH KOIN* 🎁\n\n"
            "Terima kasih telah setia menggunakan layanan kami!\n\n"
            "✨ *Cara Dapatkan Koin Gratis:*\n"
            "• Lakukan Daily Check-in setiap hari\n"
            "• Bagikan link referral Anda ke teman-teman\n\n"
            "Koin dapat langsung digunakan untuk pembuatan dokumen Canva Edu tanpa biaya!"
        ),
        "en": (
            "🎁 *CLAIM YOUR BONUS & REWARD COINS* 🎁\n\n"
            "Thank you for being our loyal member!\n\n"
            "✨ *How to Earn Free Coins:*\n"
            "• Claim your Daily Check-in bonus\n"
            "• Share your referral link with friends\n\n"
            "Use your coins to generate Canva Edu documents completely free!"
        ),
    },
    "stock": {
        "id": (
            "📦 *UPDATE STOK PRODUK TERSEDIA* 📦\n\n"
            "Kabar gembira! Stok akun digital & lisensi resmi telah di-restock:\n\n"
            "• 🎥 CapCut Pro\n"
            "• 🤖 Claude AI API\n"
            "• 💻 GPT Codex\n"
            "• 📺 Prime Video\n"
            "• 🎓 Gemini Pro\n\n"
            "🚀 *Proses Otomatis & Cepat*\n"
            "Pembayaran instan via QRIS & USDT BinancePay 24/7."
        ),
        "en": (
            "📦 *PRODUCT RESTOCK ANNOUNCEMENT* 📦\n\n"
            "Great news! Digital accounts & subscriptions are now fully restocked:\n\n"
            "• 🎥 CapCut Pro\n"
            "• 🤖 Claude AI API\n"
            "• 💻 GPT Codex\n"
            "• 📺 Prime Video\n"
            "• 🎓 Gemini Pro\n\n"
            "🚀 *Instant & Automated Delivery*\n"
            "Available 24/7 via QRIS & USDT BinancePay."
        ),
    },
    "info": {
        "id": (
            "📢 *INFORMASI & LAYANAN SISTEM* 📢\n\n"
            "Halo semuanya! Seluruh server dan layanan otomatisasi kami berjalan lancar & optimal.\n\n"
            "💡 *Kemudahan Transaksi:*\n"
            "• QRIS otomatis real-time\n"
            "• Binance Pay USDT aman tanpa potongan fee\n\n"
            "Silakan akses menu utama untuk bertransaksi. Hubungi admin bila membutuhkan bantuan."
        ),
        "en": (
            "📢 *SYSTEM INFORMATION & STATUS* 📢\n\n"
            "Hello everyone! All bot services and automated delivery systems are running smoothly.\n\n"
            "💡 *Smooth Transactions:*\n"
            "• Instant automated QRIS\n"
            "• Zero gas fee Binance Pay USDT\n\n"
            "Open the main menu to get started. Contact admin if you need any assistance."
        ),
    },
    "promo": {
        "id": (
            "🔥 *PROMO SPESIAL HARI INI* 🔥\n\n"
            "Upgrade kebutuhan digital, editing video, dan AI tools Anda dengan harga terbaik bergaransi!\n\n"
            "🎉 Akun legal, proses instan, dan siap pakai.\n"
            "Buka menu utama bot dan amankan produk favorit Anda sekarang."
        ),
        "en": (
            "🔥 *SPECIAL PROMOTION TODAY* 🔥\n\n"
            "Upgrade your creative workflow, video editing, and AI tools at special rates!\n\n"
            "🎉 Guaranteed quality and instant delivery.\n"
            "Open the main menu now to claim your favorite products."
        ),
    },
    "custom": {
        "id": (
            "🔔 *PEMBERITAHUAN TERBARU*\n\n"
            "Halo sahabat! Ada pembaruan terbaru di bot kami. Silakan cek menu utama untuk melihat fitur dan produk yang tersedia."
        ),
        "en": (
            "🔔 *LATEST ANNOUNCEMENT*\n\n"
            "Hello everyone! We have updated our services. Please check the main menu for the latest features and available products."
        ),
    },
}

_GEMINI_DEFAULT_INFO_EN = (
    "🛍️ <b>Gemini Pro 18Months (link)</b>\n\n"
    "<i>important (click in the \"not working \" button if the link not work)</i>\n"
    "&gt; 18 Months Plan 🤖\n"
    "&gt;  5TB cloud storage included 🛴\n"
    "&gt; You can add 5 users ⚡️\n"
    "&gt; Not Shared ❌\n"
    "&gt; 100% Private 🔐\n"
    "&gt; NO NEED ANY CARD 💳\n"
    "&gt; 24 Hours Hold warranty ✔️\n"
    "&gt; Works in any country no verification 🛫\n\n"
    "-&gt; Full Family Account. It's Not an Invite ! ✅\n\n"
    "Paste the received redeem link into your browser and click on “Activate Offer”. Your subscription/offer will then be activated successfully !\n\n"
    "💵 Price: $0.90"
)

_GEMINI_DEFAULT_INFO_ID = (
    "🛍️ <b>Gemini Pro 18 Bulan (link)</b>\n\n"
    "<i>Penting (hubungi support jika link tidak berfungsi)</i>\n"
    "&gt; Paket 18 Bulan Aktif 🤖\n"
    "&gt;  Termasuk Cloud Storage 5TB 🛴\n"
    "&gt; Bisa tambah hingga 5 user anggota ⚡️\n"
    "&gt; Bukan Akun Bersama (Private) ❌\n"
    "&gt; 100% Pribadi & Aman 🔐\n"
    "&gt; Tanpa Perlu Kartu Kredit / Debit 💳\n"
    "&gt; Garansi 24 Jam Aktif ✔️\n"
    "&gt; Berlaku di semua negara tanpa verifikasi 🛫\n\n"
    "-&gt; Akun Full Family. Bukan Sistem Undangan Invite! ✅\n\n"
    "Buka link redeem/aktivasi yang diterima di browser dan klik “Activate Offer”. Langganan / paket Anda akan langsung aktif secara instan!\n\n"
    "💵 Harga: Rp20.000 / $0.90"
)

# ──────────────────────────────────────────────────────────────────────────────
# Product Catalog  — new products are added here; no other code needs changing
# Each entry carries all pricing defaults and env-var names for ProdSeller.
# ──────────────────────────────────────────────────────────────────────────────
_PRODUCT_CATALOG: dict[str, dict] = {
    "capcut": {
        "emoji": "🎥",
        "label_id": "CapCut Pro",
        "label_en": "CapCut Pro",
        "price_coins_key": "capcut_price",
        "price_idr_key": "capcut_price_idr",
        "price_qris_key": "capcut_qris_price_idr",
        "price_binance_key": "capcut_binance_price_usdt",
        "default_coins": 50,
        "default_idr": 30000,
        "default_qris_idr": 30000,
        "default_binance_usdt": "1.7",
        "prodseller_default_id": "6a2fda51035a6d898f2106fe",
        "prodseller_id_env": "PRODSELLER_CAPCUT_ID",
        "prodseller_name_env": "PRODSELLER_CAPCUT_NAME",
        "prodseller_default": "CapCut",
        "stock_key": "capcut_manual_stock",
        "info_key": "capcut_info",
        "default_info_id": "• Akun / Lisensi CapCut Pro Aktif\n• Tanpa watermark, ekspor hingga kualitas 4K\n• Akses semua template, font, musik & efek AI\n• Pengiriman cepat & garansi aktif",
        "default_info_en": "• Active CapCut Pro Account / License\n• Watermark-free, export up to 4K quality\n• Full access to templates, fonts, music & AI tools\n• Fast delivery & active warranty",
    },
    "claude": {
        "emoji": "🤖",
        "label_id": "Claude API",
        "label_en": "Claude API",
        "price_coins_key": "claude_price",
        "price_idr_key": "claude_price_idr",
        "price_qris_key": "claude_qris_price_idr",
        "price_binance_key": "claude_binance_price_usdt",
        "default_coins": 50,
        "default_idr": 100000,
        "default_qris_idr": 100000,
        "default_binance_usdt": "5.00",
        "prodseller_default_id": "6ac0e0ab5f3b1a835b386fe8",
        "prodseller_id_env": "PRODSELLER_CLAUDE_ID",
        "prodseller_name_env": "PRODSELLER_CLAUDE_NAME",
        "prodseller_default": "Claude",
        "stock_key": "claude_manual_stock",
        "info_key": "claude_info",
        "default_info_id": "• Akun / Langganan Claude API\n• Akses model canggih Claude 3.5 Sonnet / Opus\n• Kemampuan penalaran, coding & analisis dokumen tinggi\n• Limit pesan lebih besar & respon cepat",
        "default_info_en": "• Claude API Account / Subscription\n• Access to advanced Claude 3.5 Sonnet / Opus models\n• High reasoning, coding & document analysis capabilities\n• Higher message limits & fast response times",
    },
    "codex": {
        "emoji": "💻",
        "label_id": "API Codex 10M",
        "label_en": "API Codex 10M",
        "price_coins_key": "codex_price",
        "price_idr_key": "codex_price_idr",
        "price_qris_key": "codex_qris_price_idr",
        "price_binance_key": "codex_binance_price_usdt",
        "default_coins": 30,
        "default_idr": 20000,
        "default_qris_idr": 20000,
        "default_binance_usdt": "1.20",
        "markup_usdt": 0.5,
        "prodseller_default_id": "6ac0ea6d5f3b1a835b398396",
        "prodseller_id_env": "PRODSELLER_CODEX_ID",
        "prodseller_name_env": "PRODSELLER_CODEX_NAME",
        "prodseller_default": "API CODEX-10M Token-1Day",
        "stock_key": "codex_manual_stock",
        "info_key": "codex_info",
        "default_info_id": (
            "🗝️ API ChatGPT CODEX - 10M Token - 1 day\n"
            "🛡️ 100% Genuine Codex API (100% refund guaranteed if not authentic).\n"
            "⚡ Seamlessly compatible with all tools & IDEs: 9router, Codex, Cursor, VS Code, etc.\n"
            "⏳ Validity: 1 Day\n\n"
            "📋 Quick Setup Instructions:\n"
            "🔹 Step 1: Visit 👉 https://miraiapi.com/usage/#redeem to redeem your code (Enter the code provided in your order details).\n"
            "🔹 Step 2: Visit 👉 https://miraiapi.com/usage/#config to configure your API Key, select your target App, and choose the ideal Model.\n"
            "✨ All done & Ready to code!\n"
            "🤖 Available Models: gpt-6-astra, gpt-6-sol, gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol\n"
            "📊 Check quota balance & expiry date at: 🔗 https://miraiapi.com/usage/\n\n"
            "⚠️ Important Notice: The validity period only starts counting once the redeem code is activated."
        ),
        "default_info_en": (
            "🗝️ API ChatGPT CODEX - 10M Token - 1 day\n"
            "🛡️ 100% Genuine Codex API (100% refund guaranteed if not authentic).\n"
            "⚡ Seamlessly compatible with all tools & IDEs: 9router, Codex, Cursor, VS Code, etc.\n"
            "⏳ Validity: 1 Day\n\n"
            "📋 Quick Setup Instructions:\n"
            "🔹 Step 1: Visit 👉 https://miraiapi.com/usage/#redeem to redeem your code (Enter the code provided in your order details).\n"
            "🔹 Step 2: Visit 👉 https://miraiapi.com/usage/#config to configure your API Key, select your target App, and choose the ideal Model.\n"
            "✨ All done & Ready to code!\n"
            "🤖 Available Models: gpt-6-astra, gpt-6-sol, gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol\n"
            "📊 Check quota balance & expiry date at: 🔗 https://miraiapi.com/usage/\n\n"
            "⚠️ Important Notice: The validity period only starts counting once the redeem code is activated."
        ),
    },
    "spotify": {
        "emoji": "🎧",
        "label_id": "Spotify Premium 1M",
        "label_en": "Spotify Premium 1M",
        "price_coins_key": "spotify_price",
        "price_idr_key": "spotify_price_idr",
        "price_qris_key": "spotify_qris_price_idr",
        "price_binance_key": "spotify_binance_price_usdt",
        "default_coins": 35,
        "default_idr": 23000,
        "default_qris_idr": 23000,
        "default_binance_usdt": "1.43",
        "markup_usdt": 0.5,
        "prodseller_default_id": "6acfc869a8f487d336b13845",
        "prodseller_id_env": "PRODSELLER_SPOTIFY_ID",
        "prodseller_name_env": "PRODSELLER_SPOTIFY_NAME",
        "prodseller_default": "Spotify premium account1M FW",
        "stock_key": "spotify_manual_stock",
        "info_key": "spotify_info",
        "default_info_id": (
            "TERMS & CONDITIONS:\n\n"
            "✅ Free to change the password or not change it also doesn't matter, because only you can access the account.\n\n"
            "⌛️ Please be patient not to change the details of the name/profile photo in the FIRST 1 MONTH SINCE PURCHASE, so that the account remains durable or wait for 1 month.\n\n"
            "⚠️ PROHIBITED TO CHANGE EMAIL! Caught changing email = BURNT GUARANTEE + KICK FROM FAMILY\n\n"
            "TIPS:\nBefore logging in, it is recommended to Clear Data first for android users and Offload/reInstall for iOS users, to avoid incorrect password even though it is correct.\n\n"
            "REMINDER:\nIf the tips above have been tried but still incorrect, it means that there is a suspicious activity where the security system from Spotify automatically resets the password by itself."
        ),
        "default_info_en": (
            "TERMS & CONDITIONS:\n\n"
            "✅ Free to change the password or not change it also doesn't matter, because only you can access the account.\n\n"
            "⌛️ Please be patient not to change the details of the name/profile photo in the FIRST 1 MONTH SINCE PURCHASE, so that the account remains durable or wait for 1 month.\n\n"
            "⚠️ PROHIBITED TO CHANGE EMAIL! Caught changing email = BURNT GUARANTEE + KICK FROM FAMILY\n\n"
            "TIPS:\nBefore logging in, it is recommended to Clear Data first for android users and Offload/reInstall for iOS users, to avoid incorrect password even though it is correct.\n\n"
            "REMINDER:\nIf the tips above have been tried but still incorrect, it means that there is a suspicious activity where the security system from Spotify automatically resets the password by itself."
        ),
    },
    "scribd": {
        "emoji": "📚",
        "label_id": "Scribd Premium 1M",
        "label_en": "Scribd Premium 1M",
        "price_coins_key": "scribd_price",
        "price_idr_key": "scribd_price_idr",
        "price_qris_key": "scribd_qris_price_idr",
        "price_binance_key": "scribd_binance_price_usdt",
        "default_coins": 30,
        "default_idr": 20000,
        "default_qris_idr": 20000,
        "default_binance_usdt": "1.20",
        "markup_usdt": 0.5,
        "prodseller_default_id": "6ac88922cd35776c4d2cf283",
        "prodseller_id_env": "PRODSELLER_SCRIBD_ID",
        "prodseller_name_env": "PRODSELLER_SCRIBD_NAME",
        "prodseller_default": "SCRIBD PREMIUM 1M FW",
        "stock_key": "scribd_manual_stock",
        "info_key": "scribd_info",
        "default_info_id": (
            "FULL PRIVATE ACCOUNT\n\n"
            "FULL ACCESS TO OUTLOOK MAIL\n\n"
            "EMAIL/PASSWORD LOGIN\n\n"
            "PREMIUM MONTHLY PLAN"
        ),
        "default_info_en": (
            "FULL PRIVATE ACCOUNT\n\n"
            "FULL ACCESS TO OUTLOOK MAIL\n\n"
            "EMAIL/PASSWORD LOGIN\n\n"
            "PREMIUM MONTHLY PLAN"
        ),
    },
    "notion": {
        "emoji": "📝",
        "label_id": "Notion Plus 12M",
        "label_en": "Notion Plus 12M",
        "price_coins_key": "notion_price",
        "price_idr_key": "notion_price_idr",
        "price_qris_key": "notion_qris_price_idr",
        "price_binance_key": "notion_binance_price_usdt",
        "default_coins": 35,
        "default_idr": 23000,
        "default_qris_idr": 23000,
        "default_binance_usdt": "1.42",
        "markup_usdt": 0.5,
        "prodseller_default_id": "6a54b931351561c645a43e8c",
        "prodseller_id_env": "PRODSELLER_NOTION_ID",
        "prodseller_name_env": "PRODSELLER_NOTION_NAME",
        "prodseller_default": "Notion Plus 12M",
        "stock_key": "notion_manual_stock",
        "info_key": "notion_info",
        "default_info_id": (
            "✅ Account email:pass given\n"
            "✅ This is Notion Education Plus Account\n"
            "✅ Email change is allowed\n"
            "✅ 12 Month duration\n"
            "✅ Reset account security after login\n"
            "✅ To login go to outlook.com first then login there and login with same email:pass on notion too\n\n"
            "Format: Mail/Hotmail password/notion password"
        ),
        "default_info_en": (
            "✅ Account email:pass given\n"
            "✅ This is Notion Education Plus Account\n"
            "✅ Email change is allowed\n"
            "✅ 12 Month duration\n"
            "✅ Reset account security after login\n"
            "✅ To login go to outlook.com first then login there and login with same email:pass on notion too\n\n"
            "Format: Mail/Hotmail password/notion password"
        ),
    },
    "office365": {
        "emoji": "💼",
        "label_id": "Office 365 Plus 1Y",
        "label_en": "Office 365 Plus 1Y",
        "price_coins_key": "office365_price",
        "price_idr_key": "office365_price_idr",
        "price_qris_key": "office365_qris_price_idr",
        "price_binance_key": "office365_binance_price_usdt",
        "default_coins": 20,
        "default_idr": 12000,
        "default_qris_idr": 12000,
        "default_binance_usdt": "0.69",
        "markup_usdt": 0.5,
        "prodseller_default_id": "6a2fe23a1c8697b163aedcbd",
        "prodseller_id_env": "PRODSELLER_OFFICE365_ID",
        "prodseller_name_env": "PRODSELLER_OFFICE365_NAME",
        "prodseller_default": "Microsoft Office 365 Plus 1 year",
        "stock_key": "office365_manual_stock",
        "info_key": "office365_info",
        "default_info_id": (
            "Microsoft Office 365 Plus – 1 Month + 11 Months (GIFT) Subscription\n\n"
            "What's Included:\n"
            "• Microsoft Word\n"
            "• Microsoft Excel\n"
            "• Microsoft PowerPoint\n"
            "• Microsoft OneNote\n"
            "• Microsoft Forms\n"
            "• 1TB OneDrive Cloud Storage\n\n"
            "Product Details:\n"
            "• Subscription Duration: 1 Month (Guaranteed) + 11 Months (GIFT)\n"
            "• Supported Devices: Up to 5 Windows PCs\n"
            "• Delivery: Instant Digital Delivery after payment\n\n"
            "Account Delivery: Email : Password format"
        ),
        "default_info_en": (
            "Microsoft Office 365 Plus – 1 Month + 11 Months (GIFT) Subscription\n\n"
            "What's Included:\n"
            "• Microsoft Word\n"
            "• Microsoft Excel\n"
            "• Microsoft PowerPoint\n"
            "• Microsoft OneNote\n"
            "• Microsoft Forms\n"
            "• 1TB OneDrive Cloud Storage\n\n"
            "Product Details:\n"
            "• Subscription Duration: 1 Month (Guaranteed) + 11 Months (GIFT)\n"
            "• Supported Devices: Up to 5 Windows PCs\n"
            "• Delivery: Instant Digital Delivery after payment\n\n"
            "Account Delivery: Email : Password format"
        ),
    },
    "figma": {
        "emoji": "🎨",
        "label_id": "Figma Pro Edu 2Y",
        "label_en": "Figma Pro Edu 2Y",
        "price_coins_key": "figma_price",
        "price_idr_key": "figma_price_idr",
        "price_qris_key": "figma_qris_price_idr",
        "price_binance_key": "figma_binance_price_usdt",
        "default_coins": 100,
        "default_idr": 63000,
        "default_qris_idr": 63000,
        "default_binance_usdt": "3.90",
        "markup_usdt": 0.5,
        "prodseller_default_id": "6a7826d9cf6984bb8ba101e8",
        "prodseller_id_env": "PRODSELLER_FIGMA_ID",
        "prodseller_name_env": "PRODSELLER_FIGMA_NAME",
        "prodseller_default": "Figma Pro Edu 2yrs",
        "stock_key": "figma_manual_stock",
        "info_key": "figma_info",
        "default_info_id": (
            "Figma Pro Education Plan 2 year\n"
            "Very stable accounts, no issue since 6 months.\n"
            "Format: email | password | email token\n"
            "Token access OTP: https://hitools.pro/read-hotmail (figma and hotmail password same)\n"
            "🔥 The Make feature is now available in Opus 4.7\n"
            "🔥 Get 3,000 credits per month.\n"
            "Note: Never change email figma"
        ),
        "default_info_en": (
            "Figma Pro Education Plan 2 year\n"
            "Very stable accounts, no issue since 6 months.\n"
            "Format: email | password | email token\n"
            "Token access OTP: https://hitools.pro/read-hotmail (figma and hotmail password same)\n"
            "🔥 The Make feature is now available in Opus 4.7\n"
            "🔥 Get 3,000 credits per month.\n"
            "Note: Never change email figma"
        ),
    },
    "primevideo": {
        "emoji": "📺",
        "label_id": "Prime Video",
        "label_en": "Prime Video",
        "price_coins_key": "primevideo_price",
        "price_idr_key": "primevideo_price_idr",
        "price_qris_key": "primevideo_qris_price_idr",
        "price_binance_key": "primevideo_binance_price_usdt",
        "default_coins": 35,
        "default_idr": 35000,
        "default_qris_idr": 35000,
        "default_binance_usdt": "2.0",
        "prodseller_default_id": "6a3d636221735658e32bd2a6",
        "prodseller_id_env": "PRODSELLER_PRIMEVIDEO_ID",
        "prodseller_name_env": "PRODSELLER_PRIMEVIDEO_NAME",
        "prodseller_default": "Prime Video",
        "stock_key": "primevideo_manual_stock",
        "info_key": "primevideo_info",
        "default_info_id": "• Langganan Amazon Prime Video Premium\n• Streaming film & series eksklusif Amazon Originals\n• Kualitas video hingga 4K UHD & HDR\n• Support Smartphone, Tablet, PC & Smart TV",
        "default_info_en": "• Amazon Prime Video Premium Subscription\n• Stream exclusive movies & Amazon Originals\n• Video quality up to 4K UHD & HDR\n• Supports Smartphones, Tablets, PC & Smart TV",
    },
    "chatgpt_k12": {
        "emoji": "🧠",
        "label_id": "ChatGPT Plus K12 2Y",
        "label_en": "ChatGPT Plus K12 2Y",
        "price_coins_key": "chatgpt_k12_price",
        "price_idr_key": "chatgpt_k12_price_idr",
        "price_qris_key": "chatgpt_k12_qris_price_idr",
        "price_binance_key": "chatgpt_k12_binance_price_usdt",
        "default_coins": 90,
        "default_idr": 55000,
        "default_qris_idr": 55000,
        "default_binance_usdt": "3.40",
        "markup_usdt": 0.5,
        "prodseller_default_id": "6a495a5f02999800df961920",
        "prodseller_id_env": "PRODSELLER_CHATGPT_K12_ID",
        "prodseller_name_env": "PRODSELLER_CHATGPT_K12_NAME",
        "prodseller_default": "ChatGPT Plus K12 Edu 2 years",
        "stock_key": "chatgpt_k12_manual_stock",
        "info_key": "chatgpt_k12_info",
        "default_info_id": (
            "Features:\n"
            "- Unlimited messages with GPT-6 Astra\n"
            "- Work Feature available\n"
            "- Web Search & Deep Research\n"
            "- File uploads, File Search & connected apps\n"
            "- Voice Mode & Image Generation & Codex\n"
            "- Advanced Data Analysis & structured-data tools\n"
            "- Memory for personalized assistance\n"
            "- Custom GPTs & Shared Projects\n"
            "- Collaboration tools for teachers & schools\n"
            "- Education-grade privacy, security & compliance\n"
            "- SSO, RBAC, domain controls & admin analytics\n\n"
            "Delivery Format: 🚀\n"
            "Email | Pass | 2FA | MailBox Link | Guide on How to activate/join K12 workspace\n\n"
            "Get 2FA code: https://2fa.live/\n"
            "Plan duration: 2 years (Warranty: 24 Hours)\n\n"
            "⚠️ Note: Login to browser first before using it on the app."
        ),
        "default_info_en": (
            "Features:\n"
            "- Unlimited messages with GPT-6 Astra\n"
            "- Work Feature available\n"
            "- Web Search & Deep Research\n"
            "- File uploads, File Search & connected apps\n"
            "- Voice Mode & Image Generation & Codex\n"
            "- Advanced Data Analysis & structured-data tools\n"
            "- Memory for personalized assistance\n"
            "- Custom GPTs & Shared Projects\n"
            "- Collaboration tools for teachers & schools\n"
            "- Education-grade privacy, security & compliance\n"
            "- SSO, RBAC, domain controls & admin analytics\n\n"
            "Delivery Format: 🚀\n"
            "Email | Pass | 2FA | MailBox Link | Guide on How to activate/join K12 workspace\n\n"
            "Get 2FA code: https://2fa.live/\n"
            "Plan duration: 2 years (Warranty: 24 Hours)\n\n"
            "⚠️ Note: Login to browser first before using it on the app."
        ),
    },
    "ilovepdf": {
        "emoji": "📄",
        "label_id": "iLovePdf Premium 1Y",
        "label_en": "iLovePdf Premium 1Y",
        "price_coins_key": "ilovepdf_price",
        "price_idr_key": "ilovepdf_price_idr",
        "price_qris_key": "ilovepdf_qris_price_idr",
        "price_binance_key": "ilovepdf_binance_price_usdt",
        "default_coins": 25,
        "default_idr": 14000,
        "default_qris_idr": 14000,
        "default_binance_usdt": "0.85",
        "markup_usdt": 0.5,
        "prodseller_default_id": "6a6207cf92969197bb382958",
        "prodseller_id_env": "PRODSELLER_ILOVEPDF_ID",
        "prodseller_name_env": "PRODSELLER_ILOVEPDF_NAME",
        "prodseller_default": "iLovePdf Premium 1Yr",
        "stock_key": "ilovepdf_manual_stock",
        "info_key": "ilovepdf_info",
        "default_info_id": (
            "🔻 Full access to all iLovePDF tools\n"
            "🔻 Unlimited document processing\n"
            "🔻 Access across Web, Mobile, and Desktop\n"
            "🔻 Digital Signatures & Ad-free experience\n"
            "🔻 Regional file processing & 2000 AI Credits\n"
            "✅ Diberikan Akun email:pass iLovePdf\n"
            "⚡️ Login ke website iLovePdf dengan email:pass lalu ganti password akun."
        ),
        "default_info_en": (
            "🔻 Full access to all iLovePDF tools\n"
            "🔻 Unlimited document processing\n"
            "🔻 Access across Web, Mobile, and Desktop\n"
            "🔻 Digital Signatures & Ad-free experience\n"
            "🔻 Regional file processing & 2000 AI Credits\n"
            "✅ You are given email:pass of iLovePdf\n"
            "⚡️ Login to iLovePdf website with email:pass given and change password of account."
        ),
    },
    "outlook": {
        "emoji": "✉️",
        "label_id": "Emails Outlook/Hotmail",
        "label_en": "Emails Outlook/Hotmail",
        "price_coins_key": "outlook_price",
        "price_idr_key": "outlook_price_idr",
        "price_qris_key": "outlook_qris_price_idr",
        "price_binance_key": "outlook_binance_price_usdt",
        "default_coins": 15,
        "default_idr": 8000,
        "default_qris_idr": 8000,
        "default_binance_usdt": "0.52",
        "markup_usdt": 0.5,
        "prodseller_default_id": "6a2ff705dbe65bbecc0d3d9d",
        "prodseller_id_env": "PRODSELLER_OUTLOOK_ID",
        "prodseller_name_env": "PRODSELLER_OUTLOOK_NAME",
        "prodseller_default": " Emails Outlook/hotmail",
        "stock_key": "outlook_manual_stock",
        "info_key": "outlook_info",
        "default_info_id": (
            "Full email Access + OTP\n"
            "Format : email|password|token\n"
            "OTP link : https://dongvanfb.net/read_mail_box/"
        ),
        "default_info_en": (
            "Full email Access + OTP\n"
            "Format : email|password|token\n"
            "OTP link : https://dongvanfb.net/read_mail_box/"
        ),
    },
    "appletv": {
        "emoji": "🍏",
        "label_id": "Apple TV 12M Link",
        "label_en": "Apple TV 12M Link",
        "price_coins_key": "appletv_price",
        "price_idr_key": "appletv_price_idr",
        "price_qris_key": "appletv_qris_price_idr",
        "price_binance_key": "appletv_binance_price_usdt",
        "default_coins": 40,
        "default_idr": 31000,
        "default_qris_idr": 31000,
        "default_binance_usdt": "1.90",
        "markup_usdt": 0.5,
        "prodseller_default_id": "6abeace70dbb401865ffb2d2",
        "prodseller_id_env": "PRODSELLER_APPLETV_ID",
        "prodseller_name_env": "PRODSELLER_APPLETV_NAME",
        "prodseller_default": "Apple TV 12 Months Link",
        "stock_key": "appletv_manual_stock",
        "info_key": "appletv_info",
        "default_info_id": (
            "📺 APPLE TV 12M ACTIVATION LINK\n\n"
            "🎁 48 HOURS HOLD WARRANTY\n"
            "🍏 SIMPLE AS GEMINI/DUOLINGO LINKS\n"
            "NO CARD/PAYMENT METHOD REQUIRED ✅\n\n"
            "📱 ACTIVATION PROCESS:\n"
            "GO TO APPLE TV WEBSITE AND CREATE AN ACCOUNT USING USA VPN, PASTE LINK AND ACTIVATE SUBSCRIPTION.\n"
            "NO VPN NEEDED AFTER ACTIVATING SUBSCRIPTION.\n"
            "ℹ️ NO WARRANTY AFTER ACTIVATION"
        ),
        "default_info_en": (
            "📺 APPLE TV 12M ACTIVATION LINK\n\n"
            "🎁 48 HOURS HOLD WARRANTY\n"
            "🍏 SIMPLE AS GEMINI/DUOLINGO LINKS\n"
            "NO CARD/PAYMENT METHOD REQUIRED ✅\n\n"
            "📱 ACTIVATION PROCESS:\n"
            "GO TO APPLE TV WEBSITE AND CREATE AN ACCOUNT USING USA VPN, PASTE LINK AND ACTIVATE SUBSCRIPTION.\n"
            "NO VPN NEEDED AFTER ACTIVATING SUBSCRIPTION.\n"
            "ℹ️ NO WARRANTY AFTER ACTIVATION"
        ),
    },
    "adobe_express": {
        "emoji": "⚡",
        "label_id": "Adobe Express 12M",
        "label_en": "Adobe Express 12M",
        "price_coins_key": "adobe_express_price",
        "price_idr_key": "adobe_express_price_idr",
        "price_qris_key": "adobe_express_qris_price_idr",
        "price_binance_key": "adobe_express_binance_price_usdt",
        "default_coins": 20,
        "default_idr": 12000,
        "default_qris_idr": 12000,
        "default_binance_usdt": "0.75",
        "markup_usdt": 0.5,
        "prodseller_default_id": "6a5b873847b606c66fc160b2",
        "prodseller_id_env": "PRODSELLER_ADOBE_EXPRESS_ID",
        "prodseller_name_env": "PRODSELLER_ADOBE_EXPRESS_NAME",
        "prodseller_default": "Adobe Express 12M",
        "stock_key": "adobe_express_manual_stock",
        "info_key": "adobe_express_info",
        "default_info_id": (
            "- You will receive a redeem link, open it and login with your email you will upgraded instantly to Premium member of adobe express for 12 months.\n"
            "- No VPN, No VISA or payment required, simple as 1+1=2\n"
            "⚠️ If you encounter a region restriction or region mismatch error, connect to an Indian VPN and try again."
        ),
        "default_info_en": (
            "- You will receive a redeem link, open it and login with your email you will upgraded instantly to Premium member of adobe express for 12 months.\n"
            "- No VPN, No VISA or payment required, simple as 1+1=2\n"
            "⚠️ If you encounter a region restriction or region mismatch error, connect to an Indian VPN and try again."
        ),
    },
}


def _get_catalog_product_price(key: str, pp: dict | None = None) -> tuple[int, str]:
    """Return (price_idr, price_usdt) respecting admin settings and ProdSeller + 0.5 USDT markup."""
    cfg = _PRODUCT_CATALOG.get(key, {})
    if not cfg:
        return 0, "0"

    provider_price = None
    if pp and "price" in pp:
        try:
            provider_price = float(pp["price"])
        except (ValueError, TypeError):
            pass
    elif _prodseller_configured():
        expires_at, cached = _prodseller_products_cache
        if cached:
            target_id = os.getenv(cfg.get("prodseller_id_env", ""), "").strip() or cfg.get("prodseller_default_id", "")
            target_name = os.getenv(cfg.get("prodseller_name_env", ""), cfg.get("prodseller_default", "")).strip().lower()
            for p in cached:
                if (target_id and str(p.get("id")) == target_id) or (target_name and target_name in str(p.get("name", "")).lower()):
                    try:
                        provider_price = float(p.get("price", 0))
                        break
                    except (ValueError, TypeError):
                        pass

    markup = cfg.get("markup_usdt", 0)

    # If markup is configured and live provider_price is available, strictly calculate provider_price + markup
    if provider_price is not None and provider_price > 0 and markup:
        price_usdt = f"{(provider_price + markup):.2f}".rstrip("0").rstrip(".")
        if price_usdt.endswith("."):
            price_usdt = price_usdt[:-1]
        price_idr = int(round(((provider_price + markup) * 16200) / 1000) * 1000)
        return price_idr, price_usdt

    # Fallback to custom admin setting or defaults
    custom_usdt = _setting_text(cfg.get("price_binance_key", ""), "")
    if custom_usdt and custom_usdt.strip():
        price_usdt = custom_usdt.strip()
    else:
        price_usdt = cfg.get("default_binance_usdt", "1.0")

    custom_idr = _setting(cfg.get("price_idr_key", ""), 0)
    if custom_idr and custom_idr > 0:
        price_idr = custom_idr
    else:
        price_idr = cfg.get("default_idr", 20000)

    return price_idr, price_usdt


def _db() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with _db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL DEFAULT 'id',
                coins INTEGER NOT NULL DEFAULT 0,
                referral_code TEXT NOT NULL UNIQUE,
                referred_by INTEGER,
                last_checkin TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS redeem_codes (
                code TEXT PRIMARY KEY,
                coins INTEGER NOT NULL,
                max_uses INTEGER NOT NULL DEFAULT 1,
                uses INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS redemptions (
                code TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                redeemed_at TEXT NOT NULL,
                PRIMARY KEY (code, user_id)
            );
            CREATE TABLE IF NOT EXISTS coin_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS gemini_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS payment_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                method TEXT NOT NULL,
                amount TEXT NOT NULL,
                reference TEXT NOT NULL,
                evidence_file_id TEXT,
                email TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                provider_order_id TEXT,
                user_chat_id INTEGER,
                user_message_id INTEGER,
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                reviewed_by INTEGER
            );
            CREATE TABLE IF NOT EXISTS settled_shopee_transactions (
                transaction_id TEXT PRIMARY KEY,
                payment_id INTEGER,
                amount INTEGER,
                tx_time INTEGER,
                settled_at TEXT
            );
            """
        )
        catalog_settings_defaults = []
        for c_key, c_cfg in _PRODUCT_CATALOG.items():
            catalog_settings_defaults.extend([
                (c_cfg["price_coins_key"], str(c_cfg["default_coins"])),
                (c_cfg["price_idr_key"], str(c_cfg["default_idr"])),
                (c_cfg["price_qris_key"], str(c_cfg["default_qris_idr"])),
                (c_cfg["price_binance_key"], str(c_cfg["default_binance_usdt"])),
                (c_cfg["stock_key"], "0"),
                (c_cfg["info_key"], ""),
                (f"active_{c_key}", "1"),
            ])

        connection.executemany(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
            [
                ("doc_price", "3"),
                ("gemini_price", "20"),
                ("gemini_price_idr", "20000"),
                ("gemini_qris_price_idr", "20000"),
                ("gemini_binance_price_usdt", "0.60"),
                ("checkin_reward", "1"),
                ("referral_reward", "2"),
                ("gemini_manual_stock", "0"),
                ("gemini_info", ""),
                ("active_docs", "1"),
                ("active_gemini", "1"),
            ] + catalog_settings_defaults,
        )

        # Migrate legacy codex default price if still untouched
        connection.execute(
            "UPDATE settings SET value = '1.20' WHERE key = 'codex_binance_price_usdt' AND value = '2.5'"
        )
        connection.execute(
            "UPDATE settings SET value = '20000' WHERE key = 'codex_price_idr' AND value = '55000'"
        )
        connection.execute(
            "UPDATE settings SET value = '20000' WHERE key = 'codex_qris_price_idr' AND value = '55000'"
        )
        connection.execute(
            "UPDATE settings SET value = '30' WHERE key = 'codex_price' AND value IN ('50', '25')"
        )
        for column, definition in (
            ("user_chat_id", "INTEGER"),
            ("user_message_id", "INTEGER"),
            # product_key tracks which catalog product the payment is for.
            # DEFAULT 'gemini' ensures backward-compat with existing rows.
            ("product_key", "TEXT NOT NULL DEFAULT 'gemini'"),
            ("raw_amount", "INTEGER DEFAULT 0"),
            ("qris_payload", "TEXT DEFAULT ''"),
            ("auto_settled", "INTEGER DEFAULT 0"),
            ("delivered_data", "TEXT DEFAULT ''"),
            ("shopee_tx_id", "TEXT DEFAULT NULL"),
        ):
            try:
                connection.execute(f"ALTER TABLE payment_requests ADD COLUMN {column} {definition}")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise

        # Pre-seed already settled past transaction IDs to never allow reuse
        for past_tx_id in ("142440650217903282", "160602852084275760"):
            connection.execute(
                "INSERT OR IGNORE INTO settled_shopee_transactions (transaction_id, payment_id, amount, tx_time, settled_at) VALUES (?, 0, 0, 0, CURRENT_TIMESTAMP)",
                (past_tx_id,),
            )


def _admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", os.getenv("ADMIN_USER_ID", ""))
    return {int(value.strip()) for value in raw.split(",") if value.strip().isdigit()}


def _is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in _admin_ids()


def _setting(name: str, default: int) -> int:
    with _db() as connection:
        row = connection.execute("SELECT value FROM settings WHERE key = ?", (name,)).fetchone()
    try:
        return int(row["value"]) if row else default
    except (TypeError, ValueError):
        return default


def _setting_text(name: str, default: str) -> str:
    with _db() as connection:
        row = connection.execute("SELECT value FROM settings WHERE key = ?", (name,)).fetchone()
    return str(row["value"]) if row else default


def _format_idr(amount: int) -> str:
    return f"Rp{amount:,}".replace(",", ".")


def _ensure_user(user_id: int, username: str = "") -> sqlite3.Row:
    with _db() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO users(user_id, username, referral_code) VALUES (?, ?, ?)",
            (user_id, username, secrets.token_urlsafe(6).upper()),
        )
        connection.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
        return connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def _user_from_update(update: Update) -> sqlite3.Row | None:
    user = update.effective_user
    if user is None:
        return None
    return _ensure_user(user.id, user.username or user.full_name or "")


def _add_coins(user_id: int, amount: int, reason: str = "Manual adjustment") -> int:
    with _db() as connection:
        connection.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
        row = connection.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,)).fetchone()
        connection.execute(
            "INSERT INTO coin_transactions(user_id, amount, balance_after, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, row["coins"], reason, datetime.now().isoformat()),
        )
    return int(row["coins"])


def _spend_coins(user_id: int, amount: int, reason: str = "Purchase") -> bool:
    with _db() as connection:
        cursor = connection.execute(
            "UPDATE users SET coins = coins - ? WHERE user_id = ? AND coins >= ?",
            (amount, user_id, amount),
        )
        if cursor.rowcount == 1:
            row = connection.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,)).fetchone()
            connection.execute(
                "INSERT INTO coin_transactions(user_id, amount, balance_after, reason, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, -amount, row["coins"], reason, datetime.now().isoformat()),
            )
    return cursor.rowcount == 1


def _coin_history(user_id: int, limit: int = 15) -> list[sqlite3.Row]:
    with _db() as connection:
        return connection.execute(
            "SELECT amount, balance_after, reason, created_at FROM coin_transactions WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


def _gemini_stock_count() -> int:
    with _db() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM gemini_stock WHERE active = 1").fetchone()
    return int(row["total"])


class ProdSellerError(RuntimeError):
    """Safe provider error that never contains the API key."""


class ProdSellerFundingError(ProdSellerError):
    """Provider account cannot fund the requested order."""


def _prodseller_base_url() -> str:
    return os.getenv("PRODSELLER_BASE_URL", "https://prodseller.com/v1").rstrip("/")


def _prodseller_request_sync(method: str, path: str, **kwargs) -> dict:
    api_key = os.getenv("PRODSELLER_API_KEY", "").strip()
    if not api_key or api_key.startswith("psk_your_"):
        raise ProdSellerError("ProdSeller API is not configured")
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    if method.upper() == "POST":
        headers["Content-Type"] = "application/json"
    headers.update(kwargs.pop("headers", {}))
    body = kwargs.pop("json", None)
    request = Request(
        f"{_prodseller_base_url()}{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers=headers,
        method=method.upper(),
    )
    try:
        with urlopen(request, timeout=20) as response:
            status_code = response.status
            raw_payload = response.read()
    except HTTPError as exc:
        status_code = exc.code
        raw_payload = exc.read()
    except (URLError, TimeoutError, OSError) as exc:
        raise ProdSellerError("ProdSeller is temporarily unreachable") from exc
    try:
        payload = json.loads(raw_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProdSellerError("ProdSeller returned an invalid response") from exc
    if not 200 <= status_code < 300:
        provider_message = payload.get("error") if isinstance(payload, dict) else None
        logger.warning("ProdSeller request failed: status=%s error=%s", status_code, provider_message)
        raise ProdSellerError(provider_message or f"ProdSeller request failed ({status_code})")
    return payload


async def _prodseller_products(force_refresh: bool = False) -> list[dict]:
    global _prodseller_products_cache
    expires_at, cached = _prodseller_products_cache
    if not force_refresh and time.time() < expires_at and cached:
        return cached
    payload = await asyncio.to_thread(_prodseller_request_sync, "GET", "/products")
    products = payload.get("products", [])
    _prodseller_products_cache = (time.time() + 60, products)
    return products


async def _find_gemini_product() -> dict:
    product_id = os.getenv("PRODSELLER_PRODUCT_ID", "").strip()
    product_name = os.getenv("PRODSELLER_PRODUCT_NAME", "Gemini Pro").strip().lower()
    products = await _prodseller_products()
    if product_id:
        for product in products:
            if str(product.get("id")) == product_id:
                return product
    matches = [product for product in products if product_name and product_name in str(product.get("name", "")).lower()]
    if not matches:
        raise ProdSellerError("Gemini Pro product was not found")
    return matches[0]


async def _create_gemini_order(
    user_id: int,
    product: dict,
    email: str | None = None,
    charge_coins: bool = False,
) -> dict:
    price = _setting("gemini_price", 20)
    provider_balance = await asyncio.to_thread(_prodseller_request_sync, "GET", "/balance")
    try:
        provider_price = float(product.get("price", 0))
        available_balance = float(provider_balance.get("balance", 0))
    except (TypeError, ValueError) as exc:
        raise ProdSellerError("ProdSeller returned an invalid balance") from exc
    if available_balance < provider_price:
        raise ProdSellerFundingError("ProdSeller balance is insufficient")
    if charge_coins and not _spend_coins(user_id, price, "Gemini Pro purchase"):
        raise ProdSellerError(f"Insufficient coin balance; requires {price} coins")
    idempotency_key = f"gemini-{user_id}-{secrets.token_hex(12)}"
    body = {"productId": product["id"], "quantity": 1}
    if email:
        body["email"] = email
    try:
        order = await asyncio.to_thread(
            _prodseller_request_sync,
            "POST",
            "/orders",
            json=body,
            headers={"Idempotency-Key": idempotency_key},
        )
    except ProdSellerError:
        if charge_coins:
            _add_coins(user_id, price, "Gemini Pro purchase refund")
        raise
    return order


# ─────────────────────────────────────────────────────────────────────────────
# Generic Catalog Functions  (CapCut / Claude AI / GPT Codex / Prime Video)
# ─────────────────────────────────────────────────────────────────────────────

async def _find_catalog_product(key: str) -> dict:
    """Locate a ProdSeller product for any catalog entry by ID or name."""
    cfg = _PRODUCT_CATALOG[key]
    product_id   = os.getenv(cfg["prodseller_id_env"], "").strip() or cfg.get("prodseller_default_id", "")
    product_name = os.getenv(cfg["prodseller_name_env"], cfg["prodseller_default"]).strip().lower()
    products = await _prodseller_products()
    if product_id:
        for p in products:
            if str(p.get("id")) == product_id:
                return p
    matches = [p for p in products if product_name and product_name in str(p.get("name", "")).lower()]
    if not matches:
        raise ProdSellerError(f"{cfg['prodseller_default']} product was not found on ProdSeller")
    return matches[0]


async def _create_catalog_order(
    user_id: int,
    key: str,
    product: dict,
    email: str | None = None,
    charge_coins: bool = False,
) -> dict:
    """Create a ProdSeller order for a catalog product, optionally deducting coins."""
    cfg = _PRODUCT_CATALOG[key]
    price = _setting(cfg["price_coins_key"], cfg["default_coins"])
    provider_balance = await asyncio.to_thread(_prodseller_request_sync, "GET", "/balance")
    try:
        provider_price    = float(product.get("price", 0))
        available_balance = float(provider_balance.get("balance", 0))
    except (TypeError, ValueError) as exc:
        raise ProdSellerError("ProdSeller returned an invalid balance") from exc
    if available_balance < provider_price:
        raise ProdSellerFundingError("ProdSeller balance is insufficient")
    label = cfg["label_en"]
    if charge_coins and not _spend_coins(user_id, price, f"{label} purchase"):
        raise ProdSellerError(f"Insufficient coin balance; requires {price} coins")
    idempotency_key = f"{key}-{user_id}-{secrets.token_hex(12)}"
    body: dict = {"productId": product["id"], "quantity": 1}
    if email:
        body["email"] = email
    try:
        order = await asyncio.to_thread(
            _prodseller_request_sync,
            "POST",
            "/orders",
            json=body,
            headers={"Idempotency-Key": idempotency_key},
        )
    except ProdSellerError:
        if charge_coins:
            _add_coins(user_id, price, f"{label} purchase refund")
        raise
    return order


def _prodseller_configured() -> bool:
    """Return True when a real ProdSeller API key is present."""
    k = os.getenv("PRODSELLER_API_KEY", "").strip()
    return bool(k) and not k.startswith("psk_your_")


async def _show_catalog_product(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str) -> None:
    """Render the product-detail page for any catalog product."""
    cfg     = _PRODUCT_CATALOG[key]
    english = _is_english(update)
    label   = cfg["label_en"] if english else cfg["label_id"]
    emoji   = cfg["emoji"]
    price_idr, price_usdt = _get_catalog_product_price(key)
    price_display = f"{price_usdt} USDT" if english else _format_idr(price_idr)
    context.user_data["buying_product"] = key

    admin_info    = _setting_text(cfg["info_key"], "").strip()
    fallback_info = cfg.get("default_info_en" if english else "default_info_id", "")

    if not _prodseller_configured():
        stock        = _setting(cfg["stock_key"], 0)
        stock_text   = f"🟢 Tersedia ({stock} unit)" if not english else f"🟢 In Stock ({stock} units)"
        if stock <= 0:
            stock_text = "🔴 Stok Habis" if not english else "🔴 Out of Stock"
        info_to_show = admin_info or fallback_info
        info_block   = f"\n\n{_safe_html(info_to_show)}" if info_to_show else ""
        text = (
            f"<b>{emoji} {_safe_html(label)}</b>\n\n"
            + (f"Price: <b>{price_display}</b>\nStock: <b>{stock_text}</b>"
               if english else
               f"Harga: <b>{price_display}</b>\nStok: <b>{stock_text}</b>")
            + info_block
        )
    else:
        try:
            pp = await _find_catalog_product(key)
        except ProdSellerError as exc:
            logger.info("Catalog product %s unavailable: %s", key, exc)
            await _safe_edit_text(
                update,
                f"<b>{emoji} {_safe_html(label)}</b>\n\n"
                + ("Product is temporarily unavailable. Please contact admin."
                   if english else
                   "Produk sedang tidak tersedia. Silakan hubungi admin."),
                parse_mode="HTML", reply_markup=_back_keyboard(),
            )
            return
        price_idr, price_usdt = _get_catalog_product_price(key, pp)
        price_display = f"{price_usdt} USDT" if english else _format_idr(price_idr)
        p_stock      = pp.get("stock")
        if pp.get("inStock") is False or p_stock == 0:
            stock_text = "🔴 Stok Habis" if not english else "🔴 Out of Stock"
        else:
            stock_text = f"🟢 Tersedia ({p_stock} unit)" if p_stock is not None else ("🟢 In Stock" if english else "🟢 Tersedia")
        live_desc    = pp.get("description", "").strip()
        info_to_show = admin_info or live_desc or fallback_info
        info_block   = f"\n\n{_safe_html(info_to_show)}" if info_to_show else ""
        p_name       = pp.get("name", label)
        text = (
            f"<b>{emoji} {_safe_html(p_name)}</b>\n\n"
            + (f"Price: <b>{price_display}</b>\nStock: <b>{stock_text}</b>"
               if english else
               f"Harga: <b>{price_display}</b>\nStok: <b>{stock_text}</b>")
            + info_block
        )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🛒 Buy {label}" if english else f"🛒 Beli {label}", callback_data=f"catalog_buy:{key}")],
        [InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="menu:main")],
    ])
    await _safe_edit_text(update, text, parse_mode="HTML", reply_markup=keyboard)


async def _show_catalog_payment_methods(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str) -> None:
    """Payment method selection screen for a catalog product (QRIS & Binance only; coins reserved for Canva)."""
    cfg     = _PRODUCT_CATALOG[key]
    english = _is_english(update)
    label   = cfg["label_en"] if english else cfg["label_id"]
    price_idr, price_usdt = _get_catalog_product_price(key)
    binance_price = price_usdt
    qris_price    = _format_idr(price_idr)

    text = (
        f"<b>💳 {'Purchase' if english else 'Beli'} {_safe_html(label)}</b>\n\n"
        + ("Choose payment method (Binance USDT or QRIS). Your order is verified by admin before delivery."
           if english else
           "Pilih metode pembayaran (Binance USDT atau QRIS). Pesanan Anda diverifikasi oleh admin sebelum dikirim.")
    )
    rows = [
        [InlineKeyboardButton(f"💳 Binance · {binance_price} USDT", callback_data=f"catalog_pay:{key}:binance")],
        [InlineKeyboardButton(f"📱 QRIS · {qris_price}",            callback_data=f"catalog_pay:{key}:qris")],
        [InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data=f"product:{key}")],
    ]
    await _safe_edit_text(update, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))


async def _show_dynamic_qris_instruction(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    product_key: str,
    base_price: int,
    product_label: str,
    back_callback: str,
) -> bool:
    """Attempt to present dynamic QRIS with automatic payment tracking.

    Returns True if dynamic QRIS was successfully presented, False to fallback to static QRIS.
    """
    if not _shopee_qris_raw:
        return False

    try:
        now_dt = datetime.now()
        pending_cutoff = (now_dt - timedelta(minutes=16)).isoformat()
        cooldown_cutoff = (now_dt - timedelta(hours=2)).isoformat()
        reserved_amounts = set()
        with _db() as connection:
            rows = connection.execute(
                """
                SELECT raw_amount FROM payment_requests
                WHERE method = 'qris' AND raw_amount > 0 AND (
                    (status = 'pending' AND created_at >= ?) OR
                    (status = 'approved' AND reviewed_at >= ?)
                )
                """,
                (pending_cutoff, cooldown_cutoff),
            ).fetchall()
            for r in rows:
                if r["raw_amount"]:
                    reserved_amounts.add(int(r["raw_amount"]))

        unique_amount, unique_code = _amount_allocator.allocate(base_price, reserved_amounts=reserved_amounts)
        dyn_payload = qris_engine.static_to_dynamic_qris(_shopee_qris_raw, unique_amount)
        qr_url = qris_engine.get_qris_qr_image_url(dyn_payload, size=450)
    except Exception as exc:
        logger.warning("Could not construct dynamic QRIS for %s: %s, falling back to static", product_key, exc)
        return False

    user = _user_from_update(update)
    email = context.user_data.get("product_email") or context.user_data.get("gemini_email")
    english = _is_english(update)

    with _db() as connection:
        cursor = connection.execute(
            "INSERT INTO payment_requests "
            "(user_id, method, amount, reference, email, product_key, raw_amount, qris_payload, created_at) "
            "VALUES (?, 'qris', ?, ?, ?, ?, ?, ?, ?)",
            (
                user["user_id"] if user else 0,
                _format_idr(unique_amount),
                f"QRIS-DYN-{unique_amount}",
                email,
                product_key,
                unique_amount,
                dyn_payload,
                datetime.now().isoformat(),
            ),
        )
        payment_id = cursor.lastrowid

    context.user_data["current_qris_payment_id"] = payment_id

    if english:
        caption = (
            f"<b>📱 Automatic QRIS Payment</b>\n\n"
            f"Product: <b>{_safe_html(product_label)}</b>\n"
            f"Total Amount: <b><code>Rp{unique_amount:,}</code></b>\n"
            f"<i>(Includes unique code Rp{unique_code} for instant auto-verification)</i>\n\n"
            f"⚠️ <b>IMPORTANT:</b>\n"
            f"• Please transfer the <b>EXACT</b> amount above (do not round off).\n"
            f"• Supported: BCA, Livin, Mandiri, BRI, ShopeePay, GoPay, OVO, DANA, etc.\n"
            f"• Order is delivered automatically once payment is detected.\n\n"
            f"⏱ Valid for: <b>15 minutes</b>"
        ).replace(",", ".")
    else:
        caption = (
            f"<b>📱 Pembayaran QRIS Otomatis</b>\n\n"
            f"Produk: <b>{_safe_html(product_label)}</b>\n"
            f"Total Bayar: <b><code>Rp{unique_amount:,}</code></b>\n"
            f"<i>(Termasuk kode unik Rp{unique_code} untuk verifikasi otomatis instan)</i>\n\n"
            f"⚠️ <b>PENTING:</b>\n"
            f"• Mohon transfer <b>TEPAT</b> sesuai nominal di atas (jangan dibulatkan).\n"
            f"• Mendukung semua Bank & E-Wallet (BCA, Livin, Mandiri, BRI, ShopeePay, GoPay, OVO, DANA, dll).\n"
            f"• Pesanan akan otomatis terkirim segera setelah pembayaran terdeteksi.\n\n"
            f"⏱ Batas Waktu: <b>15 menit</b>"
        ).replace(",", ".")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Check Payment Status" if english else "🔄 Cek Status Pembayaran", callback_data=f"qris_check:{payment_id}")],
        [
            InlineKeyboardButton("❌ Cancel Order" if english else "❌ Batalkan Pesanan", callback_data=f"payment:cancel:{payment_id}"),
            InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data=back_callback),
        ],
    ])

    if update.effective_chat:
        if update.callback_query and update.callback_query.message:
            try:
                await update.callback_query.message.delete()
            except TelegramError:
                pass
        try:
            sent_msg = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=qr_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            if sent_msg:
                with _db() as connection:
                    connection.execute(
                        "UPDATE payment_requests SET user_chat_id = ?, user_message_id = ? WHERE id = ?",
                        (sent_msg.chat_id, sent_msg.message_id, payment_id),
                    )
            return True
        except TelegramError as exc:
            logger.warning("Failed to send dynamic QRIS photo for %s: %s, falling back to static", product_key, exc)
            return False

    return False


async def _show_catalog_payment_instruction(
    update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, method: str,
) -> None:
    """Show Binance or QRIS payment instructions for a catalog product."""
    cfg     = _PRODUCT_CATALOG[key]
    english = _is_english(update)
    context.user_data["payment_method"] = method
    context.user_data["buying_product"] = key
    context.user_data["step"]           = f"catalog_payment:{key}:{method}"
    back_btn = [
        [
            InlineKeyboardButton("❌ Cancel Order" if english else "❌ Batalkan Pesanan", callback_data="payment:cancel_current"),
            InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data=f"catalog_payment_methods:{key}"),
        ]
    ]

    price_idr, price_usdt = _get_catalog_product_price(key)
    if method == "binance":
        account = os.getenv("BINANCE_ACCOUNT_ID", "").strip() or os.getenv("BINANCE_PAYMENT_ADDRESS", "").strip()
        if not account or account.startswith("your_"):
            await _safe_edit_text(
                update,
                "Binance payment is not configured. Please contact admin." if english
                else "Pembayaran Binance belum dikonfigurasi. Silakan hubungi admin.",
                reply_markup=InlineKeyboardMarkup(back_btn),
            )
            return
        binance_price = price_usdt
        network  = os.getenv("BINANCE_NETWORK", "").strip()
        net_line = f"\nNetwork: <b>{_safe_html(network)}</b>" if network else ""
        text = (
            f"<b>💳 Direct Binance Transfer</b>\n\nAmount: <b>{_safe_html(binance_price)} USDT</b>\n"
            f"Binance account:\n<code>{_safe_html(account)}</code>{net_line}\n\n"
            + ("Transfer USDT, then send the transaction ID/hash." if english
               else "Transfer USDT ke akun ini, lalu kirim TXID/hash transaksi.")
        )
        await _safe_edit_text(update, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_btn))
    else:
        raw_price = price_idr
        label = f"{cfg['emoji']} {cfg['label_en'] if english else cfg['label_id']}"
        if await _show_dynamic_qris_instruction(
            update=update,
            context=context,
            product_key=key,
            base_price=raw_price,
            product_label=label,
            back_callback=f"catalog_payment_methods:{key}",
        ):
            return

        qris_price = _format_idr(raw_price)
        note       = os.getenv("QRIS_PAYMENT_NOTE", "").strip()
        text = (
            f"<b>📱 QRIS Payment</b>\n\nAmount: <b>{qris_price}</b>\n"
            + (f"{_safe_html(note)}\n\n" if note else "")
            + ("After payment, send the transaction reference or screenshot." if english
               else "Setelah membayar, kirim referensi transaksi atau screenshot.")
        )
        qris_path = Path(os.getenv("QRIS_IMAGE_PATH", "QRIS-YOWES-DIGITAL-PRO.jpeg"))
        if not qris_path.is_absolute():
            qris_path = BASE_DIR / qris_path
        if qris_path.exists() and update.effective_chat:
            try:
                if update.callback_query and update.callback_query.message:
                    await update.callback_query.message.delete()
                with qris_path.open("rb") as qf:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id, photo=qf,
                        caption=text, parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(back_btn),
                    )
                return
            except TelegramError as exc:
                logger.warning("Could not send QRIS image for %s: %s", key, exc)
        await _safe_edit_text(update, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_btn))


async def _complete_catalog_coin_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str) -> None:
    """Coins are strictly reserved for Canva document generation."""
    cfg   = _PRODUCT_CATALOG.get(key, {})
    label = cfg.get("label_en" if _is_english(update) else "label_id", "Produk digital")
    msg = (
        f"Coins can only be used for Canva document generation. Please purchase {label} via QRIS or Binance USDT."
        if _is_english(update) else
        f"Koin hanya dapat digunakan untuk pembuatan dokumen Canva. Silakan beli {label} melalui QRIS atau Binance USDT."
    )
    await _present_text(update, msg, reply_markup=_back_keyboard(f"catalog_payment_methods:{key}"))


async def _create_catalog_payment_request(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    key: str, reference: str, evidence_file_id: str | None = None,
) -> None:
    """Persist a payment_requests row for a catalog product and notify admins."""
    user = _user_from_update(update)
    if not user:
        return
    cfg     = _PRODUCT_CATALOG[key]
    english = _is_english(update)
    label   = cfg["label_en"] if english else cfg["label_id"]
    method  = context.user_data.get("payment_method")
    if method not in {"binance", "qris"}:
        await _present_text(update, "Choose a payment method first." if english
                            else "Pilih metode pembayaran terlebih dahulu.",
                            reply_markup=_back_keyboard(f"catalog_payment_methods:{key}"))
        return
    amount = (_setting_text(cfg["price_binance_key"], cfg["default_binance_usdt"]) + " USDT"
              if method == "binance" else
              _format_idr(_setting(cfg["price_qris_key"], cfg["default_qris_idr"])))
    email = context.user_data.get("product_email") or context.user_data.get("gemini_email")
    with _db() as connection:
        cursor = connection.execute(
            "INSERT INTO payment_requests"
            "(user_id, method, amount, reference, evidence_file_id, email, product_key, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user["user_id"], method, amount, reference[:500],
             evidence_file_id, email,
             key, datetime.now().isoformat()),
        )
        payment_id = cursor.lastrowid
    await _notify_payment_admins(context, payment_id)
    context.user_data.pop("step", None)
    msg = (
        f"<b>Payment submitted</b>\n\nRequest: <code>#{payment_id}</code>\nProduct: <b>{_safe_html(label)}</b>\n"
        "Your payment is waiting for admin verification."
        if english else
        f"<b>Pembayaran terkirim</b>\n\nRequest: <code>#{payment_id}</code>\nProduk: <b>{_safe_html(label)}</b>\n"
        "Pembayaran sedang menunggu verifikasi admin."
    )
    sent = await _present_text(update, msg, parse_mode="HTML", reply_markup=_back_keyboard("menu:main"))
    if sent and getattr(sent, "chat_id", None) and getattr(sent, "message_id", None):
        with _db() as connection:
            connection.execute(
                "UPDATE payment_requests SET user_chat_id = ?, user_message_id = ? WHERE id = ?",
                (sent.chat_id, sent.message_id, payment_id),
            )


# ─────────────────────────────────────────────────────────────────────────────

async def _broadcast_announcement(
    context: ContextTypes.DEFAULT_TYPE,
    broadcast_type: str,
    message_text: str | None = None,
    use_template: bool = False,
) -> int:
    """Broadcast an announcement to every registered user.

    Returns the number of users successfully notified.
    Delivers only the broadcast content without hardcoded title prefixes.
    """
    with _db() as connection:
        users = connection.execute("SELECT user_id, language FROM users").fetchall()

    sent = 0
    tmpl_data = _BROADCAST_TEMPLATES.get(broadcast_type, _BROADCAST_TEMPLATES.get("info", {}))
    for user in users:
        lang = user["language"] if user["language"] in ("id", "en") else "id"
        if use_template:
            full_message = tmpl_data.get(lang) or tmpl_data.get("id") or (message_text or "")
        else:
            full_message = message_text or ""

        if not full_message.strip():
            continue

        try:
            await context.bot.send_message(
                chat_id=user["user_id"],
                text=full_message,
                parse_mode="Markdown",
            )
            sent += 1
        except RetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await context.bot.send_message(
                    chat_id=user["user_id"],
                    text=full_message,
                    parse_mode="Markdown",
                )
                sent += 1
            except TelegramError as retry_err:
                logger.info(
                    "Broadcast skipped for user %s (retry): %s",
                    user["user_id"], retry_err,
                )
        except TelegramError as exc:
            logger.info("Broadcast skipped for user %s: %s", user["user_id"], exc)
    return sent


async def _broadcast_redeem_code(
    context: ContextTypes.DEFAULT_TYPE,
    code: str,
    coins: int,
    max_uses: int,
) -> int:
    with _db() as connection:
        users = connection.execute("SELECT user_id, language FROM users").fetchall()

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎟️ Redeem Now", callback_data="redeem:input")]]
    )
    sent = 0
    for user in users:
        if user["language"] == "en":
            message = (
                "*New Redeem Code Available*\n\n"
                f"Code: `{code}`\nReward: *{coins} 🪙*\nAvailable uses: *{max_uses}*\n\n"
                "Redeem it before the quota runs out."
            )
        else:
            message = (
                "*Redeem Code Baru Tersedia*\n\n"
                f"Kode: `{code}`\nHadiah: *{coins} 🪙*\nBatas penggunaan: *{max_uses}*\n\n"
                "Segera gunakan sebelum kuota habis."
            )
        try:
            await context.bot.send_message(
                chat_id=user["user_id"],
                text=message,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            sent += 1
        except RetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await context.bot.send_message(
                    chat_id=user["user_id"],
                    text=message,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
                sent += 1
            except TelegramError as retry_error:
                logger.info("Redeem notification skipped for user %s: %s", user["user_id"], retry_error)
        except TelegramError as exc:
            logger.info("Redeem notification skipped for user %s: %s", user["user_id"], exc)
    return sent


def _set_setting(name: str, value: int) -> None:
    with _db() as connection:
        connection.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (name, str(value)),
        )


def _set_setting_text(name: str, value: str) -> None:
    with _db() as connection:
        connection.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (name, value),
        )


init_database()


def load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env_file()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_country_display(code: str) -> str:
    return COUNTRY_LABELS.get(code.lower(), code.upper())


async def _safe_reply_text(update: Update, text: str, **kwargs):
    target = None
    if update.callback_query is not None and update.callback_query.message is not None:
        target = update.callback_query.message
    elif update.message is not None:
        target = update.message
    if target is None:
        return None
    try:
        return await target.reply_text(text, **kwargs)
    except TelegramError as exc:
        if "can't parse entities" in str(exc).lower():
            safe_kwargs = dict(kwargs)
            safe_kwargs.pop("parse_mode", None)
            return await target.reply_text(text, **safe_kwargs)
        raise


async def _safe_edit_text(update: Update, text: str, **kwargs):
    """Edit the current inline-keyboard message to show new text.

    Falls back gracefully when the current message is a photo/media
    (e.g. after the QRIS payment screen): deletes the media message
    and sends a fresh text message so the user always gets a response.
    """
    if update.callback_query is not None:
        msg = update.callback_query.message
        bot = getattr(update.callback_query, "_bot", None)
        if bot is None and hasattr(update.callback_query, "get_bot"):
            try:
                bot = update.callback_query.get_bot()
            except Exception:
                pass

        # If current message is a photo/media message (e.g. QRIS image), delete and send fresh text
        if msg is not None and getattr(msg, "photo", None):
            try:
                await msg.delete()
            except Exception:
                pass
            if update.effective_chat and bot:
                return await bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    **kwargs,
                )

        try:
            return await update.callback_query.edit_message_text(text, **kwargs)
        except TelegramError as exc:
            err_lower = str(exc).lower()
            if "message is not modified" in err_lower:
                # Content unchanged — not an error worth acting on.
                return None
            if "there is no text" in err_lower or "no text in the message" in err_lower or "message can't be edited" in err_lower:
                try:
                    if msg:
                        await msg.delete()
                except Exception:
                    pass
                if update.effective_chat and bot:
                    return await bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=text,
                        **kwargs,
                    )
            logger.warning("_safe_edit_text failed: %s", exc)
            return None
    if update.message is not None:
        return await update.message.reply_text(text, **kwargs)
    return None


async def _present_text(update: Update, text: str, **kwargs):
    if update.callback_query is not None:
        return await _safe_edit_text(update, text, **kwargs)
    return await _safe_reply_text(update, text, **kwargs)


async def _send_generated_file(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_path: str,
    caption: str = "",
) -> None:
    chat = update.effective_chat
    if chat is None or context.bot is None:
        return

    path = Path(file_path)
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            with path.open("rb") as generated_file:
                await context.bot.send_photo(
                    chat_id=chat.id,
                    photo=generated_file,
                    caption=caption or None,
                )
            return
        except TelegramError as exc:
            logger.warning("Photo upload failed for %s; retrying as document: %s", path.name, exc)

    with path.open("rb") as generated_file:
        await context.bot.send_document(
            chat_id=chat.id,
            document=generated_file,
            caption=caption or None,
        )


def _format_country_list() -> list[list[InlineKeyboardButton]]:
    buttons = []
    row = []
    for code in list_countries():
        row.append(InlineKeyboardButton(get_country_display(code), callback_data=f"country:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return buttons


def _format_doc_type_buttons(country_code: str, update: Update | None = None) -> list[list[InlineKeyboardButton]]:
    gen = get_country(country_code)()
    types = ["all"] + gen.get_document_types()
    buttons = []
    for doc in types:
        label = "ALL DOCUMENTS" if doc == "all" else doc.replace("_", " ").title()
        buttons.append([InlineKeyboardButton(label, callback_data=f"doc:{doc}")])
    if update:
        buttons.append([InlineKeyboardButton("⬅️ Back" if _is_english(update) else "⬅️ Kembali", callback_data="menu:main")])
    return buttons


def _normalize_document_type(value: str, supported_types: list[str]) -> str | None:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "teacher_id": "teacher_id",
        "teaching_id": "teaching_id",
        "teaching_license": "teaching_license",
        "employment_letter": "employment_letter",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in supported_types else None


def _format_school_buttons(
    country_code: str,
    limit=8,
    english: bool = False,
    include_back: bool = False,
    allow_manual: bool = True,
    back_callback: str = "menu:main",
):
    gen = get_country(country_code)()
    schools = gen.schools[:limit]
    buttons = [
        [InlineKeyboardButton(school["name"], callback_data=f"school:{school['name']}")]
        for school in schools
    ]
    if allow_manual:
        buttons.append([InlineKeyboardButton("✍️ Type manually" if english else "✍️ Ketik sendiri", callback_data="school:manual")])
    if include_back:
        buttons.append([InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data=back_callback)])
    return buttons


def _format_gender_buttons(update: Update | None = None) -> list[list[InlineKeyboardButton]]:
    return [
        [InlineKeyboardButton("🎲 Random", callback_data="gender:Random")],
        [InlineKeyboardButton("👨 Male", callback_data="gender:Male")],
        [InlineKeyboardButton("👩 Female", callback_data="gender:Female")],
    ] + ([[InlineKeyboardButton("⬅️ Back" if update and _is_english(update) else "⬅️ Kembali", callback_data="menu:main")]] if update else [])


def _format_position_buttons(country_code: str, english: bool = False, include_back: bool = False) -> list[list[InlineKeyboardButton]]:
    gen = get_country(country_code)()
    positions = gen.get_positions()
    buttons = []
    for pos in positions[:8]:
        buttons.append([InlineKeyboardButton(pos, callback_data=f"position:{pos}")])
    buttons.append([InlineKeyboardButton("✍️ Type manually" if english else "✍️ Ketik sendiri", callback_data="position:manual")])
    if include_back:
        buttons.append([InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="menu:main")])
    return buttons


def _document_type_keyboard(country_code: str, update: Update) -> InlineKeyboardMarkup:
    rows = _format_doc_type_buttons(country_code, update)
    edit_label = "✏️ Edit School" if _is_english(update) else "✏️ Edit Sekolah"
    rows.insert(-1, [InlineKeyboardButton(edit_label, callback_data="wizard:school")])
    return InlineKeyboardMarkup(rows)


def _generate_random_dob() -> str:
    year = random.randint(1985, 2003)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{day:02d}/{month:02d}/{year}"


def _generate_random_data(country_code: str) -> dict:
    gen = get_country(country_code)()
    first, last = gen.generate_name()
    school = gen.random_school()
    position = random.choice(gen.get_positions())
    gender = random.choice(["Male", "Female"])
    dob = _generate_random_dob()
    return {
        "first_name": first,
        "last_name": last,
        "school": school["name"],
        "position": position,
        "gender": gender,
        "dob": dob,
    }


def _apply_random_defaults(context: ContextTypes.DEFAULT_TYPE, country_code: str) -> None:
    data = _generate_random_data(country_code)
    context.user_data["first_name"] = data["first_name"]
    context.user_data["last_name"] = data["last_name"]
    context.user_data["school"] = data["school"]
    context.user_data["position"] = data["position"]
    context.user_data["gender"] = data["gender"]
    context.user_data["dob"] = data["dob"]
    context.user_data["document_type"] = "all"


def _language(update: Update) -> str:
    row = _user_from_update(update)
    return row["language"] if row else "id"


def _is_english(update: Update) -> bool:
    return _language(update) == "en"


def _safe_html(value: object) -> str:
    return escape(str(value), quote=False)


_TEXT = {
    "new_document": ("*New Document*\n\nChoose the country to use.", "*Buat Dokumen Baru*\n\nPilih negara yang akan digunakan."),
    "choose_country": ("*Document creation*\n\nChoose a country.", "*Mulai pembuatan dokumen*\n\nPilih negara yang akan dipakai."),
    "last_name": ("Send your *last name*.", "Silakan kirim *nama belakang* Anda."),
    "gender": ("Choose *gender*.", "Pilih *jenis kelamin*."),
    "school": ("Choose a *school* or type one manually.", "Pilih *sekolah* atau ketik sendiri."),
    "position": ("Choose or send your *position*.", "Pilih atau kirim *jabatan/posisi* Anda."),
    "dob": ("Send your *date of birth* in `DD/MM/YYYY` format.", "Kirim *tanggal lahir* dalam format `DD/MM/YYYY`."),
    "choose_school": ("Send the *school name* you want.", "Silakan kirim *nama sekolah* yang diinginkan."),
    "choose_position": ("Send your *position*.", "Silakan kirim *jabatan / posisi* Anda."),
    "choose_dob": ("Send your *date of birth* in `DD/MM/YYYY` format.", "Silakan kirim *tanggal lahir* dalam format `DD/MM/YYYY`."),
    "review": ("*Document Review*", "*Review Dokumen*"),
    "create": ("Create Document", "Buat Dokumen"),
    "random_again": ("Randomize Again", "Random Ulang"),
    "edit": ("Edit Data", "Edit Data"),
}


def _t(update: Update, key: str) -> str:
    english, indonesian = _TEXT[key]
    return english if _is_english(update) else indonesian


_main_menu_refresh_counter: int = 0


def _main_menu_text(update: Update, refreshed: bool = False) -> str:
    global _main_menu_refresh_counter
    tz_wib = timezone(timedelta(hours=7))
    now_wib = datetime.now(tz_wib).strftime("%H:%M:%S")
    if refreshed:
        _main_menu_refresh_counter += 1
    zw = "\u200b" * (_main_menu_refresh_counter % 5 + 1)
    if _language(update) == "en":
        base = "*Yowes Main Menu*\n\nChoose a service below. Your balance and activity are saved securely."
        if refreshed:
            base += f"\n\n_⚡ Real-time stock updated at {now_wib} WIB_{zw}"
        return base
    base = "*Menu Utama Yowes*\n\nPilih layanan di bawah. Saldo dan aktivitas Anda tersimpan dengan aman."
    if refreshed:
        base += f"\n\n_⚡ Stok realtime diperbarui pukul {now_wib} WIB_{zw}"
    return base


def _get_product_stock_status(key: str) -> bool:
    """Return True if product is in stock (🟢), False if out of stock (🔴)."""
    if key == "docs":
        return True

    # Ensure live ProdSeller cache is available if configured
    global _prodseller_products_cache
    if _prodseller_configured():
        expires_at, cached = _prodseller_products_cache
        if not cached or time.time() >= expires_at:
            try:
                payload = _prodseller_request_sync("GET", "/products")
                items = payload.get("products", [])
                if items:
                    _prodseller_products_cache = (time.time() + 60, items)
            except Exception as exc:
                logger.debug("Live stock auto-refresh error: %s", exc)

    if key == "gemini":
        if _prodseller_configured():
            expires_at, cached = _prodseller_products_cache
            if cached:
                p_id = os.getenv("PRODSELLER_PRODUCT_ID", "").strip()
                p_name = os.getenv("PRODSELLER_PRODUCT_NAME", "Gemini Pro").strip().lower()
                for p in cached:
                    if (p_id and str(p.get("id")) == p_id) or (p_name and p_name in str(p.get("name", "")).lower()):
                        if p.get("inStock") is False:
                            return False
                        stk = p.get("stock")
                        return stk is None or stk > 0
            return (_gemini_stock_count() > 0) or (_setting("gemini_manual_stock", 0) > 0)

        return (_gemini_stock_count() > 0) or (_setting("gemini_manual_stock", 0) > 0)

    if key in _PRODUCT_CATALOG:
        cfg = _PRODUCT_CATALOG[key]
        if not _prodseller_configured():
            return _setting(cfg["stock_key"], 0) > 0
        expires_at, cached = _prodseller_products_cache
        if cached:
            target_id = os.getenv(cfg["prodseller_id_env"], "").strip() or cfg.get("prodseller_default_id", "")
            target_name = os.getenv(cfg["prodseller_name_env"], cfg["prodseller_default"]).strip().lower()
            for p in cached:
                if (target_id and str(p.get("id")) == target_id) or (target_name and target_name in str(p.get("name", "")).lower()):
                    if p.get("inStock") is False:
                        return False
                    stk = p.get("stock")
                    return stk is None or stk > 0
        return _setting(cfg["stock_key"], 0) > 0

    return True


def _is_product_active(key: str) -> bool:
    """Return True if product is set as active/displayed by admin, False if hidden."""
    return _setting(f"active_{key}", 1) == 1


def _main_menu_keyboard(update: Update) -> InlineKeyboardMarkup:
    english = _language(update) == "en"
    doc_price = _setting("doc_price", 3)
    if english:
        gemini_price = f"{_setting_text('gemini_binance_price_usdt', '0.60')} USDT"
    else:
        gemini_price = _format_idr(_setting("gemini_price_idr", 20000))

    gemini_dot = "🟢" if _get_product_stock_status("gemini") else "🔴"

    product_buttons = []
    if _is_product_active("docs"):
        product_buttons.append([InlineKeyboardButton(f"🎓 Canva Doc Education · {doc_price} 🪙 · 🟢", callback_data="product:docs")])
    if _is_product_active("gemini"):
        product_buttons.append([InlineKeyboardButton(
            f"✨ Gemini Pro 18 Bulan · {gemini_price} · {gemini_dot}" if not english
            else f"✨ Gemini Pro 18 Months · {gemini_price} · {gemini_dot}",
            callback_data="product:gemini",
        )])

    for key, cfg in _PRODUCT_CATALOG.items():
        if not _is_product_active(key):
            continue
        price_idr, price_usdt = _get_catalog_product_price(key)
        price_str = f"{price_usdt} USDT" if english else _format_idr(price_idr)
        stock_dot = "🟢" if _get_product_stock_status(key) else "🔴"
        label = cfg["label_en"] if english else cfg["label_id"]
        product_buttons.append([
            InlineKeyboardButton(f"{cfg['emoji']} {label} · {price_str} · {stock_dot}", callback_data=f"product:{key}")
        ])

    refresh_button = [
        [InlineKeyboardButton("🔄 Refresh Status Stok" if not english else "🔄 Refresh Stock Status", callback_data="menu:refresh_stock")]
    ]

    bottom_buttons = [
        [
            InlineKeyboardButton("🪙 Coin Saya" if not english else "🪙 My Coins", callback_data="account:coins"),
            InlineKeyboardButton("📦 Pesanan Saya" if not english else "📦 My Orders", callback_data="user:orders:0"),
        ],
        [
            InlineKeyboardButton("🤝 Referral", callback_data="referral:menu"),
            InlineKeyboardButton("🎁 Check-in Harian" if not english else "🎁 Daily Check-in", callback_data="checkin:daily"),
        ],
        [InlineKeyboardButton("🎟️ Redeem Code", callback_data="redeem:input")],
        [InlineKeyboardButton("🌐 Bahasa / Language", callback_data="settings:language")],
        [
            InlineKeyboardButton("🌐 Web Store" if not english else "🌐 Web Store", url=WEB_STORE_URL),
            InlineKeyboardButton("💬 Hubungi Support" if not english else "💬 Contact Support", url=SUPPORT_URL),
        ],
        *([[InlineKeyboardButton("⚙️ Admin Settings", callback_data="admin:menu")]] if _is_admin(update.effective_user.id if update.effective_user else None) else []),
    ]

    return InlineKeyboardMarkup(product_buttons + refresh_button + bottom_buttons)


def _back_keyboard(callback_data: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data=callback_data)]])


def _membership_keyboard(update: Update) -> InlineKeyboardMarkup:
    join_label = "📢 Join Channel" if _is_english(update) else "📢 Join Channel"
    check_label = "✅ Check Membership" if _is_english(update) else "✅ Saya Sudah Join"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(join_label, url=REQUIRED_CHANNEL_URL)],
            [InlineKeyboardButton(check_label, callback_data="membership:check")],
        ]
    )


async def require_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if user is None or context.bot is None:
        return False
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user.id)
    except TelegramError as exc:
        logger.warning("Could not verify channel membership for %s: %s", user.id, exc)
        await _safe_reply_text(
            update,
            "Membership verification is temporarily unavailable. Please try again shortly."
            if _is_english(update)
            else "Verifikasi keanggotaan sedang tidak tersedia. Silakan coba lagi beberapa saat.",
        )
        return False

    is_member = member.status in {"member", "administrator", "creator"}
    if member.status == "restricted":
        is_member = bool(getattr(member, "is_member", False))
    if is_member:
        return True

    await _safe_reply_text(
        update,
        (
            "*Join Required Channel*\n\nJoin our Telegram channel first, then press *Check Membership* to unlock the bot."
            if _is_english(update)
            else "*Wajib Join Channel*\n\nSilakan join channel Telegram terlebih dahulu, lalu tekan *Saya Sudah Join* untuk menggunakan bot."
        ),
        parse_mode="Markdown",
        reply_markup=_membership_keyboard(update),
    )
    return False


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False, refreshed: bool = False) -> None:
    _user_from_update(update)
    if _prodseller_configured():
        expires_at, cached = _prodseller_products_cache
        if not cached or time.time() >= expires_at:
            try:
                await _prodseller_products()
            except Exception as exc:
                logger.info("Could not fetch ProdSeller products in show_main_menu: %s", exc)
    menu_text = _main_menu_text(update, refreshed=refreshed)
    if edit and update.callback_query is not None:
        await _safe_edit_text(
            update, menu_text, parse_mode="Markdown", reply_markup=_main_menu_keyboard(update)
        )
    else:
        await _safe_reply_text(update, menu_text, parse_mode="Markdown", reply_markup=_main_menu_keyboard(update))


def _process_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or not context.args:
        return
    argument = context.args[0]
    if not argument.startswith("ref_"):
        return
    code = argument[4:].upper()
    with _db() as connection:
        owner = connection.execute("SELECT user_id FROM users WHERE referral_code = ?", (code,)).fetchone()
        if not owner or owner["user_id"] == user.id:
            return
        current = connection.execute("SELECT referred_by FROM users WHERE user_id = ?", (user.id,)).fetchone()
        should_reward = bool(current and current["referred_by"] is None)
        owner_id = owner["user_id"]
    if should_reward:
        reward = _setting("referral_reward", 2)
        with _db() as connection:
            connection.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (owner_id, user.id))
        _add_coins(owner_id, reward, "Referral reward")
        _add_coins(user.id, reward, "Referral welcome reward")


def _make_dashboard_text() -> str:
    return (
        "*Yowes Document Dashboard*\n\n"
        "Pilih salah satu opsi di bawah untuk membuat dokumen pengajar secara profesional dan terstruktur."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_channel_membership(update, context):
        return
    _process_referral(update, context)

    # Deep-linking support (e.g. from Web Store: /start buy_gemini or /start buy_ilovepdf)
    if context.args and len(context.args) > 0:
        arg = context.args[0]
        if arg.startswith("buy_") or arg.startswith("product_"):
            target_key = arg.split("_", 1)[1]
            if target_key in _PRODUCT_CATALOG or target_key in ("docs", "gemini"):
                await show_product(update, context, target_key)
                return

    await show_main_menu(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_channel_membership(update, context):
        return
    english = _is_english(update)
    contact_handle = SUPPORT_USERNAME
    if english:
        help_text = (
            "<b>📖 Service & Feature Guide</b>\n\n"
            "🎓 <b>Canva Doc Education:</b>\n"
            "• Select country & document type from the main menu.\n"
            "• Fill in profile details and confirm.\n"
            "• Documents generated instantly using coins (🪙).\n\n"
            "🛍️ <b>Digital Products:</b>\n"
            "• Available: Gemini Pro, CapCut Pro, Claude API, GPT Codex, Prime Video.\n"
            "• Instant payment via <b>QRIS</b> (IDR) & <b>Binance Pay</b> (USDT).\n"
            "• Automated delivery straight to your chat.\n\n"
            "✨ <b>Other Menus & Rewards:</b>\n"
            "• 🎁 <b>Daily Check-in:</b> Free bonus coins every 24 hours.\n"
            "• 🤝 <b>Referral Program:</b> Earn extra coins by inviting friends.\n"
            "• 🎟️ <b>Redeem Code:</b> Claim special promo voucher coins.\n"
            f"• 💬 <b>Customer Support:</b> Contact {contact_handle} for assistance."
        )
    else:
        help_text = (
            "<b>📖 Panduan Layanan & Fitur</b>\n\n"
            "🎓 <b>Canva Doc Education:</b>\n"
            "• Pilih negara & tipe dokumen di menu utama.\n"
            "• Lengkapi data profil lalu konfirmasi.\n"
            "• Dokumen dibuat instan menggunakan koin (🪙).\n\n"
            "🛍️ <b>Produk Digital:</b>\n"
            "• Tersedia: Gemini Pro, CapCut Pro, Claude API, GPT Codex, Prime Video.\n"
            "• Pembayaran otomatis via <b>QRIS</b> (Rupiah) & <b>Binance Pay</b> (USDT).\n"
            "• Akun/lisensi dikirim otomatis langsung ke chat bot.\n\n"
            "✨ <b>Menu & Fitur Lainnya:</b>\n"
            "• 🎁 <b>Check-in Harian:</b> Klaim koin gratis setiap hari.\n"
            "• 🤝 <b>Program Referral:</b> Ajak teman dan dapatkan bonus koin.\n"
            "• 🎟️ <b>Redeem Code:</b> Klaim kode voucher koin hadiah.\n"
            f"• 💬 <b>Bantuan Support:</b> Hubungi {contact_handle} untuk bantuan."
        )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏠 Menu Utama" if not english else "🏠 Main Menu", callback_data="menu:main"),
                InlineKeyboardButton("💬 Hubungi Support" if not english else "💬 Contact Support", url=SUPPORT_URL),
            ]
        ]
    )
    await _safe_reply_text(update, help_text, parse_mode="HTML", reply_markup=keyboard)


async def countries(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_channel_membership(update, context):
        return
    lines = []
    for code in list_countries():
        gen = get_country(code)()
        lines.append(f"• *{code.upper()}* — {gen.get_country_name()} ({', '.join(gen.get_document_types())})")
    title = "*Supported countries*" if _is_english(update) else "*Negara yang didukung*"
    await _safe_reply_text(update, title + "\n\n" + "\n".join(lines), parse_mode="Markdown")


async def show_coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = _user_from_update(update)
    if not user:
        return
    english = user["language"] == "en"
    text = (
        f"*My Coins*\n\nBalance: *{user['coins']} 🪙*\n\n"
        "💡 _Coins are exclusively used for creating Canva Education documents._\n"
        "Earn coins from daily check-ins, referrals, and redeem codes."
        if english
        else f"*Coin Saya*\n\nSaldo: *{user['coins']} 🪙*\n\n"
        "💡 _Koin khusus digunakan untuk pembuatan dokumen Canva Education._\n"
        "Dapatkan coin melalui check-in harian, referral, dan redeem code."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📜 Histori Koin" if not english else "📜 Coin History", callback_data="account:history"),
                InlineKeyboardButton("📦 Pesanan Saya" if not english else "📦 My Orders", callback_data="user:orders:0"),
            ],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main")],
        ]
    )
    await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=keyboard)


async def show_coin_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = _user_from_update(update)
    if not user:
        return
    history = _coin_history(user["user_id"])
    english = user["language"] == "en"
    title = "*Coin History*" if english else "*Histori Koin*"
    if not history:
        text = f"{title}\n\n" + ("No transactions yet." if english else "Belum ada transaksi koin.")
    else:
        lines = []
        for item in history:
            sign = "+" if item["amount"] > 0 else ""
            date = item["created_at"].replace("T", " ")[:16]
            lines.append(f"`{date}`  {sign}{item['amount']} 🪙  · {item['reason']}  · saldo {item['balance_after']}")
        text = f"{title}\n\n" + "\n".join(lines)
    await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=_back_keyboard("account:coins"))


async def show_user_orders(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    """Display product order history including licenses, keys, and activation links."""
    user = _user_from_update(update)
    if not user:
        return
    english = user["language"] == "en"
    page_size = 3
    offset = max(0, page) * page_size

    with _db() as connection:
        total_count = connection.execute(
            "SELECT COUNT(*) AS total FROM payment_requests WHERE user_id = ?",
            (user["user_id"],),
        ).fetchone()["total"]
        orders = connection.execute(
            "SELECT * FROM payment_requests WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (user["user_id"], page_size, offset),
        ).fetchall()

    total_pages = max(1, (total_count + page_size - 1) // page_size)
    current_page = max(0, min(page, total_pages - 1))

    if not orders:
        empty_text = (
            "<b>📦 Order History</b>\n\n"
            "You have no digital product purchase history yet.\n"
            "Please select a product from the main menu to make an order."
            if english else
            "<b>📦 Riwayat Pesanan Produk</b>\n\n"
            "Anda belum memiliki riwayat pembelian produk digital.\n"
            "Silakan pilih produk pada menu utama untuk melakukan pemesanan."
        )
        await _safe_edit_text(update, empty_text, parse_mode="HTML", reply_markup=_back_keyboard("menu:main"))
        return

    header = (
        f"<b>📦 Order History</b> (Page {current_page + 1}/{total_pages})\n\n"
        f"Total Orders: <b>{total_count}</b>\n"
        "────────────────────────\n"
        if english else
        f"<b>📦 Riwayat Pesanan Produk</b> (Halaman {current_page + 1}/{total_pages})\n\n"
        f"Total Pesanan: <b>{total_count}</b>\n"
        "────────────────────────\n"
    )

    blocks = []
    for ord_row in orders:
        pkey = ord_row["product_key"] if "product_key" in ord_row.keys() and ord_row["product_key"] else "gemini"
        if pkey in _PRODUCT_CATALOG:
            cfg = _PRODUCT_CATALOG[pkey]
            prod_label = f"{cfg['emoji']} {cfg['label_en'] if english else cfg['label_id']}"
        else:
            prod_label = "✨ Gemini Pro"

        status_raw = ord_row["status"]
        if status_raw == "approved":
            status_text = "✅ Approved / Delivered" if english else "✅ Sukses Terkirim"
        elif status_raw == "pending":
            status_text = "⏳ Pending Verification" if english else "⏳ Menunggu Verifikasi"
        elif status_raw == "provider_failed":
            status_text = "⚠️ Processing (Admin)" if english else "⚠️ Sedang Diproses Admin"
        elif status_raw == "cancelled":
            status_text = "❌ Cancelled" if english else "❌ Dibatalkan"
        elif status_raw == "expired":
            status_text = "⏱ Expired" if english else "⏱ Kedaluwarsa (Batal)"
        else:
            status_text = "❌ Rejected" if english else "❌ Ditolak"

        method_text = str(ord_row["method"]).upper()
        amount_text = ord_row["amount"] or "-"
        date_str = ord_row["created_at"].replace("T", " ")[:16]

        provider_order_id = ord_row["provider_order_id"] or "-"
        delivered = ord_row["delivered_data"] if "delivered_data" in ord_row.keys() and ord_row["delivered_data"] else ""

        block = (
            f"<b>{prod_label}</b>\n"
            f"• Date: <code>{date_str}</code>\n"
            f"• Method: <b>{method_text}</b> ({amount_text})\n"
            f"• Status: <b>{status_text}</b>\n"
            f"• Order ID: <code>{_safe_html(provider_order_id)}</code>\n"
            + (f"• <b>Access / License:</b>\n<code>{_safe_html(delivered)}</code>\n" if delivered else "")
        ) if english else (
            f"<b>{prod_label}</b>\n"
            f"• Tanggal: <code>{date_str}</code>\n"
            f"• Metode: <b>{method_text}</b> ({amount_text})\n"
            f"• Status: <b>{status_text}</b>\n"
            f"• Order ID: <code>{_safe_html(provider_order_id)}</code>\n"
            + (f"• <b>Akses / Lisensi:</b>\n<code>{_safe_html(delivered)}</code>\n" if delivered else "")
        )
        blocks.append(block)

    full_text = header + "\n────────────────────────\n".join(blocks)

    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev" if english else "⬅️ Sebelumnya", callback_data=f"user:orders:{current_page - 1}"))
    if current_page + 1 < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️" if english else "Berikutnya ➡️", callback_data=f"user:orders:{current_page + 1}"))

    keyboard_rows = []
    if nav_buttons:
        keyboard_rows.append(nav_buttons)
    keyboard_rows.append([InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu:main")])

    await _safe_edit_text(update, full_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard_rows))


async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = _user_from_update(update)
    if not user:
        return
    bot_username = context.bot.username or os.getenv("BOT_USERNAME", "your_bot")
    bot_username = bot_username.lstrip("@")
    link = f"https://t.me/{bot_username}?start=ref_{user['referral_code']}"
    reward = _setting("referral_reward", 2)
    text = (
        f"*Referral Program*\n\nYour link:\n`{link}`\n\nYou and your friend receive *{reward} 🪙* after the first join."
        if user["language"] == "en"
        else f"*Sistem Referral*\n\nLink Anda:\n`{link}`\n\nAnda dan teman Anda mendapatkan *{reward} 🪙* setelah teman bergabung."
    )
    await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=_back_keyboard())


async def daily_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = _user_from_update(update)
    if not user:
        return
    today = datetime.now().date().isoformat()
    reward = _setting("checkin_reward", 1)
    with _db() as connection:
        if user["last_checkin"] == today:
            message = "Check-in hari ini sudah dilakukan." if user["language"] != "en" else "Today's check-in is already completed."
            balance = user["coins"]
        else:
            connection.execute("UPDATE users SET last_checkin = ? WHERE user_id = ?", (today, user["user_id"]))
            balance = None
            message = f"Check-in berhasil. Anda mendapatkan {reward} 🪙." if user["language"] != "en" else f"Check-in complete. You received {reward} 🪙."
    if balance is None:
        balance = _add_coins(user["user_id"], reward, "Daily check-in")
    await _safe_edit_text(update, f"*🎁 Daily Check-in*\n\n{message}\nSaldo: *{balance} 🪙*", parse_mode="Markdown", reply_markup=_back_keyboard())


async def show_language_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _safe_edit_text(
        update,
        "*Language / Bahasa*\n\nPilih bahasa tampilan bot:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🇮🇩 Indonesia", callback_data="language:id")],
                [InlineKeyboardButton("🇬🇧 English", callback_data="language:en")],
                [InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main")],
            ]
        ),
    )


async def show_redeem_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["step"] = REDEEM_CODE
    await _safe_edit_text(
        update,
        "*Redeem Code*\n\nSend your redeem code in the next message." if _is_english(update) else "*Redeem Code*\n\nKirim kode redeem Anda melalui pesan berikutnya.",
        parse_mode="Markdown",
        reply_markup=_back_keyboard(),
    )


async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id if update.effective_user else None):
        await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard())
        return
    doc_p = _setting("doc_price", 3)
    checkin_r = _setting("checkin_reward", 1)
    ref_r = _setting("referral_reward", 2)
    gemini_p = _format_idr(_setting("gemini_price_idr", 20000))
    gemini_u = _setting_text("gemini_binance_price_usdt", "0.60")
    docs_act_tag = "🟢" if _is_product_active("docs") else "🔴"
    gem_act_tag = "🟢" if _is_product_active("gemini") else "🔴"
    prod_lines_en = [f"• {gem_act_tag} ✨ Gemini Pro: *{gemini_u} USDT* ({gemini_p})"]
    prod_lines_id = [f"• {gem_act_tag} ✨ Gemini Pro: *{gemini_p}* ({gemini_u} USDT)"]
    for c_key, c_cfg in _PRODUCT_CATALOG.items():
        p_idr, p_usdt = _get_catalog_product_price(c_key)
        p_idr_fmt = _format_idr(p_idr)
        act_tag = "🟢" if _is_product_active(c_key) else "🔴"
        prod_lines_en.append(f"• {act_tag} {c_cfg['emoji']} {c_cfg['label_en']}: *{p_usdt} USDT* ({p_idr_fmt})")
        prod_lines_id.append(f"• {act_tag} {c_cfg['emoji']} {c_cfg['label_id']}: *{p_idr_fmt}* ({p_usdt} USDT)")

    prod_text_en = "\n".join(prod_lines_en)
    prod_text_id = "\n".join(prod_lines_id)

    if _is_english(update):
        text = (
            f"*Admin Dashboard*\n\n"
            f"🎓 *Canva Education:* [{docs_act_tag}]\n"
            f"• Doc Price: *{doc_p} 🪙*\n"
            f"• Daily Check-in: *{checkin_r} 🪙*\n"
            f"• Referral Reward: *{ref_r} 🪙*\n\n"
            f"🛍️ *Digital Products (USDT / IDR) [🟢 Active / 🔴 Inactive]:*\n"
            f"{prod_text_en}"
        )
    else:
        text = (
            f"*Admin Dashboard*\n\n"
            f"🎓 *Canva Education:* [{docs_act_tag}]\n"
            f"• Harga Dokumen: *{doc_p} 🪙*\n"
            f"• Reward Check-in: *{checkin_r} 🪙*\n"
            f"• Reward Referral: *{ref_r} 🪙*\n\n"
            f"🛍️ *Harga Produk Digital (Rupiah / USDT) [🟢 Aktif / 🔴 Nonaktif]:*\n"
            f"{prod_text_id}"
        )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 Canva & Rewards" if _is_english(update) else "💰 Canva & Reward", callback_data="admin:prices"),
                InlineKeyboardButton("🏷️ Product Prices" if _is_english(update) else "🏷️ Harga Produk", callback_data="admin:product_prices"),
            ],
            [
                InlineKeyboardButton("📜 Trans History" if _is_english(update) else "📜 Histori Transaksi", callback_data="admin:tx_history"),
                InlineKeyboardButton("🎟️ Redeem Code" if _is_english(update) else "🎟️ Buat Redeem", callback_data="admin:redeem"),
            ],
            [
                InlineKeyboardButton("➕ Grant Coins" if _is_english(update) else "➕ Tambah Koin", callback_data="admin:addcoins"),
                InlineKeyboardButton("📦 Product Stock" if _is_english(update) else "📦 Stok Produk", callback_data="admin:stock"),
            ],
            [
                InlineKeyboardButton("ℹ️ Product Info" if _is_english(update) else "ℹ️ Info Produk", callback_data="admin:info"),
                InlineKeyboardButton("📢 Broadcast" if _is_english(update) else "📢 Broadcast", callback_data="admin:broadcast"),
            ],
            [
                InlineKeyboardButton("💳 Provider Balance" if _is_english(update) else "💳 Saldo Provider", callback_data="admin:provider_balance"),
                InlineKeyboardButton("🎛️ Status Produk" if _is_english(update) else "🎛️ Status Produk", callback_data="admin:visibility"),
            ],
            [
                InlineKeyboardButton("⬅️ Back" if _is_english(update) else "⬅️ Kembali", callback_data="menu:main"),
            ],
        ]
    )
    await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=keyboard)


async def show_admin_transaction_history(
    update: Update, context: ContextTypes.DEFAULT_TYPE, tab: str = "payments", page: int = 0
) -> None:
    if not _is_admin(update.effective_user.id if update.effective_user else None):
        await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard())
        return
    english = _is_english(update)
    limit = 6
    page = max(0, page)

    with _db() as connection:
        if tab == "coins":
            total_count = connection.execute("SELECT COUNT(*) as c FROM coin_transactions").fetchone()["c"]
            total_pages = max(1, (total_count + limit - 1) // limit)
            page = min(page, total_pages - 1)
            offset = page * limit
            rows = connection.execute(
                """
                SELECT c.*, u.username
                FROM coin_transactions c
                LEFT JOIN users u ON c.user_id = u.user_id
                ORDER BY c.id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

            header = (
                f"<b>📜 Coin Transaction History</b>\n"
                f"Total: <b>{total_count}</b> transactions · Page <b>{page + 1}/{total_pages}</b>\n\n"
                if english else
                f"<b>📜 Histori Transaksi Koin</b>\n"
                f"Total: <b>{total_count}</b> transaksi · Halaman <b>{page + 1}/{total_pages}</b>\n\n"
            )
            if not rows:
                content = "<i>No coin transactions recorded yet.</i>" if english else "<i>Belum ada transaksi koin yang tercatat.</i>"
            else:
                lines = []
                for r in rows:
                    sign = "+" if r["amount"] > 0 else ""
                    dt = str(r["created_at"]).replace("T", " ")[:16]
                    uname = f"@{r['username']}" if r["username"] else f"ID: {r['user_id']}"
                    lines.append(
                        f"• <b>#{r['id']}</b> · <code>{_safe_html(uname)}</code>\n"
                        f"  <b>{sign}{r['amount']} 🪙</b> (Saldo: {r['balance_after']} 🪙)\n"
                        f"  <i>{_safe_html(r['reason'])}</i> · <code>{dt}</code>"
                    )
                content = "\n\n".join(lines)
            text = header + content

        else:
            tab = "payments"
            total_count = connection.execute("SELECT COUNT(*) as c FROM payment_requests").fetchone()["c"]
            approved_count = connection.execute("SELECT COUNT(*) as c FROM payment_requests WHERE status = 'approved'").fetchone()["c"]
            pending_count = connection.execute("SELECT COUNT(*) as c FROM payment_requests WHERE status = 'pending'").fetchone()["c"]
            rejected_count = connection.execute("SELECT COUNT(*) as c FROM payment_requests WHERE status = 'rejected'").fetchone()["c"]
            total_pages = max(1, (total_count + limit - 1) // limit)
            page = min(page, total_pages - 1)
            offset = page * limit
            rows = connection.execute(
                """
                SELECT p.*, u.username
                FROM payment_requests p
                LEFT JOIN users u ON p.user_id = u.user_id
                ORDER BY p.id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

            header = (
                f"<b>📜 Payment Requests History</b>\n"
                f"Total: <b>{total_count}</b> (✅ {approved_count} · ⏳ {pending_count} · ❌ {rejected_count})\n"
                f"Page <b>{page + 1}/{total_pages}</b>\n\n"
                if english else
                f"<b>📜 Histori Pembayaran Produk</b>\n"
                f"Total: <b>{total_count}</b> (✅ {approved_count} · ⏳ {pending_count} · ❌ {rejected_count})\n"
                f"Halaman <b>{page + 1}/{total_pages}</b>\n\n"
            )
            if not rows:
                content = "<i>No payment requests recorded yet.</i>" if english else "<i>Belum ada permintaan pembayaran.</i>"
            else:
                lines = []
                for r in rows:
                    st = r["status"]
                    st_icon = "✅" if st == "approved" else ("⏳" if st == "pending" else ("❌" if st == "rejected" else "⚠️"))
                    dt = str(r["created_at"]).replace("T", " ")[:16]
                    uname = f"@{r['username']}" if r["username"] else f"ID: {r['user_id']}"
                    pkey = r["product_key"] if "product_key" in r.keys() and r["product_key"] else "gemini"
                    if pkey in _PRODUCT_CATALOG:
                        cfg = _PRODUCT_CATALOG[pkey]
                        prod_label = f"{cfg['emoji']} {cfg['label_en' if english else 'label_id']}"
                    else:
                        prod_label = "✨ Gemini Pro"
                    method_str = str(r["method"]).upper()
                    prov_order = f"\n  Order: <code>{_safe_html(r['provider_order_id'])}</code>" if r["provider_order_id"] else ""
                    lines.append(
                        f"• <b>#{r['id']}</b> · {prod_label} ({st_icon} <b>{st.capitalize()}</b>)\n"
                        f"  User: <code>{_safe_html(uname)}</code> · {method_str} <b>{_safe_html(r['amount'])}</b>\n"
                        f"  Waktu: <code>{dt}</code>{prov_order}"
                    )
                content = "\n\n".join(lines)
            text = header + content

    btn_payments = ("💳 Payments •" if tab == "payments" else "💳 Payments") if english else ("💳 Pembayaran •" if tab == "payments" else "💳 Pembayaran")
    btn_coins = ("🪙 Coins •" if tab == "coins" else "🪙 Coins") if english else ("🪙 Koin •" if tab == "coins" else "🪙 Koin")
    tab_row = [
        InlineKeyboardButton(btn_payments, callback_data="admin:tx:payments:0"),
        InlineKeyboardButton(btn_coins, callback_data="admin:tx:coins:0"),
    ]

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin:tx:{tab}:{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"🔄 {page + 1}/{total_pages}", callback_data=f"admin:tx:{tab}:{page}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin:tx:{tab}:{page + 1}"))

    back_row = [InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="admin:menu")]

    keyboard = InlineKeyboardMarkup([tab_row, nav_row, back_row])
    await _safe_edit_text(update, text, parse_mode="HTML", reply_markup=keyboard)


async def show_provider_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id if update.effective_user else None):
        await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
        return
    try:
        balance = await asyncio.to_thread(_prodseller_request_sync, "GET", "/balance")
        text = (
            f"*Provider Balance*\n\nBalance: *{balance.get('balance', '-')} USDT*\nMembership: *{balance.get('membership', '-')}*"
            if _is_english(update)
            else f"*Saldo Provider*\n\nSaldo: *{balance.get('balance', '-')} USDT*\nMembership: *{balance.get('membership', '-')}*"
        )
    except ProdSellerError:
        text = "Provider balance is unavailable. Check PRODSELLER_API_KEY." if _is_english(update) else "Saldo provider tidak tersedia. Periksa PRODSELLER_API_KEY."
    await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=_back_keyboard("admin:menu"))


async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE, product: str) -> None:
    if not _is_product_active(product) and not _is_admin(update.effective_user.id if update.effective_user else None):
        msg = (
            "This product is currently disabled or unavailable."
            if _is_english(update) else
            "Produk ini sedang dinonaktifkan atau tidak tersedia. Silakan pilih produk lainnya."
        )
        await _safe_edit_text(update, msg, reply_markup=_back_keyboard("menu:main"))
        return

    if product == "docs":
        context.user_data["product"] = "docs"
        await start_wizard(update, context, edit=True)
        return
    if product in _PRODUCT_CATALOG:
        await _show_catalog_product(update, context, product)
        return
    customer_price_idr = _setting("gemini_price_idr", 20000)
    customer_price_usdt = _setting_text("gemini_binance_price_usdt", "0.60")
    english = _language(update) == "en"
    gemini_info = _setting_text("gemini_info", "").strip()
    if gemini_info:
        info_content = _safe_html(gemini_info)
    else:
        info_content = _GEMINI_DEFAULT_INFO_EN if english else _GEMINI_DEFAULT_INFO_ID

    if not _prodseller_configured():
        stock = max(_gemini_stock_count(), _setting("gemini_manual_stock", 0))
        if stock > 0:
            stock_label = f"🟢 Tersedia ({stock} unit)" if not english else f"🟢 In Stock ({stock} units)"
        else:
            stock_label = "🔴 Stok Habis" if not english else "🔴 Out of Stock"
        text = f"{info_content}\n\n📦 <b>{'Stock' if english else 'Stok'}:</b> {stock_label}"
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🛒 Buy Gemini Pro" if english else "🛒 Beli Gemini Pro", callback_data="gemini:buy")],
                [InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="menu:main")],
            ]
        )
        await _safe_edit_text(update, text, parse_mode="HTML", reply_markup=keyboard)
        return
    try:
        provider_product = await _find_gemini_product()
    except ProdSellerError as exc:
        await _safe_edit_text(
            update,
            "Gemini Pro is temporarily unavailable. Please contact admin." if english else "Gemini Pro sedang tidak tersedia. Silakan hubungi admin.",
            reply_markup=_back_keyboard(),
        )
        logger.info("Gemini product unavailable: %s", exc)
        return
    provider_stock = provider_product.get("stock")
    if provider_product.get("inStock") is False or provider_stock == 0:
        stock_label = "🔴 Stok Habis" if not english else "🔴 Out of Stock"
    else:
        stock_label = f"🟢 Tersedia ({provider_stock} unit)" if provider_stock is not None else ("🟢 In Stock" if english else "🟢 Tersedia")
    text = f"{info_content}\n\n📦 <b>{'Stock' if english else 'Stok'}:</b> {stock_label}"
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛒 Buy Gemini Pro" if english else "🛒 Beli Gemini Pro", callback_data="gemini:buy")],
            [InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="menu:main")],
        ]
    )
    context.user_data["gemini_product_id"] = provider_product.get("id")
    await _safe_edit_text(update, text, parse_mode="HTML", reply_markup=keyboard)


async def show_gemini_payment_methods(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    english = _is_english(update)
    binance_price = _setting_text("gemini_binance_price_usdt", "0.60")
    qris_price = _format_idr(_setting("gemini_qris_price_idr", 20000))
    text = (
        "<b>Choose payment method</b>\n\nSelect Binance USDT or QRIS. Your order is processed after admin verification."
        if english
        else "<b>Pilih metode pembayaran</b>\n\nPilih Binance USDT atau QRIS. Pesanan diproses setelah diverifikasi admin."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"💳 Binance · {binance_price} USDT", callback_data="gemini:pay:binance")],
            [InlineKeyboardButton(f"📱 QRIS · {qris_price}", callback_data="gemini:pay:qris")],
            [InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="product:gemini")],
        ]
    )
    await _safe_edit_text(update, text, parse_mode="HTML", reply_markup=keyboard)


async def show_payment_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str) -> None:
    english = _is_english(update)
    context.user_data["payment_method"] = method
    context.user_data["step"] = f"gemini_payment_{method}"
    if method == "binance":
        account = os.getenv("BINANCE_ACCOUNT_ID", "").strip() or os.getenv("BINANCE_PAYMENT_ADDRESS", "").strip()
        network = os.getenv("BINANCE_NETWORK", "").strip()
        if not account or account.startswith("your_"):
            await _safe_edit_text(
                update,
                "Binance account payment is not configured. Please contact admin." if english else "Akun pembayaran Binance belum dikonfigurasi. Silakan hubungi admin.",
                reply_markup=_back_keyboard("gemini:buy"),
            )
            return
        network_line = f"\nNetwork: <b>{_safe_html(network)}</b>" if network else ""
        binance_price = _setting_text("gemini_binance_price_usdt", "0.60")
        text = (
            f"<b>Direct Binance Transfer</b>\n\nAmount: <b>{_safe_html(binance_price)} USDT</b>\nBinance account:\n<code>{_safe_html(account)}</code>{network_line}\n\nTransfer USDT directly to this admin Binance account, then send the transaction ID/hash."
            if english
            else f"<b>Transfer Langsung Binance</b>\n\nJumlah: <b>{_safe_html(binance_price)} USDT</b>\nAkun Binance admin:\n<code>{_safe_html(account)}</code>{network_line}\n\nTransfer USDT langsung ke akun Binance admin ini, lalu kirim TXID/hash transaksi."
        )
    else:
        raw_price = _setting("gemini_qris_price_idr", 20000)
        label = "✨ Gemini Pro"
        if await _show_dynamic_qris_instruction(
            update=update,
            context=context,
            product_key="gemini",
            base_price=raw_price,
            product_label=label,
            back_callback="gemini:payment_methods",
        ):
            return

        note = os.getenv("QRIS_PAYMENT_NOTE", "Scan QRIS and send the transaction reference or screenshot.").strip()
        qris_price = _format_idr(raw_price)
        text = (
            f"<b>QRIS Payment</b>\n\nAmount: <b>{qris_price}</b>\n{_safe_html(note)}\n\nAfter payment, send the transaction reference or screenshot."
            if english
            else f"<b>Pembayaran QRIS</b>\n\nJumlah: <b>{qris_price}</b>\n{_safe_html(note)}\n\nSetelah membayar, kirim referensi transaksi atau screenshot."
        )
        qris_url = os.getenv("QRIS_IMAGE_URL", "").strip()
        qris_path = Path(os.getenv("QRIS_IMAGE_PATH", "QRIS-YOWES-DIGITAL-PRO.jpeg"))
        if not qris_path.is_absolute():
            qris_path = BASE_DIR / qris_path
        if qris_path.exists() and update.effective_chat and context.bot:
            payment_buttons = [
                [
                    InlineKeyboardButton("❌ Cancel Order" if english else "❌ Batalkan Pesanan", callback_data="payment:cancel_current"),
                    InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="gemini:payment_methods"),
                ]
            ]
            try:
                if update.callback_query and update.callback_query.message:
                    await update.callback_query.message.delete()
                with qris_path.open("rb") as qris_file:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=qris_file,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(payment_buttons),
                    )
                return
            except TelegramError as exc:
                logger.warning("Could not send local QRIS image: %s", exc)
    payment_buttons = []
    if method == "qris" and qris_url:
        payment_buttons.append([InlineKeyboardButton("📱 Open QRIS", url=qris_url)])
    payment_buttons.append([
        InlineKeyboardButton("❌ Cancel Order" if english else "❌ Batalkan Pesanan", callback_data="payment:cancel_current"),
        InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="gemini:payment_methods"),
    ])
    await _safe_edit_text(update, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(payment_buttons))


async def _notify_payment_admins(context: ContextTypes.DEFAULT_TYPE, payment_id: int) -> None:
    with _db() as connection:
        payment = connection.execute(
            "SELECT p.*, u.username FROM payment_requests p LEFT JOIN users u ON u.user_id = p.user_id WHERE p.id = ?",
            (payment_id,),
        ).fetchone()
    if not payment:
        return
    # Resolve a human-readable product label for the admin notification
    pkey = payment["product_key"] if "product_key" in payment.keys() else "gemini"
    if pkey in _PRODUCT_CATALOG:
        cfg = _PRODUCT_CATALOG[pkey]
        product_label = f"{cfg['emoji']} {cfg['label_en']}"
    else:
        product_label = "✨ Gemini Pro"
    admin_keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Verify", callback_data=f"payment:approve:{payment_id}"),
            InlineKeyboardButton("❌ Reject",  callback_data=f"payment:reject:{payment_id}"),
        ]]
    )
    message = (
        f"<b>💳 Payment Verification</b>\n\n"
        f"ID: <code>#{payment_id}</code>\n"
        f"Product: <b>{product_label}</b>\n"
        f"User: <code>{payment['user_id']}</code> @{_safe_html(payment['username'] or '-')}\n"
        f"Method: <b>{_safe_html(payment['method'])}</b>\n"
        f"Amount: <b>{_safe_html(payment['amount'])}</b>\n"
        f"Reference: <code>{_safe_html(payment['reference'])}</code>\n"
        f"Email: {_safe_html(payment['email'] or '-')}"
    )
    for admin_id in _admin_ids():
        try:
            await context.bot.send_message(chat_id=admin_id, text=message, parse_mode="HTML", reply_markup=admin_keyboard)
            if payment["evidence_file_id"]:
                await context.bot.send_photo(chat_id=admin_id, photo=payment["evidence_file_id"], caption=f"Payment evidence #{payment_id}")
        except TelegramError as exc:
            logger.info("Could not notify admin %s for payment %s: %s", admin_id, payment_id, exc)


async def _create_payment_request(update: Update, context: ContextTypes.DEFAULT_TYPE, reference: str, evidence_file_id: str | None = None) -> None:
    user = _user_from_update(update)
    if not user:
        return
    method = context.user_data.get("payment_method")
    if method not in {"binance", "qris"}:
        await _present_text(update, "Pilih metode pembayaran terlebih dahulu.", reply_markup=_back_keyboard("gemini:payment_methods"))
        return
    amount = _setting_text("gemini_binance_price_usdt", "0.60") + " USDT" if method == "binance" else _format_idr(_setting("gemini_qris_price_idr", 20000))
    with _db() as connection:
        cursor = connection.execute(
            "INSERT INTO payment_requests(user_id, method, amount, reference, evidence_file_id, email, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user["user_id"], method, amount, reference[:500], evidence_file_id, context.user_data.get("gemini_email"), datetime.now().isoformat()),
        )
        payment_id = cursor.lastrowid
    await _notify_payment_admins(context, payment_id)
    context.user_data.pop("step", None)
    message = (
        f"<b>Payment submitted</b>\n\nRequest: <code>#{payment_id}</code>\nYour payment is waiting for admin verification."
        if _is_english(update)
        else f"<b>Pembayaran terkirim</b>\n\nRequest: <code>#{payment_id}</code>\nPembayaran sedang menunggu verifikasi admin."
    )
    sent_message = await _present_text(update, message, parse_mode="HTML", reply_markup=_back_keyboard("product:gemini"))
    if sent_message and getattr(sent_message, "chat_id", None) and getattr(sent_message, "message_id", None):
        with _db() as connection:
            connection.execute(
                "UPDATE payment_requests SET user_chat_id = ?, user_message_id = ? WHERE id = ?",
                (sent_message.chat_id, sent_message.message_id, payment_id),
            )


async def _update_user_payment_message(
    context: ContextTypes.DEFAULT_TYPE | Any,
    payment: sqlite3.Row,
    text: str,
    reply_markup=None,
) -> None:
    chat_id = payment["user_chat_id"]
    message_id = payment["user_message_id"]
    if chat_id and message_id:
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            return
        except TelegramError:
            pass
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            return
        except TelegramError as exc:
            logger.info("Could not edit payment message %s: %s", payment["id"], exc)
    try:
        await context.bot.send_message(chat_id=payment["user_id"], text=text, parse_mode="HTML", reply_markup=reply_markup)
    except TelegramError as exc:
        logger.warning("Could not send payment delivery message to user %s: %s", payment["user_id"], exc)


def _extract_order_delivery(order: dict) -> tuple[str, str | None]:
    """Extract delivered credentials/access text and optional file/download URL from an order payload."""
    delivered_parts: list[str] = []
    file_url: str | None = None

    for fk in ("fileUrl", "file_url", "downloadUrl", "download_url", "file", "attachmentUrl"):
        val = order.get(fk)
        if isinstance(val, str) and (val.startswith("http://") or val.startswith("https://")):
            file_url = val
            break

    dkey = order.get("deliveredKey")
    if dkey:
        if isinstance(dkey, str) and dkey.strip():
            delivered_parts.append(dkey.strip())
        elif isinstance(dkey, list):
            delivered_parts.extend([str(k).strip() for k in dkey if str(k).strip()])
        elif isinstance(dkey, dict):
            for k, v in dkey.items():
                delivered_parts.append(f"{k}: {v}")

    dkeys = order.get("deliveredKeys")
    if isinstance(dkeys, list):
        for k in dkeys:
            if isinstance(k, str) and k.strip() and k.strip() not in delivered_parts:
                delivered_parts.append(k.strip())
            elif isinstance(k, dict):
                formatted = "\n".join(f"{dk}: {dv}" for dk, dv in k.items())
                if formatted not in delivered_parts:
                    delivered_parts.append(formatted)

    raw_keys = order.get("keys")
    if isinstance(raw_keys, list):
        for k in raw_keys:
            if isinstance(k, str) and k.strip() and k.strip() not in delivered_parts:
                delivered_parts.append(k.strip())

    for field in ("account", "credentials", "license", "licenseKey", "data", "deliveredData"):
        val = order.get(field)
        if not val:
            continue
        if isinstance(val, str) and val.strip() and val.strip() not in delivered_parts:
            if (val.startswith("http://") or val.startswith("https://")) and any(val.lower().endswith(ext) for ext in (".txt", ".pdf", ".zip", ".json")):
                if not file_url:
                    file_url = val
            delivered_parts.append(val.strip())
        elif isinstance(val, dict):
            formatted = "\n".join(f"{k}: {v}" for k, v in val.items())
            if formatted not in delivered_parts:
                delivered_parts.append(formatted)
        elif isinstance(val, list):
            for item in val:
                s = str(item).strip()
                if s and s not in delivered_parts:
                    delivered_parts.append(s)

    delivered_text = "\n".join(delivered_parts).strip()
    return delivered_text, file_url


async def _fulfill_payment_request(context: ContextTypes.DEFAULT_TYPE | Any, payment_id: int) -> tuple[bool, str]:
    """Execute product delivery for an approved/verified payment request."""
    bot = getattr(context, "bot", context)
    with _db() as connection:
        row = connection.execute("SELECT * FROM payment_requests WHERE id = ?", (payment_id,)).fetchone()
        if not row:
            return False, "Payment not found"
        payment = dict(row)
        # If already approved AND already has delivered credentials, prevent duplicate charges/orders
        if payment.get("status") == "approved" and payment.get("delivered_data"):
            return True, "Already approved"

    pkey = payment.get("product_key") or "gemini"
    user_id = payment["user_id"]
    delivered = ""
    file_url = None
    order: dict = {}
    provider_order_id = ""

    try:
        if pkey in _PRODUCT_CATALOG:
            cfg = _PRODUCT_CATALOG[pkey]
            product_label = f"{cfg['emoji']} {cfg['label_en']}"
            product = await _find_catalog_product(pkey)
            order = await _create_catalog_order(user_id, pkey, product, payment.get("email"), charge_coins=False)
            delivered, file_url = _extract_order_delivery(order)
            provider_order_id = str(order.get("orderId") or f"ORD-{payment_id}")
        else:
            product_label = "✨ Gemini Pro"
            order_fulfilled = False

            # 1. Try ProdSeller if configured and inStock
            if _prodseller_configured():
                try:
                    product = await _find_gemini_product()
                    if product.get("inStock") is not False:
                        order = await _create_gemini_order(user_id, product, payment.get("email"), charge_coins=False)
                        delivered, file_url = _extract_order_delivery(order)
                        if delivered:
                            order_fulfilled = True
                            provider_order_id = str(order.get("orderId") or f"GEMINI-{payment_id}")
                except Exception as exc:
                    logger.warning("ProdSeller Gemini order attempt failed: %s; falling back to local stock", exc)

            # 2. Seamless fallback to local gemini_stock in SQLite
            if not order_fulfilled:
                with _db() as connection:
                    row = connection.execute(
                        "SELECT id, link, description FROM gemini_stock WHERE active = 1 ORDER BY id ASC LIMIT 1"
                    ).fetchone()
                    if row:
                        connection.execute("UPDATE gemini_stock SET active = 0 WHERE id = ?", (row["id"],))
                        delivered = str(row["link"] or "").strip()
                        provider_order_id = f"LOCAL-GEMINI-{payment_id}-{row['id']}"
                        order = {
                            "orderId": provider_order_id,
                            "status": "completed",
                            "deliveredKey": delivered,
                        }
                        order_fulfilled = True
                    else:
                        provider_order_id = f"MANUAL-{payment_id}"
                        order = {"orderId": provider_order_id, "status": "pending_stock"}

            if not delivered and not order_fulfilled:
                raise ProdSellerError("Semua stok Gemini Pro (online & lokal) sedang kosong. Admin akan segera memproses.")

        # Save fulfilled delivery to database
        with _db() as connection:
            connection.execute(
                """
                UPDATE payment_requests
                SET status = 'approved',
                    provider_order_id = ?,
                    delivered_data = ?,
                    reviewed_at = ?
                WHERE id = ?
                """,
                (provider_order_id, delivered, datetime.now().isoformat(), payment_id),
            )

        finish_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Riwayat Pesanan", callback_data="user:orders:0")],
            [InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu:main")],
        ])

        # Step A: Update payment banner concisely (under 1024 chars, safe for photo caption)
        qris_caption = (
            f"<b>✅ Pembayaran QRIS Berhasil Diverifikasi!</b>\n\n"
            f"Pesanan: <b>{product_label}</b>\n"
            f"Order ID: <code>{_safe_html(provider_order_id)}</code>\n"
            f"Status: <b>✅ Sukses Terkirim</b>\n\n"
            f"<i>👇 Detail akun & file lisensi pesanan Anda telah dikirimkan di bawah ini.</i>"
        )
        await _update_user_payment_message(context, payment, qris_caption, finish_keyboard)

        # Step B: Send dedicated copyable credential message to buyer
        if delivered:
            delivery_msg = (
                f"<b>🎉 Pesanan Anda Berhasil Dikirim!</b>\n\n"
                f"📦 Produk: <b>{product_label}</b>\n"
                f"🆔 Order ID: <code>{_safe_html(provider_order_id)}</code>\n"
                f"────────────────────────\n"
                f"🔑 <b>Data Akun / Akses Lisensi:</b>\n"
                f"<code>{_safe_html(delivered)}</code>\n"
                f"────────────────────────\n"
                f"💡 <i>Tip: Tap / klik pada kotak teks di atas untuk menyalin akun / lisensi secara instan.</i>\n\n"
                f"📄 <i>File data akun (.txt) juga kami lampirkan di bawah ini untuk backup Anda.</i>"
            )
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=delivery_msg,
                    parse_mode="HTML",
                )
            except TelegramError as exc:
                logger.warning("Could not send delivery text message to %s: %s", user_id, exc)

            # Step C: Send .txt document attachment with credentials
            safe_slug = re.sub(r"[^A-Za-z0-9_-]", "_", pkey).strip("_")
            filename = f"{safe_slug}_order_{payment_id}.txt"
            file_body = (
                f"====================================================\n"
                f"       YOWES DIGITAL PRO - ORDER DELIVERY DATA      \n"
                f"====================================================\n"
                f"Product  : {product_label}\n"
                f"Order ID : {provider_order_id}\n"
                f"Payment  : #{payment_id} ({payment.get('amount', '-')})\n"
                f"Date     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"====================================================\n\n"
                f"ACCOUNT / ACCESS / LICENSE DETAILS:\n"
                f"----------------------------------------------------\n"
                f"{delivered}\n"
                f"----------------------------------------------------\n\n"
                f"IMPORTANT NOTES:\n"
                f"1. Simpan data ini baik-baik dan jangan bagikan kepada siapapun.\n"
                f"2. Jika membutuhkan bantuan atau kendala garansi, hubungi:\n"
                f"   Telegram: {SUPPORT_USERNAME} ({SUPPORT_URL})\n"
                f"====================================================\n"
            )
            try:
                bio = io.BytesIO(file_body.encode("utf-8"))
                bio.name = filename
                await bot.send_document(
                    chat_id=user_id,
                    document=bio,
                    filename=filename,
                    caption=f"📄 <b>File Lisensi & Akun</b> — {product_label}\nSimpan file ini sebagai arsip pesanan Anda.",
                    parse_mode="HTML",
                )
            except TelegramError as exc:
                logger.warning("Could not send delivery txt document to %s: %s", user_id, exc)

            # Step D: If provider returned an external file/guide URL, deliver it too!
            if file_url:
                try:
                    download_kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬇️ Unduh File / Dokumen", url=file_url)]
                    ])
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"📁 <b>File Tambahan / Panduan Pesanan</b>\n\nProvider menyertakan file unduhan untuk produk ini:\n<code>{_safe_html(file_url)}</code>",
                        parse_mode="HTML",
                        reply_markup=download_kb,
                    )
                except TelegramError as exc:
                    logger.warning("Could not send attached file info to %s: %s", user_id, exc)

        return True, "Success"

    except (ProdSellerError, Exception) as exc:
        logger.error("Error fulfilling payment #%s for product %s: %s", payment_id, pkey, exc)
        with _db() as connection:
            connection.execute("UPDATE payment_requests SET status = 'provider_failed' WHERE id = ?", (payment_id,))
        err_msg = (
            "<b>Pembayaran terverifikasi</b>\n\n"
            "Namun pengiriman produk sedang diproses secara manual oleh admin. Kami akan segera menghubungi atau mengirimkannya."
        )
        await _update_user_payment_message(context, payment, err_msg, _back_keyboard("menu:main"))
        return False, str(exc)


async def _notify_admins_auto_paid(
    context: ContextTypes.DEFAULT_TYPE | Any,
    payment_id: int,
    amount: int,
) -> None:
    """Notify all admins that a dynamic ShopeePay QRIS was automatically verified and settled."""
    with _db() as connection:
        payment = connection.execute(
            "SELECT p.*, u.username FROM payment_requests p LEFT JOIN users u ON u.user_id = p.user_id WHERE p.id = ?",
            (payment_id,),
        ).fetchone()
    if not payment:
        return
    pkey = payment["product_key"] if "product_key" in payment.keys() else "gemini"
    if pkey in _PRODUCT_CATALOG:
        cfg = _PRODUCT_CATALOG[pkey]
        product_label = f"{cfg['emoji']} {cfg['label_en']}"
    else:
        product_label = "✨ Gemini Pro"

    message = (
        f"<b>⚡ Auto-Settled QRIS ShopeePay</b>\n\n"
        f"ID: <code>#{payment_id}</code>\n"
        f"Produk: <b>{product_label}</b>\n"
        f"User: <code>{payment['user_id']}</code> @{_safe_html(payment['username'] or '-')}\n"
        f"Nominal: <b>{_format_idr(amount)}</b>\n"
        f"Status: <b>✅ Sukses Terverifikasi Otomatis</b>"
    )
    for admin_id in _admin_ids():
        try:
            await context.bot.send_message(chat_id=admin_id, text=message, parse_mode="HTML")
        except TelegramError as exc:
            logger.info("Could not notify admin %s of auto payment: %s", admin_id, exc)


def _get_settled_shopee_tx_ids() -> set[str]:
    """Retrieve all ShopeePay transaction IDs that have already been settled/consumed."""
    tx_ids: set[str] = set()
    try:
        with _db() as connection:
            rows = connection.execute(
                """
                SELECT transaction_id FROM settled_shopee_transactions WHERE transaction_id IS NOT NULL AND transaction_id != ''
                UNION
                SELECT shopee_tx_id FROM payment_requests WHERE shopee_tx_id IS NOT NULL AND shopee_tx_id != ''
                """
            ).fetchall()
            for r in rows:
                if r[0]:
                    tx_ids.add(str(r[0]).strip())
    except Exception as exc:
        logger.warning("Error fetching settled ShopeePay transaction IDs: %s", exc)
    return tx_ids


def _find_matching_shopee_tx(
    payment: dict,
    recent_txs: list[dict],
    settled_tx_ids: set[str],
) -> dict | None:
    """Find a valid, unconsumed ShopeePay transaction matching the specific payment request.

    Guarantees:
    - Amount matches exact integer value
    - Status is completed / success (status 3)
    - Transaction ID has never been settled previously
    - Transaction timestamp occurred strictly within the payment's active lifecycle (created_at - 45s .. created_at + 17m)
    """
    target_amount = payment.get("raw_amount") or 0
    if target_amount <= 0:
        return None

    try:
        created_dt = datetime.fromisoformat(payment["created_at"])
        payment_ts = int(created_dt.timestamp())
    except Exception:
        payment_ts = 0

    # 45s clock skew tolerance before payment created
    min_tx_time = payment_ts - 45 if payment_ts > 0 else 0
    # 17 minutes maximum validity after payment created
    max_tx_time = payment_ts + 1020 if payment_ts > 0 else int(time.time()) + 3600

    for tx in recent_txs:
        tx_id = str(tx.get("id") or tx.get("transactionId") or tx.get("raw", {}).get("transactionId") or "").strip()
        if not tx_id or tx_id in settled_tx_ids:
            continue

        tx_amount = shopeepay_engine.parse_shopee_amount(tx.get("amount", 0))
        if tx_amount != target_amount:
            continue

        tx_status = tx.get("status")
        # Status 3 represents COMPLETED_STATUS
        if tx_status not in (3, "3", "SUCCESS", "COMPLETED"):
            continue

        tx_time = int(tx.get("create_time") or tx.get("raw", {}).get("createTime") or 0)
        # Verify transaction time falls within this payment's creation and expiration window
        if payment_ts > 0 and (tx_time < min_tx_time or tx_time > max_tx_time):
            continue

        return tx

    return None


def _claim_and_record_settlement(payment_id: int, tx: dict) -> bool:
    """Atomically record ShopeePay transaction claim for a payment request to prevent double-spending."""
    tx_id = str(tx.get("id") or tx.get("transactionId") or tx.get("raw", {}).get("transactionId") or "").strip()
    if not tx_id:
        return False
    tx_amount = shopeepay_engine.parse_shopee_amount(tx.get("amount", 0))
    tx_time = int(tx.get("create_time") or tx.get("raw", {}).get("createTime") or 0)

    with _db() as connection:
        row = connection.execute("SELECT status FROM payment_requests WHERE id = ?", (payment_id,)).fetchone()
        if not row or row["status"] != "pending":
            return False

        existing = connection.execute(
            "SELECT 1 FROM settled_shopee_transactions WHERE transaction_id = ?", (tx_id,)
        ).fetchone()
        if existing:
            return False

        try:
            connection.execute(
                """
                INSERT INTO settled_shopee_transactions (transaction_id, payment_id, amount, tx_time, settled_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tx_id, payment_id, tx_amount, tx_time, datetime.now().isoformat()),
            )
            connection.execute(
                """
                UPDATE payment_requests
                SET auto_settled = 1,
                    shopee_tx_id = ?
                WHERE id = ? AND status = 'pending'
                """,
                (tx_id, payment_id),
            )
            return True
        except sqlite3.IntegrityError:
            return False


async def _check_and_settle_qris_payment(
    context: ContextTypes.DEFAULT_TYPE | Any,
    payment_id: int,
) -> tuple[bool, str]:
    """Check ShopeePay mutations for a specific pending dynamic QRIS payment and fulfill if matched."""
    with _db() as connection:
        row = connection.execute(
            "SELECT * FROM payment_requests WHERE id = ?", (payment_id,)
        ).fetchone()
    if not row:
        return False, "Transaksi tidak ditemukan."
    payment = dict(row)
    if payment["status"] == "approved":
        return True, "Pembayaran sudah terverifikasi dan pesanan telah dikirim."
    if payment["status"] in ("expired", "cancelled", "rejected"):
        return False, f"Pesanan berstatus {payment['status']}. Silakan buat pesanan baru."

    target_amount = payment.get("raw_amount") or 0
    if not target_amount or target_amount <= 0:
        return False, "Bukan pembayaran QRIS dinamis otomatis."

    try:
        recent_txs = await _shopeepay_client.fetch_recent_transactions(30)
    except Exception as exc:
        logger.warning("Error fetching ShopeePay transactions: %s", exc)
        return False, f"Gagal mengecek mutasi: {exc}"

    settled_tx_ids = _get_settled_shopee_tx_ids()
    matched_tx = _find_matching_shopee_tx(payment, recent_txs, settled_tx_ids)

    if not matched_tx:
        return False, f"Pembayaran {_format_idr(target_amount)} belum terdeteksi di mutasi ShopeePay. Pastikan Anda telah mentransfer nominal persis dan tunggu 10-30 detik."

    # Atomically claim transaction
    claimed = _claim_and_record_settlement(payment_id, matched_tx)
    if not claimed:
        with _db() as connection:
            chk = connection.execute("SELECT status FROM payment_requests WHERE id = ?", (payment_id,)).fetchone()
            if chk and chk["status"] == "approved":
                return True, "Pembayaran sudah terverifikasi."
        return False, "Transaksi mutasi ini sudah digunakan untuk pesanan lain atau telah diproses."

    ok, fulfill_msg = await _fulfill_payment_request(context, payment_id)
    if ok:
        _amount_allocator.release(target_amount, into_cooldown=True)
        await _notify_admins_auto_paid(context, payment_id, target_amount)
        return True, "Sukses"
    return False, fulfill_msg


async def _shopeepay_mutation_poller(application) -> None:
    """Background polling loop that checks ShopeePay mutations every 8-10 seconds for pending QRIS."""
    logger.info("ShopeePay mutation poller started (dynamic QRIS background check)")
    while True:
        try:
            await asyncio.sleep(8)
            _amount_allocator.cleanup()

            # 1. Auto-expire pending QRIS payments exceeding 15 minutes
            expire_cutoff = (datetime.now() - timedelta(minutes=15)).isoformat()
            with _db() as connection:
                expired_payments = connection.execute(
                    "SELECT * FROM payment_requests WHERE method = 'qris' AND status = 'pending' AND created_at < ?",
                    (expire_cutoff,),
                ).fetchall()
                if expired_payments:
                    connection.execute(
                        "UPDATE payment_requests SET status = 'expired', reviewed_at = ? WHERE method = 'qris' AND status = 'pending' AND created_at < ?",
                        (datetime.now().isoformat(), expire_cutoff),
                    )

            for exp_p in expired_payments:
                if exp_p["raw_amount"]:
                    _amount_allocator.cancel(exp_p["raw_amount"])
                logger.info("Auto-expired pending QRIS payment #%s (amount: %s)", exp_p["id"], exp_p["amount"])
                exp_text = (
                    f"⏱ <b>Batas Waktu Pembayaran Berakhir</b>\n\n"
                    f"Pesanan <b>#{exp_p['id']}</b> ({_safe_html(exp_p['amount'])}) telah dibatalkan otomatis karena melebihi batas waktu 15 menit.\n\n"
                    f"Slot pembayaran telah dibebaskan. Silakan buat pesanan baru melalui menu utama jika Anda masih ingin membeli."
                )
                exp_kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu:main")],
                ])
                try:
                    await _update_user_payment_message(application, exp_p, exp_text, exp_kb)
                except Exception as exc:
                    logger.debug("Could not notify user for expired payment #%s: %s", exp_p["id"], exc)

            # 2. Check active pending QRIS orders within the 15-minute window
            with _db() as connection:
                rows = connection.execute(
                    "SELECT * FROM payment_requests WHERE method = 'qris' AND status = 'pending' AND raw_amount > 0 AND created_at >= ?",
                    (expire_cutoff,),
                ).fetchall()
                pending_payments = [dict(r) for r in rows]

            if not pending_payments:
                continue

            recent_txs = await _shopeepay_client.fetch_recent_transactions(30)
            if not recent_txs:
                continue

            settled_tx_ids = _get_settled_shopee_tx_ids()

            for payment in pending_payments:
                p_id = payment["id"]
                target_amount = payment["raw_amount"]
                matched_tx = _find_matching_shopee_tx(payment, recent_txs, settled_tx_ids)

                if matched_tx:
                    logger.info("ShopeePay poller matched payment #%s for amount %s (tx: %s)", p_id, target_amount, matched_tx.get("id"))
                    claimed = _claim_and_record_settlement(p_id, matched_tx)
                    if claimed:
                        tx_id_str = str(matched_tx.get("id") or matched_tx.get("transactionId") or "")
                        if tx_id_str:
                            settled_tx_ids.add(tx_id_str)

                        ok, _ = await _fulfill_payment_request(application, p_id)
                        if ok:
                            _amount_allocator.release(target_amount, into_cooldown=True)
                            await _notify_admins_auto_paid(application, p_id, target_amount)

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("ShopeePay poller iteration exception: %s", exc)
            await asyncio.sleep(5)


async def _handle_cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: int) -> None:
    """Handle user or admin cancellation of an active pending payment."""
    english = _is_english(update)
    user_id = update.effective_user.id if update.effective_user else 0
    query = update.callback_query

    with _db() as connection:
        payment = connection.execute("SELECT * FROM payment_requests WHERE id = ?", (payment_id,)).fetchone()
        if not payment:
            if query:
                await query.answer("Pesanan tidak ditemukan." if not english else "Order not found.", show_alert=True)
            return

        if payment["user_id"] != user_id and not _is_admin(user_id):
            if query:
                await query.answer("Akses ditolak." if not english else "Access denied.", show_alert=True)
            return

        if payment["status"] != "pending":
            st_text = payment["status"]
            msg = f"Pesanan ini sudah berstatus '{st_text}'." if not english else f"This order is already '{st_text}'."
            if query:
                await query.answer(msg, show_alert=True)
            return

        connection.execute(
            "UPDATE payment_requests SET status = 'cancelled', reviewed_at = ? WHERE id = ?",
            (datetime.now().isoformat(), payment_id),
        )

    if payment["raw_amount"]:
        _amount_allocator.cancel(payment["raw_amount"])

    context.user_data.pop("current_qris_payment_id", None)
    context.user_data.pop("step", None)
    context.user_data.pop("payment_method", None)
    context.user_data.pop("buying_product", None)

    if query:
        await query.answer("Pesanan berhasil dibatalkan." if not english else "Order successfully cancelled.")

    cancel_msg = (
        f"❌ <b>Pesanan Dibatalkan</b>\n\n"
        f"Pesanan <b>#{payment_id}</b> sebesar <b>{_safe_html(payment['amount'])}</b> telah berhasil dibatalkan.\n"
        f"Kode unik dan slot pembayaran telah dibebaskan.\n\n"
        f"Anda dapat melakukan pemesanan baru kapan saja melalui menu utama."
        if not english else
        f"❌ <b>Order Cancelled</b>\n\n"
        f"Order <b>#{payment_id}</b> for <b>{_safe_html(payment['amount'])}</b> has been successfully cancelled.\n"
        f"Unique code and payment slot have been released.\n\n"
        f"You can create a new order anytime from the main menu."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Menu Utama" if not english else "🏠 Main Menu", callback_data="menu:main")],
    ])
    await _safe_edit_text(update, cancel_msg, parse_mode="HTML", reply_markup=keyboard)


async def _review_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: int, approved: bool) -> None:
    admin = update.effective_user
    if not admin or not _is_admin(admin.id):
        await _safe_reply_text(update, "Admin access required.")
        return
    with _db() as connection:
        payment = connection.execute("SELECT * FROM payment_requests WHERE id = ?", (payment_id,)).fetchone()
        if not payment or payment["status"] != "pending":
            await _safe_edit_text(update, "Payment is already reviewed or not found.", reply_markup=_back_keyboard("admin:menu"))
            return
        if not approved:
            connection.execute(
                "UPDATE payment_requests SET status = 'rejected', reviewed_at = ?, reviewed_by = ? WHERE id = ? AND status = 'pending'",
                (datetime.now().isoformat(), admin.id, payment_id),
            )
    pkey = payment["product_key"] if "product_key" in payment.keys() else "gemini"
    back_product = f"product:{pkey}" if pkey in _PRODUCT_CATALOG else "product:gemini"
    if not approved:
        await _update_user_payment_message(
            context, payment,
            "<b>Payment rejected</b>\n\nThe transfer could not be verified."
            if _is_english(update)
            else "<b>Pembayaran ditolak</b>\n\nTransfer tidak dapat diverifikasi.",
            _back_keyboard(back_product),
        )
        await _safe_edit_text(update, f"Payment #{payment_id} rejected.", reply_markup=_back_keyboard("admin:menu"))
        return

    ok, reason = await _fulfill_payment_request(context, payment_id)
    if ok:
        await _safe_edit_text(update, f"Payment #{payment_id} verified and fulfilled.", reply_markup=_back_keyboard("admin:menu"))
    else:
        await _safe_edit_text(update, f"Payment verified, provider fulfillment pending: {reason}", reply_markup=_back_keyboard("admin:menu"))
async def _complete_gemini_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, email: str | None = None) -> None:
    english = _is_english(update)
    message = (
        "Coins can only be used for Canva document generation. Please purchase Gemini Pro via QRIS or Binance USDT."
        if english
        else "Koin hanya dapat digunakan untuk pembuatan dokumen Canva. Silakan beli Gemini Pro melalui QRIS atau Binance USDT."
    )
    await _present_text(update, message, reply_markup=_back_keyboard("gemini:payment_methods"))


async def schools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_channel_membership(update, context):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/schools us`" if _is_english(update) else "Format: `/schools us`", parse_mode="Markdown")
        return

    country = context.args[0].lower()
    try:
        gen = get_country(country)()
    except ValueError:
        await update.message.reply_text(f"Country `{country}` is not available." if _is_english(update) else f"Negara `{country}` tidak tersedia.", parse_mode="Markdown")
        return

    items = [f"• {school['name']}" for school in gen.schools[:20]]
    text = (f"*Schools for {gen.get_country_name()}*" if _is_english(update) else f"*Sekolah untuk {gen.get_country_name()}*") + "\n\n" + "\n".join(items)
    if len(gen.schools) > 20:
        text += f"\n\n… and {len(gen.schools) - 20} more schools." if _is_english(update) else f"\n\n… dan {len(gen.schools) - 20} sekolah lainnya."
    await _safe_reply_text(update, text, parse_mode="Markdown")


async def handle_dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = (query.data or "") if query else ""

    if not (data.startswith("qris_check:") or data.startswith("payment:cancel") or data == "menu:refresh_stock"):
        if query:
            try:
                await query.answer()
            except TelegramError:
                pass

    if data == "membership:check":
        if await require_channel_membership(update, context):
            await show_main_menu(update, context, edit=True)
        return

    if not await require_channel_membership(update, context):
        return

    if data == "menu:main":
        context.user_data.pop("step", None)
        await show_main_menu(update, context, edit=True)
        return

    if data == "menu:refresh_stock":
        english = _is_english(update)
        if _prodseller_configured():
            try:
                await _prodseller_products(force_refresh=True)
            except Exception as exc:
                logger.warning("Failed force refreshing ProdSeller products: %s", exc)
        await show_main_menu(update, context, edit=True, refreshed=True)
        if query:
            try:
                await query.answer(
                    "✅ Status stok berhasil diperbarui!" if not english else "✅ Stock status updated!",
                    show_alert=False,
                )
            except TelegramError:
                pass
        return

    if data.startswith("product:"):
        await show_product(update, context, data.split(":", 1)[1])
        return

    if data == "gemini:buy":
        if not _prodseller_configured():
            stock = max(_gemini_stock_count(), _setting("gemini_manual_stock", 0))
            if stock <= 0:
                await _safe_edit_text(
                    update,
                    "Gemini Pro is currently out of stock." if _is_english(update) else "Gemini Pro sedang habis stok.",
                    reply_markup=_back_keyboard("product:gemini"),
                )
                return
            await show_gemini_payment_methods(update, context)
            return
        try:
            product = await _find_gemini_product()
        except ProdSellerError:
            await _safe_edit_text(update, "Gemini Pro is currently unavailable.", reply_markup=_back_keyboard())
            return
        if product.get("inStock") is False or product.get("stock") == 0:
            await _safe_edit_text(update, "Gemini Pro is currently out of stock.", reply_markup=_back_keyboard())
            return
        if product.get("requiresEmailActivation"):
            context.user_data["step"] = "gemini_payment_email"
            await _safe_edit_text(
                update,
                "Send the activation email before choosing a payment method."
                if _is_english(update)
                else "Kirim email aktivasi sebelum memilih metode pembayaran.",
                reply_markup=_back_keyboard("product:gemini"),
            )
        else:
            await show_gemini_payment_methods(update, context)
        return

    if data == "gemini:payment_methods":
        await show_gemini_payment_methods(update, context)
        return

    if data.startswith("gemini:pay:"):
        await show_payment_instruction(update, context, data.split(":", 2)[2])
        return

    if data.startswith("catalog_buy:"):
        key = data.split(":", 1)[1]
        if key not in _PRODUCT_CATALOG:
            await _safe_edit_text(update, "Product not found.", reply_markup=_back_keyboard())
            return
        cfg = _PRODUCT_CATALOG[key]
        if not _prodseller_configured():
            stock = _setting(cfg["stock_key"], 0)
            if stock <= 0:
                await _safe_edit_text(
                    update,
                    f"{cfg['label_en']} is currently out of stock." if _is_english(update) else f"{cfg['label_id']} sedang habis stok.",
                    reply_markup=_back_keyboard(f"product:{key}"),
                )
                return
            await _show_catalog_payment_methods(update, context, key)
            return
        try:
            product = await _find_catalog_product(key)
        except ProdSellerError:
            await _safe_edit_text(
                update,
                f"{cfg['label_en']} is currently unavailable." if _is_english(update) else f"{cfg['label_id']} sedang tidak tersedia.",
                reply_markup=_back_keyboard(f"product:{key}"),
            )
            return
        if product.get("inStock") is False or product.get("stock") == 0:
            await _safe_edit_text(
                update,
                f"{cfg['label_en']} is currently out of stock." if _is_english(update) else f"{cfg['label_id']} sedang habis stok.",
                reply_markup=_back_keyboard(f"product:{key}"),
            )
            return
        if product.get("requiresEmailActivation"):
            context.user_data["buying_product"] = key
            context.user_data["step"] = f"catalog_payment_email:{key}"
            await _safe_edit_text(
                update,
                "Send the activation email before choosing a payment method."
                if _is_english(update)
                else "Kirim email aktivasi sebelum memilih metode pembayaran.",
                reply_markup=_back_keyboard(f"product:{key}"),
            )
        else:
            await _show_catalog_payment_methods(update, context, key)
        return

    if data.startswith("catalog_payment_methods:"):
        key = data.split(":", 1)[1]
        if key in _PRODUCT_CATALOG:
            await _show_catalog_payment_methods(update, context, key)
        return

    if data.startswith("catalog_pay:"):
        parts = data.split(":", 2)
        if len(parts) == 3:
            key, method = parts[1], parts[2]
            if key in _PRODUCT_CATALOG:
                if method == "coins":
                    await _complete_catalog_coin_purchase(update, context, key)
                elif method in {"binance", "qris"}:
                    await _show_catalog_payment_instruction(update, context, key, method)
        return

    if data.startswith("payment:"):
        parts = data.split(":")
        if len(parts) == 3 and parts[1] in {"approve", "reject"} and parts[2].isdigit():
            await _review_payment(update, context, int(parts[2]), parts[1] == "approve")
        elif len(parts) == 3 and parts[1] == "cancel" and parts[2].isdigit():
            await _handle_cancel_payment(update, context, int(parts[2]))
        elif data == "payment:cancel_current":
            context.user_data.pop("current_qris_payment_id", None)
            context.user_data.pop("step", None)
            context.user_data.pop("payment_method", None)
            context.user_data.pop("buying_product", None)
            if query:
                try:
                    await query.answer("Pesanan dibatalkan." if not _is_english(update) else "Order cancelled.")
                except TelegramError:
                    pass
            await show_main_menu(update, context, edit=True)
        return

    if data.startswith("qris_check:"):
        payment_id_str = data.split(":", 1)[1]
        if payment_id_str.isdigit():
            payment_id = int(payment_id_str)
            english = _is_english(update)
            if query:
                try:
                    await query.answer(
                        "🔍 Checking ShopeePay mutation..." if english else "🔍 Memeriksa mutasi ShopeePay...",
                        show_alert=False,
                    )
                except TelegramError:
                    pass
            success, message = await _check_and_settle_qris_payment(context, payment_id)
            if success:
                if query:
                    try:
                        await query.answer(
                            "✅ Payment verified! Your order has been delivered." if english else "✅ Pembayaran terverifikasi! Pesanan Anda telah dikirim.",
                            show_alert=True,
                        )
                    except TelegramError:
                        pass
            else:
                if query:
                    try:
                        await query.answer(
                            f"⏳ {message}",
                            show_alert=True,
                        )
                    except TelegramError:
                        pass
        return

    if data == "gemini:legacy_buy":
        await show_gemini_payment_methods(update, context)
        return

    if data == "wizard:document_types":
        country = context.user_data.get("country")
        if country:
            context.user_data.pop("school_selection_mode", None)
            await _safe_edit_text(
                update,
                "Choose a document type." if _is_english(update) else "Pilih tipe dokumen yang akan dibuat.",
                reply_markup=_document_type_keyboard(country, update),
            )
        else:
            await show_main_menu(update, context, edit=True)
        return

    if data == "wizard:school":
        country = context.user_data.get("country")
        if not country:
            await _safe_edit_text(update, "Choose a country first." if _is_english(update) else "Pilih negara terlebih dahulu.", reply_markup=_back_keyboard())
            return
        context.user_data["school_selection_mode"] = "pre_doc"
        school_keyboard = InlineKeyboardMarkup(
            _format_school_buttons(
                country,
                english=_is_english(update),
                include_back=True,
                allow_manual=False,
                back_callback="wizard:document_types",
            )
        )
        await _safe_edit_text(
            update,
            (
                f"*Select School*\n\nChoose an existing school for {get_country_display(country)}."
                if _is_english(update)
                else f"*Pilih Sekolah*\n\nPilih sekolah yang tersedia untuk {get_country_display(country)}."
            ),
            parse_mode="Markdown",
            reply_markup=school_keyboard,
        )
        return

    if data == "account:coins":
        await show_coins(update, context)
        return

    if data == "account:history":
        await show_coin_history(update, context)
        return

    if data == "referral:menu":
        await show_referral(update, context)
        return

    if data == "checkin:daily":
        await daily_checkin(update, context)
        return

    if data == "settings:language":
        await show_language_settings(update, context)
        return

    if data.startswith("language:"):
        language = data.split(":", 1)[1]
        user = update.effective_user
        if user:
            _ensure_user(user.id, user.username or user.full_name or "")
            with _db() as connection:
                connection.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user.id))
        await show_main_menu(update, context, edit=True)
        return

    if data == "redeem:input":
        await show_redeem_prompt(update, context)
        return

    if data == "admin:menu":
        await show_admin_menu(update, context)
        return

    if data == "admin:provider_balance":
        await show_provider_balance(update, context)
        return

    if data == "admin:tx_history":
        await show_admin_transaction_history(update, context, tab="payments", page=0)
        return

    if data.startswith("admin:tx:"):
        parts = data.split(":")
        tab = parts[2] if len(parts) > 2 else "payments"
        page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        await show_admin_transaction_history(update, context, tab=tab, page=page)
        return

    if data == "admin:prices":
        context.user_data["step"] = "admin_prices"
        await _safe_edit_text(
            update,
            "Send: `doc_price checkin_reward referral_reward`\nExample: `3 1 2`" if _is_english(update) else "Kirim format: `doc_price checkin_reward referral_reward`\nContoh: `3 1 2`",
            parse_mode="Markdown",
            reply_markup=_back_keyboard("admin:menu"),
        )
    if data == "admin:visibility":
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
            return
        english = _is_english(update)
        text = (
            "*🎛️ Product Visibility Settings*\n\n"
            "Click any product below to toggle its status:\n"
            "🟢 *Active* (Visible to customers on the menu)\n"
            "🔴 *Inactive* (Hidden from customers on the menu)\n\n"
            "💡 _Use this when a product is temporarily or permanently out of stock so customers cannot order it._"
            if english else
            "*🎛️ Pengaturan Status Tampilan Produk*\n\n"
            "Klik produk di bawah untuk mengubah statusnya:\n"
            "🟢 *Aktif* (Ditampilkan ke pengguna di menu utama)\n"
            "🔴 *Nonaktif* (Disembunyikan dari menu pengguna)\n\n"
            "💡 _Gunakan fitur ini ketika produk sedang kehabisan stok agar pengguna tidak dapat memesannya._"
        )
        buttons = []
        docs_act = _is_product_active("docs")
        docs_icon = "🟢" if docs_act else "🔴"
        buttons.append([InlineKeyboardButton(f"{docs_icon} 🎓 Canva Doc Education", callback_data="admin:toggle_vis:docs")])

        gem_act = _is_product_active("gemini")
        gem_icon = "🟢" if gem_act else "🔴"
        buttons.append([InlineKeyboardButton(f"{gem_icon} ✨ Gemini Pro", callback_data="admin:toggle_vis:gemini")])

        for c_key, c_cfg in _PRODUCT_CATALOG.items():
            is_act = _is_product_active(c_key)
            icon = "🟢" if is_act else "🔴"
            c_label = c_cfg["label_en"] if english else c_cfg["label_id"]
            buttons.append([InlineKeyboardButton(f"{icon} {c_cfg['emoji']} {c_label}", callback_data=f"admin:toggle_vis:{c_key}")])

        buttons.append([InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="admin:menu")])
        await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("admin:toggle_vis:"):
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
            return
        key = data.split(":", 2)[2]
        curr = _setting(f"active_{key}", 1)
        new_val = 0 if curr == 1 else 1
        with _db() as connection:
            connection.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (f"active_{key}", str(new_val)),
            )

        if key == "docs":
            prod_name = "🎓 Canva Doc Education"
        elif key == "gemini":
            prod_name = "✨ Gemini Pro"
        elif key in _PRODUCT_CATALOG:
            c_cfg = _PRODUCT_CATALOG[key]
            prod_name = f"{c_cfg['emoji']} {c_cfg['label_id']}"
        else:
            prod_name = key

        status_str = "🟢 Aktif (Ditampilkan)" if new_val == 1 else "🔴 Nonaktif (Disembunyikan)"
        if _is_english(update):
            status_str = "🟢 Active (Visible)" if new_val == 1 else "🔴 Inactive (Hidden)"

        if query:
            try:
                await query.answer(f"{prod_name} -> {status_str}", show_alert=False)
            except TelegramError:
                pass

        english = _is_english(update)
        text = (
            "*🎛️ Product Visibility Settings*\n\n"
            "Click any product below to toggle its status:\n"
            "🟢 *Active* (Visible to customers on the menu)\n"
            "🔴 *Inactive* (Hidden from customers on the menu)\n\n"
            "💡 _Use this when a product is temporarily or permanently out of stock so customers cannot order it._"
            if english else
            "*🎛️ Pengaturan Status Tampilan Produk*\n\n"
            "Klik produk di bawah untuk mengubah statusnya:\n"
            "🟢 *Aktif* (Ditampilkan ke pengguna di menu utama)\n"
            "🔴 *Nonaktif* (Disembunyikan dari menu pengguna)\n\n"
            "💡 _Gunakan fitur ini ketika produk sedang kehabisan stok agar pengguna tidak dapat memesannya._"
        )
        buttons = []
        docs_act = _is_product_active("docs")
        docs_icon = "🟢" if docs_act else "🔴"
        buttons.append([InlineKeyboardButton(f"{docs_icon} 🎓 Canva Doc Education", callback_data="admin:toggle_vis:docs")])

        gem_act = _is_product_active("gemini")
        gem_icon = "🟢" if gem_act else "🔴"
        buttons.append([InlineKeyboardButton(f"{gem_icon} ✨ Gemini Pro", callback_data="admin:toggle_vis:gemini")])

        for c_key, c_cfg in _PRODUCT_CATALOG.items():
            is_act = _is_product_active(c_key)
            icon = "🟢" if is_act else "🔴"
            c_label = c_cfg["label_en"] if english else c_cfg["label_id"]
            buttons.append([InlineKeyboardButton(f"{icon} {c_cfg['emoji']} {c_label}", callback_data=f"admin:toggle_vis:{c_key}")])

        buttons.append([InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="admin:menu")])
        await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data in {"admin:product_prices", "admin:gemini_prices"}:
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
            return
        english = _is_english(update)
        text = (
            "*🏷️ Digital Product Pricing*\n\nSelect a product to update prices (Customer Menu, QRIS, Binance USDT):"
            if english else
            "*🏷️ Kelola Harga Produk Digital*\n\nPilih produk yang ingin diatur harganya (Menu Utama, QRIS, Binance USDT):"
        )
        buttons = [
            [InlineKeyboardButton("✨ Gemini Pro", callback_data="admin:price_target:gemini")],
        ]
        for c_key, c_cfg in _PRODUCT_CATALOG.items():
            buttons.append([InlineKeyboardButton(f"{c_cfg['emoji']} {c_cfg['label_en'] if english else c_cfg['label_id']}", callback_data=f"admin:price_target:{c_key}")])
        buttons.append([InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="admin:menu")])
        await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("admin:price_target:"):
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
            return
        target = data.split(":", 2)[2]
        context.user_data["admin_price_target"] = target
        context.user_data["step"] = "admin_product_prices"
        english = _is_english(update)
        if target == "gemini":
            label = "Gemini Pro"
            p_idr = _format_idr(_setting("gemini_price_idr", 20000))
            p_qris = _format_idr(_setting("gemini_qris_price_idr", 20000))
            p_binance = _setting_text("gemini_binance_price_usdt", "0.60")
        elif target in _PRODUCT_CATALOG:
            cfg = _PRODUCT_CATALOG[target]
            label = cfg["label_en"] if english else cfg["label_id"]
            p_idr = _format_idr(_setting(cfg["price_idr_key"], cfg["default_idr"]))
            p_qris = _format_idr(_setting(cfg["price_qris_key"], cfg["default_qris_idr"]))
            p_binance = _setting_text(cfg["price_binance_key"], cfg["default_binance_usdt"])
        else:
            return

        if english:
            text = (
                f"*🏷️ {label} Price Management*\n\n"
                f"Current prices:\n"
                f"• Menu Price: *{p_idr}*\n"
                f"• QRIS: *{p_qris}*\n"
                f"• Binance: *{p_binance} USDT*\n\n"
                "Send the new prices:\n"
                "`CUSTOMER_IDR QRIS_IDR BINANCE_USDT`\n\n"
                "Example: `30000 30000 1.7`\n"
                "_(Or send 1 number if Menu & QRIS are the same, e.g. `30000`)_"
            )
        else:
            text = (
                f"*🏷️ Pengaturan Harga {label}*\n\n"
                f"Harga saat ini:\n"
                f"• Harga Menu: *{p_idr}*\n"
                f"• QRIS: *{p_qris}*\n"
                f"• Binance: *{p_binance} USDT*\n\n"
                "Kirim harga baru dengan format:\n"
                "`HARGA_MENU HARGA_QRIS HARGA_BINANCE_USDT`\n\n"
                "Contoh: `30000 30000 1.7`\n"
                "_(Atau kirim 1 angka jika Harga Menu & QRIS sama, contoh: `30000`)_"
            )
        await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=_back_keyboard("admin:product_prices"))
        return

    if data == "admin:redeem":
        context.user_data["step"] = "admin_redeem"
        await _safe_edit_text(
            update,
            "Send: `CODE COINS MAX_USES`\nExample: `WELCOME50 50 100`" if _is_english(update) else "Kirim format: `KODE JUMLAH_COIN MAKS_PAKAI`\nContoh: `WELCOME50 50 100`",
            parse_mode="Markdown",
            reply_markup=_back_keyboard("admin:menu"),
        )
        return

    if data == "admin:addcoins":
        context.user_data["step"] = ADMIN_ADD_COINS
        await _safe_edit_text(
            update,
            "Send: `USER_ID COINS`\nExample: `123456789 10`" if _is_english(update) else "Kirim format: `USER_ID JUMLAH_COIN`\nContoh: `123456789 10`",
            parse_mode="Markdown",
            reply_markup=_back_keyboard("admin:menu"),
        )
        return

    if data == "admin:stock":
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
            return
        english = _is_english(update)
        text = (
            "*📦 Product Stock Management*\n\nSelect a product to update stock:"
            if english else
            "*📦 Kelola Stok Produk*\n\nPilih produk yang ingin diatur stoknya:"
        )
        buttons = [
            [InlineKeyboardButton("✨ Gemini Pro", callback_data="admin:stock_target:gemini")],
        ]
        for c_key, c_cfg in _PRODUCT_CATALOG.items():
            buttons.append([InlineKeyboardButton(f"{c_cfg['emoji']} {c_cfg['label_en'] if english else c_cfg['label_id']}", callback_data=f"admin:stock_target:{c_key}")])
        buttons.append([InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="admin:menu")])
        await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("admin:stock_target:"):
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
            return
        target = data.split(":", 2)[2]
        context.user_data["admin_stock_target"] = target
        context.user_data["step"] = ADMIN_SET_STOCK
        english = _is_english(update)
        if target == "gemini":
            current_stock = _setting("gemini_manual_stock", 0)
            label = "Gemini Pro"
        elif target in _PRODUCT_CATALOG:
            cfg = _PRODUCT_CATALOG[target]
            current_stock = _setting(cfg["stock_key"], 0)
            label = cfg["label_en"] if english else cfg["label_id"]
        else:
            return
        if english:
            text = (
                f"*📦 {label} Stock Management*\n\n"
                f"Current stock: *{current_stock} units*\n\n"
                "Send a number to update the stock count.\n"
                "Example: `15`"
            )
        else:
            text = (
                f"*📦 Kelola Stok {label}*\n\n"
                f"Stok saat ini: *{current_stock} unit*\n\n"
                "Kirim angka untuk memperbarui jumlah stok.\n"
                "Contoh: `15`"
            )
        await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=_back_keyboard("admin:stock"))
        return

    if data == "admin:info":
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
            return
        english = _is_english(update)
        text = (
            "*ℹ️ Product Info Management*\n\nSelect a product to update info message:"
            if english else
            "*ℹ️ Kelola Info Produk*\n\nPilih produk yang ingin diatur pesan infonya:"
        )
        buttons = [
            [InlineKeyboardButton("✨ Gemini Pro", callback_data="admin:info_target:gemini")],
        ]
        for c_key, c_cfg in _PRODUCT_CATALOG.items():
            buttons.append([InlineKeyboardButton(f"{c_cfg['emoji']} {c_cfg['label_en'] if english else c_cfg['label_id']}", callback_data=f"admin:info_target:{c_key}")])
        buttons.append([InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="admin:menu")])
        await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("admin:info_target:"):
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
            return
        target = data.split(":", 2)[2]
        context.user_data["admin_info_target"] = target
        context.user_data["step"] = ADMIN_SET_INFO
        english = _is_english(update)
        if target == "gemini":
            current_info = _setting_text("gemini_info", "")
            label = "Gemini Pro"
        elif target in _PRODUCT_CATALOG:
            cfg = _PRODUCT_CATALOG[target]
            current_info = _setting_text(cfg["info_key"], "")
            label = cfg["label_en"] if english else cfg["label_id"]
        else:
            return
        preview = current_info if current_info.strip() else "-"
        if english:
            text = (
                f"*ℹ️ {label} Info*\n\n"
                f"Current info text:\n_{preview}_\n\n"
                f"Send the new info text to display in the {label} purchase chat.\n"
                "Send `-` to clear the info."
            )
        else:
            text = (
                f"*ℹ️ Info {label}*\n\n"
                f"Teks info saat ini:\n_{preview}_\n\n"
                f"Kirim teks info baru yang akan ditampilkan di chat pembelian {label}.\n"
                "Kirim `-` untuk menghapus info."
            )
        await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=_back_keyboard("admin:info"))
        return

    if data == "admin:broadcast":
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
            return
        english = _is_english(update)
        with _db() as connection:
            total_users = connection.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        if english:
            text = (
                f"*📢 Broadcast Announcement*\n\n"
                f"Registered users: *{total_users}*\n\n"
                "Choose an announcement category:"
            )
        else:
            text = (
                f"*📢 Kirim Pengumuman*\n\n"
                f"Total pengguna terdaftar: *{total_users}*\n\n"
                "Pilih kategori pengumuman:"
            )
        type_rows = []
        items = list(_BROADCAST_TYPES.items())
        for i in range(0, len(items), 2):
            row = []
            for key, (emoji, label_id, label_en) in items[i : i + 2]:
                label = label_en if english else label_id
                row.append(InlineKeyboardButton(f"{emoji} {label}", callback_data=f"admin:broadcast_type:{key}"))
            type_rows.append(row)
        type_rows.append([InlineKeyboardButton("⬅️ Back" if english else "⬅️ Kembali", callback_data="admin:menu")])
        await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(type_rows))
        return

    if data.startswith("admin:broadcast_type:"):
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
            return
        broadcast_type = data.split(":", 2)[2]
        if broadcast_type not in _BROADCAST_TYPES:
            await _safe_edit_text(update, "Kategori tidak valid.", reply_markup=_back_keyboard("admin:broadcast"))
            return
        english = _is_english(update)
        emoji, label_id, label_en = _BROADCAST_TYPES[broadcast_type]
        label = label_en if english else label_id
        context.user_data["broadcast_type"] = broadcast_type
        context.user_data["step"] = ADMIN_BROADCAST
        tmpl_preview = _BROADCAST_TEMPLATES.get(broadcast_type, {}).get("en" if english else "id", "")
        if english:
            text = (
                f"*{emoji} {label} Broadcast*\n\n"
                f"📋 *Preset Template:*\n"
                f"────────────────────────\n"
                f"{tmpl_preview}\n"
                f"────────────────────────\n\n"
                f"👉 Tap *🚀 Send This Template* below to broadcast this template immediately, "
                f"or *type and send your own message* in chat to send custom content.\n\n"
                f"_(Delivered cleanly without title headers)_"
            )
            buttons = [
                [InlineKeyboardButton("🚀 Send This Template", callback_data=f"admin:broadcast_send_tmpl:{broadcast_type}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="admin:broadcast")],
            ]
        else:
            text = (
                f"*{emoji} Broadcast {label}*\n\n"
                f"📋 *Template Siap Pakai:*\n"
                f"────────────────────────\n"
                f"{tmpl_preview}\n"
                f"────────────────────────\n\n"
                f"👉 Klik *🚀 Kirim Template Ini* untuk langsung menyiarkan template di atas, "
                f"atau *ketik langsung pesan Anda di chat* jika ingin mengirim teks sendiri.\n\n"
                f"_(Pesan dikirim murni isinya tanpa tambahan judul kategori)_"
            )
            buttons = [
                [InlineKeyboardButton("🚀 Kirim Template Ini", callback_data=f"admin:broadcast_send_tmpl:{broadcast_type}")],
                [InlineKeyboardButton("⬅️ Kembali", callback_data="admin:broadcast")],
            ]
        await _safe_edit_text(
            update, text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    if data.startswith("admin:broadcast_send_tmpl:"):
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:menu"))
            return
        broadcast_type = data.split(":", 2)[2]
        if broadcast_type not in _BROADCAST_TYPES:
            await _safe_edit_text(update, "Kategori tidak valid.", reply_markup=_back_keyboard("admin:broadcast"))
            return
        english = _is_english(update)
        emoji, label_id, label_en = _BROADCAST_TYPES[broadcast_type]
        label = label_en if english else label_id
        await _safe_edit_text(
            update,
            f"⏳ Sending *{emoji} {label}* template broadcast\u2026 Please wait."
            if english
            else f"⏳ Mengirim broadcast template *{emoji} {label}*\u2026 Harap tunggu.",
            parse_mode="Markdown",
        )
        sent = await _broadcast_announcement(context, broadcast_type, use_template=True)
        context.user_data.pop("step", None)
        context.user_data.pop("broadcast_type", None)
        await _safe_edit_text(
            update,
            f"✅ Template broadcast sent to *{sent}* user(s)."
            if english
            else f"✅ Template broadcast berhasil dikirim ke *{sent}* pengguna.",
            parse_mode="Markdown",
            reply_markup=_back_keyboard("admin:menu"),
        )
        return

    if data == "new:document":
        context.user_data.clear()
        keyboard = InlineKeyboardMarkup(_format_country_list() + [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main")]])
        await _safe_edit_text(update, _t(update, "choose_country"), parse_mode="Markdown", reply_markup=keyboard)
        return

    if data == "menu:countries":
        keyboard = InlineKeyboardMarkup(_format_country_list() + [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main")]])
        await _safe_edit_text(update, "*Daftar negara*", parse_mode="Markdown", reply_markup=keyboard)
        return

    if data == "menu:help":
        await help_command(update, context)
        return

    if data in {"menu:home", "menu:main"}:
        context.user_data.clear()
        await show_main_menu(update, context, edit=True)
        return

    if data == "user:orders" or data.startswith("user:orders:"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        await show_user_orders(update, context, page=page)
        return

    if data == "action:randomize":
        country = context.user_data.get("country")
        if not country:
            await _safe_reply_text(update, "Silakan pilih negara terlebih dahulu.")
            return
        _apply_random_defaults(context, country)
        await confirm_data(update, context)
        return

    if data.startswith("country:"):
        country = data.split(":", 1)[1]
        context.user_data["country"] = country
        _apply_random_defaults(context, country)
        gen = get_country(country)()
        keyboard = _document_type_keyboard(country, update)
        english = _is_english(update)
        await _safe_edit_text(
            update,
            (
                f"<b>Selected country:</b> {_safe_html(get_country_display(country))}\n\nYour data has been filled automatically.\n"
                f"Name: {_safe_html(context.user_data['first_name'])} {_safe_html(context.user_data['last_name'])}\n"
                f"School: {_safe_html(context.user_data['school'])}\nPosition: {_safe_html(context.user_data['position'])}\n"
                f"Date of birth: {_safe_html(context.user_data['dob'])}\n\nChoose a document type."
                if english
                else f"<b>Negara dipilih:</b> {_safe_html(get_country_display(country))}\n\nBerikut data otomatis yang sudah diisi untuk Anda.\n"
                f"Nama: {_safe_html(context.user_data['first_name'])} {_safe_html(context.user_data['last_name'])}\nSekolah: {_safe_html(context.user_data['school'])}\n"
                f"Posisi: {_safe_html(context.user_data['position'])}\nTanggal lahir: {_safe_html(context.user_data['dob'])}\n\nPilih tipe dokumen yang akan dibuat."
            ),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    if data.startswith("doc:"):
        doc_type = data.split(":", 1)[1]
        country = context.user_data.get("country")
        supported = get_country(country)().get_document_types() if country else []
        normalized = "all" if doc_type == "all" else _normalize_document_type(doc_type, supported)
        if normalized is None:
            await _safe_reply_text(
                update,
                "This document type is not available for the selected country." if _is_english(update) else "Tipe dokumen ini tidak tersedia untuk negara yang dipilih.",
                reply_markup=_back_keyboard("menu:main"),
            )
            return
        context.user_data["document_type"] = normalized
        await confirm_data(update, context)
        return

    if data.startswith("gender:"):
        gender = data.split(":", 1)[1]
        context.user_data["gender"] = gender
        await _safe_edit_text(update, _t(update, "choose_school"), parse_mode="Markdown", reply_markup=_back_keyboard())
        context.user_data["step"] = SCHOOL
        return

    if data.startswith("school:"):
        school_value = data.split(":", 1)[1]
        if school_value == "manual":
            await query.edit_message_text("Type the school name manually." if _is_english(update) else "Ketik nama sekolah secara manual.", parse_mode="Markdown")
            context.user_data["step"] = SCHOOL
            return
        context.user_data["school"] = school_value
        if context.user_data.pop("school_selection_mode", None) == "pre_doc":
            country = context.user_data.get("country")
            await _safe_edit_text(
                update,
                (
                    f"<b>Selected school:</b> {_safe_html(school_value)}\n\nChoose a document type."
                    if _is_english(update)
                    else f"<b>Sekolah dipilih:</b> {_safe_html(school_value)}\n\nPilih tipe dokumen yang akan dibuat."
                ),
                parse_mode="HTML",
                reply_markup=_document_type_keyboard(country, update),
            )
            return
        await _safe_edit_text(update, _t(update, "choose_position"), parse_mode="Markdown", reply_markup=_back_keyboard())
        context.user_data["step"] = POSITION
        return

    if data.startswith("position:"):
        position_value = data.split(":", 1)[1]
        if position_value == "manual":
            await query.edit_message_text("Type your position manually." if _is_english(update) else "Ketik jabatan Anda secara manual.", parse_mode="Markdown")
            context.user_data["step"] = POSITION
            return
        context.user_data["position"] = position_value
        await _safe_edit_text(update, _t(update, "choose_dob"), parse_mode="Markdown", reply_markup=_back_keyboard())
        context.user_data["step"] = DOB
        return

    if data == "confirm:generate":
        await generate_document_from_state(update, context)
        return

    if data == "confirm:edit":
        await start_wizard(update, context, edit=True)
        return


async def start_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False) -> None:
    if not await require_channel_membership(update, context):
        return
    context.user_data.clear()
    keyboard = InlineKeyboardMarkup(_format_country_list() + [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main")]])
    if edit and update.callback_query is not None:
        await _safe_edit_text(update, _t(update, "new_document"), parse_mode="Markdown", reply_markup=keyboard)
    else:
        await _safe_reply_text(update, _t(update, "new_document"), parse_mode="Markdown", reply_markup=keyboard)


async def handle_text_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_channel_membership(update, context):
        return
    text = (update.message.text or update.message.caption or "").strip()
    photo_file_id = update.message.photo[-1].file_id if update.message.photo else None
    step = context.user_data.get("step")
    country = context.user_data.get("country")

    if step == "gemini_payment_email":
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", text):
            await update.message.reply_text(
                "Please send a valid email address." if _is_english(update) else "Silakan kirim alamat email yang valid.",
                reply_markup=_back_keyboard(),
            )
            return
        context.user_data["gemini_email"] = text
        context.user_data.pop("step", None)
        await show_gemini_payment_methods(update, context)
        return

    if step in {"gemini_payment_binance", "gemini_payment_qris"}:
        if not text and not photo_file_id:
            await update.message.reply_text(
                "Send a transaction reference or screenshot." if _is_english(update) else "Kirim referensi transaksi atau screenshot.",
                reply_markup=_back_keyboard("gemini:payment_methods"),
            )
            return
        reference = text or "Screenshot evidence"
        await _create_payment_request(update, context, reference, photo_file_id)
        return

    if isinstance(step, str) and step.startswith("catalog_payment_email:"):
        key = step.split(":", 1)[1]
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", text):
            await update.message.reply_text(
                "Please send a valid email address." if _is_english(update) else "Silakan kirim alamat email yang valid.",
                reply_markup=_back_keyboard(f"product:{key}"),
            )
            return
        context.user_data["product_email"] = text
        context.user_data.pop("step", None)
        await _show_catalog_payment_methods(update, context, key)
        return

    if isinstance(step, str) and step.startswith("catalog_payment:"):
        parts = step.split(":")
        if len(parts) == 3:
            key, method = parts[1], parts[2]
            if not text and not photo_file_id:
                await update.message.reply_text(
                    "Send a transaction reference or screenshot." if _is_english(update) else "Kirim referensi transaksi atau screenshot.",
                    reply_markup=_back_keyboard(f"catalog_payment_methods:{key}"),
                )
                return
            reference = text or "Screenshot evidence"
            await _create_catalog_payment_request(update, context, key, reference, photo_file_id)
            return

    if step == REDEEM_CODE:
        user = _user_from_update(update)
        code = text.upper()
        if not user:
            return
        with _db() as connection:
            reward = connection.execute(
                "SELECT * FROM redeem_codes WHERE code = ? AND active = 1 AND uses < max_uses",
                (code,),
            ).fetchone()
            used = connection.execute(
                "SELECT 1 FROM redemptions WHERE code = ? AND user_id = ?", (code, user["user_id"])
            ).fetchone()
            if not reward or used:
                await update.message.reply_text("Kode tidak valid, sudah habis, atau sudah pernah digunakan.", reply_markup=_back_keyboard())
                context.user_data.pop("step", None)
                return
            reward_coins = reward["coins"]
            connection.execute("INSERT INTO redemptions(code, user_id, redeemed_at) VALUES (?, ?, ?)", (code, user["user_id"], datetime.now().isoformat()))
            connection.execute("UPDATE redeem_codes SET uses = uses + 1 WHERE code = ?", (code,))
        balance = _add_coins(user["user_id"], reward_coins, f"Redeem code {code}")
        context.user_data.pop("step", None)
        await update.message.reply_text(f"Redeem berhasil. Anda mendapatkan *{reward['coins']} 🪙*.", parse_mode="Markdown")
        await show_main_menu(update, context)
        return

    if step == ADMIN_BROADCAST:
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            return
        broadcast_type = context.user_data.get("broadcast_type", "info")
        if not text:
            await update.message.reply_text(
                "❌ Message cannot be empty. Send the announcement text."
                if _is_english(update)
                else "❌ Pesan tidak boleh kosong. Kirim teks pengumuman.",
            )
            return
        if len(text) > 3000:
            await update.message.reply_text(
                "❌ Message too long (max 3000 characters)."
                if _is_english(update)
                else "❌ Pesan terlalu panjang (maksimal 3000 karakter).",
            )
            return
        emoji, label_id, label_en = _BROADCAST_TYPES.get(broadcast_type, ("📢", "Info", "Info"))
        label = label_en if _is_english(update) else label_id
        await update.message.reply_text(
            f"⏳ Sending *{emoji} {label}* broadcast\u2026 Please wait."
            if _is_english(update)
            else f"⏳ Mengirim broadcast *{emoji} {label}*\u2026 Harap tunggu.",
            parse_mode="Markdown",
        )
        sent = await _broadcast_announcement(context, broadcast_type, text)
        context.user_data.pop("step", None)
        context.user_data.pop("broadcast_type", None)
        await update.message.reply_text(
            f"✅ Broadcast sent to *{sent}* user(s)."
            if _is_english(update)
            else f"✅ Broadcast berhasil dikirim ke *{sent}* pengguna.",
            parse_mode="Markdown",
        )
        await show_admin_menu(update, context)
        return

    if step == ADMIN_SET_STOCK:
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            return
        if not text.isdigit() or int(text) < 0:
            await update.message.reply_text(
                "❌ Invalid input. Send a whole number (e.g. `15`)."
                if _is_english(update)
                else "❌ Input tidak valid. Kirim angka bulat (contoh: `15`).",
                parse_mode="Markdown",
            )
            return
        new_stock = int(text)
        target = context.user_data.pop("admin_stock_target", "gemini")
        if target == "gemini":
            _set_setting("gemini_manual_stock", new_stock)
            label = "Gemini Pro"
        elif target in _PRODUCT_CATALOG:
            cfg = _PRODUCT_CATALOG[target]
            _set_setting(cfg["stock_key"], new_stock)
            label = cfg["label_en"] if _is_english(update) else cfg["label_id"]
        else:
            label = target
        context.user_data.pop("step", None)
        await update.message.reply_text(
            f"✅ {label} stock updated to *{new_stock}* units."
            if _is_english(update)
            else f"✅ Stok {label} berhasil diperbarui menjadi *{new_stock}* unit.",
            parse_mode="Markdown",
        )
        await show_admin_menu(update, context)
        return

    if step == ADMIN_SET_INFO:
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            return
        if len(text) > 2000:
            await update.message.reply_text(
                "❌ Info text is too long (max 2000 characters)."
                if _is_english(update)
                else "❌ Teks info terlalu panjang (maksimal 2000 karakter).",
            )
            return
        new_info = "" if text.strip() == "-" else text.strip()
        target = context.user_data.pop("admin_info_target", "gemini")
        if target == "gemini":
            _set_setting_text("gemini_info", new_info)
            label = "Gemini Pro"
        elif target in _PRODUCT_CATALOG:
            cfg = _PRODUCT_CATALOG[target]
            _set_setting_text(cfg["info_key"], new_info)
            label = cfg["label_en"] if _is_english(update) else cfg["label_id"]
        else:
            label = target
        context.user_data.pop("step", None)
        if new_info:
            reply = (
                f"✅ {label} info updated.\n\n_{new_info}_"
                if _is_english(update)
                else f"✅ Info {label} berhasil diperbarui.\n\n_{new_info}_"
            )
        else:
            reply = f"✅ {label} info cleared." if _is_english(update) else f"✅ Info {label} berhasil dihapus."
        await update.message.reply_text(reply, parse_mode="Markdown")
        await show_admin_menu(update, context)
        return

    if step in {"admin_product_prices", "admin_gemini_prices"}:
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            return
        target = context.user_data.get("admin_price_target") or "gemini"
        english = _is_english(update)
        tokens = text.split()
        if len(tokens) == 1 and tokens[0].isdigit() and int(tokens[0]) > 0:
            price_idr = int(tokens[0])
            qris_idr = price_idr
            binance_usdt = None
        elif len(tokens) == 2 and tokens[0].isdigit() and int(tokens[0]) > 0:
            price_idr = int(tokens[0])
            qris_idr = price_idr
            try:
                binance_usdt = float(tokens[1])
                if binance_usdt <= 0:
                    raise ValueError
            except ValueError:
                await update.message.reply_text("Format USDT tidak valid. Contoh: `30000 1.7`")
                return
        elif len(tokens) == 3 and tokens[0].isdigit() and tokens[1].isdigit() and int(tokens[0]) > 0 and int(tokens[1]) > 0:
            price_idr = int(tokens[0])
            qris_idr = int(tokens[1])
            try:
                binance_usdt = float(tokens[2])
                if binance_usdt <= 0:
                    raise ValueError
            except ValueError:
                await update.message.reply_text("Format USDT tidak valid. Contoh: `30000 30000 1.7`")
                return
        else:
            await update.message.reply_text(
                "Format tidak valid. Gunakan: `HARGA_MENU HARGA_QRIS HARGA_BINANCE`\nContoh: `30000 30000 1.7` atau `30000`",
                parse_mode="Markdown",
            )
            return

        if target == "gemini":
            label = "Gemini Pro"
            _set_setting("gemini_price_idr", price_idr)
            _set_setting("gemini_qris_price_idr", qris_idr)
            if binance_usdt is not None:
                _set_setting_text("gemini_binance_price_usdt", str(binance_usdt))
        elif target in _PRODUCT_CATALOG:
            cfg = _PRODUCT_CATALOG[target]
            label = cfg["label_en"] if english else cfg["label_id"]
            _set_setting(cfg["price_idr_key"], price_idr)
            _set_setting(cfg["price_qris_key"], qris_idr)
            if binance_usdt is not None:
                _set_setting_text(cfg["price_binance_key"], str(binance_usdt))
        else:
            return

        context.user_data.pop("step", None)
        context.user_data.pop("admin_price_target", None)
        usdt_info = f", Binance: *{binance_usdt} USDT*" if binance_usdt is not None else ""
        msg = (
            f"✅ *{label}* price updated:\nMenu: *{_format_idr(price_idr)}*, QRIS: *{_format_idr(qris_idr)}*{usdt_info}"
            if english else
            f"✅ Harga *{label}* berhasil diperbarui:\nMenu: *{_format_idr(price_idr)}*, QRIS: *{_format_idr(qris_idr)}*{usdt_info}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        await show_admin_menu(update, context)
        return

    if step == "admin_prices":
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            return
        values = text.split()
        if not all(value.isdigit() for value in values):
            await update.message.reply_text("Format tidak valid. Gunakan: `3 1 2` (doc_price checkin_reward referral_reward)", parse_mode="Markdown")
            return
        if len(values) == 3:
            _set_setting("doc_price", int(values[0]))
            _set_setting("checkin_reward", int(values[1]))
            _set_setting("referral_reward", int(values[2]))
        elif len(values) == 4:
            _set_setting("doc_price", int(values[0]))
            _set_setting("gemini_price", int(values[1]))
            _set_setting("checkin_reward", int(values[2]))
            _set_setting("referral_reward", int(values[3]))
        else:
            await update.message.reply_text("Format tidak valid. Gunakan: `3 1 2` (doc_price checkin_reward referral_reward)", parse_mode="Markdown")
            return
        context.user_data.pop("step", None)
        await update.message.reply_text("Pengaturan harga Canva doc dan reward koin berhasil diperbarui.")
        await show_admin_menu(update, context)
        return

    if step == "admin_redeem":
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            return
        match = re.fullmatch(r"([A-Za-z0-9_-]+)\s+(\d+)\s+(\d+)", text)
        if not match or int(match.group(2)) <= 0 or int(match.group(3)) <= 0:
            await update.message.reply_text("Format tidak valid. Gunakan: `WELCOME50 50 100`", parse_mode="Markdown")
            return
        code, coins, max_uses = match.group(1).upper(), int(match.group(2)), int(match.group(3))
        with _db() as connection:
            connection.execute(
                "INSERT INTO redeem_codes(code, coins, max_uses) VALUES (?, ?, ?) ON CONFLICT(code) DO UPDATE SET coins = excluded.coins, max_uses = excluded.max_uses, uses = 0, active = 1",
                (code, coins, max_uses),
            )
        notified = await _broadcast_redeem_code(context, code, coins, max_uses)
        context.user_data.pop("step", None)
        await update.message.reply_text(
            f"Redeem code `{code}` aktif: {coins} coin, maksimal {max_uses} penggunaan.\nNotifikasi terkirim ke {notified} user.",
            parse_mode="Markdown",
        )
        await show_admin_menu(update, context)
        return

    if step == ADMIN_ADD_COINS:
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            return
        match = re.fullmatch(r"(\d+)\s+(\d+)", text)
        if not match or int(match.group(2)) <= 0:
            await update.message.reply_text("Format tidak valid. Gunakan: `USER_ID JUMLAH_COIN`", parse_mode="Markdown")
            return
        target_id, amount = int(match.group(1)), int(match.group(2))
        _ensure_user(target_id)
        balance = _add_coins(target_id, amount, "Admin coin grant")
        context.user_data.pop("step", None)
        await update.message.reply_text(f"Berhasil menambahkan {amount} 🪙 ke user `{target_id}`. Saldo sekarang: {balance} 🪙.", parse_mode="Markdown")
        await show_admin_menu(update, context)
        return

    if step == FIRST_NAME:
        context.user_data["first_name"] = text
        await update.message.reply_text(_t(update, "last_name"), parse_mode="Markdown")
        context.user_data["step"] = LAST_NAME
        return

    if step == LAST_NAME:
        context.user_data["last_name"] = text
        keyboard = InlineKeyboardMarkup(_format_gender_buttons(update))
        await update.message.reply_text(_t(update, "gender"), parse_mode="Markdown", reply_markup=keyboard)
        context.user_data["step"] = GENDER
        return

    if step == GENDER:
        context.user_data["gender"] = text.title()
        if country:
            school_buttons = InlineKeyboardMarkup(_format_school_buttons(country, english=_is_english(update), include_back=True))
            await update.message.reply_text(_t(update, "school"), parse_mode="Markdown", reply_markup=school_buttons)
        else:
            await update.message.reply_text("Silakan pilih negara terlebih dahulu.")
        context.user_data["step"] = SCHOOL
        return

    if step == SCHOOL:
        context.user_data["school"] = text
        if country:
            position_buttons = InlineKeyboardMarkup(_format_position_buttons(country, english=_is_english(update), include_back=True))
            await update.message.reply_text(_t(update, "position"), parse_mode="Markdown", reply_markup=position_buttons)
        else:
            await update.message.reply_text("Silakan pilih negara terlebih dahulu.")
        context.user_data["step"] = POSITION
        return

    if step == POSITION:
        context.user_data["position"] = text
        await update.message.reply_text(_t(update, "dob"), parse_mode="Markdown")
        context.user_data["step"] = DOB
        return

    if step == DOB:
        context.user_data["dob"] = text
        await confirm_data(update, context)
        return

    if text.lower() in {"/start", "/new"}:
        await start_wizard(update, context)
        return

    if text.lower() == "/generate":
        await generate_fast_command(update, context)
        return

    await update.message.reply_text("Silakan mulai dengan `/start` atau `/new` untuk membuat dokumen.")


async def confirm_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payload = context.user_data
    country = payload.get("country")
    if not country:
        await update.message.reply_text("Negara belum dipilih.")
        return

    summary = (
        f"<b>{'Document Review' if _is_english(update) else 'Review Dokumen'}</b>\n\n"
        f"• {'Country' if _is_english(update) else 'Negara'}: {_safe_html(get_country_display(country))}\n"
        f"• {'Document type' if _is_english(update) else 'Tipe Dokumen'}: {_safe_html(payload.get('document_type', 'all'))}\n"
        f"• {'Name' if _is_english(update) else 'Nama'}: {_safe_html(payload.get('first_name', ''))} {_safe_html(payload.get('last_name', ''))}\n"
        f"• Gender: {_safe_html(payload.get('gender', 'Random'))}\n"
        f"• {'School' if _is_english(update) else 'Sekolah'}: {_safe_html(payload.get('school', '-'))}\n"
        f"• {'Position' if _is_english(update) else 'Posisi'}: {_safe_html(payload.get('position', '-'))}\n"
        f"• {'Date of birth' if _is_english(update) else 'Tanggal Lahir'}: {_safe_html(payload.get('dob', '-'))}"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"✅ {_t(update, 'create')}", callback_data="confirm:generate")],
            [InlineKeyboardButton(f"🎲 {_t(update, 'random_again')}", callback_data="action:randomize")],
            [InlineKeyboardButton(f"✏️ {_t(update, 'edit')}", callback_data="confirm:edit")],
        ]
    )
    if update.callback_query is not None:
        await _safe_edit_text(update, summary, parse_mode="HTML", reply_markup=keyboard)
    else:
        await _safe_reply_text(update, summary, parse_mode="HTML", reply_markup=keyboard)


async def generate_document_from_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payload = context.user_data
    country = payload.get("country")
    if not country:
        await update.message.reply_text("Negara belum dipilih.")
        return

    required = ["first_name", "last_name", "school", "position", "dob"]
    missing = [field for field in required if not payload.get(field)]
    if missing:
        await _safe_reply_text(update, f"Data belum lengkap: {', '.join(missing)}")
        return

    selected_type = payload.get("document_type")
    if selected_type not in (None, "all"):
        supported_types = get_country(country)().get_document_types()
        selected_type = _normalize_document_type(selected_type, supported_types)
        if selected_type is None:
            await _safe_reply_text(
                update,
                "The selected document type is not available for this country." if _is_english(update) else "Tipe dokumen yang dipilih tidak tersedia untuk negara ini.",
                reply_markup=_back_keyboard("menu:main"),
            )
            return

    user = _user_from_update(update)
    price = _setting("doc_price", 3)
    if not user or not _spend_coins(user["user_id"], price, "Canva Doc Education generate"):
        await _safe_reply_text(
            update,
            (
                f"Insufficient balance. Document generation requires *{price} 🪙*. Use daily check-in, referrals, or a redeem code."
                if _is_english(update)
                else f"Saldo tidak cukup. Pembuatan dokumen membutuhkan *{price} 🪙*. Silakan check-in, gunakan referral, atau redeem code."
            ),
            parse_mode="Markdown",
            reply_markup=_back_keyboard(),
        )
        return

    try:
        result = generate_documents(
            country=country,
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            school_name=payload["school"],
            position=payload["position"],
            date_of_birth=payload["dob"],
            gender=payload.get("gender", "Random"),
            document_types=(None if selected_type in (None, "all") else [selected_type]),
            output_dir="output/telegram",
        )
    except ValueError as exc:
        _add_coins(user["user_id"], price, "Document generation refund")
        message = str(exc)
        if "not found for" in message.lower() or "school" in message.lower():
            user_message = (
                "The school was not found. Choose one from the available list or enter a closer name."
                if _is_english(update)
                else "Maaf, sekolah yang Anda masukkan tidak ditemukan. Silakan pilih sekolah dari daftar yang tersedia atau ketik nama yang lebih mirip."
            )
        elif "document type" in message.lower():
            user_message = f"The document type is not available for this country.\n\nDetails: {message}" if _is_english(update) else f"Tipe dokumen tidak sesuai dengan negara yang dipilih.\n\nDetail: {message}"
        else:
            user_message = (
                "The document could not be created. Check your data and try again."
                if _is_english(update)
                else "Maaf, dokumen tidak dapat dibuat untuk saat ini. Silakan periksa data yang Anda masukkan dan coba lagi."
            )
        await _safe_reply_text(update, user_message)
        return
    except Exception as exc:
        _add_coins(user["user_id"], price, "Document generation refund")
        logger.exception("Unexpected document generation failure")
        await _safe_reply_text(
            update,
            "An internal error occurred while creating the document. Your data is preserved; please try again or return to the dashboard."
            if _is_english(update)
            else "Terjadi kesalahan internal saat membuat dokumen. Data Anda belum hilang; silakan coba lagi atau pilih Dashboard.",
        )
        return

    files = result.get("files", [])
    if not files:
        _add_coins(user["user_id"], price, "Document generation refund")
        await _safe_reply_text(update, "No document files were created." if _is_english(update) else "Tidak ada file yang berhasil dibuat.")
        return

    summary = (
        f"<b>{'Documents created successfully' if _is_english(update) else 'Dokumen selesai dibuat'}</b>\n\n"
        f"• {'Country' if _is_english(update) else 'Negara'}: {_safe_html(result['country'])}\n"
        f"• {'School' if _is_english(update) else 'Sekolah'}: {_safe_html(result['school'])}\n"
        f"• {'Types' if _is_english(update) else 'Tipe'}: {_safe_html(', '.join(result['document_types']))}\n"
        f"• {'Files' if _is_english(update) else 'Total file'}: {_safe_html(result['count'])}"
    )
    next_actions = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🆕 Buat Dokumen Lagi", callback_data="new:document")],
            [InlineKeyboardButton("🏠 Dashboard", callback_data="menu:home")],
        ]
    )
    if update.callback_query is not None:
        await _safe_edit_text(update, summary, parse_mode="HTML", reply_markup=next_actions)
    else:
        await _safe_reply_text(update, summary, parse_mode="HTML", reply_markup=next_actions)

    for index, file_path in enumerate(files, start=1):
        await _send_generated_file(
            update,
            context,
            file_path,
            caption=f"Dokumen {index}/{len(files)} • {Path(file_path).stem}",
        )

    context.user_data.clear()


async def generate_fast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _safe_reply_text(
        update,
        "Gunakan format cepat berikut:\n`/generate us John Smith \"Valley High\" \"Head of Science Department\" \"12/05/1988\" Male teacher_id,employment_letter`",
        parse_mode="Markdown",
    )


async def generate_legacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_channel_membership(update, context):
        return
    if not context.args:
        await _safe_reply_text(update, "Format salah. Contoh: `/generate us John Smith \"Valley High\" \"Head of Science Department\" \"12/05/1988\" Male teacher_id,employment_letter`", parse_mode="Markdown")
        return

    raw = update.message.text.replace(f"/{context.command}", "", 1).strip()
    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        await _safe_reply_text(update, f"Format tidak valid: {exc}")
        return

    if len(parts) < 6:
        await _safe_reply_text(update, "Format yang benar: `/generate <country> <first_name> <last_name> <school> <position> <dob> [gender] [documents]`", parse_mode="Markdown")
        return

    country = parts[0].lower()
    first_name = parts[1]
    last_name = parts[2]
    school_name = parts[3]
    position = parts[4]
    dob = parts[5]
    gender = "Random"
    documents = None

    others = parts[6:]
    if others:
        if others[0].lower() in {"random", "male", "female"}:
            gender = others[0].title()
            others = others[1:]
        if others:
            documents = []
            for item in others:
                for doc in item.split(","):
                    doc = doc.strip()
                    if doc:
                        documents.append(doc)

        user = _user_from_update(update)
        price = _setting("doc_price", 3)
        if not user or not _spend_coins(user["user_id"], price, "Canva Doc Education generate"):
            await _safe_reply_text(
                update,
                f"Saldo tidak cukup. Pembuatan dokumen membutuhkan *{price} 🪙*.",
                parse_mode="Markdown",
                reply_markup=_back_keyboard(),
            )
            return

    try:
        result = generate_documents(
            country=country,
            first_name=first_name,
            last_name=last_name,
            school_name=school_name,
            position=position,
            date_of_birth=dob,
            gender=gender,
            document_types=documents,
            output_dir="output/telegram",
        )
    except Exception as exc:
        _add_coins(user["user_id"], price, "Document generation refund")
        logger.exception("Legacy generate failed")
        await _safe_reply_text(update, f"Gagal menghasilkan dokumen: {exc}")
        return

    files = result.get("files", [])
    if not files:
        _add_coins(user["user_id"], price, "Document generation refund")
        await _safe_reply_text(update, "Tidak ada file yang dibuat.")
        return

    await _safe_reply_text(
        update,
        f"*Dokumen berhasil dibuat*\n\n• Negara: {result['country']}\n• Sekolah: {result['school']}\n• Dokumen: {', '.join(result['document_types'])}",
        parse_mode="Markdown",
    )
    for index, file_path in enumerate(files, start=1):
        await _send_generated_file(
            update,
            context,
            file_path,
            caption=f"Dokumen {index}/{len(files)} • {Path(file_path).stem}",
        )


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Add it to your environment or .env file before starting the bot.")

    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=45.0,
        write_timeout=45.0,
        pool_timeout=30.0,
        media_write_timeout=60.0,
    )
    get_updates_request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=75.0,
        write_timeout=45.0,
        pool_timeout=30.0,
        media_write_timeout=60.0,
    )
    app = (
        ApplicationBuilder()
        .token(token)
        .request(request)
        .get_updates_request(get_updates_request)
        .post_init(_start_media_cleanup)
        .post_shutdown(_stop_media_cleanup)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", start_wizard))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("countries", countries))
    app.add_handler(CommandHandler("schools", schools))
    app.add_handler(CommandHandler("generate", generate_legacy))

    app.add_handler(CallbackQueryHandler(handle_dashboard_callback))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_text_flow))

    # Start Web App Store server for Botkeep domain integration
    try:
        from web_store import start_web_server_thread
        start_web_server_thread()
    except Exception as exc:
        logger.warning("Could not launch Web Store server: %s", exc)

    logger.info("Starting Yowes Telegram bot")
    app.run_polling(drop_pending_updates=True, timeout=60, bootstrap_retries=-1)


if __name__ == "__main__":
    main()
