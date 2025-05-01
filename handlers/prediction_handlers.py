import asyncio

from telegram import Update
from telegram.ext import ContextTypes, Application, CommandHandler

from services import red
from parser import red_parser

DEFAULT_DURATION = 10 # minutes
DEFAULT_INTERVAL = 60 # seconds

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

async def prediction_loop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    code = context.user_data.get("code")
    interval = context.user_data.get("default_interval", DEFAULT_INTERVAL)
    duration = context.user_data.get("default_duration", DEFAULT_DURATION)
    token = context.user_data.get('red_token')

    await update.message.reply_text(f"Starting prediction for {code} stop, during {duration} minutes, every {interval} seconds")

    try:
        for _ in range(duration*60//interval):
            prediction = red.get_prediction(token, code)
            parsed_prediction = red_parser.red_parser(prediction)
            reply = red_parser.reply_text(parsed_prediction)
            # await update.message.reply_text(prediction)
            await update.message.reply_text(reply)
            await asyncio.sleep(interval)
        await update.message.reply_text("💯 Finished sending predictions!")
    except asyncio.CancelledError:
        await update.message.reply_text("⛔️ Prediction updates have been cancelled.")
        raise


async def prediction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'prediction_task' in context.user_data and not context.user_data['prediction_task'].done():
        await update.message.reply_text("⚠️ Prediction updates are already running!")
        return
    
    token = red.get_token()
    if not token:
        await update.message.reply_text("🚫 Couldn't get a token from red.cl")
        return
    context.user_data['red_token'] = token

    if len(context.args) != 0:
        context.user_data['code']  = context.args[0]
    elif context.user_data.get('default_code'):
        context.user_data['code']  = context.user_data.get('default_code')
    else:
        await update.message.reply_text('⚠️ A code must be provided or setted with /default_code PI445 for example')
        return
    
    task = asyncio.create_task(prediction_loop(update, context))
    context.user_data['prediction_task'] = task


async def stop_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    task = context.user_data.get('prediction_task')
    if task and not task.done():
        task.cancel()
        await update.message.reply_text("❗️ Cancelling prediction updates...")
    else:
        await update.message.reply_text("⚠️ No prediction updates are currently running.")

async def default_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        code = context.args[0]
        context.user_data["default_code"] = code
        await update.message.reply_text(f"✅ Default code setted to {code}")
    except:
        await update.message.reply_text(f"❌ a code must be provided")

async def default_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        duration = context.args[0]
        context.user_data["default_duration"] = int(duration)
        await update.message.reply_text(f"✅ Default duration setted to {duration} minutes")
    except:
        await update.message.reply_text(f"❌ invalid duration has been provided")

async def default_interval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        interval = context.args[0]
        context.user_data["default_range"] = int(interval)
        await update.message.reply_text(f"✅ Default range setted to {interval} seconds")
    except:
        await update.message.reply_text(f"❌ invalid interval has been provided")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    code = context.user_data.get("default_code")
    interval = context.user_data.get("default_interval", DEFAULT_INTERVAL)
    duration = context.user_data.get("default_duration", DEFAULT_DURATION)

    await update.message.reply_text(f"ℹ️ Default code setted is {code}, interval is {interval} seconds, during {duration} minutes")

def add_to(app: Application):
    app.add_handler(CommandHandler("prediction", prediction))
    app.add_handler(CommandHandler("p", prediction))

    app.add_handler(CommandHandler("stop_prediction", stop_prediction))
    app.add_handler(CommandHandler("s", stop_prediction))

    app.add_handler(CommandHandler("default_code", default_code))
    app.add_handler(CommandHandler("dc", default_code))

    app.add_handler(CommandHandler("default_interval", default_interval))
    app.add_handler(CommandHandler("di", default_interval))

    app.add_handler(CommandHandler("default_duration", default_duration))
    app.add_handler(CommandHandler("dd", default_duration))

    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("i", info))