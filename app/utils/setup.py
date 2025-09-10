"""
Funcionalidades compartilhadas de configuração para a aplicação
"""
import os
import logging
import sys

def configurar_logging(arquivo_log, habilitar_debug=False):
    """Configura logging para a aplicação"""
    os.makedirs(os.path.dirname(arquivo_log), exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO if not habilitar_debug else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(arquivo_log),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def garantir_diretorios(caminhos):
    """Cria diretórios se eles não existirem"""
    for caminho in caminhos:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
