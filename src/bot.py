import logging
import asyncio
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

try:
    from telegram.ext import JobQueue as _JobQueue
    _job_queue = _JobQueue()
except (RuntimeError, ImportError):
    _job_queue = None
from src.config import settings
from src.utils.logging import setup_logging
from src.pipeline import process_link
from src.storage.writer import get_link_stats

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    if update.effective_user.id != settings.telegram_user_id:
        return

    await update.message.reply_text(
        "Hi! I'm LinkStash. Send me a link (or a list of links, one per line) and I'll summarize and store them for you."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply with saved link counts and 3 most recent entries."""
    if update.effective_user.id != settings.telegram_user_id:
        return

    stats = get_link_stats()
    total = stats["total"]
    by_category = stats["by_category"]
    recent = stats["recent"]

    lines = [f"📚 *LinkStash Status* — {total} links saved\n"]
    if by_category:
        lines.append("*By category:*")
        for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
            lines.append(f"  • {cat}: {count}")
    if recent:
        lines.append("\n*3 most recent:*")
        for entry in recent:
            lines.append(f"  • [{entry['title']}]({entry['url']}) — {entry['category']}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def _send_processing_result(bot, chat_id: int, url: str) -> None:
    """Process a single URL and send the result back to Telegram."""
    try:
        result = await process_link(url)

        if result.status == "success":
            if result.notify:
                msg = f"✅ **{result.title}** stored in **{result.category}**."
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
                if result.summary and result.summary != "scrape_failed":
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"📝 **Relevant Summary**:\n{result.summary}",
                        parse_mode="Markdown",
                    )
            else:
                await bot.send_message(chat_id=chat_id, text=f"🗑️ Not relevant — saved to bin.")
        elif result.status == "duplicate":
            await bot.send_message(chat_id=chat_id, text=f"⏭️ {url} was already processed. Skipped.")
        else:
            summary = result.summary or ""
            if summary.startswith("rate_limit_error"):
                msg = f"⏳ Rate limited while processing {url}. Try again in a moment."
            elif summary.startswith("scrape_error"):
                msg = f"🌐 Could not fetch {url}. The page may be down or require login."
            elif summary.startswith("llm_error"):
                msg = f"🤖 LLM error processing {url}. Check your OpenAI API key/quota."
            else:
                msg = f"❌ Failed to process {url}.\nReason: {summary}"
            await bot.send_message(chat_id=chat_id, text=msg)
    except Exception as e:
        logger.exception(f"Bot error processing {url}: {e}")
        await bot.send_message(chat_id=chat_id, text=f"❌ Fatal error processing {url}: {str(e)}")


async def process_link_job(context: ContextTypes.DEFAULT_TYPE):
    """Background job to process a single URL."""
    url = context.job.data["url"]
    chat_id = context.job.data["chat_id"]
    await _send_processing_result(context.bot, chat_id, url)


async def _delayed_process_link(bot, chat_id: int, url: str, delay_seconds: float) -> None:
    """Fallback processor when PTB JobQueue is unavailable."""
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)
    await _send_processing_result(bot, chat_id, url)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log unexpected Telegram handler errors."""
    logger.exception("Unhandled Telegram error", exc_info=context.error)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming messages as links."""
    # Ensure it's the authorized user
    if update.effective_user.id != settings.telegram_user_id:
        logger.warning(f"Unauthorized access attempt by user: {update.effective_user.id}")
        return

    text = update.message.text
    if not text:
        return
        
    # Split text by newlines and filter empty lines
    urls = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not urls:
        await update.message.reply_text("Please provide valid URLs.")
        return
        
    # Acknowledge receipt immediately
    await update.message.reply_text(f"Got {len(urls)} link(s), queuing for processing...")
    
    use_job_queue = context.job_queue is not None
    if not use_job_queue:
        logger.warning("PTB JobQueue is unavailable; falling back to asyncio task scheduling.")

    # Enqueue each URL as a separate background job
    for i, url in enumerate(urls):
        if not url.startswith("http"):
            await update.message.reply_text(f"❌ '{url}' is not a valid HTTP/HTTPS URL. Skipped.")
            continue

        delay_seconds = i * 2.0
        if use_job_queue:
            context.job_queue.run_once(
                process_link_job,
                when=delay_seconds,
                data={"url": url, "chat_id": update.effective_chat.id},
                name=f"process_link_{update.effective_message.message_id}_{i}",
            )
        else:
            context.application.create_task(
                _delayed_process_link(context.bot, update.effective_chat.id, url, delay_seconds)
            )

def main():
    """Start the bot."""
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set.")
        sys.exit(1)
        
    if not settings.telegram_user_id:
        logger.error("TELEGRAM_USER_ID is not set.")
        sys.exit(1)

    builder = ApplicationBuilder().token(settings.telegram_bot_token)
    if _job_queue is not None:
        builder = builder.job_queue(_job_queue)
    application = builder.build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("Starting LinkStash Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
