"""Ver eventos guardados en BD"""
import pymysql

conn = pymysql.connect(host='localhost', port=3307, user='root', password='', db='logistics_db')
cursor = conn.cursor(pymysql.cursors.DictCursor)

cursor.execute('SELECT id, trip_id, event_type, processed, created_at FROM events ORDER BY created_at DESC LIMIT 5')
events = cursor.fetchall()

print('Ultimos 5 eventos en BD:')
print('-'*80)
for e in events:
    trip_short = str(e['trip_id'])[:8] if e['trip_id'] else 'None'
    processed = 'SI' if e['processed'] else 'NO'
    print(f"{e['event_type']:25} | Proc: {processed} | Trip: {trip_short}... | {e['created_at']}")

conn.close()

