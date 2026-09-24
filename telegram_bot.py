import asyncio
import logging
import os
import random
import re
import secrets
import shlex
import sqlite3
from datetime import datetime
from pathlib import Path

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

from countries import get_country, list_countries
from mcp_server import generate_documents

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output" / "telegram"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATA_DIR / "bot.sqlite3"

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
            """
        )
        connection.executemany(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
            [("doc_price", "3"), ("gemini_price", "20"), ("checkin_reward", "1"), ("referral_reward", "2")],
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


def _safe_reply_text(update: Update, text: str, **kwargs):
    if update.callback_query is not None:
        return update.callback_query.message.reply_text(text, **kwargs)
    if update.message is not None:
        return update.message.reply_text(text, **kwargs)
    return None


def _safe_edit_text(update: Update, text: str, **kwargs):
    if update.callback_query is not None:
        return update.callback_query.edit_message_text(text, **kwargs)
    if update.message is not None:
        return update.message.reply_text(text, **kwargs)
    return None


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


def _format_doc_type_buttons(country_code: str) -> list[list[InlineKeyboardButton]]:
    gen = get_country(country_code)()
    types = ["all"] + gen.get_document_types()
    buttons = []
    for doc in types:
        buttons.append([InlineKeyboardButton(doc.upper(), callback_data=f"doc:{doc}")])
    return buttons


def _format_school_buttons(country_code: str, limit=8, english: bool = False):
    gen = get_country(country_code)()
    schools = gen.schools[:limit]
    buttons = [
        [InlineKeyboardButton(school["name"], callback_data=f"school:{school['name']}")]
        for school in schools
    ]
    buttons.append([InlineKeyboardButton("✍️ Type manually" if english else "✍️ Ketik sendiri", callback_data="school:manual")])
    return buttons


def _format_gender_buttons() -> list[list[InlineKeyboardButton]]:
    return [
        [InlineKeyboardButton("🎲 Random", callback_data="gender:Random")],
        [InlineKeyboardButton("👨 Male", callback_data="gender:Male")],
        [InlineKeyboardButton("👩 Female", callback_data="gender:Female")],
    ]


def _format_position_buttons(country_code: str, english: bool = False) -> list[list[InlineKeyboardButton]]:
    gen = get_country(country_code)()
    positions = gen.get_positions()
    buttons = []
    for pos in positions[:8]:
        buttons.append([InlineKeyboardButton(pos, callback_data=f"position:{pos}")])
    buttons.append([InlineKeyboardButton("✍️ Type manually" if english else "✍️ Ketik sendiri", callback_data="position:manual")])
    return buttons


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


def _main_menu_text(update: Update) -> str:
    if _language(update) == "en":
        return "*Yowes Main Menu*\n\nChoose a service below. Your balance and activity are saved securely."
    return "*Menu Utama Yowes*\n\nPilih layanan di bawah. Saldo dan aktivitas Anda tersimpan dengan aman."


def _main_menu_keyboard(update: Update) -> InlineKeyboardMarkup:
    english = _language(update) == "en"
    doc_price = _setting("doc_price", 3)
    gemini_price = _setting("gemini_price", 20)
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"🎓 Canva Doc Education · {doc_price} 🪙", callback_data="product:docs")],
            [InlineKeyboardButton(f"✨ Gemini Pro 18 Bulan · {gemini_price} 🪙" if not english else f"✨ Gemini Pro 18 Months · {gemini_price} 🪙", callback_data="product:gemini")],
            [InlineKeyboardButton("🪙 Coin Saya" if not english else "🪙 My Coins", callback_data="account:coins")],
            [InlineKeyboardButton("🤝 Referral" if not english else "🤝 Referral", callback_data="referral:menu")],
            [InlineKeyboardButton("🎁 Check-in Harian" if not english else "🎁 Daily Check-in", callback_data="checkin:daily")],
            [InlineKeyboardButton("🌐 Bahasa / Language", callback_data="settings:language")],
            [InlineKeyboardButton("🎟️ Redeem Code", callback_data="redeem:input")],
            *([[InlineKeyboardButton("⚙️ Admin Settings", callback_data="admin:menu")]] if _is_admin(update.effective_user.id if update.effective_user else None) else []),
        ]
    )


def _back_keyboard(callback_data: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data=callback_data)]])


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False) -> None:
    _user_from_update(update)
    if edit and update.callback_query is not None:
        await update.callback_query.edit_message_text(
            _main_menu_text(update), parse_mode="Markdown", reply_markup=_main_menu_keyboard(update)
        )
    else:
        await _safe_reply_text(update, _main_menu_text(update), parse_mode="Markdown", reply_markup=_main_menu_keyboard(update))


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
    _process_referral(update, context)
    await show_main_menu(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "*Quick guide*\n\n1. Press *Canva Doc Education*\n2. Choose a country\n3. Choose a document type\n4. Complete the profile data\n5. Confirm and receive your PNG files\n\n"
        "*Quick command*\n`/generate us John Smith \"Valley High\" \"Head of Science Department\" \"12/05/1988\" Male teacher_id,employment_letter`\n\nGender: `Random`, `Male`, `Female`"
        if _is_english(update)
        else
        "*Panduan cepat*\n\n"
        "1. Tekan *Buat Dokumen Baru*\n"
        "2. Pilih negara\n"
        "3. Pilih tipe dokumen\n"
        "4. Isi nama, sekolah, jabatan, gender, dan tanggal lahir\n"
        "5. Konfirmasi dan dokumen akan dibuat otomatis\n\n"
        "*Contoh format cepat*\n"
        "`/generate us John Smith \"Valley High\" \"Head of Science Department\" \"12/05/1988\" Male teacher_id,employment_letter`\n\n"
        "Gender: `Random`, `Male`, `Female`"
    )
    await _safe_reply_text(update, help_text, parse_mode="Markdown")


async def countries(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        "Earn coins from daily check-ins, referrals, and redeem codes."
        if english
        else f"*Coin Saya*\n\nSaldo: *{user['coins']} 🪙*\n\nDapatkan coin melalui check-in harian, referral, dan redeem code."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📜 Histori Koin" if not english else "📜 Coin History", callback_data="account:history")],
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
    if _is_english(update):
        text = (
            f"*Admin Settings*\n\nCanva Doc price: {_setting('doc_price', 3)} 🪙\n"
            f"Gemini Pro price: {_setting('gemini_price', 20)} 🪙\n"
            f"Check-in reward: {_setting('checkin_reward', 1)} 🪙\n"
            f"Referral reward: {_setting('referral_reward', 2)} 🪙"
        )
    else:
        text = (
            f"*Admin Settings*\n\nHarga Canva Doc: {_setting('doc_price', 3)} 🪙\n"
            f"Harga Gemini Pro: {_setting('gemini_price', 20)} 🪙\n"
            f"Reward check-in: {_setting('checkin_reward', 1)} 🪙\n"
            f"Reward referral: {_setting('referral_reward', 2)} 🪙"
        )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💰 Set Prices" if _is_english(update) else "💰 Atur Harga", callback_data="admin:prices")],
            [InlineKeyboardButton("🎟️ Create Redeem Code" if _is_english(update) else "🎟️ Buat Redeem Code", callback_data="admin:redeem")],
            [InlineKeyboardButton("➕ Grant User Coins" if _is_english(update) else "➕ Tambah Coin User", callback_data="admin:addcoins")],
            [InlineKeyboardButton("📦 Manage Gemini Stock" if _is_english(update) else "📦 Kelola Stok Gemini", callback_data="admin:stock")],
            [InlineKeyboardButton("⬅️ Back" if _is_english(update) else "⬅️ Kembali", callback_data="menu:main")],
        ]
    )
    await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=keyboard)


async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE, product: str) -> None:
    if product == "docs":
        context.user_data["product"] = "docs"
        await start_wizard(update, context)
        return
    price = _setting("gemini_price", 20)
    stock = _gemini_stock_count()
    english = _language(update) == "en"
    await _safe_edit_text(
        update,
        (
            f"*Gemini Pro 18 Months*\n\nPrice: *{price} 🪙*\nStock available: *{stock}*\n\nContact admin for activation."
            if english
            else f"*Gemini Pro 18 Bulan*\n\nHarga: *{price} 🪙*\nStok tersedia: *{stock}*\n\nHubungi admin untuk proses aktivasi akun."
        ),
        parse_mode="Markdown",
        reply_markup=_back_keyboard(),
    )


async def schools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    await query.answer()
    data = query.data or ""

    if data == "menu:main":
        context.user_data.pop("step", None)
        await show_main_menu(update, context, edit=True)
        return

    if data.startswith("product:"):
        await show_product(update, context, data.split(":", 1)[1])
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

    if data == "admin:prices":
        context.user_data["step"] = "admin_prices"
        await _safe_edit_text(
            update,
            "Send: `doc_price gemini_price checkin_reward referral_reward`\nExample: `3 20 1 2`" if _is_english(update) else "Kirim format: `doc_price gemini_price checkin_reward referral_reward`\nContoh: `3 20 1 2`",
            parse_mode="Markdown",
            reply_markup=_back_keyboard("admin:menu"),
        )
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
        with _db() as connection:
            stock = connection.execute(
                "SELECT id, link, description FROM gemini_stock WHERE active = 1 ORDER BY id DESC LIMIT 10"
            ).fetchall()
        if stock:
            lines = [f"• #{item['id']} — {item['description']}\n  {item['link']}" for item in stock]
            title = "Active Gemini Stock" if _is_english(update) else "Stok Gemini Aktif"
            text = f"*{title}: {_gemini_stock_count()}*\n\n" + "\n".join(lines)
        else:
            text = "*Active Gemini Stock: 0*\n\nNo stock available." if _is_english(update) else "*Stok Gemini Aktif: 0*\n\nBelum ada stok."
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("➕ Add Stock" if _is_english(update) else "➕ Tambah Stok", callback_data="admin:addstock")],
                [InlineKeyboardButton("⬅️ Back" if _is_english(update) else "⬅️ Kembali", callback_data="admin:menu")],
            ]
        )
        await _safe_edit_text(update, text, parse_mode="Markdown", reply_markup=keyboard)
        return

    if data == "admin:addstock":
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            await _safe_edit_text(update, "Akses ditolak.", reply_markup=_back_keyboard("admin:stock"))
            return
        context.user_data["step"] = "admin_stock"
        await _safe_edit_text(
            update,
            "Send one stock item per message:\n`JIO_LINK | DESCRIPTION`\n\nExample:\n`https://jio.example/item-001 | Gemini Pro 18 months - personal account`" if _is_english(update) else "Kirim satu stok per pesan dengan format:\n`LINK_JIO | DESKRIPSI`\n\nContoh:\n`https://jio.example/item-001 | Gemini Pro 18 bulan - akun personal`",
            parse_mode="Markdown",
            reply_markup=_back_keyboard("admin:stock"),
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

    if data == "menu:home":
        context.user_data.clear()
        await show_main_menu(update, context, edit=True)
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
        keyboard = InlineKeyboardMarkup(_format_doc_type_buttons(country))
        english = _is_english(update)
        await _safe_edit_text(
            update,
            (
                f"*Selected country:* {get_country_display(country)}\n\nYour data has been filled automatically.\n"
                f"Name: {context.user_data['first_name']} {context.user_data['last_name']}\n"
                f"School: {context.user_data['school']}\nPosition: {context.user_data['position']}\n"
                f"Date of birth: {context.user_data['dob']}\n\nChoose a document type."
                if english
                else f"*Negara dipilih:* {get_country_display(country)}\n\nBerikut data otomatis yang sudah diisi untuk Anda.\n"
                f"Nama: {context.user_data['first_name']} {context.user_data['last_name']}\nSekolah: {context.user_data['school']}\n"
                f"Posisi: {context.user_data['position']}\nTanggal lahir: {context.user_data['dob']}\n\nPilih tipe dokumen yang akan dibuat."
            ),
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return

    if data.startswith("doc:"):
        doc_type = data.split(":", 1)[1]
        context.user_data["document_type"] = doc_type
        await confirm_data(update, context)
        return

    if data.startswith("gender:"):
        gender = data.split(":", 1)[1]
        context.user_data["gender"] = gender
        await _safe_edit_text(update, "Silakan kirim *nama sekolah* yang diinginkan.", parse_mode="Markdown")
        context.user_data["step"] = SCHOOL
        return

    if data.startswith("school:"):
        school_value = data.split(":", 1)[1]
        if school_value == "manual":
            await query.edit_message_text("Type the school name manually." if _is_english(update) else "Ketik nama sekolah secara manual.", parse_mode="Markdown")
            context.user_data["step"] = SCHOOL
            return
        context.user_data["school"] = school_value
        await _safe_edit_text(update, _t(update, "choose_position"), parse_mode="Markdown")
        context.user_data["step"] = POSITION
        return

    if data.startswith("position:"):
        position_value = data.split(":", 1)[1]
        if position_value == "manual":
            await query.edit_message_text("Type your position manually." if _is_english(update) else "Ketik jabatan Anda secara manual.", parse_mode="Markdown")
            context.user_data["step"] = POSITION
            return
        context.user_data["position"] = position_value
        await _safe_edit_text(update, _t(update, "choose_dob"), parse_mode="Markdown")
        context.user_data["step"] = DOB
        return

    if data == "confirm:generate":
        await generate_document_from_state(update, context)
        return

    if data == "confirm:edit":
        await start_wizard(update, context)
        return


async def start_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    keyboard = InlineKeyboardMarkup(_format_country_list() + [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main")]])
    await _safe_reply_text(update, _t(update, "new_document"), parse_mode="Markdown", reply_markup=keyboard)


async def handle_text_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    step = context.user_data.get("step")
    country = context.user_data.get("country")

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

    if step == "admin_stock":
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            return
        if "|" not in text:
            await update.message.reply_text("Format tidak valid. Gunakan: `LINK_JIO | DESKRIPSI`", parse_mode="Markdown")
            return
        link, description = (part.strip() for part in text.split("|", 1))
        if not link.startswith(("https://", "http://")) or not description:
            await update.message.reply_text("Link harus diawali http:// atau https:// dan deskripsi wajib diisi.")
            return
        with _db() as connection:
            connection.execute(
                "INSERT INTO gemini_stock(link, description, created_at) VALUES (?, ?, ?)",
                (link, description, datetime.now().isoformat()),
            )
        context.user_data.pop("step", None)
        await update.message.reply_text(f"Stok Gemini berhasil ditambahkan. Total stok aktif: *{_gemini_stock_count()}*.", parse_mode="Markdown")
        await show_admin_menu(update, context)
        return

    if step == "admin_prices":
        if not _is_admin(update.effective_user.id if update.effective_user else None):
            return
        values = text.split()
        if len(values) != 4 or not all(value.isdigit() for value in values):
            await update.message.reply_text("Format tidak valid. Gunakan: `3 20 1 2`", parse_mode="Markdown")
            return
        for key, value in zip(("doc_price", "gemini_price", "checkin_reward", "referral_reward"), values):
            _set_setting(key, int(value))
        context.user_data.pop("step", None)
        await update.message.reply_text("Pengaturan harga dan reward berhasil diperbarui.")
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
        keyboard = InlineKeyboardMarkup(_format_gender_buttons())
        await update.message.reply_text(_t(update, "gender"), parse_mode="Markdown", reply_markup=keyboard)
        context.user_data["step"] = GENDER
        return

    if step == GENDER:
        context.user_data["gender"] = text.title()
        if country:
            school_buttons = InlineKeyboardMarkup(_format_school_buttons(country, english=_is_english(update)))
            await update.message.reply_text(_t(update, "school"), parse_mode="Markdown", reply_markup=school_buttons)
        else:
            await update.message.reply_text("Silakan pilih negara terlebih dahulu.")
        context.user_data["step"] = SCHOOL
        return

    if step == SCHOOL:
        context.user_data["school"] = text
        if country:
            position_buttons = InlineKeyboardMarkup(_format_position_buttons(country, english=_is_english(update)))
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
        f"{_t(update, 'review')}\n\n• Country: {get_country_display(country)}\n• Document type: {payload.get('document_type', 'all')}\n"
        f"• Name: {payload.get('first_name', '')} {payload.get('last_name', '')}\n• Gender: {payload.get('gender', 'Random')}\n"
        f"• School: {payload.get('school', '-')}\n• Position: {payload.get('position', '-')}\n• Date of birth: {payload.get('dob', '-')}"
        if _is_english(update)
        else f"{_t(update, 'review')}\n\n• Negara: {get_country_display(country)}\n• Tipe Dokumen: {payload.get('document_type', 'all')}\n"
        f"• Nama: {payload.get('first_name', '')} {payload.get('last_name', '')}\n• Gender: {payload.get('gender', 'Random')}\n"
        f"• Sekolah: {payload.get('school', '-')}\n• Posisi: {payload.get('position', '-')}\n• Tanggal Lahir: {payload.get('dob', '-')}"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"✅ {_t(update, 'create')}", callback_data="confirm:generate")],
            [InlineKeyboardButton(f"🎲 {_t(update, 'random_again')}", callback_data="action:randomize")],
            [InlineKeyboardButton(f"✏️ {_t(update, 'edit')}", callback_data="confirm:edit")],
        ]
    )
    await _safe_reply_text(update, summary, parse_mode="Markdown", reply_markup=keyboard)


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
            document_types=(None if payload.get("document_type") in (None, "all") else [payload["document_type"]]),
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
        await _safe_reply_text(update, user_message, parse_mode="Markdown")
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
        f"*Documents created successfully*\n\n• Country: {result['country']}\n• School: {result['school']}\n"
        f"• Types: {', '.join(result['document_types'])}\n• Files: {result['count']}"
        if _is_english(update)
        else f"*Dokumen selesai dibuat*\n\n• Negara: {result['country']}\n• Sekolah: {result['school']}\n• Tipe: {', '.join(result['document_types'])}\n• Total file: {result['count']}"
    )
    next_actions = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🆕 Buat Dokumen Lagi", callback_data="new:document")],
            [InlineKeyboardButton("🏠 Dashboard", callback_data="menu:home")],
        ]
    )
    await _safe_reply_text(update, summary, parse_mode="Markdown", reply_markup=next_actions)

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

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", start_wizard))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("countries", countries))
    app.add_handler(CommandHandler("schools", schools))
    app.add_handler(CommandHandler("generate", generate_legacy))

    app.add_handler(CallbackQueryHandler(handle_dashboard_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_flow))

    logger.info("Yowes Telegram bot started successfully")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
