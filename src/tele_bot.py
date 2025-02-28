import os
import logging
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.models import AllModels
from config import MODEL_CHOICES

logger = logging.getLogger(__name__)

# Load Variable
load_dotenv()

TELE_API_KEY: str | None = os.getenv("TELE_API_KEY")
api_keys: dict[str, str | None] = {
    "Claude": os.getenv("CLA_API_KEY"),
    "Deepseek": os.getenv("DS_API_KEY"),
    "ChatGPT": os.getenv("GPT_API_KEY"),
}

user_models = {}
llm_models = AllModels(api_keys, MODEL_CHOICES)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! I am Ken's personal AI Assisant. Please select which AI model would you like to chat with."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Just send me any message, and I'll respond with AI-generated content!")


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = []
    for key in MODEL_CHOICES.keys():
        keyboard.append([InlineKeyboardButton(key, callback_data=f"provider_{key}")])

    keyboard.append([InlineKeyboardButton("Surprise Me!", callback_data="random")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text("Main Menu\n\nPlease select AI Model:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Main Menu\n\nPlease select AI Model:", reply_markup=reply_markup)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_main_menu(update, context)


# Function to display the products submenu
async def show_model_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, provider: str) -> None:
    query = update.callback_query
    if query is not None:
        models = MODEL_CHOICES[provider]

        keyboard = []
        for model in models:
            keyboard.append([InlineKeyboardButton(model["name"], callback_data=f"model_{provider}_{model['id']}")])

        keyboard.append([InlineKeyboardButton("◀️ Back to Main Menu", callback_data="back_to_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Models - Select your model:", reply_markup=reply_markup)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # Answer the callback query

    # Get the callback data
    data = query.data
    user_id = query.from_user.id

    if data.startswith("provider_"):
        provider = data.split("_")[1]
        await show_model_selection_menu(update, context, provider)

    elif data == "random":
        await query.edit_message_text("Sorry currently not available. WIP")

    elif data == "back_to_main":
        await show_main_menu(update, context)

    # model_provider_model_id
    elif data.startswith("model_"):
        data_split = data.split("_")
        provider = data_split[1]
        model_id = data_split[-1]

        db_users[user_id] = {
            "provider": provider,
            "model_id": model_id,
        }

        await query.edit_message_text(
            f"You have selected: {provider}\n\n"
            f"Using model: {model_id}\n\n"
            "You can now start chatting with this model. Simply send a message!\n\n"
            "Use /change_model to select a different AI model at any time."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    message_text = update.message.text

    if user_id not in user_models:
        await update.message.reply_text(
            "Please select an AI model first before sending messages.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Select Model", callback_data="back_to_main")]]),
        )
        return

    model_info = user_models[user_id]
    provider = model_info["provider"]
    model_id = model_info["model_id"]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("Thinking...")

    response_text = await llm_models.query_model(provider, model_id, message_text)

    await update.message.reply_text(response_text)
