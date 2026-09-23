import logging
import os
import random
import shlex
from datetime import datetime
from pathlib import Path

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.error import TelegramError
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


def _format_school_buttons(country_code: str, limit=8):
    gen = get_country(country_code)()
    schools = gen.schools[:limit]
    buttons = [
        [InlineKeyboardButton(school["name"], callback_data=f"school:{school['name']}")]
        for school in schools
    ]
    buttons.append([InlineKeyboardButton("✍️ Ketik sendiri", callback_data="school:manual")])
    return buttons


def _format_gender_buttons() -> list[list[InlineKeyboardButton]]:
    return [
        [InlineKeyboardButton("🎲 Random", callback_data="gender:Random")],
        [InlineKeyboardButton("👨 Male", callback_data="gender:Male")],
        [InlineKeyboardButton("👩 Female", callback_data="gender:Female")],
    ]


def _format_position_buttons(country_code: str) -> list[list[InlineKeyboardButton]]:
    gen = get_country(country_code)()
    positions = gen.get_positions()
    buttons = []
    for pos in positions[:8]:
        buttons.append([InlineKeyboardButton(pos, callback_data=f"position:{pos}")])
    buttons.append([InlineKeyboardButton("✍️ Ketik sendiri", callback_data="position:manual")])
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


def _make_dashboard_text() -> str:
    return (
        "*Yowes Document Dashboard*\n\n"
        "Pilih salah satu opsi di bawah untuk membuat dokumen pengajar secara profesional dan terstruktur."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🆕 Buat Dokumen Baru", callback_data="new:document")],
            [InlineKeyboardButton("🌍 Lihat Negara", callback_data="menu:countries")],
            [InlineKeyboardButton("❓ Bantuan", callback_data="menu:help")],
        ]
    )
    await _safe_reply_text(update, _make_dashboard_text(), parse_mode="Markdown", reply_markup=keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
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
    await _safe_reply_text(update, "*Negara yang didukung*\n\n" + "\n".join(lines), parse_mode="Markdown")


async def schools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Format: `/schools us`", parse_mode="Markdown")
        return

    country = context.args[0].lower()
    try:
        gen = get_country(country)()
    except ValueError:
        await update.message.reply_text(f"Negara `{country}` tidak tersedia.", parse_mode="Markdown")
        return

    items = [f"• {school['name']}" for school in gen.schools[:20]]
    text = f"*Sekolah untuk {gen.get_country_name()}*\n\n" + "\n".join(items)
    if len(gen.schools) > 20:
        text += f"\n\n… dan {len(gen.schools) - 20} sekolah lainnya."
    await _safe_reply_text(update, text, parse_mode="Markdown")


async def handle_dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "new:document":
        context.user_data.clear()
        await _safe_edit_text(update, "*Mulai pembuatan dokumen*\n\nPilih negara yang akan dipakai.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(_format_country_list()))
        return

    if data == "menu:countries":
        await _safe_edit_text(update, "*Daftar negara*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(_format_country_list()))
        return

    if data == "menu:help":
        await help_command(update, context)
        return

    if data == "menu:home":
        context.user_data.clear()
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🆕 Buat Dokumen Baru", callback_data="new:document")],
                [InlineKeyboardButton("🌍 Lihat Negara", callback_data="menu:countries")],
                [InlineKeyboardButton("❓ Bantuan", callback_data="menu:help")],
            ]
        )
        await _safe_edit_text(update, _make_dashboard_text(), parse_mode="Markdown", reply_markup=keyboard)
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
        await _safe_edit_text(
            update,
            f"*Negara dipilih:* {get_country_display(country)}\n\n"
            "Berikut data otomatis yang sudah diisi untuk Anda.\n"
            f"Nama: {context.user_data['first_name']} {context.user_data['last_name']}\n"
            f"Sekolah: {context.user_data['school']}\n"
            f"Posisi: {context.user_data['position']}\n"
            f"Tanggal lahir: {context.user_data['dob']}\n\n"
            "Pilih tipe dokumen yang akan dibuat.",
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
            await query.edit_message_text("Ketik nama sekolah secara manual.", parse_mode="Markdown")
            context.user_data["step"] = SCHOOL
            return
        context.user_data["school"] = school_value
        await _safe_edit_text(update, "Silakan kirim *jabatan / posisi* Anda.", parse_mode="Markdown")
        context.user_data["step"] = POSITION
        return

    if data.startswith("position:"):
        position_value = data.split(":", 1)[1]
        if position_value == "manual":
            await query.edit_message_text("Ketik jabatan Anda secara manual.", parse_mode="Markdown")
            context.user_data["step"] = POSITION
            return
        context.user_data["position"] = position_value
        await _safe_edit_text(update, "Silakan kirim *tanggal lahir* dalam format `DD/MM/YYYY`.", parse_mode="Markdown")
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
    keyboard = InlineKeyboardMarkup(_format_country_list())
    await _safe_reply_text(update, "*Buat Dokumen Baru*\n\nPilih negara yang akan digunakan.", parse_mode="Markdown", reply_markup=keyboard)


async def handle_text_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    step = context.user_data.get("step")
    country = context.user_data.get("country")

    if step == FIRST_NAME:
        context.user_data["first_name"] = text
        await update.message.reply_text("Silakan kirim *nama belakang* Anda.", parse_mode="Markdown")
        context.user_data["step"] = LAST_NAME
        return

    if step == LAST_NAME:
        context.user_data["last_name"] = text
        keyboard = InlineKeyboardMarkup(_format_gender_buttons())
        await update.message.reply_text("Pilih *jenis kelamin*.", parse_mode="Markdown", reply_markup=keyboard)
        context.user_data["step"] = GENDER
        return

    if step == GENDER:
        context.user_data["gender"] = text.title()
        if country:
            school_buttons = InlineKeyboardMarkup(_format_school_buttons(country))
            await update.message.reply_text("Pilih *sekolah* atau ketik sendiri.", parse_mode="Markdown", reply_markup=school_buttons)
        else:
            await update.message.reply_text("Silakan pilih negara terlebih dahulu.")
        context.user_data["step"] = SCHOOL
        return

    if step == SCHOOL:
        context.user_data["school"] = text
        if country:
            position_buttons = InlineKeyboardMarkup(_format_position_buttons(country))
            await update.message.reply_text("Pilih atau kirim *jabatan/posisi* Anda.", parse_mode="Markdown", reply_markup=position_buttons)
        else:
            await update.message.reply_text("Silakan pilih negara terlebih dahulu.")
        context.user_data["step"] = POSITION
        return

    if step == POSITION:
        context.user_data["position"] = text
        await update.message.reply_text("Kirim *tanggal lahir* dalam format `DD/MM/YYYY`.", parse_mode="Markdown")
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
        "*Review Dokumen*\n\n"
        f"• Negara: {get_country_display(country)}\n"
        f"• Tipe Dokumen: {payload.get('document_type', 'all')}\n"
        f"• Nama: {payload.get('first_name', '')} {payload.get('last_name', '')}\n"
        f"• Gender: {payload.get('gender', 'Random')}\n"
        f"• Sekolah: {payload.get('school', '-')}\n"
        f"• Posisi: {payload.get('position', '-')}\n"
        f"• Tanggal Lahir: {payload.get('dob', '-')}"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Buat Dokumen", callback_data="confirm:generate")],
            [InlineKeyboardButton("🎲 Random Ulang", callback_data="action:randomize")],
            [InlineKeyboardButton("✏️ Edit Data", callback_data="confirm:edit")],
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
        message = str(exc)
        if "not found for" in message.lower() or "school" in message.lower():
            user_message = (
                "Maaf, sekolah yang Anda masukkan tidak ditemukan. "
                "Silakan pilih sekolah dari daftar yang tersedia atau ketik nama yang lebih mirip."
            )
        elif "document type" in message.lower():
            user_message = f"Tipe dokumen tidak sesuai dengan negara yang dipilih.\n\nDetail: {message}"
        else:
            user_message = (
                "Maaf, dokumen tidak dapat dibuat untuk saat ini. "
                "Silakan periksa data yang Anda masukkan dan coba lagi."
            )
        await _safe_reply_text(update, user_message, parse_mode="Markdown")
        return
    except Exception as exc:
        logger.exception("Unexpected document generation failure")
        await _safe_reply_text(
            update,
            "Terjadi kesalahan internal saat membuat dokumen. Data Anda belum hilang; silakan coba lagi atau pilih Dashboard.",
        )
        return

    files = result.get("files", [])
    if not files:
        await _safe_reply_text(update, "Tidak ada file yang berhasil dibuat.")
        return

    summary = (
        f"*Dokumen selesai dibuat*\n\n"
        f"• Negara: {result['country']}\n"
        f"• Sekolah: {result['school']}\n"
        f"• Tipe: {', '.join(result['document_types'])}\n"
        f"• Total file: {result['count']}"
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
        logger.exception("Legacy generate failed")
        await _safe_reply_text(update, f"Gagal menghasilkan dokumen: {exc}")
        return

    files = result.get("files", [])
    if not files:
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
