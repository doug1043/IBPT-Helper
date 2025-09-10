"""
Arquivo de configuração para automação IBPT
"""
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# URL base do IBPT
IBPT_BASE_URL = os.getenv("URL_IBPT")

# Credenciais de login
USERNAME = os.getenv("IBPT_USERNAME")
PASSWORD = os.getenv("IBPT_PASSWORD")

# CNPJ da empresa
CNPJ = os.getenv("CNPJ_EMPRESA")

# Configurações da tabela
ESTADOS_STR = os.getenv("ESTADOS")
ESTADOS = [estado.strip() for estado in ESTADOS_STR.split(",")] if ESTADOS_STR else []
OUTPUT_FILE = "data/tabela_aliquotas_ibpt.zip"

# Configurações de timeout
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "30"))
DELAY_SECONDS = int(os.getenv("DELAY_SECONDS", "10"))

# Configurações opcionais para log
LOG_FILE = "logs/ibpt_auto_update.log"
ENABLE_DEBUG = os.getenv("ENABLE_DEBUG", "true").lower() == "true"

# Configurações do Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME")
GRUPOS_FILE = "data/grupos.json" 