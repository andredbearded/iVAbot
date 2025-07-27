import os
import logging
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------- ЛОГИРОВАНИЕ ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("ivabot")

# ---------------- НАСТРОЙКИ ----------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # опционально: чтобы присылать алерты админу

# Память на сеанс (RAM). На Railway перезапуск — всё очищается.
USER_STATE: dict[int, str] = {}          # user_id -> state  (NONE | ASK)
USER_LAST_QUESTIONS: dict[int, list] = {}  # для примитивного логирования в рантайме


# ---------------- ВСПОМОГАТЕЛЬНОЕ ----------------
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❓ Задать вопрос", callback_data="ask"),
            InlineKeyboardButton("ℹ️ Что умею", callback_data="about"),
        ],
        [
            InlineKeyboardButton("📚 Программы IVA", callback_data="programs"),
            InlineKeyboardButton("📞 Контакты", callback_data="contacts"),
        ],
    ])


def faq_like_answer(text: str) -> str:
    """Очень простая «заглушка» вместо ChatGPT.
    Добавь сюда правила под свои частые вопросы.
    """
    t = text.lower()

    if any(k in t for k in ["цена", "стоимость", "сколько стоит", "сколько стоит курс"]):
        return (
            "Сейчас я работаю в тестовом режиме без доступа к базе цен. "
            "Напиши администратору @your_admin (или нажми «Контакты») — подскажут актуальную стоимость."
        )

    if any(k in t for k in ["pva", "phone visual artist"]):
        return "PVA — программа для авторов, кто снимает на телефон, но мыслит как визуальный артист. (Тестовый ответ без AI)"
    if any(k in t for k in ["pps", "personal photography style"]):
        return "PPS — маршрут к вашему авторскому стилю в фотографии. (Тестовый ответ без AI)"
    if any(k in t for k in ["mfa", "fashion"]):
        return "MFA — для работы на стыке моды, видео, клипов и новых медиа. (Тестовый ответ без AI)"
    if any(k in t for k in ["mva", "visual arts"]):
        return "MVA — междисциплинарная программа для визуальных артистов. (Тестовый ответ без AI)"
    if any(k in t for k in ["pvp", "personal visual practice"]):
        return "PVP — серия мастер‑классов по практикам мировых фотографов. (Тестовый ответ без AI)"

    # fallback: просто эхо с пометкой (чтобы ты видел, что без LLM)
    return f"Тестовый режим (без OpenAI). Ты спросил: «{text}»"


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=text)
        except Exception as e:
            logger.warning("Failed to notify admin: %s", e)


# ---------------- ХЕНДЛЕРЫ ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    USER_STATE[user.id] = "NONE"
    logger.info("User %s started bot", user.id)
    await update.message.reply_text(
        "Привет! Я тестовый IVA бот (без OpenAI). Чем могу помочь?",
        reply_markup=main_menu_kb(),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start — главное меню\n"
        "/help — помощь\n"
        "/health — проверить, что я жив\n"
        "/cancel — отменить режим вопроса"
    )


async def health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("✅ OK. Время сервера: " + datetime.utcnow().isoformat())


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    USER_STATE[user_id] = "NONE"
    await update.message.reply_text("Ок, вышли из режима вопроса.", reply_markup=main_menu_kb())


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # обязательный ACK, чтобы убрать "часики"
    user_id = query.from_user.id

    data = query.data
    logger.info("Button '%s' from user %s", data, user_id)

    if data == "ask":
        USER_STATE[user_id] = "ASK"
        await query.edit_message_text(
            "Задай свой вопрос одним сообщением. Я отвечу в тестовом режиме без OpenAI.",
        )
    elif data == "about":
        await query.edit_message_text(
            "Я тестовый бот IVA: показываю меню, принимаю вопросы и отвечаю без OpenAI (заглушкой).\n"
            "Скоро научусь говорить умнее 🤖",
            reply_markup=main_menu_kb(),
        )
    elif data == "programs":
        await query.edit_message_text(
            "Основные программы:\n"
            "• PPS — Personal Photography Style\n"
            "• PVA — Phone Visual Artist\n"
            "• PVP — Personal Visual Practice\n"
            "• MFA — Master of Fashion Arts\n"
            "• MVA — Master of Visual Arts\n\n"
            "Спроси подробнее про любую.",
            reply_markup=main_menu_kb(),
        )
    elif data == "contacts":
        await query.edit_message_text(
            "Контакты института (пример):\n"
            "Telegram: @your_admin\nEmail: hello@example.com",
            reply_markup=main_menu_kb(),
        )
    else:
        await query.edit_message_text("Неизвестная команда.", reply_markup=main_menu_kb())


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка всех текстов, когда пользователь не нажимает кнопки."""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    state = USER_STATE.get(user_id, "NONE")
    logger.info("Text from %s (state=%s): %s", user_id, state, text)

    # логируем в память
    USER_LAST_QUESTIONS.setdefault(user_id, []).append((datetime.utcnow(), text))
    if len(USER_LAST_QUESTIONS[user_id]) > 20:
        USER_LAST_QUESTIONS[user_id] = USER_LAST_QUESTIONS[user_id][-20:]

    if state == "ASK":
        # тут «заглушка» вместо LLM
        answer = faq_like_answer(text)
        await update.message.reply_text(answer, reply_markup=main_menu_kb())
        USER_STATE[user_id] = "NONE"
    else:
        # пользователь вне режима вопроса — показываем меню
        await update.message.reply_text(
            "Нажми кнопку «❓ Задать вопрос» или выбери другой пункт меню.",
            reply_markup=main_menu_kb(),
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception: %s", context.error)
    # уведомим админа, если задан
    await notify_admin(context, f"⚠️ Ошибка у бота: {context.error}")


# ---------------- MAIN ----------------
def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("health", health))
    application.add_handler(CommandHandler("cancel", cancel))

    # кнопки
    application.add_handler(CallbackQueryHandler(on_button))

    # тексты
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    # ошибки
    application.add_error_handler(error_handler)

    logger.info("Bot started")
    application.run_polling(close_loop=False)


if __name__ == "__main__":
    main()