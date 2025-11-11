"""
Monitor de Webhooks de Wialon en Tiempo Real
=============================================

Este script monitorea el archivo wialon_webhooks.log y muestra
los nuevos webhooks en tiempo real con formato coloreado.

Uso:
    python scripts/monitor_wialon_webhooks.py

O para ver los últimos N registros:
    python scripts/monitor_wialon_webhooks.py --tail 10
"""

import os
import time
import sys
from datetime import datetime

# Colores ANSI
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'


def tail_file(filename, n_lines=20):
    """Muestra las últimas N líneas del archivo"""
    if not os.path.exists(filename):
        print(f"{Colors.YELLOW}⚠ Archivo {filename} no existe aún. Esperando...{Colors.ENDC}")
        return []
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        return lines[-n_lines:] if len(lines) > n_lines else lines


def format_webhook_entry(lines):
    """Formatea una entrada de webhook con colores"""
    output = []
    is_error = any('✗ ERROR' in line for line in lines)
    
    for line in lines:
        if '=' * 50 in line:
            output.append(f"{Colors.CYAN}{line}{Colors.ENDC}")
        elif 'WIALON WEBHOOK RECIBIDO' in line:
            output.append(f"{Colors.BOLD}{Colors.CYAN}{line}{Colors.ENDC}")
        elif 'Timestamp:' in line:
            output.append(f"{Colors.YELLOW}{line}{Colors.ENDC}")
        elif '✓ PROCESADO EXITOSAMENTE' in line:
            output.append(f"{Colors.GREEN}{Colors.BOLD}{line}{Colors.ENDC}")
        elif '✗ ERROR' in line:
            output.append(f"{Colors.RED}{Colors.BOLD}{line}{Colors.ENDC}")
        elif 'Success: False' in line:
            output.append(f"{Colors.RED}{line}{Colors.ENDC}")
        elif 'Success: True' in line:
            output.append(f"{Colors.GREEN}{line}{Colors.ENDC}")
        else:
            output.append(line)
    
    return ''.join(output)


def monitor_file(filename):
    """Monitorea el archivo en tiempo real (modo tail -f)"""
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}")
    print(f"MONITOR DE WEBHOOKS DE WIALON")
    print(f"{'='*80}{Colors.ENDC}\n")
    print(f"Monitoreando: {Colors.YELLOW}{filename}{Colors.ENDC}")
    print(f"Presiona Ctrl+C para salir\n")
    
    # Mostrar últimas 20 líneas existentes
    if os.path.exists(filename):
        print(f"{Colors.CYAN}--- Últimos registros ---{Colors.ENDC}")
        last_lines = tail_file(filename, 100)
        print(''.join(last_lines[-100:]))
    
    # Crear archivo si no existe
    if not os.path.exists(filename):
        open(filename, 'a').close()
    
    # Seguir archivo en tiempo real
    with open(filename, 'r', encoding='utf-8') as f:
        # Ir al final del archivo
        f.seek(0, 2)
        
        print(f"\n{Colors.GREEN}✓ Esperando nuevos webhooks...{Colors.ENDC}\n")
        
        while True:
            line = f.readline()
            if line:
                # Colorear y mostrar
                if '=' * 50 in line:
                    print(f"{Colors.CYAN}{line.rstrip()}{Colors.ENDC}")
                elif 'WIALON WEBHOOK RECIBIDO' in line:
                    print(f"{Colors.BOLD}{Colors.CYAN}{line.rstrip()}{Colors.ENDC}")
                elif 'Timestamp:' in line:
                    print(f"{Colors.YELLOW}{line.rstrip()}{Colors.ENDC}")
                elif '✓ PROCESADO EXITOSAMENTE' in line:
                    print(f"{Colors.GREEN}{Colors.BOLD}{line.rstrip()}{Colors.ENDC}")
                elif '✗ ERROR' in line:
                    print(f"{Colors.RED}{Colors.BOLD}{line.rstrip()}{Colors.ENDC}")
                elif 'Success: False' in line:
                    print(f"{Colors.RED}{line.rstrip()}{Colors.ENDC}")
                elif 'Success: True' in line:
                    print(f"{Colors.GREEN}{line.rstrip()}{Colors.ENDC}")
                else:
                    print(line.rstrip())
            else:
                time.sleep(0.1)


def main():
    """Punto de entrada principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Monitor de webhooks de Wialon en tiempo real"
    )
    parser.add_argument(
        '--tail',
        type=int,
        metavar='N',
        help='Mostrar solo las últimas N líneas y salir'
    )
    parser.add_argument(
        '--file',
        type=str,
        default='wialon_webhooks.log',
        help='Archivo de log a monitorear (default: wialon_webhooks.log)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.tail:
            # Modo tail: mostrar últimas N líneas y salir
            lines = tail_file(args.file, args.tail)
            print(''.join(lines))
        else:
            # Modo monitor: seguir archivo en tiempo real
            monitor_file(args.file)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Monitor detenido por el usuario{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.ENDC}")
        sys.exit(1)


if __name__ == "__main__":
    main()

