import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application

from handlers import prediction_handlers

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PORT = int(os.environ.get("PORT")) 
NGROK_URL = os.environ.get("NGROK_URL") 
SECRET_PATH = os.environ.get("SECRET_PATH") 
WEBHOOK_URL = f"{NGROK_URL}/{SECRET_PATH}" 

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

telegram_app: Application | None = None

async def app_init():
    global telegram_app
    logger.info("Iniciando lifespan")

    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    prediction_handlers.add_to(telegram_app)

    await telegram_app.initialize()

    logger.info("Aplicación PTB inicializada.")

    try:
        await telegram_app.bot.set_webhook(
            url=WEBHOOK_URL,
            allowed_updates=Update.ALL_TYPES,
        )
        logger.info(f"Webhook establecido en {WEBHOOK_URL}")
        webhook_info = await telegram_app.bot.get_webhook_info()
        logger.info(f"Confirmación Webhook: {webhook_info}")

    except Exception as e:
        logger.error(f"Error al establecer el webhook: {e}", exc_info=True)

    await telegram_app.start()
    logger.info("Aplicación PTB iniciada (modo webhook).")

async def app_kill():
    global telegram_app
    logger.info("⏳ Deteniendo lifespan")
    if telegram_app:
        logger.info("⏳ Deteniendo aplicación PTB")
        await telegram_app.stop()
        try:
            logger.info("⏳ Intentando eliminar webhook")
            if await telegram_app.bot.delete_webhook():
                logger.info("✅ Webhook eliminado")
            else:
                logger.warning("⚠️ No se pudo eliminar el webhook")
        except Exception as e:
            logger.error(f"❌ Error eliminando webhook: {e}", exc_info=True)
        await telegram_app.shutdown()
        logger.info("✅Aplicación PTB detenida.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await app_init()
    yield
    await app_kill()

app = FastAPI(lifespan=lifespan)

@app.post(f"/{SECRET_PATH}")
async def telegram_webhook_endpoint(request: Request):
    if not telegram_app:
        logger.error("Webhook llamado pero PTB App no está lista.")
        return Response(status_code=503) # Service Unavailable

    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        logger.info(f"Update recibido: {update.update_id}")
        await telegram_app.process_update(update)
        return Response(status_code=200) # OK
    except Exception as e:
        logger.error(f"Error procesando update: {e}", exc_info=True)
        return Response(status_code=500) # Internal Server Error

@app.get("/")
async def health_check():
    """Verifica que el servidor FastAPI esté vivo."""
    return {"status": "FastAPI está corriendo"}

if __name__ == "__main__":
    print(f"Corriendo Uvicorn en http://127.0.0.1:{PORT}")
    print(f"El webhook se configurará en: {WEBHOOK_URL}")
    
    uvicorn.run(
        "bot_webhook:app", 
        host="127.0.0.1", # Escucha solo localmente
        port=PORT,         # Puerto 8000 (o el que configuraste)
        reload=True        # Reinicia en cambios (¡solo para desarrollo!)
    )