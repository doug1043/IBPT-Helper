import os
import json
import logging

logger = logging.getLogger(__name__)

class GruposManager:
    """
    Classe para gerenciar os grupos com status ativo/inativo
    """
    def __init__(self, grupos_file="data/grupos.json"):
        self.grupos_file = grupos_file
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(self.grupos_file), exist_ok=True)
        # Inicializar o arquivo se não existir
        if not os.path.exists(self.grupos_file):
            self.save_grupos({})
    
    def get_grupos(self):
        """
        Obtém o dicionário de grupos com seus status
        
        Returns:
            dict: Dicionário com IDs dos grupos como chaves e status como valores
        """
        try:
            if os.path.exists(self.grupos_file):
                with open(self.grupos_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Erro ao obter grupos: {str(e)}")
            return {}
    
    def get_grupos_ativos(self):
        """
        Obtém a lista de IDs dos grupos ativos
        
        Returns:
            list: Lista de IDs dos grupos ativos
        """
        grupos = self.get_grupos()
        return [chat_id for chat_id, status in grupos.items() if status.get('ativo', False)]
    
    def get_grupos_inativos(self):
        """
        Obtém a lista de IDs dos grupos inativos
        
        Returns:
            list: Lista de IDs dos grupos inativos
        """
        grupos = self.get_grupos()
        return [chat_id for chat_id, status in grupos.items() if not status.get('ativo', False)]
    
    def add_grupo(self, chat_id, nome_grupo=None, is_active=False):
        """
        Adiciona um grupo à lista ou atualiza seu nome.
        Por padrão, o grupo é adicionado como inativo.
        
        Args:
            chat_id: ID do chat do grupo
            nome_grupo: Nome do grupo (opcional)
            is_active: Define se o grupo deve ser ativado no momento da adição
            
        Returns:
            bool: True se o grupo foi adicionado/atualizado, False caso contrário
        """
        try:
            grupos = self.get_grupos()
            chat_id_str = str(chat_id)
            
            # Adicionar/atualizar grupo
            if chat_id_str in grupos:
                # Apenas atualiza o nome se fornecido
                if nome_grupo:
                    grupos[chat_id_str]['nome'] = nome_grupo
            else:
                grupos[chat_id_str] = {
                    'ativo': is_active,
                    'nome': nome_grupo or 'Grupo sem nome'
                }
            
            # Salvar alterações
            self.save_grupos(grupos)
            if not is_active:
                logger.info(f"Grupo adicionado como inativo: {chat_id}")
            else:
                logger.info(f"Grupo adicionado e ativado: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar/ativar grupo: {str(e)}")
            return False
    
    def remove_grupo(self, chat_id):
        """
        Remove um grupo da lista completamente
        
        Args:
            chat_id: ID do chat do grupo
            
        Returns:
            bool: True se o grupo foi removido, False caso contrário
        """
        try:
            grupos = self.get_grupos()
            chat_id_str = str(chat_id)
            
            # Remover grupo se existir
            if chat_id_str in grupos:
                del grupos[chat_id_str]
                # Salvar alterações
                self.save_grupos(grupos)
                logger.info(f"Grupo removido: {chat_id}")
                return True
            else:
                logger.info(f"Tentativa de remover grupo inexistente: {chat_id}")
                return False
        except Exception as e:
            logger.error(f"Erro ao remover grupo: {str(e)}")
            return False
    
    def desativar_grupo(self, chat_id):
        """
        Desativa um grupo (mantém na lista mas não envia mensagens)
        
        Args:
            chat_id: ID do chat do grupo
            
        Returns:
            bool: True se o grupo foi desativado, False caso contrário
        """
        try:
            grupos = self.get_grupos()
            chat_id_str = str(chat_id)
            
            # Desativar grupo se existir
            if chat_id_str in grupos:
                grupos[chat_id_str]['ativo'] = False
                # Salvar alterações
                self.save_grupos(grupos)
                logger.info(f"Grupo desativado: {chat_id}")
                return True
            else:
                logger.info(f"Tentativa de desativar grupo inexistente: {chat_id}")
                return False
        except Exception as e:
            logger.error(f"Erro ao desativar grupo: {str(e)}")
            return False
    
    def ativar_grupo(self, chat_id):
        """
        Ativa um grupo para receber mensagens
        
        Args:
            chat_id: ID do chat do grupo
            
        Returns:
            bool: True se o grupo foi ativado, False caso contrário
        """
        try:
            grupos = self.get_grupos()
            chat_id_str = str(chat_id)
            
            # Ativar grupo se existir
            if chat_id_str in grupos:
                grupos[chat_id_str]['ativo'] = True
                # Salvar alterações
                self.save_grupos(grupos)
                logger.info(f"Grupo ativado: {chat_id}")
                return True
            else:
                logger.info(f"Tentativa de ativar grupo inexistente: {chat_id}")
                return False
        except Exception as e:
            logger.error(f"Erro ao ativar grupo: {str(e)}")
            return False
    
    def save_grupos(self, grupos):
        """
        Salva o dicionário de grupos no arquivo
        
        Args:
            grupos: Dicionário com IDs dos grupos como chaves e status como valores
        """
        try:
            with open(self.grupos_file, 'w') as f:
                json.dump(grupos, f, indent=4)
        except Exception as e:
            logger.error(f"Erro ao salvar grupos: {str(e)}")
