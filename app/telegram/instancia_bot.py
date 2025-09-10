"""
Instância singleton do bot do Telegram
"""
from app.telegram.bot import TelegramBot
from app.utils.config import TELEGRAM_TOKEN, GRUPOS_FILE

_instancia_bot = None

def obter_instancia_bot():
    """Obter ou criar a instância singleton do bot"""
    global _instancia_bot
    if _instancia_bot is None:
        _instancia_bot = TelegramBot(TELEGRAM_TOKEN, GRUPOS_FILE)
    return _instancia_bot
