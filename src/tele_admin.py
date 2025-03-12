import logging

from datetime import datetime
from telegram import CallbackQuery, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from src.database import get_user_mgr

logger = logging.getLogger(__name__)
AWAITING_USER_ID = 1
AWAITING_ACCESS_LEVEL = 2
AWAITING_FREE_CREDITS = 3


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_mgr = get_user_mgr()

    user = user_mgr.get_user(user_id)
    if not user or user["access_level"] != "admin":
        await update.message.reply_text("⛔ You don't have admin privileges to use this command.")
        return

    await show_admin_dashboard(update, context)


async def show_admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_mgr = get_user_mgr()

    user_counts = user_mgr.get_user_count()
    active_users = user_mgr.get_active_users(7)
    total_cost = user_mgr.get_total_cost()

    keyboard = [
        [InlineKeyboardButton("📊 Usage Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
        [InlineKeyboardButton("🔎 Show Recent User", callback_data="admin_show_users")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    dashboard_text = (
        "🔐 Admin Dashboard\n\n"
        f"Users: {user_counts['total']} total\n"
        f"• {user_counts['free']} free\n"
        f"• {user_counts['premium']} premium\n"
        f"• {user_counts['admin']} admin\n\n"
        f"Active in last 7 days: {active_users}\n"
        f"Total API Cost: ${total_cost:.2f}\n\n"
        "Select an option:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(dashboard_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(dashboard_text, reply_markup=reply_markup)


async def show_usage_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_mgr = get_user_mgr()
    query = update.callback_query

    daily_stats = user_mgr.get_daily_stats(7)
    provider_stats = user_mgr.get_provider_stats()

    daily_text = "📅 Daily Usage (Last 7 days):\n\n"

    if daily_stats:
        for day in daily_stats:
            daily_text += (
                f"• {day['date']}: {day['total_messages']} messages\n"
                f"  Free: {day['free_user_messages']} | "
                f"Premium: {day['premium_user_messages']} | "
                f"Admin: {day['admin_user_messages']} | "
                f"Cost: ${day['total_cost']:.2f}\n"
            )
    else:
        daily_text += "No data available yet\n"

    # Format provider stats
    provider_text = "\n📱 Provider Usage:\n\n"

    for provider in provider_stats:
        avg_cost = provider["total_cost"] / provider["total_messages"] if provider["total_messages"] > 0 else 0
        provider_text += (
            f"• {provider['provider'].capitalize()}: {provider['total_messages']} messages\n"
            f"  Tokens: {provider['total_tokens']:,} | "
            f"Cost: ${provider['total_cost']:.2f} | "
            f"Avg: ${avg_cost:.4f}/msg\n"
        )

    # Create back button
    keyboard = [[InlineKeyboardButton("◀️ Back to Dashboard", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(f"{daily_text}\n{provider_text}", reply_markup=reply_markup)


async def show_recent_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query: CallbackQuery | None = update.callback_query

    user_mgr = get_user_mgr()
    users = user_mgr.list_users(limit=10)

    if not users:
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text("No users found in the database.", reply_markup=reply_markup)
        return

    user_text = "👥 Recent Users:\n\n"

    for user in users:
        last_active = datetime.fromisoformat(user["last_active_at"]).strftime("%Y-%m-%d")
        user_text += (
            f"ID: {user['user_id']}\n"
            f"Name: {user['first_name'] or ''} {user['last_name'] or ''}\n"
            f"@{user['username'] or 'No username'}\n"
            f"Access: {user['access_level'].upper()}\n"
            f"Free queries: {user['remaining_free_queries']}\n"
            f"Total queries: {user['total_queries']}\n"
            f"Last active: {last_active}\n\n"
        )

    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(user_text, reply_markup=reply_markup)


async def start_change_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the add premium user conversation"""
    query = update.callback_query

    await query.edit_message_text(
        "➕ Change User Roles\n\n"
        "Please enter the Telegram user ID of the user you want to change user role.\n\n"
        "You can use /cancel to cancel this operation."
    )

    return AWAITING_USER_ID


async def process_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user ID for premium access"""
    try:
        user_id = int(update.message.text.strip())
        context.user_data["target_user_id"] = user_id

        # Check if user exists
        user_mgr = get_user_mgr()
        user = user_mgr.get_user(user_id)

        if not user:
            await update.message.reply_text(
                f"⚠️ User with ID {user_id} not found in the database. "
                "The user needs to start the bot at least once before you can modify their access.\n\n"
                "Please enter another user ID or use /cancel to abort:"
            )
            return AWAITING_USER_ID

        # Ask for access level
        keyboard = [
            [InlineKeyboardButton("Free", callback_data="access_free")],
            [InlineKeyboardButton("Premium", callback_data="access_premium")],
            [InlineKeyboardButton("Admin", callback_data="access_admin")],
            [InlineKeyboardButton("Cancel", callback_data="access_cancel")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        user_text = (
            f"User ID: {user_id}\n"
            f"Username: {user['username'] or 'Not set'}\n"
            f"Name: {user['first_name'] or ''} {user['last_name'] or ''}\n"
            f"Current access: {user['access_level']}\n"
            f"Free queries left: {user['remaining_free_queries']}\n\n"
            "Select the new access level:"
        )

        await update.message.reply_text(user_text, reply_markup=reply_markup)
        return AWAITING_ACCESS_LEVEL

    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid numeric user ID.\nTry again or use /cancel to abort:")
        return AWAITING_USER_ID


async def process_access_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the selected access level"""
    query = update.callback_query
    await query.answer()

    action = query.data.split("_")[1]

    if action == "cancel":
        await query.edit_message_text("Operation canceled.")
        return ConversationHandler.END

    user_id = context.user_data.get("target_user_id")
    access_level = action

    # Update user access
    user_mgr = get_user_mgr()
    success = user_mgr.update_user_access(user_id, access_level)

    if success:
        await query.edit_message_text(f"✅ User {user_id} access level updated to {access_level.upper()}.")
    else:
        await query.edit_message_text(f"❌ Failed to update user {user_id} access level. Please try again later.")

    return ConversationHandler.END


async def start_add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the add free credits conversation"""
    query = update.callback_query

    await query.edit_message_text(
        "⏱️ Add Free Credits\n\n"
        "Please enter the Telegram user ID of the user you want to give additional free credits to.\n\n"
        "You can use /cancel to cancel this operation."
    )

    return AWAITING_USER_ID


async def process_user_id_for_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user ID for adding credits"""
    try:
        user_id = int(update.message.text.strip())
        context.user_data["target_user_id"] = user_id

        # Check if user exists
        user_mgr = get_user_mgr()
        user = user_mgr.get_user(user_id)

        if not user:
            await update.message.reply_text(
                f"⚠️ User with ID {user_id} not found in the database. "
                "The user needs to start the bot at least once before you can add credits.\n\n"
                "Please enter another user ID or use /cancel to abort:"
            )
            return AWAITING_USER_ID

        # Ask for number of credits
        await update.message.reply_text(
            f"User ID: {user_id}\n"
            f"Username: {user['username'] or 'Not set'}\n"
            f"Name: {user['first_name'] or ''} {user['last_name'] or ''}\n"
            f"Current access: {user['access_level']}\n"
            f"Free queries left: {user['remaining_free_queries']}\n\n"
            "How many free credits do you want to add? (Enter a number)\n"
            "This will be added to their current free credits."
        )
        return AWAITING_FREE_CREDITS

    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid numeric user ID.\nTry again or use /cancel to abort:")
        return AWAITING_USER_ID


async def process_free_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the number of free credits to add"""
    try:
        credits = int(update.message.text.strip())
        if credits <= 0:
            await update.message.reply_text(
                "⚠️ Please enter a positive number of credits.\nTry again or use /cancel to abort:"
            )
            return AWAITING_FREE_CREDITS

        user_id = context.user_data.get("target_user_id")

        # Get current credits and add new ones
        user_mgr = get_user_mgr()
        user = user_mgr.get_user(user_id)
        current_credits = user["remaining_free_queries"]
        new_total = current_credits + credits

        # Update user credits
        success = user_mgr.reset_free_queries(user_id, new_total)

        if success:
            await update.message.reply_text(
                f"✅ Added {credits} free credits to user {user_id}.\nTheir new total is {new_total} credits."
            )
        else:
            await update.message.reply_text(f"❌ Failed to add credits to user {user_id}. Please try again later.")

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid number of credits.\nTry again or use /cancel to abort:")
        return AWAITING_FREE_CREDITS


async def cancel_admin_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current admin conversation"""
    await update.message.reply_text("❌ Operation canceled.\n\nUse /admin to return to the admin dashboard.")
    return ConversationHandler.END


# Conversation Handle
add_premium_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_change_role, pattern="^admin_change_role$")],
    states={
        AWAITING_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_id)],
        AWAITING_ACCESS_LEVEL: [CallbackQueryHandler(process_access_level, pattern="^access_")],
    },
    fallbacks=[CommandHandler("cancel", cancel_admin_conversation)],
)

add_credits_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_add_credits, pattern="^admin_add_credits$")],
    states={
        AWAITING_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_id_for_credits)],
        AWAITING_FREE_CREDITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_free_credits)],
    },
    fallbacks=[CommandHandler("cancel", cancel_admin_conversation)],
)


async def show_user_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("➕ Change User Role", callback_data="admin_change_role")],
        [InlineKeyboardButton("⏱️ Add Free Credits", callback_data="admin_add_credits")],
        [InlineKeyboardButton("◀️ Back to Dashboard", callback_data="admin_dashboard")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("👥 User Management\n\nSelect an action to manage users:", reply_markup=reply_markup)


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_mgr = get_user_mgr()
    user = user_mgr.get_user(user_id)

    if not user or user["access_level"] != "admin":
        await query.edit_message_text("⛔ You don't have admin privileges to use this feature.")
        return

    action = query.data

    if action == "admin_dashboard":
        await show_admin_dashboard(update, context)
    elif action == "admin_stats":
        await show_usage_statistics(update, context)
    elif action == "admin_users":
        await show_user_management(update, context)
    elif action == "admin_show_users":
        await show_recent_users(update, context)
