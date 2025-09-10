#!/bin/bash

echo "🐳 IBPT BOT - Gerando Imagem Docker"
echo "=================================="

# Verificar se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando. Inicie o Docker primeiro."
    exit 1
fi

# Gerar apenas a imagem (sem montar container)
echo "📦 Gerando imagem ibpt-bot:latest..."
docker build -t ibpt-bot:latest .

if [ $? -eq 0 ]; then
    echo "✅ Imagem gerada com sucesso!"
    echo ""
    echo "📋 Próximos passos:"
    echo "1. Copie o arquivo env.example para .env"
    echo "2. Configure suas credenciais no arquivo .env"
    echo "3. Use o docker-compose.yml no Portainer"
    echo ""
    echo "🎉 Imagem pronta para usar no Portainer!"
    echo "📋 Use o arquivo docker-compose.yml no Portainer"
else
    echo "❌ Erro ao gerar a imagem. Verifique os logs acima."
    exit 1
fi 