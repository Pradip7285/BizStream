import os
import shutil
import tempfile
import asyncio
from datetime import datetime
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

load_dotenv(override=True)

USER_SESSIONS = {}
AUTHORIZED_USERS =list(map(int, os.getenv("AUTHORIZED_USERS", "").split(","))) 

def download_pile_path(user_id):
    return os.path.join(tempfile.gettempdir(), f"{user_id}_bevco_downloads")

def is_user_authorized(user_id):
    return user_id in AUTHORIZED_USERS

def zip_download_folder(download_dir):
    try:
        zip_path = shutil.make_archive(download_dir, 'zip', download_dir)
        print(f"📦 Folder successfully zipped at: {zip_path}")
        shutil.rmtree(download_dir)
        return zip_path
    except Exception as e:
        print(f"❌ Failed to zip folder: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_authorized(user_id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return ConversationHandler.END
    await update.message.reply_text("Hi! Choose a task:\n- /invoice\n- /stock\n- /inventory")

async def invoice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_authorized(user_id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return ConversationHandler.END
    USER_SESSIONS[user_id] = {"module": "invoice"}
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
    except ValueError:
        await update.message.reply_text("❌ Invalid date format. Use DD-MM-YYYY.")
        return

    base_dir = download_pile_path(user_id)
    download_dir = os.path.join(base_dir, "invoice", today)
    os.makedirs(download_dir, exist_ok=True)

    driver = setup_browser(download_dir)
    captcha_path = get_captcha_image(driver, user=user_id)

    USER_SESSIONS[user_id] = {
        "driver": driver,
        "module": "invoice",
        "download_dir": download_dir,
        "date": today
    }

    try:
        with open(captcha_path, 'rb') as captcha_file:
            await update.message.reply_photo(
                photo=InputFile(captcha_file, filename="captcha.png"),
                caption="Please reply with the CAPTCHA text:"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending CAPTCHA: {e}")

async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await initiate_task(update, context, "stock")

async def inventory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await initiate_task(update, context, "inventory")

async def initiate_task(update: Update, context: ContextTypes.DEFAULT_TYPE, module: str):
    user_id = update.effective_user.id
    if not is_user_authorized(user_id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    today = datetime.today().strftime('%d-%m-%Y')
    download_dir = os.path.join(download_pile_path(user_id), module,today)
    os.makedirs(download_dir, exist_ok=True)

    driver = setup_browser(download_dir)
    captcha_path = get_captcha_image(driver, user=user_id)

    USER_SESSIONS[user_id] = {
        "driver": driver,
        "module": module,
        "download_dir": download_dir
    }

    try:
        with open(captcha_path, 'rb') as captcha_file:
            await update.message.reply_photo(
                photo=InputFile(captcha_file, filename="captcha.png"),
                caption="Please reply with the CAPTCHA text:"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending CAPTCHA: {e}")

async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_authorized(user_id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return ConversationHandler.END

    if user_id not in USER_SESSIONS:
        await update.message.reply_text("Session expired. Please try /start again.")
        return ConversationHandler.END

    captcha_input = update.message.text.strip()
    session = USER_SESSIONS[user_id]
    driver = session["driver"]
    module = session["module"]
    download_dir = session["download_dir"]

    # Show progress message
    progress_msg = await update.message.reply_text("⏳ Processing your task... Please wait.")

    try:
        login(driver, captcha_text=captcha_input)

        if module == "invoice":
            await asyncio.to_thread(invoice.scrape_invoice, driver, download_dir, session.get("date"))
        elif module == "stock":
            await asyncio.to_thread(stock.scrape_reports, driver, download_dir)
        elif module == "inventory":
            await asyncio.to_thread(inventory.scrap_inventory, driver, download_dir)

        driver.quit()
        zip_path = await asyncio.to_thread(zip_download_folder, download_dir)

        await progress_msg.delete()

        if zip_path:
            with open(zip_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"{module}.zip",
                    caption="✅ Task completed!"
                )
    except Exception as e:
        await progress_msg.delete()
        await update.message.reply_text(f"❌ Error: {e}")
        driver.quit()
    finally:
        await asyncio.sleep(1)
        try:
            shutil.rmtree(download_pile_path(user_id))
        except Exception as e:
            print(f"Cleanup error: {e}")
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
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("invoice", invoice_command))
    app.add_handler(CommandHandler("stock", stock_command))
    app.add_handler(CommandHandler("inventory", inventory_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, dynamic_router))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
