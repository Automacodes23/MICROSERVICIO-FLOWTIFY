"""
Script para verificar y limpiar locks de MySQL
"""
import pymysql
import sys
import time

config = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',
    'password': '',
    'database': 'logistics_db',
    'charset': 'utf8mb4',
    'connect_timeout': 5
}

def main():
    print("\n" + "="*60)
    print("Verificando locks en MySQL")
    print("="*60 + "\n")
    
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # 1. Ver procesos activos
        print("[1] Procesos activos en MySQL:")
        cursor.execute("SHOW PROCESSLIST")
        processes = cursor.fetchall()
        
        print(f"\n  Total de procesos: {len(processes)}")
        for proc in processes:
            pid, user, host, db, command, time_val, state, info = proc
            if command != 'Sleep' or db == 'logistics_db':
                print(f"    PID {pid}: {user}@{host} - DB:{db} - CMD:{command} - Time:{time_val}s")
                if info:
                    print(f"           Query: {info[:80]}...")
        
        # 2. Ver locks de tabla
        print("\n[2] Locks de tabla:")
        cursor.execute("""
            SELECT 
                r.trx_id waiting_trx_id,
                r.trx_mysql_thread_id waiting_thread,
                r.trx_query waiting_query,
                b.trx_id blocking_trx_id,
                b.trx_mysql_thread_id blocking_thread,
                b.trx_query blocking_query
            FROM information_schema.innodb_lock_waits w
            INNER JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
            INNER JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id
        """)
        locks = cursor.fetchall()
        
        if locks:
            print(f"  Locks encontrados: {len(locks)}")
            for lock in locks:
                print(f"    Bloqueado por thread: {lock[4]}")
        else:
            print("  No hay locks activos")
        
        # 3. Ver transacciones activas
        print("\n[3] Transacciones activas:")
        cursor.execute("""
            SELECT trx_id, trx_state, trx_started, trx_mysql_thread_id, trx_query
            FROM information_schema.innodb_trx
        """)
        transactions = cursor.fetchall()
        
        if transactions:
            print(f"  Transacciones activas: {len(transactions)}")
            for trx in transactions:
                print(f"    TRX {trx[0]}: {trx[1]} - Thread:{trx[3]} - Started:{trx[2]}")
                if trx[4]:
                    print(f"           Query: {trx[4][:80]}...")
        else:
            print("  No hay transacciones activas")
        
        # 4. Matar procesos problemáticos (excepto el nuestro)
        print("\n[4] Limpiando procesos...")
        current_pid = conn.thread_id()
        killed = 0
        
        for proc in processes:
            pid = proc[0]
            db = proc[3]
            command = proc[4]
            
            # Matar procesos que estén en logistics_db y no sean el actual
            if pid != current_pid and db == 'logistics_db' and command != 'Sleep':
                try:
                    cursor.execute(f"KILL {pid}")
                    print(f"  [OK] Proceso {pid} terminado")
                    killed += 1
                except Exception as e:
                    print(f"  [WARN] No se pudo terminar proceso {pid}: {e}")
        
        if killed == 0:
            print("  No hay procesos que terminar")
        else:
            print(f"\n  Total de procesos terminados: {killed}")
            print("  Esperando 2 segundos...")
            time.sleep(2)
        
        print("\n" + "="*60)
        print("[OK] Limpieza completada")
        print("="*60 + "\n")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

