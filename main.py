import os
import logging

from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from src.database import init_user_mgr
from src.tele_common import start, help_command, menu_command, common_callback, handle_message
from src.tele_admin import admin_command, admin_callback, add_premium_conv, add_credits_conv

from config import (
    QUERY_PATH,
    DB_MASTER_FPATH,
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def start_bot() -> None:
    # Load Variable
    load_dotenv()
    init_user_mgr(DB_MASTER_FPATH, QUERY_PATH)

    TELE_TOKEN: str | None = os.getenv("TELE_API_KEY")
    if not TELE_TOKEN:
        logger.error("No Telegram API found in env variable.")
        raise AssertionError("No Telegram Bot API, exiting program.")

    application = Application.builder().token(TELE_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("change_model", menu_command))

    application.add_handler(add_premium_conv)
    application.add_handler(add_credits_conv)

    application.add_handler(CallbackQueryHandler(common_callback, pattern="^(provider_|model_|back_)"))
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


# Run
if "__main__" == __name__:
    try:
        start_bot()
    except Exception as e:
        logger.error(e)
