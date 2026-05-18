import json
import os

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

def wczytaj_json(nazwa_pliku): #wczytywanie z JSON
    if not nazwa_pliku.endswith('.json'): nazwa_pliku += '.json'
    if not os.path.exists(nazwa_pliku): return None
    try:
        with open(nazwa_pliku, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        #konwersja przy wczytywaniu (HH:MM -> float)
        processed_data = []
        for item in raw_data:
            start = item['godzina_rozp']
            end = item['godzina_zako']
            
            #jesli jest HH:MM zamienia na float
            if isinstance(start, str): start = czas_na_float(start)
            if isinstance(end, str): end = czas_na_float(end)
            
            item['godzina_rozp'] = start
            item['godzina_zako'] = end
            processed_data.append(item)
            
        return processed_data
    except Exception as e:
        print(f"Błąd JSON: {e}")
        return None

def zapisz_json(nazwa_pliku, dane): #zapisywanie do JSON
    if not nazwa_pliku.endswith('.json'): nazwa_pliku += '.json'
    try:
        #kopia danych do zapisu (nie psucie danych w pamięci RAM konwersją na stringi, wykresy sie źle wyświetlaja)
        dane_do_zapisu = []
        for r in dane:
            kopia = r.copy()
            kopia['godzina_rozp'] = float_na_czas(r['godzina_rozp'])
            kopia['godzina_zako'] = float_na_czas(r['godzina_zako'])
            dane_do_zapisu.append(kopia)
            
        with open(nazwa_pliku, 'w', encoding='utf-8') as f:
            json.dump(dane_do_zapisu, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Błąd zapisu JSON: {e}")