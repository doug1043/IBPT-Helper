FROM python:3.10-alpine

# Instalar dependências do sistema necessárias
RUN apk add --no-cache gcc musl-dev dcron

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de requisitos e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código-fonte
COPY . .

# Criar diretórios necessários
RUN mkdir -p logs data

# Garantir que os arquivos de log e dados sejam criados e com permissões corretas
RUN touch logs/ibpt_auto_update.log logs/telegram_bot.log logs/cron.log data/last_version_downloaded.txt
RUN chmod -R 777 logs data

# Configurar o cron job para verificar a tabela IBPT
RUN echo "0 7 * * * cd /app && python /app/run.py >> /app/logs/ibpt_auto_update.log 2>&1" > /etc/crontabs/root

# Criar script de inicialização
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'echo "Iniciando IBPT BOT..."' >> /app/start.sh && \
    echo 'python /app/run.py' >> /app/start.sh && \
    echo 'crond -f &' >> /app/start.sh && \
    echo 'python /app/run_bot.py' >> /app/start.sh && \
    chmod +x /app/start.sh

# Comando padrão para iniciar
CMD ["/app/start.sh"] 