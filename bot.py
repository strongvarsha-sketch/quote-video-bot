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
    await update.message.reply_text(
        "Pick a quote video style:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def on_category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data
    category = CATEGORIES.get(key)
    if not category:
        await query.edit_message_text("Something went wrong, try /start again.")
        return

    await query.edit_message_text(f"Making your {category['label']} video... give me a minute ⏳")

    quote = random.choice(category["quotes"])
    keywords = category["photo_keywords"]

    tmp = videomaker.TMP_DIR
    photo_dir = os.path.join(tmp, f"{key}_{query.message.chat_id}")
    os.makedirs(photo_dir, exist_ok=True)
    video_path = os.path.join(tmp, f"{key}_video.mp4")
    voice_path = os.path.join(tmp, f"{key}_voice.mp3")

    try:
        photo_paths = videomaker.fetch_photos(keywords, count=3, out_dir=photo_dir)
        lang = category.get("lang", "en")
        has_voice = videomaker.make_voice(quote, voice_path, lang=lang)
        videomaker.build_video(
            quote=quote,
            attribution=ATTRIBUTION_TEXT,
            photo_paths=photo_paths,
            out_path=video_path,
            duration=20,
            voice_path=voice_path if has_voice else None,
            lang=lang,
        )
        with open(video_path, "rb") as f:
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=f,
                caption=f'"{quote}"',
            )
    except Exception as e:
        log.exception("Video generation failed")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Sorry, something went wrong making the video: {e}",
        )
    finally:
        import shutil
        if os.path.isdir(photo_dir):
            shutil.rmtree(photo_dir, ignore_errors=True)
        for p in (video_path, voice_path):
            if os.path.exists(p):
                os.remove(p)


def main():
    import sys

    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_category_chosen))

    if "--local" in sys.argv:
        # For testing on your own computer only.
        log.info("Bot starting in local polling mode...")
        app.run_polling()
        return

    # Production mode on Render: webhook, listening on the assigned port.
    port = int(os.environ.get("PORT", 10000))
    external_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not external_url:
        raise RuntimeError(
            "RENDER_EXTERNAL_URL is not set. This is expected to be provided "
            "automatically by Render -- if you're testing locally, run with --local instead."
        )
    log.info("Bot starting in webhook mode at %s", external_url)
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{external_url}/{BOT_TOKEN}",
    )


if __name__ == "__main__":
    main()
    
