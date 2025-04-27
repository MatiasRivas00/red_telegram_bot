from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from services import red
from parser import red_parser
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

# --- New async function for sending predictions ---
async def prediction_loop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        token = context.user_data.get('red_token')
        for _ in range(10):
            prediction = red.get_prediction(token, 'PI445')
            parsed_prediction = red_parser.red_parser(prediction)
            reply = red_parser.reply_text(parsed_prediction)
            # await update.message.reply_text(prediction)
            await update.message.reply_text(reply)
            await asyncio.sleep(60)
        await update.message.reply_text("💯 Finished sending predictions!")
    except asyncio.CancelledError:
        await update.message.reply_text("⛔️ Prediction updates have been cancelled.")
        raise


async def prediction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if there's already a prediction running
    if 'prediction_task' in context.user_data and not context.user_data['prediction_task'].done():
        await update.message.reply_text("⚠️ Prediction updates are already running!")
        return
    
    # get token
    token = red.get_token()
    if not token:
        await update.message.reply_text("🚫 Couldn't get a token from red.cl")
        return
    context.user_data['red_token'] = token

    await update.message.reply_text("✅ Starting prediction updates every minute for 10 minutes...")
    
    task = asyncio.create_task(prediction_loop(update, context))
    context.user_data['prediction_task'] = task


async def stop_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    task = context.user_data.get('prediction_task')
    if task and not task.done():
        task.cancel()
        await update.message.reply_text("❗️ Cancelling prediction updates...")
    else:
        await update.message.reply_text("⚠️ No prediction updates are currently running.")


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("prediction", prediction))
app.add_handler(CommandHandler("stop_prediction", stop_prediction))



print('Bot is now running')
app.run_polling()