import logging
import os
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv # Opcional: para leer .env

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ApplicationBuilder,
)

from services import red
from parser import red_parser

# --- Configuración ---
load_dotenv() # Carga variables de .env si existe

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PORT = int(os.environ.get("PORT", 8000)) 
NGROK_URL = os.environ.get("NGROK_URL", "PON_AQUI_TU_URL_DE_NGROK_HTTPS") 
SECRET_PATH = os.environ.get("SECRET_PATH", "tu_secreto_123") 
WEBHOOK_URL = f"{NGROK_URL}/{SECRET_PATH}" 

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Handler Simplificado ---
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

# --- Lógica de FastAPI y PTB ---
ptb_app: Application | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona inicio y parada de PTB."""
    global ptb_app
    logger.info("Iniciando lifespan...")

    if not TELEGRAM_TOKEN:
        logger.error("Error: BOT_TOKEN no configurado.")
        return # No continuar si no hay token
    if not NGROK_URL:
        logger.error("Error: NGROK_URL (URL pública de ngrok) no configurada.")
        return # No continuar si no hay URL pública

    # Construir App PTB
    ptb_app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Registrar ÚNICO handler
    ptb_app.add_handler(CommandHandler("hello", hello))
    ptb_app.add_handler(CommandHandler("prediction", prediction))
    ptb_app.add_handler(CommandHandler("stop_prediction", stop_prediction))


    # Inicializar PTB
    await ptb_app.initialize()
    logger.info("Aplicación PTB inicializada.")

    # Establecer Webhook (apuntando a la URL pública de ngrok)
    try:
        await ptb_app.bot.set_webhook(
            url=WEBHOOK_URL,
            allowed_updates=Update.ALL_TYPES,
            # Opcional: usar IP del servidor Nginx si ngrok y nginx están en máquinas distintas
            # ip_address="IP.DE.TU.SERVIDOR.NGINX" 
        )
        logger.info(f"Webhook establecido en {WEBHOOK_URL}")
        webhook_info = await ptb_app.bot.get_webhook_info()
        logger.info(f"Confirmación Webhook: {webhook_info}")
        if webhook_info.url != WEBHOOK_URL:
             logger.warning("¡La URL del webhook establecida difiere de la configurada!")

    except Exception as e:
        logger.error(f"Error al establecer el webhook: {e}", exc_info=True)
        # Podrías decidir detener la app aquí si el webhook falla

    # Iniciar procesos de PTB (necesario para process_update)
    await ptb_app.start()
    logger.info("Aplicación PTB iniciada (modo webhook).")

    yield # FastAPI/Uvicorn se ejecuta aquí

    # --- Limpieza al detener ---
    logger.info("Deteniendo lifespan...")
    if ptb_app:
        logger.info("Deteniendo aplicación PTB...")
        await ptb_app.stop()
        try:
            logger.info("Intentando eliminar webhook...")
            if await ptb_app.bot.delete_webhook():
                logger.info("Webhook eliminado.")
            else:
                logger.warning("No se pudo eliminar el webhook (quizás ya no existía).")
        except Exception as e:
            logger.error(f"Error eliminando webhook: {e}", exc_info=True)
        await ptb_app.shutdown()
        logger.info("Aplicación PTB detenida.")

# Crear Instancia FastAPI
app = FastAPI(lifespan=lifespan)

@app.post(f"/{SECRET_PATH}")
async def telegram_webhook_endpoint(request: Request):
    """Recibe actualizaciones de Telegram via POST."""
    if not ptb_app:
        logger.error("Webhook llamado pero PTB App no está lista.")
        return Response(status_code=503) # Service Unavailable

    try:
        data = await request.json()
        update = Update.de_json(data, ptb_app.bot)
        logger.info(f"Update recibido: {update.update_id}")
        await ptb_app.process_update(update)
        return Response(status_code=200) # OK
    except Exception as e:
        logger.error(f"Error procesando update: {e}", exc_info=True)
        return Response(status_code=500) # Internal Server Error

@app.get("/")
async def health_check():
    """Verifica que el servidor FastAPI esté vivo."""
    return {"status": "FastAPI está corriendo"}

# --- Punto de entrada (para desarrollo/pruebas locales) ---
if __name__ == "__main__":
    # Asegúrate de que las variables de entorno estén seteadas antes de correr
    print(f"Verifica que BOT_TOKEN esté configurado.")
    print(f"Verifica que NGROK_URL sea: {NGROK_URL}")
    print(f"Corriendo Uvicorn en http://127.0.0.1:{PORT}")
    print(f"El webhook se configurará en: {WEBHOOK_URL}")
    print("Nginx debe estar corriendo y ngrok debe estar apuntando a Nginx.")
    
    uvicorn.run(
        "bot_webhook:app", 
        host="127.0.0.1", # Escucha solo localmente
        port=PORT,         # Puerto 8000 (o el que configuraste)
        reload=True        # Reinicia en cambios (¡solo para desarrollo!)
    )