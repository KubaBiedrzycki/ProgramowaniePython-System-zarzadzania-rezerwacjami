from pymongo import MongoClient

URI = "mongodb://localhost:27017/"
DB_NAME = "przychodnia"
COL = "rezerwacje"

#===KONWERSJE CZASU===
def czas_na_float(czas_str):
    try:
        h, m = map(int, czas_str.split(':'))
        return h + m/60.0
    except: return 0.0

def float_na_czas(czas_float):
    h = int(czas_float)
    m = int((czas_float - h) * 60)
    return f"{h:02d}:{m:02d}"

def polacz(): #polaczenie z baza danych mongo
    try:
        client = MongoClient(URI, serverSelectionTimeoutMS=2000)
        return client[DB_NAME][COL]
    except: return None

def eksport_do_mongo(dane): #eksportowanie
    col = polacz()
    if col is None: return
    col.delete_many({})
    
    #konwersja na HH:MM przed wysłaniem
    dane_export = []
    for r in dane:
        kopia = r.copy()
        kopia['godzina_rozp'] = float_na_czas(r['godzina_rozp'])
        kopia['godzina_zako'] = float_na_czas(r['godzina_zako'])
        dane_export.append(kopia)
        
    if dane_export: col.insert_many(dane_export)

def import_z_mongo(): #importowanie
    col = polacz()
    if col is None: return []
    dane = []
    for doc in col.find():
        if "_id" in doc: del doc["_id"]
        #konwersja powrotna HH:MM -> float
        if isinstance(doc['godzina_rozp'], str):
            doc['godzina_rozp'] = czas_na_float(doc['godzina_rozp'])
        if isinstance(doc['godzina_zako'], str):
            doc['godzina_zako'] = czas_na_float(doc['godzina_zako'])
        dane.append(doc)
    return dane