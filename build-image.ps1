Write-Host " IBPT BOT - Gerando Imagem Docker" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

# Verificar se o Docker está rodando
try {
    docker info | Out-Null
} catch {
    Write-Host " Docker não está rodando. Inicie o Docker primeiro." -ForegroundColor Red
    exit 1
}

# Gerar apenas a imagem (sem montar container)
Write-Host " Gerando imagem ibpt-bot:latest..." -ForegroundColor Yellow
docker build -t ibpt-bot:latest .

if ($LASTEXITCODE -eq 0) {
    Write-Host " Imagem gerada com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host " Próximos passos:" -ForegroundColor Cyan
    Write-Host "1. Copie o arquivo env.example para .env" -ForegroundColor White
    Write-Host "2. Configure suas credenciais no arquivo .env" -ForegroundColor White
    Write-Host "3. Use o docker-compose.yml no Portainer" -ForegroundColor White
    Write-Host ""
    Write-Host " Imagem pronta para usar no Portainer!" -ForegroundColor Green
    Write-Host " Use o arquivo docker-compose.yml no Portainer" -ForegroundColor Cyan
} else {
    Write-Host " Erro ao gerar a imagem. Verifique o log acima." -ForegroundColor Red
}
