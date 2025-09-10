"""
Verificador de versões da tabela IBPT
"""
import requests
import re
import json
import os
from datetime import datetime
import logging
from bs4 import BeautifulSoup, Tag

# Configurar logging
logger = logging.getLogger(__name__)

class IBPTVersionChecker:
    """
    Classe para verificar se há novas versões da tabela IBPT disponíveis
    comparando com a última versão baixada
    """
    
    def __init__(self, version_file="data/last_version_downloaded.txt", base_url=None):
        """
        Inicializa o verificador de versões
        
        Args:
            version_file: Arquivo para armazenar informações da última versão baixada
            base_url: URL base do site do IBPT
        """
        self.version_file = version_file
        self.current_version_info = None
        
        if not base_url:
            raise ValueError("URL base do IBPT não configurada. Configure a variável de ambiente URL_IBPT.")
        self.base_url = base_url
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })
    
    def get_current_version_info(self):
        """
        Obtém informações da versão atual disponível no site do IBPT
        
        Returns:
            dict: Informações da versão atual ou None se não conseguir obter
        """
        try:
            print("🔍 Verificando versão atual no site IBPT...")
            
            # Fazer requisição para a página inicial
            response = self.session.get(self.base_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar pelo popup de comunicado
            popup = soup.find('div', {'id': 'popupshadow'})
            if not popup or not isinstance(popup, Tag):
                print("⚠️ Popup de comunicado não encontrado")
                
                # Tentar extrair do texto geral da página
                pattern = r"vers[aã]o\s+([0-9.A-Z]+).+?vigente\s+at[eé]\s+(\d{2}/\d{2}/\d{4})"
                match = re.search(pattern, response.text, re.IGNORECASE)
                
                if match:
                    version = match.group(1)
                    vigencia_ate = match.group(2)
                    
                    # Converter data para formato datetime
                    vigencia_datetime = datetime.strptime(vigencia_ate, "%d/%m/%Y").strftime("%Y-%m-%dT%H:%M:%S")
                    
                    print(f"✅ Versão atual encontrada: {version}")
                    print(f"📅 Vigência até: {vigencia_ate}")
                    
                    # Retornar informações da versão
                    return {
                        "version": version,
                        "vigencia_ate": vigencia_ate,
                        "vigencia_datetime": vigencia_datetime,
                        "checked_at": datetime.now().isoformat()
                    }
                else:
                    print("❌ Não foi possível encontrar informações da versão atual")
                    return None
            
            # Extrair versão (ex: 25.2.A)
            popup_text = popup.get_text()
            version_match = re.search(r'Versão\s+([0-9.A-Z]+)', popup_text, re.IGNORECASE)
            if not version_match:
                print("⚠️ Versão não encontrada no popup")
                return None
            
            version = version_match.group(1)
            
            # Extrair data de vigência final (ex: 31/07/2025)
            vigencia_match = re.search(r'até\s+(\d{2}/\d{2}/\d{4})', popup_text, re.IGNORECASE)
            if not vigencia_match:
                print("⚠️ Data de vigência não encontrada")
                return None
            
            vigencia_ate = vigencia_match.group(1)
            
            # Converter data para formato datetime
            vigencia_datetime = datetime.strptime(vigencia_ate, "%d/%m/%Y").strftime("%Y-%m-%dT%H:%M:%S")
            
            print(f"✅ Versão atual encontrada: {version}")
            print(f"📅 Vigência até: {vigencia_ate}")
            
            # Retornar informações da versão
            return {
                "version": version,
                "vigencia_ate": vigencia_ate,
                "vigencia_datetime": vigencia_datetime,
                "checked_at": datetime.now().isoformat()
            }
                
        except Exception as e:
            print(f"❌ Erro ao verificar versão atual: {str(e)}")
            return None
    
    def get_last_downloaded_version(self):
        """
        Obtém informações da última versão baixada
        
        Returns:
            dict: Informações da última versão baixada ou None se não existir
        """
        if not os.path.exists(self.version_file):
            print("⚠️ Arquivo de versão não encontrado. Primeira execução?")
            return None
            
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # Tentar carregar como JSON (formato novo)
            try:
                version_info = json.loads(content)
                print(f"📋 Última versão baixada: {version_info.get('version', 'N/A')}")
                print(f"📅 Vigência até: {version_info.get('vigencia_ate', 'N/A')}")
                return version_info
            except json.JSONDecodeError:
                # Formato antigo - apenas a data
                if re.match(r'\d{2}/\d{2}/\d{4}', content):
                    print(f"📋 Formato antigo detectado - vigência: {content}")
                    return {
                        'version': 'unknown',
                        'vigencia_ate': content,
                        'vigencia_datetime': datetime.strptime(content, "%d/%m/%Y").isoformat()
                    }
                else:
                    print("⚠️ Formato de arquivo inválido")
                    return None
        except Exception as e:
            print(f"❌ Erro ao ler arquivo de versão: {str(e)}")
            return None
    
    def mark_as_downloaded(self, version_info):
        """
        Marca uma versão como baixada
        
        Args:
            version_info: Informações da versão baixada
            
        Returns:
            bool: True se salvou com sucesso, False caso contrário
        """
        try:
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(self.version_file), exist_ok=True)
            
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, ensure_ascii=False, indent=2)
            print(f"💾 Informações da versão salvas: {version_info['version']}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar informações da versão: {str(e)}")
            return False
    
    def needs_update(self):
        """
        Verifica se é necessário baixar uma nova versão
        
        Returns:
            tuple: (precisa_atualizar, info_versao_atual, info_ultima_versao)
        """
        print("🔄 Verificando se há nova versão disponível...")
        
        # Obter informações da versão atual
        current_info = self.get_current_version_info()
        self.current_version_info = current_info
        
        # Obter informações da última versão baixada
        last_info = self.get_last_downloaded_version()
        
        # Se não conseguiu obter informações da versão atual, assume que precisa atualizar
        if not current_info:
            print("⚠️ Não foi possível verificar a versão atual. Assumindo que precisa atualizar.")
            return True, None, last_info
        
        # Se não há registro da última versão baixada, precisa atualizar
        if not last_info:
            print("⚠️ Não há registro da última versão baixada. Precisa atualizar.")
            return True, current_info, None
        
        # Comparar datas de vigência
        current_vigencia = datetime.fromisoformat(current_info['vigencia_datetime'].split('T')[0])
        last_vigencia = datetime.fromisoformat(last_info['vigencia_datetime'].split('T')[0])
        
        print("📊 Comparação de versões:")
        print(f"   📅 Atual: {current_info['version']} (até {current_info['vigencia_ate']})")
        print(f"   📅 Última baixada: {last_info.get('version', 'N/A')} (até {last_info['vigencia_ate']})")
        
        # Se a versão ou data de vigência mudou, precisa atualizar
        if current_vigencia > last_vigencia:
            print("🆕 Nova versão disponível!")
            return True, current_info, last_info
        elif current_vigencia == last_vigencia and current_info['version'] != last_info.get('version', ''):
            print("🔄 Mesma vigência, mas versão diferente - atualizando")
            return True, current_info, last_info
        else:
            print("✅ Tabela já está atualizada")
            return False, current_info, last_info 