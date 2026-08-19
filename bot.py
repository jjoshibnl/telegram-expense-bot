import os
import csv
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# 1. Load variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Check if keys exist
if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Missing API credentials. Please set TELEGRAM_BOT_TOKEN and GEMINI_API_KEY in your .env file.")

# 2. Configure the Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

CSV_FILE = "expenses.csv"

# Ensure CSV header exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Category", "Amount", "Description"])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me your expense details (e.g., 'Spent 200 on groceries'), and I will log it for you.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    prompt = (
        f"Extract the expense information from this text: '{user_text}'. "
        "Return ONLY a comma-separated format like: Category, Amount, Description. "
        "Do not include any extra text, headings, or markdown."
    )

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        parsed_data = [item.strip() for item in response.text.strip().split(",")]

        if len(parsed_data) >= 3:
            category, amount, description = parsed_data[0], parsed_data[1], ",".join(parsed_data[2:])
            date_today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([date_today, category, amount, description])

            await update.message.reply_text(f"Logged:\nCategory: {category}\nAmount: {amount}\nDetails: {description}")
        else:
            await update.message.reply_text("Could not parse expense format. Please try again.")
    except Exception as e:
        await update.message.reply_text(f"Error processing expense: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()