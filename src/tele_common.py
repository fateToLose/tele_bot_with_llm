import os
import logging
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.utils import count_token, count_pricing
from src.models import AllModels
from src.database import get_user_mgr
from config import (
    MODEL_CHOICES,
    MODEL_PRICING,
)

logger = logging.getLogger(__name__)

# Load Variable
load_dotenv()

TELE_API_KEY: str | None = os.getenv("TELE_API_KEY")
api_keys: dict[str, str | None] = {
    "Claude": os.getenv("CLA_API_KEY"),
    "Deepseek": os.getenv("DS_API_KEY"),
    "ChatGPT": os.getenv("GPT_API_KEY"),
    "Perplexity": os.getenv("PEX_API_KEY"),
}

db_users = {}
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


async def common_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            "Type /change_model to select a different AI model at any time."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = update.effective_user.id
    message_text = update.message.text

    user_mgr = get_user_mgr()

    user_info = user_mgr.register_user(
        user_id=user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    bool_valid, status = user_mgr.validate_user(user_id)

    if not bool_valid:
        await update.message.reply_text(
            "⚠️ You've reached your free message limit.\n\nTo continue using the bot, please contact @Kennnnnnnn",
        )
        return None

    if user_id not in db_users:
        await update.message.reply_text(
            "Please select an AI model first before sending messages.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Select Model", callback_data="back_to_main")]]),
        )
        return None

    model_info = db_users[user_id]
    provider = model_info["provider"]
    model_id = model_info["model_id"]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("Thinking...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    response_text = await llm_models.query_model(provider, model_id, message_text)

    input_tokens = count_token(message_text)
    output_tokens = count_token(response_text)
    msg_cost = count_pricing(MODEL_PRICING, model_id, input_tokens, output_tokens)

    user_mgr.record_msg(
        user_id=user_id,
        provider=provider.lower(),
        model_id=model_id.lower(),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        query_cost=msg_cost,
    )

    if status.startswith("free:"):
        remaining: str = status.split(":")[-1]
        msg_footnote = f"\n\n\n[📊 **{remaining}** free queries remaining]"
        response_text += msg_footnote

    response_batch = [response_text[i : i + 4096] for i in range(0, len(response_text), 4096)]
    for msg in response_batch:
        await update.message.reply_text(text=msg)
