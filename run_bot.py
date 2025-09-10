"""
Script para iniciar o bot do Telegram
"""
import sys
from app.start_bot import run_telegram_bot

if __name__ == "__main__":
    # Para manter compatibilidade, apenas chamamos o run_telegram_bot
    sys.exit(0 if run_telegram_bot() else 1) 