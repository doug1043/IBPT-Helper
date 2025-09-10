# Sistema de Automação IBPT com Verificação Inteligente de Versões

Este sistema automatiza o download da tabela de alíquotas do IBPT, verificando automaticamente se há novas versões disponíveis antes de realizar o download e distribuindo via Telegram.

## 🚀 Funcionalidades

- **Verificação Automática de Versões**: Compara a versão atual do site com a última baixada
- **Download Inteligente**: Só baixa quando há uma nova versão disponível
- **Comparação por Data de Vigência**: Usa a data de vigência para determinar se há atualizações
- **Histórico de Versões**: Mantém registro das versões baixadas
- **Execução Programada**: Compatível com cron jobs para execução automática
- **Múltiplos Modos**: Normal, forçado e apenas verificação
- **Envio via Telegram**: Distribui automaticamente a tabela para grupos cadastrados
- **Gerenciamento de Grupos**: Sistema para adicionar, remover e gerenciar grupos ativos/inativos
- **Proteção contra Spam**: Sistema de rate limiting e blacklist para evitar abusos

## 🤖 Comandos do Bot

- `/start` - Registra o grupo para receber notificações automáticas.
- `/help` - Exibe a mensagem de ajuda com todos os comandos.
- `/status` - Verifica a versão e data de vigência da tabela atual no sistema.
- `/tabela UF` - Solicita o envio da tabela de um estado específico (ex: `/tabela SP`).
- `/remover` - Desativa as notificações para o grupo.
- `/admin` - Acesso a comandos administrativos (apenas para IDs autorizados).

## 🐳 Instalação via Docker (Recomendado)

### Permissões 
```bash
chmod +x build-image.sh
```

### 1. Gerar a Imagem

#### **Linux/Mac:**
```bash
./build-image.sh
```

#### **Windows PowerShell:**
```powershell
.\build-image.ps1
```

#### **Comando Manual:**
```bash
docker build -t ibpt-bot:latest .
```

### 2. Configuração

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# ========================================
# CREDENCIAIS OBRIGATÓRIAS
# ========================================

#URL Base IBPT
URL_IBPT=https://deolhonoimposto.ibpt.org.br

# Credenciais do IBPT (OBRIGATÓRIO)
IBPT_USERNAME=seu_usuario_ibpt
IBPT_PASSWORD=sua_senha_ibpt

# Configurações Empresa
CNPJ_EMPRESA=12345678910

# Configurações do Telegram (OBRIGATÓRIO)
TELEGRAM_TOKEN=seu_token_telegram
TELEGRAM_BOT_USERNAME=seu_bot_username
ADMIN_IDS=12345,54321,...

# Estados para verificar (OBRIGATÓRIO)
ESTADOS=SP,RJ,MG,RS,PR,SC,GO,MT,MS,RO,AC,AM,RR,PA,AP,TO,MA,PI,CE,RN,PB,PE,AL,SE,BA,ES,DF

# ========================================
# CONFIGURAÇÕES OPCIONAIS
# ========================================

# Configurações de tentativas
MAX_ATTEMPTS=30
DELAY_SECONDS=10

# Debug (true/false)
ENABLE_DEBUG=true

# Configurações do cron (padrão: 7h da manhã)
CRON_SCHEDULE=0 7 * * *

# Timezone
TZ=America/Sao_Paulo
```

### 3. Instalar no Portainer ou via Docker Compose

```bash
docker-compose up -d
```

### 4. Comandos Úteis

```bash
# Ver logs
docker logs ibpt-bot

# Parar o container
docker stop ibpt-bot

# Reiniciar o container
docker restart ibpt-bot

# Ver status
docker ps
```

## 📁 Estrutura do Projeto

```
├── app/                  # Código principal
│   ├── core/             # Funcionalidades principais
│   │   ├── ibpt_automation.py  # Automação do download
│   │   └── version_checker.py  # Verificador de versões
│   ├── telegram/         # Funcionalidades do bot do Telegram
│   │   └── bot.py        # Implementação do bot
│   └── utils/            # Utilitários
│       ├── config.py     # Configurações do sistema
│       └── grupos_manager.py # Gerenciamento de grupos do Telegram
├── data/                 # Arquivos de dados
│   ├── grupos.json       # Registro de grupos com status ativo/inativo
│   ├── last_version_downloaded.txt # Registro da última versão
│   └── tabela_aliquotas_ibpt.zip  # Tabela baixada
├── logs/                 # Arquivos de log
│   ├── ibpt_auto_update.log # Log da automação
│   └── telegram_bot.log  # Log do bot do Telegram
├── run.py                # Script para executar a automação
└── run_bot.py            # Script para iniciar o bot do Telegram
```

## ⚙️ Configuração Manual (Sem Docker)

### **Dependências**

O projeto usa as seguintes dependências principais:

```bash
# Instalar dependências básicas
pip install -r requirements.txt
```

#### **Dependências Principais:**
- **`requests`** - Requisições HTTP para o site do IBPT
- **`beautifulsoup4`** - Parsing HTML para extrair informações
- **`pyTelegramBotAPI`** - API do Telegram para o bot
- **`schedule`** - Agendamento de tarefas (opcional)


## 🎯 Modos de Execução

O projeto foi reorganizado para reduzir redundâncias e melhorar a estrutura do código. Agora existem dois modos de operação:

### 1. Usando o script unificado

O script `run.py` agora pode executar tanto o bot quanto a automação IBPT:

```bash
# Executar apenas a automação IBPT (padrão)
python run.py

# Executar apenas o bot do Telegram
python run.py --modo bot

# Executar a automação IBPT e depois iniciar o bot
python run.py --modo ambos
```

### 2. Usando os scripts separados (compatibilidade)

Para manter compatibilidade com scripts ou agendamentos existentes:

```bash
# Iniciar apenas o bot do Telegram
python run_bot.py

# Executar apenas a automação IBPT (verifica e baixa tabelas)
python run.py
```

### O que cada modo faz

- `automacao`: Verifica se há novas tabelas IBPT disponíveis, faz o download se necessário e notifica os grupos ativos.
- `bot`: Inicia o serviço do bot do Telegram para responder a comandos dos usuários.
- `ambos`: Executa primeiro a automação IBPT (download/verificação) e depois inicia o bot do Telegram.

## 🤖 Bot do Telegram

### Comandos do Bot:

#### Comandos para Usuários:
- `/start` - Inicia o bot e exibe informações de ajuda
- `/status` - Verifica o status da tabela atual
- `/tabela` - Solicita o envio da tabela mais recente
- `/help` - Exibe a mensagem de ajuda

#### Comandos para Administradores:
- `/admin stats` - Mostra estatísticas gerais do bot
- `/admin grupos` - Lista todos os grupos cadastrados (ativos e inativos)
- `/admin ativar ID_GRUPO` - Ativa um grupo para receber notificações
- `/admin desativar ID_GRUPO` - Desativa um grupo (não receberá notificações)
- `/admin broadcast MENSAGEM` - Envia uma mensagem para todos os grupos ativos
- `/admin blacklist` - Lista todos os usuários bloqueados
- `/admin unblock USER_ID` - Remove um usuário da blacklist

### Como Configurar o Bot:

1. **Crie um bot no Telegram** usando o [@BotFather](https://t.me/BotFather)
2. **Copie o token** fornecido pelo BotFather
3. **Configure no arquivo `.env`**
4. **Inicie o bot**:
   ```bash
   python run_bot.py
   ```
5. **Inicie uma conversa** com seu bot no Telegram
6. **Adicione o bot a grupos** para receber notificações neles

### Gerenciamento de Grupos:
- Os grupos são adicionados automaticamente quando o bot é adicionado a eles
- Os administradores podem ativar/desativar grupos usando os comandos `/admin ativar` e `/admin desativar`
- Quando uma nova versão da tabela IBPT é baixada, o bot notifica automaticamente todos os grupos ativos

## 🛡️ Sistema de Proteção contra Spam

O bot implementa um sistema robusto de proteção contra spam e abuso:

### **Configurações de Rate Limiting**

- **Cooldown entre Comandos**: 3 segundos entre comandos
- **Limite por Minuto**: Máximo de 10 comandos por minuto
- **Limite por Hora**: Máximo de 50 comandos por hora
- **Threshold de Blacklist**: 20 comandos em 1 minuto = bloqueio automático

### **Sistema de Blacklist**

- Usuários que excedem o threshold são automaticamente bloqueados
- Blacklist é persistente (salva em arquivo `data/blacklist.txt`)

### **Comandos Administrativos**

- `/admin stats` - Mostra estatísticas gerais do bot
- `/admin blacklist` - Lista todos os usuários bloqueados
- `/admin unblock USER_ID` - Remove um usuário da blacklist
- `/admin rate USER_ID` - Mostra estatísticas detalhadas de rate limit de um usuário

## ⏰ Configuração do Cron Job (Sem Docker)

Para execução automática diária às 7h da manhã:

```bash
# Editar crontab
crontab -e

# Adicionar linha para download e envio automático (ajuste os caminhos conforme necessário)
0 7 * * * /usr/bin/python3 /caminho/para/run.py >> /var/log/ibpt_auto_update.log 2>&1

# Adicionar linha para manter o bot do Telegram rodando
@reboot /usr/bin/python3 /caminho/para/run_bot.py >> /var/log/telegram_bot.log 2>&1
```

## 📋 Exemplo de Saída

```
==============================================================
🏢 AUTOMAÇÃO IBPT - DOWNLOAD INTELIGENTE DE TABELA
==============================================================
📅 Data/Hora: 25/06/2025 07:00:15
👤 Usuário: seu_email@ibpt.com
📍 Estados: CE
📁 Arquivo: tabela_aliquotas_ibpt.zip
--------------------------------------------------------------
🔍 ETAPA 1: Verificando versões...
🔍 Verificando versão atual no site IBPT...
✅ Versão atual encontrada: 25.2.A
📅 Vigência até: 31/07/2025
📋 Última versão baixada: 25.1.B
📅 Vigência até: 20/06/2025
📊 Comparação de versões:
   📅 Atual: 25.2.A (até 31/07/2025)
   📅 Última baixada: 25.1.B (até 20/06/2025)
🆕 Nova versão disponível!
🔍 ETAPA 2: Baixando nova versão...
--------------------------------------------------------------
🚀 Iniciando processo de download...
📡 GET https://deolhonoimposto.ibpt.org.br/Site/Entrar -> Status 200
✅ Login realizado com sucesso!
✅ Página da empresa acessada com sucesso
✅ Solicitação de tabela enviada com sucesso
🔄 Verificando status do processamento...
✅ Arquivo recente encontrado! Criado em: 25/06/2025 07:02:30
📥 Iniciando download...
📊 Progresso: 100.0% (1542847/1542847 bytes)
✅ Download concluído: tabela_aliquotas_ibpt.zip (1542847 bytes)

🔍 ETAPA 3: Atualizando registro de versão...
💾 Informações da versão salvas: 25.2.A
✅ Registro de versão atualizado

🔍 ETAPA 4: Enviando tabela via Telegram...
✅ Tabela enviada com sucesso via Telegram

==============================================================
🎉 DOWNLOAD CONCLUÍDO COM SUCESSO!
📁 Arquivo: tabela_aliquotas_ibpt.zip
📊 Tamanho: 1,542,847 bytes
📋 Versão: 25.2.A
📅 Vigência até: 31/07/2025
==============================================================
```

## 🔧 Solução de Problemas

### Erro de Credenciais
```
❌ Falha no login: Credenciais inválidas ou bloqueadas
```
**Solução**: Verifique username e password no `config.py` ou `.env`

### Erro de Token CSRF
```
❌ Token CSRF não encontrado na página de login
```
**Solução**: O site pode ter mudado. Verifique se está acessível e reporte o problema.

### Erro de Verificação de Versão
```
❌ Erro na verificação de versão: ...
```
**Solução**: O script continua com download forçado. Verifique conectividade com o site.

### Timeout no Processamento
```
❌ Timeout: Arquivo não foi processado no tempo esperado
```
**Solução**: Aumente `MAX_ATTEMPTS` no `config.py` ou no `.env`

### Problemas com o Bot do Telegram
```
❌ Módulo do Telegram não disponível
```
**Solução**: Instale a biblioteca pyTelegramBotAPI: `pip install pyTelegramBotAPI`

```
❌ Erro ao enviar tabela via Telegram
```
**Solução**: Verifique o token do bot e a conectividade com a API do Telegram

## 📈 Monitoramento

Para monitorar execuções:

```bash
# Ver últimas execuções
tail -f logs/ibpt_auto_update.log

# Ver logs do bot do Telegram
tail -f logs/telegram_bot.log

# Em Docker
docker logs -f ibpt-bot
```

## 🛠️ Melhorias Técnicas

O projeto implementa as seguintes melhorias técnicas:

1. **Módulo de configuração compartilhada**: Foi criado um módulo `app/utils/setup.py` que centraliza a configuração de logging e a criação de diretórios.

2. **Singleton do Bot**: O bot do Telegram agora usa um padrão singleton (`app/telegram/instancia_bot.py`), garantindo que apenas uma instância seja criada, mesmo quando usado tanto pela automação quanto pelo serviço do bot.

3. **Renomeação de funções**: As funções principais foram renomeadas para melhor refletir seus propósitos:
   - `app.start_bot.main()` → `app.start_bot.run_telegram_bot()`
   - `app.main.main()` → `app.main.run_ibpt_automation()`

## 🆘 Suporte

Este sistema foi desenvolvido para automatizar o processo de download das tabelas IBPT. Em caso de problemas:

1. Verifique se o site IBPT está acessível
2. Confirme suas credenciais
3. Verifique os logs de erro
4. Teste primeiro com `python run.py --check` para verificar a conectividade
5. Verifique se o bot do Telegram está funcionando com `python run_bot.py`
