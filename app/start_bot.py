"""
Script para iniciar o bot do Telegram
"""
import os
import datetime
from app.telegram.instancia_bot import obter_instancia_bot
from app.utils.config import TELEGRAM_TOKEN, GRUPOS_FILE, LOG_FILE
from app.utils.setup import configurar_logging, garantir_diretorios

# Configuração do logger
logger = configurar_logging("logs/telegram_bot.log")

def run_telegram_bot():
    """
    Função que inicia o bot do Telegram
    """
    try:
        # Criar diretórios necessários
        garantir_diretorios([LOG_FILE, GRUPOS_FILE])
        
        logger.info("=" * 50)
        logger.info("INICIANDO BOT DO TELEGRAM")
        
        if not TELEGRAM_TOKEN:
            logger.error("Token do Telegram não configurado!")
            return False
        
        # Iniciar o bot usando o singleton
        bot = obter_instancia_bot()
        
        # Iniciar polling
        logger.info("Bot iniciado. Pressione Ctrl+C para encerrar.")
        bot.start_polling()
        
        return True
        
    except KeyboardInterrupt:
        logger.info("Bot encerrado pelo usuário.")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {str(e)}")
        return False

# Manter compatibilidade com versões anteriores
main = run_telegram_bot

if __name__ == "__main__":
    run_telegram_bot() 