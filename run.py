"""
Ponto de entrada unificado para IBPT Bot e Automação
"""
import argparse
from app.start_bot import run_telegram_bot
from app.main import run_ibpt_automation

def main():
    parser = argparse.ArgumentParser(description='IBPT Bot e Automação')
    parser.add_argument('--modo', choices=['bot', 'automacao', 'ambos'], 
                        default='automacao', help='Modo de execução da aplicação')
    
    args = parser.parse_args()
    
    # Execute a automação IBPT primeiro se solicitado
    if args.modo in ['automacao', 'ambos']:
        run_ibpt_automation()
    
    # Execute o bot por último, pois ele bloqueia com polling infinito
    if args.modo in ['bot', 'ambos']:
        run_telegram_bot()

if __name__ == "__main__":
    main() 