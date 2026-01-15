#!/usr/bin/env python3
"""
GAIA Emergency Telegram Bot

Standalone bot that can trigger GAIA restores remotely.
Requires 2FA confirmation for any destructive action.

This bot runs independently of n8n and all other services.
"""

import os
import sys
import logging
import subprocess
import pyotp
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Configuration
CONFIG_DIR = Path("/opt/leveredge/gaia")
TOKEN_FILE = CONFIG_DIR / ".telegram_token"
SECRET_FILE = CONFIG_DIR / ".2fa_secret"
AUTHORIZED_USERS_FILE = CONFIG_DIR / ".authorized_users"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - GAIA-BOT - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/gaia-emergency-bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('GAIA-BOT')

# Load configuration
def load_config():
    config = {}

    if TOKEN_FILE.exists():
        config['token'] = TOKEN_FILE.read_text().strip()
    else:
        logger.error(f"Token file not found: {TOKEN_FILE}")
        sys.exit(1)

    if SECRET_FILE.exists():
        config['2fa_secret'] = SECRET_FILE.read_text().strip()
    else:
        # Generate new 2FA secret
        secret = pyotp.random_base32()
        SECRET_FILE.write_text(secret)
        SECRET_FILE.chmod(0o600)
        config['2fa_secret'] = secret
        logger.info(f"Generated new 2FA secret. Add to authenticator app:")
        logger.info(f"Secret: {secret}")

    if AUTHORIZED_USERS_FILE.exists():
        config['authorized_users'] = [
            int(uid.strip())
            for uid in AUTHORIZED_USERS_FILE.read_text().strip().split('\n')
            if uid.strip()
        ]
    else:
        logger.error(f"Authorized users file not found: {AUTHORIZED_USERS_FILE}")
        sys.exit(1)

    return config

CONFIG = load_config()
TOTP = pyotp.TOTP(CONFIG['2fa_secret'])

# Pending operations (waiting for 2FA)
pending_operations = {}

def is_authorized(user_id: int) -> bool:
    return user_id in CONFIG['authorized_users']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized. This incident has been logged.")
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        return

    await update.message.reply_text(
        "*GAIA Emergency Control*\n\n"
        "Available commands:\n"
        "/status - System health check\n"
        "/list - List available backups\n"
        "/restore <target> - Restore (requires 2FA)\n"
        "/fullrestore - Full system restore (requires 2FA)\n\n"
        "Targets: control-plane, prod, dev",
        parse_mode='Markdown'
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check system health"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return

    await update.message.reply_text("Checking system health...")

    try:
        result = subprocess.run(
            ['python3', '/opt/leveredge/gaia/gaia.py', 'health'],
            capture_output=True,
            text=True,
            timeout=30
        )
        await update.message.reply_text(f"```\n{result.stdout}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def list_backups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List available backups"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return

    try:
        result = subprocess.run(
            ['python3', '/opt/leveredge/gaia/gaia.py', 'list'],
            capture_output=True,
            text=True,
            timeout=30
        )
        await update.message.reply_text(f"```\n{result.stdout}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiate restore (requires 2FA)"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /restore <target>\n"
            "Targets: control-plane, prod, dev"
        )
        return

    target = context.args[0]
    if target not in ['control-plane', 'prod', 'dev']:
        await update.message.reply_text("Invalid target. Use: control-plane, prod, dev")
        return

    # Store pending operation
    pending_operations[user_id] = {
        'action': 'restore',
        'target': target
    }

    await update.message.reply_text(
        f"*Restore {target}*\n\n"
        f"This will restore {target} from the latest backup.\n"
        f"Current data will be replaced.\n\n"
        f"Enter your 2FA code to confirm:",
        parse_mode='Markdown'
    )

async def fullrestore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiate full system restore (requires 2FA)"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return

    pending_operations[user_id] = {
        'action': 'fullrestore'
    }

    await update.message.reply_text(
        "*FULL SYSTEM RESTORE*\n\n"
        "This will restore EVERYTHING:\n"
        "- Control plane\n"
        "- Production environment\n"
        "- Development environment\n\n"
        "ALL CURRENT DATA WILL BE REPLACED\n\n"
        "Enter your 2FA code to confirm:",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages (for 2FA codes)"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        return

    if user_id not in pending_operations:
        return

    code = update.message.text.strip()

    # Verify 2FA
    if not TOTP.verify(code):
        await update.message.reply_text("Invalid 2FA code. Try again or /cancel")
        return

    operation = pending_operations.pop(user_id)

    if operation['action'] == 'restore':
        target = operation['target']
        await update.message.reply_text(f"Starting restore of {target}...")

        try:
            result = subprocess.run(
                ['python3', '/opt/leveredge/gaia/gaia.py', 'restore', target, '--yes'],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode == 0:
                await update.message.reply_text(f"Restore of {target} complete!")
            else:
                await update.message.reply_text(f"Restore failed:\n```\n{result.stderr}\n```", parse_mode='Markdown')

        except subprocess.TimeoutExpired:
            await update.message.reply_text("Restore timed out")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    elif operation['action'] == 'fullrestore':
        await update.message.reply_text("Starting FULL SYSTEM RESTORE...")
        await update.message.reply_text("This may take several minutes...")

        try:
            result = subprocess.run(
                ['python3', '/opt/leveredge/gaia/gaia.py', 'restore', 'full', '--yes'],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )

            if result.returncode == 0:
                await update.message.reply_text("FULL SYSTEM RESTORE complete!")
            else:
                await update.message.reply_text(f"Restore failed:\n```\n{result.stderr}\n```", parse_mode='Markdown')

        except subprocess.TimeoutExpired:
            await update.message.reply_text("Restore timed out")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel pending operation"""
    user_id = update.effective_user.id

    if user_id in pending_operations:
        del pending_operations[user_id]
        await update.message.reply_text("Operation cancelled.")
    else:
        await update.message.reply_text("No pending operation.")

def main():
    """Run the bot"""
    logger.info("Starting GAIA Emergency Bot...")

    application = Application.builder().token(CONFIG['token']).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("list", list_backups))
    application.add_handler(CommandHandler("restore", restore))
    application.add_handler(CommandHandler("fullrestore", fullrestore))
    application.add_handler(CommandHandler("cancel", cancel))

    # Handle text messages (for 2FA codes)
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
