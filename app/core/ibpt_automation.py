"""
Classe para automação do download da tabela IBPT
"""
import requests
import time
import re
from bs4 import BeautifulSoup, Tag
import os
from urllib.parse import urljoin
import datetime


class IBPTAutomation:
    def __init__(self, cnpj=None, base_url=None):
        self.session = requests.Session()
        if not base_url:
            raise ValueError("URL base do IBPT não configurada. Configure a variável de ambiente URL_IBPT.")
        self.base_url = base_url
        if not cnpj:
            raise ValueError("CNPJ não configurado. Configure a variável de ambiente CNPJ_EMPRESA.")
        self.cnpj = cnpj
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })
        self.request_time = None  # Armazena o momento da solicitação
    
    def login(self, username, password):
        """
        Realiza login no sistema IBPT e verifica se foi bem-sucedido
        """
        login_page_url = f"{self.base_url}/Site/Entrar"    
        login_post_url = f"{self.base_url}/Usuario/Login"  

        print(f"🔒 Iniciando processo de login...")
        print(f"🌐 Acessando página de login: {login_page_url}")
        
        try:
            response = self.session.get(login_page_url)
            print(f"📡 GET {login_page_url} -> Status {response.status_code}")
            print(f"🔁 URL final: {response.url}")
            
            # Verificar se a resposta é um redirecionamento
            if response.history:
                print(f"⚠️ Redirecionamentos detectados: {len(response.history)}")
                for hist in response.history:
                    print(f"   🔄 {hist.status_code} -> {hist.url}")
            
            # Verificar se a página tem título esperado
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.find('title')
            if title:
                print(f"📑 Título da página: {title.text.strip()}")
            
            csrf_token = soup.find('input', {'name': '__RequestVerificationToken'})
            if not csrf_token or not isinstance(csrf_token, Tag):
                print("❌ Token CSRF não encontrado na página!")
                with open("login_page_debug.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                raise Exception("Token CSRF não encontrado na página de login. HTML salvo em login_page_debug.html")
            
            token_value = csrf_token.attrs.get('value')
            if not token_value:
                raise Exception("Valor do token CSRF não encontrado")
            
            print(f"✅ Token CSRF encontrado: {token_value[:10]}...")
            
            login_data = {
                '__RequestVerificationToken': token_value,
                'Email': username,
                'Senha': password,
                'RememberMe': 'false'
            }
            
            print(f"📤 Enviando dados de login para: {login_post_url}")
            print(f"👤 Usuário: {username}")
            print(f"🔑 Senha: {'*' * len(password)}")
            
            # Adicionar headers mais parecidos com navegador
            login_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'text/html,application/xhtml+xml,application/xml',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Origin': self.base_url,
                'Referer': login_page_url
            }
            
            response = self.session.post(login_post_url, data=login_data, headers=login_headers, allow_redirects=True)
            
            print(f"📡 POST {login_post_url} -> Status {response.status_code}")
            print(f"🔁 URL final após login: {response.url}")
            
            # Verificar redirecionamentos na resposta
            if response.history:
                print(f"🔄 Histórico de redirecionamentos após login:")
                for hist in response.history:
                    print(f"   {hist.status_code} -> {hist.url}")
            
            # Verificar se retornou para a página de login
            if "/Site/Entrar" in response.url:
                print("❌ Redirecionado de volta para a página de login")
                with open("login_failed_debug.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                raise Exception("❌ Falha no login: Credenciais inválidas ou bloqueadas")
            
            # Verificar mensagens de erro específicas
            if "Credenciais" in response.text or "inválidas" in response.text.lower() or "incorret" in response.text.lower():
                print("❌ Mensagem de credenciais inválidas detectada na resposta")
                with open("login_failed_debug.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                raise Exception("❌ Falha no login: Credenciais inválidas ou bloqueadas")
            
            # Verificar se está autenticado
            expected_pages = ["Gerenciar empresa", "Dashboard", "Minha Empresa", "Minha Conta"]
            auth_confirmed = False
            
            for term in expected_pages:
                if term in response.text:
                    print(f"✅ Termo de autenticação encontrado: '{term}'")
                    auth_confirmed = True
                    break
            
            if not auth_confirmed:
                print("❌ Nenhum termo de autenticação encontrado na resposta")
                with open("login_debug.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                raise Exception("❌ Login aparentemente bem-sucedido, mas não autenticou (salvo em login_debug.html)")
            
            # Verificar cookies de autenticação
            cookies = self.session.cookies.get_dict()
            print(f"🍪 Cookies após login: {len(cookies)} encontrados")
            auth_cookie = False
            
            for cookie_name in cookies:
                if "auth" in cookie_name.lower() or "session" in cookie_name.lower() or ".aspx" in cookie_name.lower():
                    print(f"✅ Cookie de autenticação encontrado: {cookie_name}")
                    auth_cookie = True
            
            if not auth_cookie:
                print("⚠️ Nenhum cookie de autenticação identificado")
            
            print("✅ Login realizado com sucesso!")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão: {str(e)}")
            raise Exception(f"❌ Erro ao conectar: {str(e)}")
        except Exception as e:
            print(f"❌ Erro no processo de login: {str(e)}")
            raise
    
    def get_empresa_home(self):
        home_url = f"{self.base_url}/Empresa/Home"
        response = self.session.get(home_url)
        
        if "Minha Empresa" not in response.text and "Gerenciar empresa" not in response.text:
            with open("empresa_home_debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            raise Exception(f"❌ Não está autenticado! Conteúdo salvo em empresa_home_debug.html | Status: {response.status_code}")

        print("✅ Página da empresa acessada com sucesso")
        return response.text
    
    def request_table_download(self, estados=["CE"]):
        """
        Solicita o download da tabela para os estados especificados
        """
        request_url = f"{self.base_url}/TabelaAliquota/Solicitar?cnpj={self.cnpj}"
        
        print(f"📋 Iniciando solicitação de tabela...")
        print(f"🌐 URL de solicitação: {request_url}")
        print(f"🏢 CNPJ utilizado: {self.cnpj}")
        print(f"🗺️ Estados solicitados: {', '.join(estados)}")
        
        try:
            response = self.session.get(request_url)
            print(f"📡 GET {request_url} -> Status {response.status_code}")
            
            # Verificar redirecionamentos
            if response.history:
                print(f"⚠️ Redirecionamentos detectados: {len(response.history)}")
                for hist in response.history:
                    print(f"   🔄 {hist.status_code} -> {hist.url}")
                    
                # Se redirecionou para login, a sessão expirou
                if "/Site/Entrar" in response.url:
                    print("❌ Sessão expirada! Redirecionado para página de login")
                    with open("session_expired.html", "w", encoding="utf-8") as f:
                        f.write(response.text)
                    raise Exception("❌ Sessão expirada. Tente fazer login novamente.")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Verificar se a página contém mensagens de erro
            error_elements = soup.select('.text-danger, .alert-danger, .validation-summary-errors')
            if error_elements:
                for error in error_elements:
                    error_text = error.text.strip()
                    if error_text:
                        print(f"❌ Erro encontrado na página: {error_text}")
                
                with open("solicitar_error.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                print("❌ Página com erro salva em solicitar_error.html")
            
            # Buscar formulário e campos específicos
            form = soup.find('form')
            if not form:
                print("❌ Formulário não encontrado na página")
                with open("solicitar_noform.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                raise Exception("Formulário de solicitação não encontrado")
            
            # Verificar se o CNPJ está na página
            if self.cnpj in response.text:
                print(f"✅ CNPJ encontrado na página")
            else:
                print(f"⚠️ CNPJ não encontrado na página. Pode indicar problemas com a empresa cadastrada.")
            
            # Verificar checkbox de estados
            estados_options = soup.select('input[name="Estados"]')
            if estados_options:
                print(f"✅ Encontradas {len(estados_options)} opções de estados")
            else:
                print("⚠️ Nenhuma opção de estado encontrada na página")
            
            csrf_token = soup.find('input', {'name': '__RequestVerificationToken'})
            if not csrf_token or not isinstance(csrf_token, Tag):
                print("❌ Token CSRF não encontrado!")
                with open("solicitar_page_debug.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                raise Exception("Token CSRF não encontrado na página de solicitação")
            
            token_value = csrf_token.attrs.get('value')
            if not token_value:
                raise Exception("Valor do token CSRF não encontrado")
            
            print(f"✅ Token CSRF encontrado: {token_value[:10]}...")
            
            # Preparar dados do formulário
            request_data = {
                '__RequestVerificationToken': token_value,
                'Estados': estados,
                'FinalidadeArquivo': 'Tabela'  
            }
            
            print(f"📤 Enviando solicitação POST para {request_url}")
            print(f"📋 Dados: Token CSRF, {len(estados)} estados, finalidade=Tabela")
            
            # Adicionar headers adicionais
            post_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'text/html,application/xhtml+xml,application/xml',
                'Referer': request_url
            }
            
            # Enviar solicitação
            response = self.session.post(request_url, data=request_data, headers=post_headers)
            
            print(f"📡 POST {request_url} -> Status {response.status_code}")
            
            if response.status_code == 200:
                # Verificar se há mensagens de sucesso ou erro na resposta
                soup = BeautifulSoup(response.content, 'html.parser')
                
                success_msg = soup.select('.alert-success, .text-success')
                if success_msg:
                    for msg in success_msg:
                        print(f"✅ Mensagem de sucesso: {msg.text.strip()}")
                
                error_msg = soup.select('.alert-danger, .text-danger, .validation-summary-errors')
                if error_msg:
                    for msg in error_msg:
                        error_text = msg.text.strip()
                        if error_text:
                            print(f"❌ Mensagem de erro: {error_text}")
                    
                    with open("request_error_response.html", "w", encoding="utf-8") as f:
                        f.write(response.text)
                    print("❌ Resposta com erro salva em request_error_response.html")
                    return False
                
                print("✅ Solicitação de tabela enviada com sucesso")
                now = datetime.datetime.now()
                print(f"⏱️  Hora atual do sistema: {now.strftime('%d/%m/%Y %H:%M:%S')}")
                print(f"⏱️  Timestamp UTC: {datetime.datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC")
                self.request_time = now  # ⏰ Salva o momento da solicitação
                return True
            else:
                print(f"❌ Erro na solicitação: {response.status_code}")
                with open("request_http_error.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão: {str(e)}")
            raise Exception(f"❌ Erro ao conectar: {str(e)}")
        except Exception as e:
            print(f"❌ Erro no processo de solicitação: {str(e)}")
            raise
    
    def check_download_status(self, max_attempts=60, delay=15):
        """
        Verifica o status do processamento e encontra o arquivo mais recente disponível
        ou aguarda até que um novo arquivo seja gerado após a solicitação atual
        """
        history_url = f"{self.base_url}/TabelaAliquota/Historico?cnpj={self.cnpj}"
        print("🔄 Verificando status do processamento...")
        
        # Flag para indicar se encontramos um arquivo disponível (mesmo que seja antigo)
        arquivo_disponivel = False
        mais_recente_url = None
        mais_recente_time = None

        for attempt in range(1, max_attempts + 1):
            response = self.session.get(history_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Busca todas as <tr> dentro da tabela, exceto o cabeçalho
            table = soup.find('table', class_='table')
            if not table or not isinstance(table, Tag):
                print("❌ Tabela não encontrada")
                time.sleep(delay)
                continue
                
            rows = table.find_all('tr')
            if len(rows) <= 1:
                print("❌ Nenhum histórico encontrado")
                time.sleep(delay)
                continue
                
            # Pular o cabeçalho (thead)
            rows = rows[1:]
                
            print(f"📊 Encontrados {len(rows)} registros no histórico")
            
            # Verifica todos os registros buscando o mais recente após a solicitação
            achou_arquivo_apos_solicitacao = False
            
            for row in rows:
                download_btn = row.select_one("a.btn-success")
                if download_btn:
                    # Arquivo está pronto para download
                    href = download_btn.get('href')
                    
                    # Extrai timestamp do URL para validar
                    match = re.search(r'/(\d{17})/', href)
                    
                    if match:
                        file_timestamp = match.group(1)
                        # Pega apenas os primeiros 14 dígitos para criar datetime
                        file_time = datetime.datetime.strptime(file_timestamp[:14], "%Y%m%d%H%M%S")
                        print(f"🔍 Análise do timestamp do arquivo:")
                        print(f"   📅 Timestamp original: {file_timestamp}")
                        print(f"   📅 Convertido para: {file_time.strftime('%d/%m/%Y %H:%M:%S')}")
                        
                        # Verifica se é o arquivo mais recente encontrado até agora
                        if mais_recente_time is None or file_time > mais_recente_time:
                            mais_recente_time = file_time
                            mais_recente_url = urljoin(self.base_url, href)
                            arquivo_disponivel = True
                        
                        # Verifica se foi criado em uma janela razoável em torno da solicitação
                        # (até 3 horas antes ou 1 hora depois)
                        if self.request_time:
                            time_diff = (file_time - self.request_time).total_seconds()
                            is_near_request = time_diff >= -10800 and time_diff <= 3600  # -3h a +1h
                            
                            if is_near_request:
                                download_url = urljoin(self.base_url, href)
                                print(f"✅ Arquivo encontrado próximo à solicitação!")
                                print(f"   📅 Arquivo criado: {file_time.strftime('%d/%m/%Y %H:%M:%S')}")
                                print(f"   📅 Solicitação feita: {self.request_time.strftime('%d/%m/%Y %H:%M:%S')}")
                                print(f"   ⏱️  Diferença: {time_diff/60:.1f} minutos")
                                return download_url
            
            # Se chegou aqui, não encontrou arquivo após a solicitação
            # Verificar se temos um arquivo pendente em processamento
            pendente = False
            for row in rows:
                pendente_span = row.select_one("span.pendente")
                if pendente_span:
                    pendente = True
                    print(f"⏳ Arquivo ainda em processamento... Tentativa {attempt}/{max_attempts}")
                    break
            
            if not pendente:
                # Se não tem pendente e já tentamos algumas vezes, vamos usar o mais recente disponível
                if arquivo_disponivel and attempt >= 3:
                    print(f"⚠️ Nenhum arquivo encontrado após a solicitação, mas há arquivos disponíveis.")
                    print(f"   📅 Arquivo mais recente: {mais_recente_time.strftime('%d/%m/%Y %H:%M:%S')}")
                    if self.request_time:
                        print(f"   📅 Solicitação feita: {self.request_time.strftime('%d/%m/%Y %H:%M:%S')}")
                    print(f"   ⚠️ Usando o arquivo mais recente disponível após 3 tentativas.")
                    return mais_recente_url
                else:
                    print(f"🔍 Verificando status... Tentativa {attempt}/{max_attempts}")
            
            if attempt < max_attempts:
                print(f"⏳ Aguardando {delay}s para próxima verificação...")
                time.sleep(delay)

        # Se o loop terminar, verificamos o que fazer
        if arquivo_disponivel and self.request_time and mais_recente_time:
            print(f"⚠️ Timeout: Verificando se o arquivo mais recente encontrado é válido.")
            print(f"   📅 Arquivo mais recente: {mais_recente_time.strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"   📅 Solicitação feita:   {self.request_time.strftime('%d/%m/%Y %H:%M:%S')}")

            # Compara o tempo do arquivo mais recente com o tempo da solicitação.
            # Damos uma margem de segurança (ex: 5 minutos) para evitar problemas com sincronia de relógio.
            if mais_recente_time < (self.request_time - datetime.timedelta(minutes=5)):
                print(f"❌ O arquivo mais recente é antigo. Nenhum arquivo novo foi gerado.")
                raise Exception("❌ Timeout: Nenhum arquivo NOVO foi gerado no tempo esperado.")
            else:
                # O arquivo mais recente é posterior à solicitação, então é seguro usá-lo.
                print(f"✅ O arquivo mais recente é válido e posterior à solicitação. Usando este arquivo.")
                return mais_recente_url
            
        raise Exception("❌ Timeout: Arquivo não foi processado no tempo esperado e nenhum arquivo válido foi encontrado.")

    def download_file(self, download_url, output_path="tabela_ibpt.zip"):
        print(f"📥 Iniciando download...")
        print(f"🔗 URL: {download_url}")
        print(f"📁 Destino: {output_path}")
        
        response = self.session.get(download_url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(output_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        print(f"\r📊 Progresso: {progress:.1f}% ({downloaded_size}/{total_size} bytes)", end="", flush=True)
        
        print(f"\n✅ Download concluído: {output_path} ({downloaded_size} bytes)")
        return output_path

    def run_automation(self, username, password, estados=["CE"], output_path="tabela_ibpt.zip"):
        try:
            print("🚀 Iniciando processo de download...")
            print(f"📅 Data/Hora: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"👤 Usuário: {username}")
            print(f"📍 Estados: {', '.join(estados)}")
            print(f"📁 Arquivo: {output_path}")
            print("-" * 50)
            
            # 1. Fazer login
            if not self.login(username, password):
                return False
            
            # 2. Acessar página da empresa
            self.get_empresa_home()
            
            # 3. Solicitar download da tabela
            if not self.request_table_download(estados):
                return False
            
            # 4. Aguardar processamento e obter link
            download_url = self.check_download_status()
            
            # 5. Baixar arquivo
            self.download_file(download_url, output_path)
            
            print("\n✅ DOWNLOAD REALIZADO COM SUCESSO!")
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO NO DOWNLOAD: {str(e)}")
            return False 