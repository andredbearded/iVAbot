import os
import logging
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------- ЛОГИРОВАНИЕ ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("ivabot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

# ---------- ПАМЯТЬ ----------
user_modes = {}

MODE_FREE = "free_chat"
MODE_COURSE = "course_picker"

MAIN_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("💬 Свободный чат", callback_data=MODE_FREE)],
        [InlineKeyboardButton("🎓 Подобрать курс", callback_data=MODE_COURSE)],
        [InlineKeyboardButton("♻️ Сбросить", callback_data="reset")],
    ]
)

# ---------- "ФЕЙКОВЫЕ" ОТВЕТЫ ----------
FAKE_FREE_RESPONSES = [
    "Я пока работаю в тестовом режиме 😌",
    "Расскажи, что тебе интересно?",
    "Я учусь быть умным ботом!",
]

FAKE_COURSE_RESPONSES = [
    "Тебе подойдёт курс PVA — для съемки на телефон 📱",
    "Похоже, тебе будет полезен курс PPP — основы фотоаппарата 📸",
    "Посмотри курс MFA — про фэшн и продвинутые проекты ✨",
]


def get_fake_response(mode: str) -> str:
    import random
    if mode == MODE_COURSE:
        return random.choice(FAKE_COURSE_RESPONSES)
    return random.choice(FAKE_FREE_RESPONSES)


# ---------- ХЕНДЛЕРЫ ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_FREE
    await update.message.reply_text(
        "Привет! Я бот Института визуальных искусств.\nПока работаю в тестовом режиме 🙂",
        reply_markup=MAIN_KEYBOARD,
    )


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "reset":
        user_modes[user_id] = MODE_FREE
        await query.edit_message_text(
            "Контекст сброшен. Что делаем дальше?", reply_markup=MAIN_KEYBOARD
        )
    else:
        user_modes[user_id] = query.data
        await query.edit_message_text(
            f"Режим изменён: {query.data}", reply_markup=MAIN_KEYBOARD
        )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = user_modes.get(user_id, MODE_FREE)
    response = get_fake_response(mode)
    await update.message.reply_text(response, reply_markup=MAIN_KEYBOARD)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start — меню\n/reset — сбросить\n/help — помощь")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Exception while handling an update: %s", context.error)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.add_error_handler(error_handler)
    logger.info("Bot started (test mode)")
    app.run_polling()


if __name__ == "__main__":
    main()