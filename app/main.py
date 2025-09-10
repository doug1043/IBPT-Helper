"""
Script principal para automação do download da tabela IBPT
"""
import datetime
from app.core.ibpt_automation import IBPTAutomation
from app.core.version_checker import IBPTVersionChecker
from app.utils.config import *
from app.telegram.instancia_bot import obter_instancia_bot
from app.utils.setup import configurar_logging, garantir_diretorios

# Configuração do logger
logger = configurar_logging(LOG_FILE, ENABLE_DEBUG)

def run_ibpt_automation():
    """
    Função que executa o fluxo de verificação e download da tabela IBPT
    """
    try:
        logger.info("=" * 50)
        logger.info("INICIANDO VERIFICAÇÃO DA TABELA IBPT")
        logger.info(f"Data/Hora: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        # Criar diretórios necessários
        garantir_diretorios([LOG_FILE, OUTPUT_FILE])
        
        # Verificar se há nova versão disponível
        checker = IBPTVersionChecker(base_url=IBPT_BASE_URL)
        needs_update, current_info, last_info = checker.needs_update()
        
        if not needs_update:
            logger.info("Tabela já está atualizada. Nada a fazer.")
            
            # Atualizar apenas o campo checked_at no arquivo
            if current_info and last_info:
                # Manter os dados existentes, mas atualizar o checked_at
                updated_info = last_info.copy()
                updated_info['checked_at'] = datetime.datetime.now().isoformat()
                checker.mark_as_downloaded(updated_info)
                logger.info("Campo 'checked_at' atualizado com sucesso.")
            
            return False
        
        # Se chegou aqui, precisa atualizar
        logger.info("Iniciando download da nova tabela...")
        
        ibpt = IBPTAutomation(cnpj=CNPJ, base_url=IBPT_BASE_URL)
        success = ibpt.run_automation(
            username=USERNAME,
            password=PASSWORD,
            estados=ESTADOS,
            output_path=OUTPUT_FILE
        )
        
        if not success:
            logger.error("Falha no processo de download.")
            return False
    except ValueError as e:
        logger.error(f"Erro de configuração: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Erro no processo: {str(e)}")
        return False

    try:
        # Marcar nova versão como baixada
        if current_info:
            checker.mark_as_downloaded(current_info)
        else:
            # Se não temos informações da versão atual do site,
            # vamos tentar obter novamente após o download
            try:
                current_info = checker.get_current_version_info()
                if current_info:
                    checker.mark_as_downloaded(current_info)
            except Exception as e:
                logger.error(f"Erro ao obter informações da versão após download: {str(e)}")
            
        # Enviar notificação pelo Telegram
        try:
            if TELEGRAM_TOKEN:
                logger.info("Enviando notificação pelo Telegram...")
                
                # Usar a instância singleton do bot
                bot = obter_instancia_bot()
                
                # Preparar mensagem
                version_info = "Nova versão disponível"
                version = "Desconhecida"
                vigencia = "Desconhecida"
                
                if current_info:
                    version = current_info.get('version', 'Desconhecida')
                    vigencia = current_info.get('vigencia_ate', 'Desconhecida')
                    version_info = f"Nova versão {version} (válida até {vigencia})"
                
                # Enviar mensagem para todos os grupos ativos
                mensagem = f"🆕 *{version_info}*\n\nA tabela IBPT foi atualizada e está disponível para download."
                enviados, falhas = bot.broadcast_mensagem(mensagem)
                grupos_ativos = len(bot.get_grupos_ativos())
                logger.info(f"Mensagem enviada para {enviados} grupos de um total de {grupos_ativos} grupos ativos ({falhas} falhas)")
                
                # Enviar arquivo para todos os grupos ativos
                caption = f"📊 *Tabela IBPT - Versão {version} (válida até {vigencia})*"
                enviados, falhas = bot.broadcast_arquivo(OUTPUT_FILE, caption)
                logger.info(f"Arquivo enviado para {enviados} grupos de um total de {grupos_ativos} grupos ativos ({falhas} falhas)")
                
        except Exception as e:
            logger.error(f"Erro ao enviar notificação pelo Telegram: {str(e)}")
        
        logger.info("Processo concluído com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"Erro no processo principal: {str(e)}")
        return False

# Manter compatibilidade com versões anteriores
main = run_ibpt_automation

if __name__ == "__main__":
    run_ibpt_automation() 