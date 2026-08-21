import os
import csv
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

# 1. Load keys
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Missing API credentials.")

# 2. Setup Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

CSV_FILE = "expenses.csv"

# Ensure CSV header exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Category", "Amount", "Description"])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! Send any expense (e.g., 'Spent 200 on books').\n"
        "Send /report to download the full CSV file."
    )

# 📄 /report command to download CSV directly in chat
async def send_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "rb") as f:
            await update.message.reply_document(document=f, filename="expenses.csv")
    else:
        await update.message.reply_text("Abhi tak koi expense save nahi hua.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    prompt = (
        f"Extract the expense information from this text: '{user_text}'. "
        "Return a JSON object with keys: category, amount, and description."
    )
    
    response = None
    last_error = ""

    # Force JSON output to guarantee a valid response format
    config = types.GenerateContentConfig(
        response_mime_type="application/json"
    )

    # Try up to 3 times for temporary busy errors
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=config,
            )
            if response:
                break
        except Exception as e:
            last_error = str(e)
            if "503" in last_error and attempt < 2:
                await asyncio.sleep(2)
                continue
            else:
                break

    if not response:
        await update.message.reply_text(f"⚠️ Error: {last_error}")
        return

    try:
        data = json.loads(response.text)
        category = data.get("category", "General")
        amount = data.get("amount", "0")
        description = data.get("description", user_text)
        
        date_today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([date_today, category, amount, description])
            
        await update.message.reply_text(f"✅ Logged:\nCategory: {category}\nAmount: {amount}\nDetails: {description}")
        
    except Exception as e:
        await update.message.reply_text("Format samajh nahi aaya. Aise likhein: 'Spent 200 on books'")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", send_report))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
