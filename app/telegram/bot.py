"""
Bot do Telegram para envio da tabela IBPT
"""
import logging
import os
import telebot
from telebot import types
import datetime
import sys
import time
import json
import re
from app.utils.grupos_manager import GruposManager

# Configuração do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/telegram_bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token, grupos_file="data/grupos.json"):
        """
        Inicializa o bot do Telegram
        
        Args:
            token: Token do bot do Telegram
            grupos_file: Arquivo para armazenar os IDs dos grupos e seus status
        """
        self.bot = telebot.TeleBot(token, num_threads=5)
        self.grupos_manager = GruposManager(grupos_file)
        
        # Sistema de proteção contra spam
        self.rate_limits = {}  # {user_id: {'last_command': timestamp, 'command_count': count}}
        self.blacklist = set()  # Set de usuários bloqueados
        self.blacklist_file = "data/blacklist.txt"
        
        # Configurações de rate limiting
        self.COOLDOWN_SECONDS = 3  # Tempo mínimo entre comandos
        self.MAX_COMMANDS_PER_MINUTE = 10  # Máximo de comandos por minuto
        self.MAX_COMMANDS_PER_HOUR = 50  # Máximo de comandos por hora
        self.BLACKLIST_THRESHOLD = 20  # Comandos em 1 minuto = blacklist
        
        # Criar diretório para os arquivos se não existir
        os.makedirs("data", exist_ok=True)
        os.makedirs(os.path.dirname(self.blacklist_file), exist_ok=True)
        
        # Carregar blacklist existente
        self._load_blacklist()
        
        # Registrar handlers
        self._register_handlers()
        
        # Registrar automaticamente grupos em que o bot já está
        self._register_existing_groups()
        
        logger.info("Bot do Telegram inicializado com proteção contra spam")
    
    def _register_existing_groups(self):
        """
        Tenta registrar grupos em que o bot já está presente
        quando é iniciado
        """
        try:
            # Verifica os membros atuais no momento de inicialização
            logger.info("Tentando registrar grupos existentes na inicialização...")
            
            # Tenta obter os grupos onde o bot já está
            registered_groups = 0
            
            # Registra o chat atual (se for um grupo)
            # Como o bot não pode obter a lista completa dos chats onde está
            # vamos ao menos registrar o chat atual
            try:
                updates = self.bot.get_updates(offset=0, timeout=1)
                for update in updates:
                    if hasattr(update, 'message') and update.message:
                        if update.message.chat.type in ['group', 'supergroup']:
                            chat_id = update.message.chat.id
                            chat_id_str = str(chat_id)
                            group_name = update.message.chat.title or "Grupo sem nome"
                            
                            # Verificar se o grupo já está registrado
                            grupos = self.grupos_manager.get_grupos()
                            if chat_id_str not in grupos:
                                self.grupos_manager.add_grupo(chat_id, group_name, is_active=False)
                                registered_groups += 1
                                logger.info(f"Grupo registrado na inicialização: ID {chat_id}, Nome: {group_name}")
                
                # Tenta enviar uma mensagem para o chat atual para verificar se é um grupo
                if registered_groups == 0:
                    # Não conseguimos registrar nenhum grupo pelos updates
                    # Vamos registrar o chat atual manualmente para teste
                    logger.info("Não foi possível registrar grupos pelos updates. Tentando obter chats manualmente...")
            except Exception as e:
                logger.error(f"Erro ao tentar registrar grupos pelos updates: {str(e)}")
            
            if registered_groups > 0:
                logger.info(f"Total de {registered_groups} grupos registrados na inicialização")
            else:
                logger.info("Nenhum grupo foi registrado na inicialização. Os grupos serão registrados quando enviarem comandos.")
        except Exception as e:
            logger.error(f"Erro ao registrar grupos existentes: {str(e)}")

    def _load_blacklist(self):
        """Carrega a lista de usuários bloqueados"""
        try:
            if os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            self.blacklist.add(line.strip())
                logger.info(f"Blacklist carregada: {len(self.blacklist)} usuários bloqueados")
        except Exception as e:
            logger.error(f"Erro ao carregar blacklist: {str(e)}")

    def _save_blacklist(self):
        """Salva a lista de usuários bloqueados"""
        try:
            with open(self.blacklist_file, 'w') as f:
                for user_id in self.blacklist:
                    f.write(f"{user_id}\n")
            logger.info(f"Blacklist salva: {len(self.blacklist)} usuários bloqueados")
        except Exception as e:
            logger.error(f"Erro ao salvar blacklist: {str(e)}")

    def _is_rate_limited(self, user_id):
        """
        Verifica se o usuário está sendo rate limited
        
        Args:
            user_id: ID do usuário
            
        Returns:
            tuple: (is_limited, reason, remaining_time)
        """
        user_id_str = str(user_id)
        current_time = time.time()
        
        # Verificar se está na blacklist
        if user_id_str in self.blacklist:
            return True, "BLACKLISTED", 0
        
        # Inicializar dados do usuário se não existir
        if user_id_str not in self.rate_limits:
            self.rate_limits[user_id_str] = {
                'last_command': 0,
                'command_count': 0,
                'minute_start': current_time,
                'hour_start': current_time,
                'minute_count': 0,
                'hour_count': 0
            }
        
        user_data = self.rate_limits[user_id_str]
        
        # Verificar cooldown entre comandos
        time_since_last = current_time - user_data['last_command']
        if time_since_last < self.COOLDOWN_SECONDS:
            remaining = self.COOLDOWN_SECONDS - time_since_last
            return True, "COOLDOWN", remaining
        
        # Verificar limite por minuto
        if current_time - user_data['minute_start'] >= 60:
            user_data['minute_start'] = current_time
            user_data['minute_count'] = 0
        
        user_data['minute_count'] += 1
        
        if user_data['minute_count'] > self.MAX_COMMANDS_PER_MINUTE:
            # Adicionar à blacklist se exceder muito
            if user_data['minute_count'] > self.BLACKLIST_THRESHOLD:
                self.blacklist.add(user_id_str)
                self._save_blacklist()
                logger.warning(f"Usuário {user_id} adicionado à blacklist por spam excessivo")
                return True, "BLACKLISTED", 0
            
            return True, "RATE_LIMITED_MINUTE", 60 - (current_time - user_data['minute_start'])
        
        # Verificar limite por hora
        if current_time - user_data['hour_start'] >= 3600:
            user_data['hour_start'] = current_time
            user_data['hour_count'] = 0
        
        user_data['hour_count'] += 1
        
        if user_data['hour_count'] > self.MAX_COMMANDS_PER_HOUR:
            return True, "RATE_LIMITED_HOUR", 3600 - (current_time - user_data['hour_start'])
        
        # Atualizar timestamp do último comando
        user_data['last_command'] = current_time
        user_data['command_count'] += 1
        
        return False, None, 0

    def _send_rate_limit_message(self, chat_id, reason, remaining_time):
        """Envia mensagem de rate limit"""
        if reason == "BLACKLISTED":
            message = (
                "🚫 *Você foi bloqueado por abuso!*\n\n"
                "Você foi adicionado à lista negra por enviar muitos comandos em um curto período.\n\n"
                "Entre em contato com o administrador para solicitar o desbloqueio."
            )
        elif reason == "COOLDOWN":
            message = (
                f"⏳ *Aguarde um momento!*\n\n"
                f"Você precisa aguardar {int(remaining_time)} segundos antes de enviar outro comando."
            )
        elif reason == "RATE_LIMITED_MINUTE":
            message = (
                f"⚠️ *Muitos comandos!*\n\n"
                f"Você enviou muitos comandos neste minuto. Aguarde {int(remaining_time)} segundos."
            )
        elif reason == "RATE_LIMITED_HOUR":
            message = (
                f"⚠️ *Limite horário atingido!*\n\n"
                f"Você enviou muitos comandos nesta hora. Aguarde {int(remaining_time)} segundos."
            )
        
        try:
            self.bot.send_message(chat_id, message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de rate limit: {str(e)}")

    def _send_long_message(self, chat_id, text, header=""):
        """
        Envia uma mensagem longa, dividindo-a em partes se necessário.
        
        Args:
            chat_id: ID do chat
            text: O texto completo da mensagem
            header: Um cabeçalho para adicionar às mensagens de continuação
        """
        max_length = 4096  # Limite de caracteres do Telegram
        header_len = len(header)
        
        # Divide a mensagem em partes, respeitando o limite de caracteres
        parts = []
        while len(text) > 0:
            if len(text) > max_length:
                # Encontra a última quebra de linha antes do limite
                split_pos = text.rfind('\n', 0, max_length - header_len)
                if split_pos == -1:
                    split_pos = max_length - header_len
                
                parts.append(text[:split_pos])
                text = text[split_pos:].lstrip()
            else:
                parts.append(text)
                break
        
        # Envia as partes
        for i, part in enumerate(parts):
            try:
                if i > 0 and header:
                    self.bot.send_message(chat_id, header + part, parse_mode='Markdown')
                else:
                    self.bot.send_message(chat_id, part, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Erro ao enviar parte da mensagem longa para {chat_id}: {e}")

    def _register_handlers(self):
        """Registra os handlers para comandos do bot"""
        
        # Função auxiliar para verificar se um grupo está ativo
        def check_grupo_ativo(message):
            """
            Verifica se um grupo está ativo e envia uma mensagem se não estiver
            
            Args:
                message: Objeto de mensagem do Telegram
                
            Returns:
                bool: True se o grupo está ativo ou não é um grupo, False caso contrário
            """
            chat_id = message.chat.id
            
            # Se não for um grupo, não precisa verificar
            if message.chat.type not in ['group', 'supergroup']:
                return True
                
            # Verificar se o grupo está registrado e ativo
            chat_id_str = str(chat_id)
            grupos = self.grupos_manager.get_grupos()
            
            # Registrar o grupo automaticamente se ainda não estiver registrado
            if chat_id_str not in grupos:
                group_name = message.chat.title or "Grupo sem nome"
                self.grupos_manager.add_grupo(chat_id, group_name, is_active=False)
                logger.info(f"Grupo registrado automaticamente ao receber comando: ID {chat_id}, Nome: {group_name}")
                
                self.bot.reply_to(
                    message,
                    "⚠️ Este grupo foi registrado automaticamente, mas está inativo.\n\n"
                    "Um administrador do bot precisa ativar este grupo para que os comandos funcionem.\n\n"
                    "Use `/start` para mais informações."
                )
                return False
            
            # Verificar se o grupo está ativo
            if not grupos[chat_id_str].get('ativo', False):
                self.bot.reply_to(
                    message,
                    "⚠️ Este grupo está registrado, mas ainda não foi ativado por um administrador do bot.\n\n"
                    "Os comandos só funcionarão após a ativação."
                )
                return False
                
            return True
        
        # Handler para quando o bot é adicionado a um novo grupo
        @self.bot.message_handler(content_types=['new_chat_members'])
        def handle_new_chat_members(message):
            """Handler para detectar quando o bot é adicionado a um grupo"""
            try:
                # Verificar se o bot está entre os novos membros
                for member in message.new_chat_members:
                    if member.id == self.bot.get_me().id:
                        # Bot foi adicionado a um novo grupo
                        chat_id = message.chat.id
                        chat_id_str = str(chat_id)
                        group_name = message.chat.title or "Grupo sem nome"
                        
                        # Verificar se o grupo já está na lista
                        grupos = self.grupos_manager.get_grupos()
                        if chat_id_str not in grupos:
                            # Adicionar grupo como inativo
                            self.grupos_manager.add_grupo(chat_id, group_name, is_active=False)
                            
                            # Enviar mensagem de boas-vindas
                            welcome_text = (
                                f"👋 Olá! Fui adicionado ao grupo *{group_name}*!\n\n"
                                "Sou o *IBPT Downloader Bot* e posso enviar a tabela de alíquotas do IBPT quando ela é atualizada.\n\n"
                                "Este grupo foi registrado, mas está *inativo*. Um administrador do bot precisa ativar este grupo "
                                "para que vocês comecem a receber notificações automáticas.\n\n"
                                "Use `/help` para ver os comandos disponíveis."
                            )
                            
                            self.bot.send_message(
                                chat_id, 
                                welcome_text, 
                                parse_mode='Markdown'
                            )
                            
                            logger.info(f"Bot adicionado a um novo grupo: ID {chat_id}, Nome: {group_name}")
                        
                        # Retornar após processar o bot
                        return
            except Exception as e:
                logger.error(f"Erro ao processar adição do bot a um grupo: {str(e)}")
        
        # Handler para quando o bot é removido de um grupo
        @self.bot.message_handler(content_types=['left_chat_member'])
        def handle_left_chat_member(message):
            """Handler para detectar quando o bot é removido de um grupo"""
            try:
                # Verificar se o bot foi removido
                if message.left_chat_member.id == self.bot.get_me().id:
                    # Bot foi removido do grupo
                    chat_id = message.chat.id
                    chat_id_str = str(chat_id)
                    group_name = message.chat.title or "Grupo sem nome"
                    
                    # Verificar se o grupo está na lista e remover
                    grupos = self.grupos_manager.get_grupos()
                    if chat_id_str in grupos:
                        self.grupos_manager.remove_grupo(chat_id)
                        logger.info(f"Bot removido do grupo: ID {chat_id}, Nome: {group_name}")
            except Exception as e:
                logger.error(f"Erro ao processar remoção do bot de um grupo: {str(e)}")
        
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            """Handler para o comando /start"""
            try:
                user_id = message.from_user.id
                chat_id = message.chat.id
                
                # Verificar rate limiting
                is_limited, reason, remaining_time = self._is_rate_limited(user_id)
                if is_limited:
                    self._send_rate_limit_message(chat_id, reason, remaining_time)
                    logger.warning(f"Rate limit aplicado para usuário {user_id}: {reason}")
                    return
                
                username = message.from_user.username or "Sem username"
                first_name = message.from_user.first_name or "Sem nome"
                
                # Verificar se é um grupo
                if message.chat.type in ['group', 'supergroup']:
                    # Verificar se o grupo já está na lista
                    grupos = self.grupos_manager.get_grupos()
                    chat_id_str = str(chat_id)
                    
                    if chat_id_str in grupos:
                        # Grupo já está registrado
                        group_name = message.chat.title or "Grupo"
                        
                        # Verificar se está ativo
                        if grupos[chat_id_str].get('ativo', False):
                            status_text = "✅ *Este grupo já está ativo para receber notificações!*"
                        else:
                            # Não ativar o grupo - apenas informar que precisa de ativação por admin
                            status_text = "⚠️ *Este grupo ainda está aguardando aprovação de um administrador do bot*"
                        
                        already_registered_text = (
                            f"👋 Olá!\n\n"
                            f"{status_text}\n\n"
                            "Este grupo está registrado para receber atualizações automáticas da tabela IBPT após aprovação.\n\n"
                            "Comandos disponíveis (apenas em grupos ativos):\n"
                            "/help - Exibe a mensagem de ajuda\n"
                            "/status - Verifica o status da tabela atual\n"
                            "/tabela UF - Solicita o envio da tabela para um estado específico (ex: /tabela SP)\n"
                            "/remover - Remove o grupo do recebimento de notificações"
                        )
                        
                        self.bot.send_message(
                            chat_id, 
                            already_registered_text, 
                            parse_mode='Markdown'
                        )
                        
                        logger.info(f"Grupo já registrado tentou /start novamente: ID {chat_id}, Nome: {message.chat.title}")
                        
                    else:
                        # Adicionar grupo à lista como inativo
                        group_name = message.chat.title or "Grupo"
                        self.grupos_manager.add_grupo(chat_id, group_name, is_active=False)
                        
                        # Enviar mensagem de boas-vindas
                        welcome_text = (
                            f"👋 Olá!\n\n"
                            "Bem-vindo ao *IBPT Downloader Bot*!\n\n"
                            "✅ *Este grupo foi registrado com sucesso e agora aguarda a aprovação de um administrador do bot para começar a receber as notificações.*\n\n"
                            "Os comandos só funcionarão quando o grupo for ativado por um administrador do bot."
                        )
                        
                        self.bot.send_message(
                            chat_id, 
                            welcome_text, 
                            parse_mode='Markdown'
                        )
                        
                        logger.info(f"Novo grupo registrado como inativo: ID {chat_id}, Nome: {group_name}")
                else:
                    # É um chat privado
                    private_chat_text = (
                        f"👋 Olá, {first_name}!\n\n"
                        "Este bot agora só envia atualizações automáticas da tabela IBPT para grupos.\n\n"
                        "Para receber atualizações, adicione este bot a um grupo e execute o comando /start lá.\n\n"
                        "Comandos disponíveis em grupos:\n"
                        "/start - Registra o grupo para receber notificações\n"
                        "/help - Exibe a mensagem de ajuda\n"
                        "/status - Verifica o status da tabela atual\n"
                        "/tabela UF - Solicita o envio da tabela para um estado específico (ex: /tabela SP)\n"
                        "/remover - Remove o grupo do recebimento de notificações"
                    )
                    
                    self.bot.send_message(
                        user_id, 
                        private_chat_text, 
                        parse_mode='Markdown'
                    )
                    
                    logger.info(f"Usuário tentou usar o bot em chat privado: ID {user_id}, Username: {username}, Nome: {first_name}")
                
            except Exception as e:
                logger.error(f"Erro no comando /start: {str(e)}")
                self.bot.reply_to(message, "❌ Ocorreu um erro ao processar seu comando. Tente novamente mais tarde.")
        
        @self.bot.message_handler(commands=['help'])
        def handle_help(message):
            """Handler para o comando /help"""
            try:
                user_id = message.from_user.id
                chat_id = message.chat.id
                
                # Verificar rate limiting
                is_limited, reason, remaining_time = self._is_rate_limited(user_id)
                if is_limited:
                    self._send_rate_limit_message(chat_id, reason, remaining_time)
                    return
                
                # Verificar se o grupo está ativo (exceto para chats privados)
                if message.chat.type in ['group', 'supergroup'] and not check_grupo_ativo(message):
                    return
                
                help_text = (
                    r"__*IBPT Downloader Bot* \- Ajuda__"
                    "\n\n"
                    r"Este bot envia automaticamente a tabela de alíquotas do IBPT quando ela é atualizada\."
                    "\n\n"
                    r"__*Comandos disponíveis:*__"
                    "\n"
                    r"`/start` \- Registra o grupo para receber notificações"
                    "\n"
                    r"`/help` \- Exibe esta mensagem de ajuda"
                    "\n"
                    r"`/status` \- Verifica o status da tabela atual"
                    "\n"
                    r"`/tabela UF` \- Solicita a tabela para um estado específico \(ex: `/tabela SP`\)"
                    "\n"
                    r"`/remover` \- Remove o grupo do recebimento de notificações"
                    "\n\n"
                    "💡 __*Dicas:*__\n"
                    "• Use `/start` para registrar o grupo para receber notificações automáticas\n"
                    "• Use `/tabela UF` para baixar a tabela do seu estado\n\n"
                    "🛡️ __*Proteção contra Spam:*__\n"
                    "• Aguarde 3 segundos entre comandos\n"
                    "• Máximo 10 comandos por minuto\n"
                    "• Máximo 50 comandos por hora\n"
                    "• Usuários abusivos são bloqueados automaticamente"
                )
                
                self.bot.send_message(
                    message.chat.id, 
                    help_text, 
                    parse_mode='MarkdownV2'
                )
                
            except Exception as e:
                logger.error(f"Erro no comando /help: {str(e)}")
                self.bot.reply_to(message, "❌ Ocorreu um erro ao processar seu comando. Tente novamente mais tarde.")
        
        @self.bot.message_handler(commands=['status'])
        def handle_status(message):
            """Handler para o comando /status"""
            try:
                user_id = message.from_user.id
                chat_id = message.chat.id
                
                # Verificar rate limiting
                is_limited, reason, remaining_time = self._is_rate_limited(user_id)
                if is_limited:
                    self._send_rate_limit_message(chat_id, reason, remaining_time)
                    return
                
                # Verificar se o grupo está ativo (exceto para chats privados)
                if message.chat.type in ['group', 'supergroup'] and not check_grupo_ativo(message):
                    return
                
                # Verificar se existe o arquivo last_version_downloaded.txt
                version_file = "data/last_version_downloaded.txt"
                
                if os.path.exists(version_file):
                    import json
                    with open(version_file, 'r') as f:
                        data = json.load(f)
                    
                    version = data.get('version', 'Desconhecida')
                    vigencia = data.get('vigencia_ate', 'Desconhecida')
                    checked_at = data.get('checked_at', 'Desconhecida')
                    
                    # Formatar data de verificação
                    try:
                        checked_datetime = datetime.datetime.fromisoformat(checked_at)
                        checked_formatted = checked_datetime.strftime("%d/%m/%Y %H:%M:%S")
                    except:
                        checked_formatted = checked_at
                    
                    status_text = (
                        "*Status da Tabela IBPT*\n\n"
                        f"📊 Versão atual: *{version}*\n"
                        f"📅 Vigência até: *{vigencia}*\n"
                        f"🔄 Última verificação: *{checked_formatted}*\n\n"
                        "Para solicitar a tabela de um estado, use o comando /tabela UF (ex: /tabela SP)"
                    )
                else:
                    status_text = (
                        "*Status da Tabela IBPT*\n\n"
                        "❓ Não há informações sobre a tabela atual.\n"
                        "Isso pode ocorrer porque o sistema ainda não baixou a tabela pela primeira vez.\n\n"
                        "Para solicitar a tabela de um estado, use o comando /tabela UF (ex: /tabela SP)"
                    )
                
                self.bot.send_message(
                    message.chat.id, 
                    status_text, 
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                logger.error(f"Erro no comando /status: {str(e)}")
                self.bot.reply_to(message, "❌ Ocorreu um erro ao processar seu comando. Tente novamente mais tarde.")
        
        @self.bot.message_handler(commands=['tabela'])
        def handle_tabela(message):
            """Handler para solicitar tabela de um estado específico"""
            try:
                user_id = message.from_user.id
                chat_id = message.chat.id
                
                # Verificar rate limiting
                is_limited, reason, remaining_time = self._is_rate_limited(user_id)
                if is_limited:
                    self._send_rate_limit_message(chat_id, reason, remaining_time)
                    return
                
                # Verificar se o grupo está ativo (exceto para chats privados)
                if message.chat.type in ['group', 'supergroup'] and not check_grupo_ativo(message):
                    return
                
                # Extrair o estado do comando
                command_parts = message.text.split()
                
                # Se não especificou o estado, mostrar ajuda
                if len(command_parts) < 2:
                    # Obter lista de estados disponíveis do .env
                    estados_disponiveis = os.getenv("ESTADOS", "CE").split(",")
                    
                    self.bot.send_message(
                        message.chat.id,
                        f"*Uso:* `/tabela UF`\n\n"
                        f"Onde UF é a sigla do estado desejado (ex: SP, RJ, MG).\n\n"
                        f"*Estados disponíveis:* {', '.join(estados_disponiveis)}\n\n"
                        f"Exemplo: `/tabela SP`",
                        parse_mode='Markdown'
                    )
                    return
                
                estado = command_parts[1].upper()
                
                # Verificar se o estado é válido (2 letras)
                if not re.match(r'^[A-Z]{2}$', estado):
                    self.bot.send_message(
                        message.chat.id,
                        f"❌ *Estado inválido:* {estado}\n\n"
                        f"Use a sigla do estado com 2 letras (ex: SP, RJ, MG).",
                        parse_mode='Markdown'
                    )
                    return
                
                # Verificar se o estado está na lista de estados configurados
                estados_disponiveis = os.getenv("ESTADOS", "CE").split(",")
                if estado not in estados_disponiveis:
                    self.bot.send_message(
                        message.chat.id,
                        f"❌ *Estado não disponível:* {estado}\n\n"
                        f"Estados disponíveis: {', '.join(estados_disponiveis)}",
                        parse_mode='Markdown'
                    )
                    return
                
                # Verificar se existe o arquivo da versão
                version_file = "data/last_version_downloaded.txt"
                if not os.path.exists(version_file):
                    self.bot.send_message(
                        message.chat.id,
                        "❌ *Informações da tabela não disponíveis*\n\n"
                        "A tabela ainda não foi baixada. Tente novamente mais tarde.",
                        parse_mode='Markdown'
                    )
                    return
                
                # Carregar informações da versão
                with open(version_file, 'r') as f:
                    data = json.load(f)
                
                version = data.get('version', 'Desconhecida')
                vigencia = data.get('vigencia_ate', 'Desconhecida')
                
                # Formatar data para exibição
                try:
                    data_obj = datetime.datetime.strptime(vigencia, "%d/%m/%Y")
                    data_formatted = data_obj.strftime("%d/%m/%Y")
                except:
                    data_formatted = vigencia
                
                # Caminho para a tabela completa
                tabela_completa_path = "data/tabela_aliquotas_ibpt.zip"
                
                # Verificar se o arquivo existe
                if not os.path.exists(tabela_completa_path):
                    self.bot.send_message(
                        message.chat.id,
                        f"❌ *Tabela para {estado} não disponível*\n\n"
                        "A tabela solicitada ainda não está disponível. Tente novamente mais tarde.",
                        parse_mode='Markdown'
                    )
                    return
                
                # Enviar mensagem de preparação
                self.bot.send_message(
                    message.chat.id,
                    f"🔍 *Preparando tabela IBPT para {estado}...*\n\n"
                    f"Isso pode levar alguns instantes.",
                    parse_mode='Markdown'
                )
                
                # Diretório temporário para extrair o arquivo
                import tempfile
                import zipfile
                import shutil
                
                # Criar diretório temporário
                temp_dir = tempfile.mkdtemp()
                
                try:
                    # Padrão de arquivo para o estado solicitado
                    # Formato: TabelaIBPTaxCE25.2.B.csv
                    arquivo_estado_pattern = f"TabelaIBPTax{estado}"
                    
                    # Flag para indicar se encontramos o arquivo do estado
                    encontrou_arquivo = False
                    nome_arquivo = ""
                    
                    # Processar o arquivo ZIP
                    with zipfile.ZipFile(tabela_completa_path, 'r') as zip_completo:
                        # Listar todos os arquivos
                        arquivos = zip_completo.namelist()
                        
                        # Filtrar apenas os arquivos do estado solicitado
                        arquivos_estado = [arq for arq in arquivos if arquivo_estado_pattern in arq]
                        
                        if not arquivos_estado:
                            self.bot.send_message(
                                message.chat.id,
                                f"❌ *Tabela para {estado} não encontrada*\n\n"
                                f"Não foi possível encontrar a tabela para o estado {estado} no arquivo atual.",
                                parse_mode='Markdown'
                            )
                            return
                        
                        # Extrair o primeiro arquivo encontrado (normalmente só deve haver um por estado)
                        arquivo_csv = arquivos_estado[0]
                        nome_arquivo = os.path.basename(arquivo_csv)
                        arquivo_path = os.path.join(temp_dir, nome_arquivo)
                        
                        # Extrair o arquivo para o diretório temporário
                        with open(arquivo_path, 'wb') as f:
                            f.write(zip_completo.read(arquivo_csv))
                            encontrou_arquivo = True
                            logger.info(f"Arquivo {arquivo_csv} extraído para o estado {estado}")
                    
                    if not encontrou_arquivo:
                        self.bot.send_message(
                            message.chat.id,
                            f"❌ *Tabela para {estado} não encontrada*\n\n"
                            f"Não foi possível encontrar a tabela para o estado {estado} no arquivo atual.",
                            parse_mode='Markdown'
                        )
                        return
                    
                    # Enviar o arquivo CSV diretamente
                    try:
                        with open(arquivo_path, 'rb') as f:
                            self.bot.send_document(
                                message.chat.id,
                                f,
                                caption=f"📊 Tabela IBPT para {estado} - Versão {version}",
                                visible_file_name=nome_arquivo
                            )
                        
                        self.bot.send_message(
                            message.chat.id,
                            f"✅ *Tabela IBPT para {estado} enviada com sucesso!*\n\n"
                            f"*Versão:* {version}\n"
                            f"*Vigência até:* {data_formatted}\n\n"
                            "Utilize esta tabela para configurar o seu sistema de emissão de Notas Fiscais.",
                            parse_mode='Markdown'
                        )
                        
                        logger.info(f"Tabela para {estado} enviada para o usuário {message.from_user.id}")
                    except Exception as e:
                        self.bot.send_message(
                            message.chat.id,
                            f"❌ *Erro ao enviar a tabela para {estado}:* {str(e)}",
                            parse_mode='Markdown'
                        )
                        logger.error(f"Erro ao enviar tabela para {estado} ao usuário {message.from_user.id}: {str(e)}")
                finally:
                    # Limpar arquivos temporários
                    try:
                        shutil.rmtree(temp_dir)
                        logger.info(f"Diretório temporário {temp_dir} removido")
                    except Exception as e:
                        logger.error(f"Erro ao remover diretório temporário {temp_dir}: {str(e)}")
            
            except Exception as e:
                logger.error(f"Erro no comando /tabela: {str(e)}")
                self.bot.reply_to(message, "❌ Ocorreu um erro ao processar seu comando. Tente novamente mais tarde.")
        
        @self.bot.message_handler(commands=['remover'])
        def handle_remover(message):
            """Handler para o comando /remover"""
            try:
                user_id = message.from_user.id
                chat_id = message.chat.id
                
                # Verificar rate limiting
                is_limited, reason, remaining_time = self._is_rate_limited(user_id)
                if is_limited:
                    self._send_rate_limit_message(chat_id, reason, remaining_time)
                    logger.warning(f"Rate limit aplicado para usuário {user_id}: {reason}")
                    return
                
                # Verificar se é um grupo
                if message.chat.type not in ['group', 'supergroup']:
                    self.bot.reply_to(
                        message,
                        "❌ Este comando só pode ser usado em grupos."
                    )
                    return
                
                # Verificar se o grupo está ativo
                if not check_grupo_ativo(message):
                    return
                
                # Verificar se o usuário é admin do grupo
                chat_member = self.bot.get_chat_member(chat_id, user_id)
                if chat_member.status not in ['creator', 'administrator']:
                    self.bot.reply_to(
                        message,
                        "❌ Apenas administradores do grupo podem remover o bot da lista de notificações."
                    )
                    return
                
                # Remover grupo da lista
                if self.grupos_manager.remove_grupo(chat_id):
                    cancel_text = (
                        "✅ *Remoção realizada com sucesso!*\n\n"
                        "Este grupo não receberá mais notificações automáticas sobre atualizações da tabela IBPT.\n\n"
                        "Caso deseje reativar as notificações no futuro, utilize o comando /start."
                    )
                    
                    self.bot.send_message(
                        chat_id, 
                        cancel_text, 
                        parse_mode='Markdown'
                    )
                    
                    logger.info(f"Grupo removido das notificações: ID {chat_id}, Nome: {message.chat.title}")
                else:
                    self.bot.reply_to(
                        message,
                        "❓ Este grupo não estava inscrito para receber notificações."
                    )
                    
                    logger.info(f"Tentativa de remover grupo não inscrito: ID {chat_id}")
                
            except Exception as e:
                logger.error(f"Erro no comando /remover: {str(e)}")
                self.bot.reply_to(message, "❌ Ocorreu um erro ao processar seu comando. Tente novamente mais tarde.")

        @self.bot.message_handler(commands=['admin'])
        def handle_admin(message):
            """Handler para comandos administrativos"""
            try:
                user_id = message.from_user.id
                chat_id = message.chat.id
                
                # Verificar rate limiting
                is_limited, reason, remaining_time = self._is_rate_limited(user_id)
                if is_limited:
                    self._send_rate_limit_message(chat_id, reason, remaining_time)
                    return
                
                # Verificar se é administrador (você pode configurar uma lista de admins)
                admin_ids = os.getenv("ADMIN_IDS", "")
                
                if not admin_ids or str(user_id) not in admin_ids.split(","):
                    self.bot.reply_to(message, "❌ Você não tem permissão para usar comandos administrativos.")
                    return
                
                # Parse do comando
                command_parts = message.text.split()
                if len(command_parts) < 2:
                    admin_help = (
                        "*Comandos Administrativos*\n\n"
                        "`/admin stats` - Mostra estatísticas do bot\n"
                        "`/admin blacklist` - Lista usuários bloqueados\n"
                        "`/admin unblock USER_ID` - Remove usuário da blacklist\n"
                        "`/admin rate USER_ID` - Mostra estatísticas de rate limit de um usuário\n"
                        "`/admin grupos` - Lista todos os grupos registrados\n"
                        "`/admin ativar GRUPO_ID` - Ativa envio de mensagens para um grupo\n"
                        "`/admin desativar GRUPO_ID` - Desativa envio de mensagens para um grupo\n"
                        "`/admin remove GRUPO_ID` - Remove completamente um grupo da lista\n"
                        "`/admin broadcast MENSAGEM` - Envia mensagem para todos os grupos ativos"
                    )
                    self.bot.send_message(chat_id, admin_help, parse_mode='Markdown')
                    return
                
                subcommand = command_parts[1].lower()
                
                if subcommand == "stats":
                    # Estatísticas gerais
                    grupos = self.grupos_manager.get_grupos()
                    grupos_ativos = self.grupos_manager.get_grupos_ativos()
                    grupos_inativos = self.grupos_manager.get_grupos_inativos()
                    blacklist_count = len(self.blacklist)
                    rate_limited_count = len(self.rate_limits)
                    
                    stats_text = (
                        "*Estatísticas do Bot*\n\n"
                        f"👥 Total de grupos: *{len(grupos)}*\n"
                        f"✅ Grupos ativos: *{len(grupos_ativos)}*\n"
                        f"❌ Grupos inativos: *{len(grupos_inativos)}*\n"
                        f"🚫 Usuários bloqueados: *{blacklist_count}*\n"
                        f"📊 Usuários com rate limit: *{rate_limited_count}*\n\n"
                        f"⚙️ Configurações:\n"
                        f"• Cooldown: {self.COOLDOWN_SECONDS}s\n"
                        f"• Máximo/minuto: {self.MAX_COMMANDS_PER_MINUTE}\n"
                        f"• Máximo/hora: {self.MAX_COMMANDS_PER_HOUR}\n"
                        f"• Threshold blacklist: {self.BLACKLIST_THRESHOLD}"
                    )
                    
                    self.bot.send_message(chat_id, stats_text, parse_mode='Markdown')
                    
                elif subcommand == "blacklist":
                    # Listar blacklist
                    if not self.blacklist:
                        self.bot.send_message(chat_id, "✅ Nenhum usuário está bloqueado.")
                    else:
                        blacklist_text = "*Usuários Bloqueados:*\n\n"
                        for i, user_id in enumerate(self.blacklist, 1):
                            blacklist_text += f"{i}. `{user_id}`\n"
                        
                        self._send_long_message(chat_id, blacklist_text, header="*Usuários Bloqueados (continuação):*\n\n")
                        
                elif subcommand == "unblock" and len(command_parts) >= 3:
                    # Desbloquear usuário
                    target_user_id = command_parts[2]
                    
                    if target_user_id in self.blacklist:
                        self.blacklist.remove(target_user_id)
                        self._save_blacklist()
                        
                        # Limpar dados de rate limit também
                        if target_user_id in self.rate_limits:
                            del self.rate_limits[target_user_id]
                        
                        self.bot.send_message(chat_id, f"✅ Usuário `{target_user_id}` foi desbloqueado.", parse_mode='Markdown')
                        logger.info(f"Usuário {target_user_id} desbloqueado por admin {user_id}")
                    else:
                        self.bot.send_message(chat_id, f"❌ Usuário `{target_user_id}` não está bloqueado.", parse_mode='Markdown')
                        
                elif subcommand == "rate" and len(command_parts) >= 3:
                    # Estatísticas de rate limit de um usuário
                    target_user_id = command_parts[2]
                    
                    if target_user_id in self.rate_limits:
                        user_data = self.rate_limits[target_user_id]
                        current_time = time.time()
                        
                        rate_text = (
                            f"*Estatísticas de Rate Limit*\n"
                            f"Usuário: `{target_user_id}`\n\n"
                            f"📊 Total de comandos: *{user_data['command_count']}*\n"
                            f"⏰ Último comando: *{datetime.datetime.fromtimestamp(user_data['last_command']).strftime('%d/%m/%Y %H:%M:%S')}*\n"
                            f"🕐 Comandos/minuto: *{user_data['minute_count']}*\n"
                            f"🕐 Comandos/hora: *{user_data['hour_count']}*\n\n"
                            f"🚫 Na blacklist: *{'Sim' if target_user_id in self.blacklist else 'Não'}*"
                        )
                        
                        self.bot.send_message(chat_id, rate_text, parse_mode='Markdown')
                    else:
                        self.bot.send_message(chat_id, f"❌ Usuário `{target_user_id}` não tem dados de rate limit.", parse_mode='Markdown')
                
                elif subcommand == "grupos":
                    # Listar todos os grupos
                    grupos_dict = self.grupos_manager.get_grupos()
                    
                    try:
                        if not grupos_dict:
                            self.bot.send_message(
                                chat_id, 
                                "*Todos os Grupos Registrados:*\n\n"
                                "Nenhum grupo está registrado ainda.\n\n"
                                "Os grupos são registrados automaticamente quando:\n"
                                "1. O bot é adicionado a um grupo\n"
                                "2. Alguém usa um comando em um grupo\n"
                                "3. Alguém usa o comando /start em um grupo",
                                parse_mode='Markdown'
                            )
                        else:
                            grupos_text = "*Todos os Grupos Registrados:*\n\n"
                            for i, (grupo_id, grupo_info) in enumerate(grupos_dict.items(), 1):
                                status = "✅ Ativo" if grupo_info.get('ativo', False) else "❌ Inativo"
                                nome = grupo_info.get('nome', 'Grupo sem nome')
                                grupos_text += f"{i}. `{grupo_id}` - {status} - {nome}\n"
                            
                            self._send_long_message(chat_id, grupos_text, header="*Todos os Grupos Registrados (continuação):*\n\n")
                            
                            # Exibir contagem de grupos
                            grupos_ativos = len(self.grupos_manager.get_grupos_ativos())
                            grupos_inativos = len(self.grupos_manager.get_grupos_inativos())
                            total_grupos = len(grupos_dict)
                            
                            stats_text = f"\n*Resumo:*\n"
                            stats_text += f"• Total de grupos: {total_grupos}\n"
                            stats_text += f"• Grupos ativos: {grupos_ativos}\n"
                            stats_text += f"• Grupos inativos: {grupos_inativos}\n"
                            
                            self.bot.send_message(chat_id, stats_text, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Erro ao listar grupos: {str(e)}")
                        self.bot.send_message(chat_id, f"❌ Erro ao listar grupos: {str(e)}", parse_mode='Markdown')
                
                elif subcommand == "ativar" and len(command_parts) >= 3:
                    # Ativar um grupo
                    target_group_id = command_parts[2]
                    
                    if self.grupos_manager.ativar_grupo(target_group_id):
                        grupos_dict = self.grupos_manager.get_grupos()
                        nome = grupos_dict.get(target_group_id, {}).get('nome', 'Grupo sem nome')
                        
                        # Informar ao administrador
                        self.bot.send_message(
                            chat_id, 
                            f"✅ Grupo `{target_group_id}` ({nome}) foi ativado com sucesso.", 
                            parse_mode='Markdown'
                        )
                        
                        # Enviar mensagem ao grupo informando que foi ativado
                        try:
                            self.bot.send_message(
                                int(target_group_id),
                                "✅ *Grupo Ativado!*\n\n"
                                "Este grupo foi ativado por um administrador do bot e agora "
                                "receberá notificações automáticas sobre atualizações da tabela IBPT.\n\n"
                                "Use `/help` para ver os comandos disponíveis.",
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logger.error(f"Erro ao enviar mensagem de ativação para o grupo {target_group_id}: {e}")
                            
                        logger.info(f"Grupo {target_group_id} ativado por admin {user_id}")
                    else:
                        self.bot.send_message(
                            chat_id, 
                            f"❌ Grupo `{target_group_id}` não encontrado.", 
                            parse_mode='Markdown'
                        )
                
                elif subcommand == "desativar" and len(command_parts) >= 3:
                    # Desativar um grupo
                    target_group_id = command_parts[2]
                    
                    if self.grupos_manager.desativar_grupo(target_group_id):
                        grupos_dict = self.grupos_manager.get_grupos()
                        nome = grupos_dict.get(target_group_id, {}).get('nome', 'Grupo sem nome')
                        self.bot.send_message(
                            chat_id, 
                            f"✅ Grupo `{target_group_id}` ({nome}) foi desativado com sucesso.", 
                            parse_mode='Markdown'
                        )
                        logger.info(f"Grupo {target_group_id} desativado por admin {user_id}")
                    else:
                        self.bot.send_message(
                            chat_id, 
                            f"❌ Grupo `{target_group_id}` não encontrado.", 
                            parse_mode='Markdown'
                        )
                
                elif subcommand == "remove" and len(command_parts) >= 3:
                    # Remover completamente um grupo da lista
                    target_group_id = command_parts[2]
                    
                    # Verificar se o grupo existe na lista antes de remover
                    grupos_dict = self.grupos_manager.get_grupos()
                    if target_group_id in grupos_dict:
                        nome = grupos_dict.get(target_group_id, {}).get('nome', 'Grupo sem nome')
                        
                        # Remover o grupo usando o método do GruposManager
                        if self.grupos_manager.remove_grupo(target_group_id):
                            self.bot.send_message(
                                chat_id, 
                                f"✅ Grupo `{target_group_id}` ({nome}) foi removido completamente da lista.", 
                                parse_mode='Markdown'
                            )
                            logger.info(f"Grupo {target_group_id} removido completamente por admin {user_id}")
                        else:
                            self.bot.send_message(
                                chat_id, 
                                f"❌ Erro ao remover o grupo `{target_group_id}` ({nome}).", 
                                parse_mode='Markdown'
                            )
                    else:
                        self.bot.send_message(
                            chat_id, 
                            f"❌ Grupo `{target_group_id}` não encontrado na lista.", 
                            parse_mode='Markdown'
                        )

                elif subcommand == "broadcast" and len(command_parts) >= 3:
                    # Enviar mensagem para todos os grupos
                    mensagem = " ".join(command_parts[2:])
                    enviados, falhas = self.broadcast_mensagem(mensagem)
                    
                    grupos_ativos = len(self.grupos_manager.get_grupos_ativos())
                    
                    self.bot.send_message(
                        chat_id, 
                        f"✅ Broadcast concluído: enviado para {enviados} grupos de um total de {grupos_ativos} grupos ativos, {falhas} falhas.",
                        parse_mode='Markdown'
                    )
                        
                else:
                    self.bot.send_message(chat_id, "❌ Comando administrativo inválido. Use /admin para ver a ajuda.")
                
            except Exception as e:
                logger.error(f"Erro no comando /admin: {str(e)}")
                self.bot.reply_to(message, "❌ Ocorreu um erro ao processar seu comando. Tente novamente mais tarde.")

    def get_grupos(self):
        """
        Obtém a lista de todos os grupos
        
        Returns:
            list: Lista de IDs dos grupos
        """
        grupos_dict = self.grupos_manager.get_grupos()
        return list(grupos_dict.keys())
    
    def get_grupos_ativos(self):
        """
        Obtém a lista de grupos ativos
        
        Returns:
            list: Lista de IDs dos grupos ativos
        """
        return self.grupos_manager.get_grupos_ativos()

    def enviar_mensagem(self, chat_id, mensagem):
        """
        Envia uma mensagem para um chat
        
        Args:
            chat_id: ID do chat no Telegram
            mensagem: Texto da mensagem
        
        Returns:
            bool: True se a mensagem foi enviada com sucesso, False caso contrário
        """
        try:
            self.bot.send_message(chat_id, mensagem, parse_mode='Markdown')
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {chat_id}: {str(e)}")
            return False

    def enviar_arquivo(self, chat_id, arquivo, caption=None):
        """
        Envia um arquivo para um chat
        
        Args:
            chat_id: ID do chat no Telegram
            arquivo: Caminho do arquivo
            caption: Legenda do arquivo (opcional)
            
        Returns:
            bool: True se o arquivo foi enviado com sucesso, False caso contrário
        """
        try:
            # Verificar tamanho do arquivo
            file_size = os.path.getsize(arquivo)
            max_size = 40 * 1024 * 1024  # 40MB (limite seguro para o Telegram)
            
            if file_size > max_size:
                # Arquivo muito grande para enviar diretamente
                size_mb = file_size / (1024 * 1024)
                mensagem = f"⚠️ *Arquivo muito grande para envio direto* ({size_mb:.1f}MB)\n\n"
                mensagem += f"O Telegram tem um limite de 50MB para envio de arquivos por bots, e este arquivo excede o limite seguro.\n\n"
                mensagem += f"*Recomendação:* Use o comando `/estado UF` para solicitar apenas a tabela de um estado específico."
                
                self.bot.send_message(
                    chat_id,
                    mensagem,
                    parse_mode='Markdown'
                )
                logger.warning(f"Arquivo muito grande para envio ({size_mb:.1f}MB): {arquivo}")
                return False
                
            with open(arquivo, 'rb') as f:
                self.bot.send_document(
                    chat_id,
                    f,
                    caption=caption,
                    visible_file_name=os.path.basename(arquivo),
                    parse_mode='Markdown'
                )
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar arquivo para {chat_id}: {str(e)}")
            return False

    def broadcast_mensagem(self, mensagem):
        """
        Envia uma mensagem para todos os grupos ativos
        
        Args:
            mensagem: Texto da mensagem
            
        Returns:
            tuple: (total_enviados, total_falhas)
        """
        grupos_ativos = self.grupos_manager.get_grupos_ativos()
        total = len(grupos_ativos)
        enviados = 0
        falhas = 0
        
        logger.info(f"Iniciando broadcast para {total} grupos ativos")
        
        for chat_id in grupos_ativos:
            try:
                success = self.enviar_mensagem(chat_id, mensagem)
                if success:
                    enviados += 1
                else:
                    falhas += 1
            except Exception as e:
                logger.error(f"Erro no broadcast para {chat_id}: {str(e)}")
                falhas += 1
        
        logger.info(f"Broadcast concluído: {enviados} enviados, {falhas} falhas")
        return enviados, falhas

    def broadcast_arquivo(self, arquivo, caption=None):
        """
        Envia um arquivo para todos os grupos ativos
        
        Args:
            arquivo: Caminho do arquivo
            caption: Legenda do arquivo (opcional)
            
        Returns:
            tuple: (total_enviados, total_falhas)
        """
        grupos_ativos = self.grupos_manager.get_grupos_ativos()
        total = len(grupos_ativos)
        enviados = 0
        falhas = 0
        
        logger.info(f"Iniciando broadcast de arquivo para {total} grupos ativos")
        
        for chat_id in grupos_ativos:
            try:
                success = self.enviar_arquivo(chat_id, arquivo, caption)
                if success:
                    enviados += 1
                else:
                    falhas += 1
            except Exception as e:
                logger.error(f"Erro no broadcast de arquivo para {chat_id}: {str(e)}")
                falhas += 1
        
        logger.info(f"Broadcast de arquivo concluído: {enviados} enviados, {falhas} falhas")
        return enviados, falhas

    def start_polling(self):
        """Inicia o polling do bot"""
        logger.info("Iniciando polling do bot")
        try:
            self.bot.infinity_polling(timeout=20, long_polling_timeout=5)
        except Exception as e:
            logger.error(f"Erro no polling do bot: {str(e)}")
            raise

    def stop_polling(self):
        """Para o polling do bot"""
        logger.info("Parando polling do bot")
        self.bot.stop_polling()