import os
import shutil
import tempfile
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from module.login import setup_browser, get_captcha_image, login
import module.invoice as invoice
import module.stock as stock
import module.inventory as inventory
from dotenv import load_dotenv
from threading import Lock

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv(override=True)

# Thread-safe user session store
class SessionStore:
    def __init__(self):
        self._sessions = {}
        self._lock = Lock()

    def get(self, user_id):
        with self._lock:
            session = self._sessions.get(user_id)
            if session and 'created_at' in session:
                # Check if session is expired (30 minutes)
                if datetime.now() - session['created_at'] > timedelta(minutes=30):
                    logger.info(f"Session expired for user {user_id}")
                    del self._sessions[user_id]
                    return None
            return session

    def set(self, user_id, value):
        with self._lock:
            value['created_at'] = datetime.now()
            self._sessions[user_id] = value

    def pop(self, user_id):
        with self._lock:
            return self._sessions.pop(user_id, None)

    def clear(self, user_id):
        with self._lock:
            if user_id in self._sessions:
                del self._sessions[user_id]

USER_SESSIONS = SessionStore()
AUTHORIZED_USERS = list(map(int, os.getenv("AUTHORIZED_USERS", "").split(",")))

# --- Helpers ---
def download_pile_path(user_id):
    return os.path.join(tempfile.gettempdir(), f"{user_id}_bevco_downloads")

def is_user_authorized(user_id):
    return user_id in AUTHORIZED_USERS

def zip_download_folder(download_dir):
    try:
        zip_path = shutil.make_archive(download_dir, 'zip', download_dir)
        logger.info(f"📦 Folder successfully zipped at: {zip_path}")
        shutil.rmtree(download_dir)
        return zip_path
    except Exception as e:
        logger.error(f"❌ Failed to zip folder: {e}")
        return None

def cleanup_user(user_id):
    try:
        shutil.rmtree(download_pile_path(user_id), ignore_errors=True)
        logger.info(f"Cleaned up user {user_id} resources")
    except Exception as e:
        logger.error(f"Cleanup error for user {user_id}: {e}")
    USER_SESSIONS.clear(user_id)

async def safe_browser_quit(driver):
    """Safely quit browser driver with error handling"""
    try:
        if driver:
            driver.quit()
            logger.info("Browser driver closed successfully")
    except Exception as e:
        logger.error(f"Error closing browser driver: {e}")

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} started the bot")
    
    if not is_user_authorized(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}")
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return ConversationHandler.END
    
    await update.message.reply_text("Hi! Choose a task:\n- /invoice\n- /stock\n- /inventory")

async def invoice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested invoice command")
    
    if not is_user_authorized(user_id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return ConversationHandler.END
    
    USER_SESSIONS.set(user_id, {"module": "invoice"})
    await update.message.reply_text("📅 Please send the date for the invoice in DD-MM-YYYY format.")

async def handle_invoice_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()

    if not is_user_authorized(user_id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return ConversationHandler.END

    try:
        parsed_date = datetime.strptime(user_input, '%d-%m-%Y')
        today = parsed_date.strftime('%d-%m-%Y')
        logger.info(f"User {user_id} requested invoice for date: {today}")
    except ValueError:
        await update.message.reply_text("❌ Invalid date format. Use DD-MM-YYYY.")
        return

    try:
        base_dir = download_pile_path(user_id)
        download_dir = os.path.join(base_dir, "invoice", today)
        os.makedirs(download_dir, exist_ok=True)

        driver = await asyncio.to_thread(setup_browser, download_dir)
        if not driver:
            await update.message.reply_text("❌ Failed to initialize browser. Please try again.")
            return

        captcha_path = await asyncio.to_thread(get_captcha_image, driver, user=user_id)
        if not captcha_path:
            await safe_browser_quit(driver)
            await update.message.reply_text("❌ Failed to get CAPTCHA. Please try again.")
            return

        USER_SESSIONS.set(user_id, {
            "driver": driver,
            "module": "invoice",
            "download_dir": download_dir,
            "date": today
        })

        with open(captcha_path, 'rb') as captcha_file:
            await update.message.reply_photo(
                photo=InputFile(captcha_file, filename="captcha.png"),
                caption="Please reply with the CAPTCHA text:"
            )
    except Exception as e:
        logger.error(f"Error in handle_invoice_date for user {user_id}: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await initiate_task(update, context, "stock")

async def inventory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await initiate_task(update, context, "inventory")

async def initiate_task(update: Update, context: ContextTypes.DEFAULT_TYPE, module: str):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested {module} command")
    
    if not is_user_authorized(user_id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    try:
        today = datetime.today().strftime('%d-%m-%Y')
        download_dir = os.path.join(download_pile_path(user_id), module, today)
        os.makedirs(download_dir, exist_ok=True)

        driver = await asyncio.to_thread(setup_browser, download_dir)
        if not driver:
            await update.message.reply_text("❌ Failed to initialize browser. Please try again.")
            return

        captcha_path = await asyncio.to_thread(get_captcha_image, driver, user=user_id)
        if not captcha_path:
            await safe_browser_quit(driver)
            await update.message.reply_text("❌ Failed to get CAPTCHA. Please try again.")
            return

        USER_SESSIONS.set(user_id, {
            "driver": driver,
            "module": module,
            "download_dir": download_dir
        })

        with open(captcha_path, 'rb') as captcha_file:
            await update.message.reply_photo(
                photo=InputFile(captcha_file, filename="captcha.png"),
                caption="Please reply with the CAPTCHA text:"
            )
    except Exception as e:
        logger.error(f"Error in initiate_task for user {user_id}, module {module}: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_authorized(user_id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return ConversationHandler.END

    session = USER_SESSIONS.get(user_id)
    if not session:
        await update.message.reply_text("Session expired. Please try /start again.")
        return ConversationHandler.END

    captcha_input = update.message.text.strip()
    driver = session["driver"]
    module = session["module"]
    download_dir = session["download_dir"]
    date = session.get("date")

    progress_msg = await update.message.reply_text("⏳ Processing your task... Please wait.")

    try:
        await asyncio.to_thread(login, driver, captcha_text=captcha_input)

        if module == "invoice":
            await asyncio.to_thread(invoice.scrape_invoice, driver, download_dir, date)
        elif module == "stock":
            await asyncio.to_thread(stock.scrape_reports, driver, download_dir)
        elif module == "inventory":
            await asyncio.to_thread(inventory.scrap_inventory, driver, download_dir)

        await safe_browser_quit(driver)
        zip_path = await asyncio.to_thread(zip_download_folder, download_dir)

        await progress_msg.delete()

        if zip_path:
            with open(zip_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"{module}.zip",
                    caption="✅ Task completed!"
                )
                logger.info(f"Successfully completed {module} task for user {user_id}")
        else:
            await update.message.reply_text("❌ Failed to create zip file.")
    except Exception as e:
        logger.error(f"Error in handle_captcha for user {user_id}, module {module}: {e}")
        await progress_msg.delete()
        await update.message.reply_text(f"❌ Error: {str(e)}")
        await safe_browser_quit(driver)
    finally:
        await asyncio.sleep(1)
        cleanup_user(user_id)
        return ConversationHandler.END

async def dynamic_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = USER_SESSIONS.get(user_id)

    if not session:
        await update.message.reply_text("Please start with /invoice, /stock, or /inventory.")
        return

    if session.get("module") == "invoice" and "driver" not in session:
        await handle_invoice_date(update, context)
    else:
        await handle_captcha(update, context)

def main():
    try:
        app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("invoice", invoice_command))
        app.add_handler(CommandHandler("stock", stock_command))
        app.add_handler(CommandHandler("inventory", inventory_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, dynamic_router))

        logger.info("🤖 Bot is running...")
        app.run_polling()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()
