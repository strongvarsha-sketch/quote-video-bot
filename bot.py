# bot.py
# Telegram bot: user picks a category, bot builds a quote video and sends it back.
#
# Runs in WEBHOOK mode (not polling) because Render's free plan only offers
# "Web Service" hosting, which needs an app that listens on a port -- a
# polling bot has no port to listen on, so Render would shut it down.
#
# Environment variables needed (set these in Render's dashboard, not in this file):
#   TELEGRAM_BOT_TOKEN     - from @BotFather
#   PEXELS_API_KEY         - from pexels.com/api
#   RENDER_EXTERNAL_URL    - Render sets this automatically, no action needed
#   PORT                   - Render sets this automatically, no action needed
#
# Run locally for testing (polling mode) with: python bot.py --local

import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
)

from quotes import CATEGORIES
import videomaker

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ATTRIBUTION_TEXT = "Empty Mind"  # shown at the bottom of every video


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton(cat["label"], callback_data=key)]
        for key, cat in CATEGORIES.items()
    ]
