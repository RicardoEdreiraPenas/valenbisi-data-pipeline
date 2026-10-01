import requests
import psycopg2
import time
import os
from datetime import datetime
from pymongo import MongoClient # Importante para NoSQL

# Variables de entorno (vienen del docker-compose.yml)
DB_HOST = os.getenv('DB_HOST', 'db')
DB_NAME = os.getenv('DB_NAME', 'valenbisi')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'password')
# URI para MongoDB: el nombre del servicio es 'mongodb'
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/')

def fetch_data():
    # URL correcta de la API de Valencia (con el typo 'dsiponibilidad')
    url = "https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/valenbisi-disponibilitat-valenbisi-dsiponibilidad/records?limit=100"
    try:
        r = requests.get(url)
        # Verificamos si la respuesta es correcta
        if r.status_code == 200:
            return r.json()['results']
        else:
            print(f"Error API status: {r.status_code}")
            return []
    except Exception as e:
        print(f"Error API: {e}")
        return []

def save_to_nosql(data):
    """Guarda el JSON bruto en MongoDB"""
    try:
        client = MongoClient(MONGO_URI)
        db = client["valenbisi_raw_db"]
        collection = db["stations_history"]
        
        # Insertamos el bloque completo de resultados con un timestamp de descarga
        document = {
            "download_time": datetime.now(),
            "results_count": len(data),
            "raw_data": data
        }
        collection.insert_one(document)
        print("INFO: Datos brutos guardados en MongoDB (NoSQL).")
        client.close()
    except Exception as e:
        print(f"Error MongoDB: {e}")

def save_to_sql(results):
    """Guarda los datos procesados en PostgreSQL"""
    try:
        conn = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        
        for station in results:
            # La nueva API usa geo_point_2d en lugar de geometry.coordinates
            lat = station['geo_point_2d']['lat']
            lon = station['geo_point_2d']['lon']
            
            # El campo 'name' ahora se llama 'address'
            station_name = station.get('address', 'Unknown')
            
            # El campo 'status' ahora se llama 'open' (T/F)
            station_status = 'OPEN' if station.get('open') == 'T' else 'CLOSED'
            
            cur.execute("""
                INSERT INTO valenbisi_raw (station_id, station_name, latitude, longitude, available_bikes, available_slots, station_status, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                station['number'], 
                station_name, 
                lat, 
                lon, 
                station['available'], 
                station['free'], 
                station_status, 
                datetime.now()
            ))
        
        conn.commit()
        print(f"INFO: {len(results)} registros insertados en PostgreSQL.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error DB SQL: {e}")

if __name__ == "__main__":
    print("Iniciando servicio de recolección (SQL + NoSQL)...")
    # Tiempo de espera inicial para asegurar que las DBs estén listas
    time.sleep(10) 
    
    while True:
        data = fetch_data()
        if data:
            # Ejecutamos ambas persistencias
            save_to_nosql(data)
            save_to_sql(data)
        
        print("Zzz... Esperando 5 minutos para la siguiente descarga.")
        time.sleep(300)