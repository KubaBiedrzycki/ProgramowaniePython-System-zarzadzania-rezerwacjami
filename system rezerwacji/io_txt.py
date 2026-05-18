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

def wczytaj_txt(nazwa_pliku): #wczytywanie z txt
    if not nazwa_pliku.endswith('.txt'): nazwa_pliku += '.txt'
    if not os.path.exists(nazwa_pliku): return None
    
    dane = []
    try:
        with open(nazwa_pliku, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        start = 1 if lines and "id;" in lines[0] else 0
        for line in lines[start:]:
            if not line.strip(): continue
            parts = line.strip().split(';')
            if len(parts) >= 6:
                #wykrywanie czy w pliku jest format HH:MM czy float
                raw_start = parts[4]
                raw_end = parts[5]
                
                val_start = czas_na_float(raw_start) if ':' in raw_start else float(raw_start)
                val_end = czas_na_float(raw_end) if ':' in raw_end else float(raw_end)

                dane.append({
                    "id": int(parts[0]),
                    "gabinet": parts[1],
                    "pracownik": parts[2],
                    "data": parts[3],
                    "godzina_rozp": val_start,
                    "godzina_zako": val_end
                })
        return dane
    except Exception as e:
        print(f"Błąd TXT: {e}")
        return []

def zapisz_txt(nazwa_pliku, dane): #zapisywanie do txt
    if not nazwa_pliku.endswith('.txt'): nazwa_pliku += '.txt'
    try:
        with open(nazwa_pliku, 'w', encoding='utf-8') as f:
            f.write("id;gabinet;pracownik;data;godzina_rozp;godzina_zako\n")
            for r in dane:
                #zapis w formacie HH:MM dla czytelnosci
                s_start = float_na_czas(r['godzina_rozp'])
                s_end = float_na_czas(r['godzina_zako'])
                f.write(f"{r['id']};{r['gabinet']};{r['pracownik']};{r['data']};{s_start};{s_end}\n")
    except Exception as e:
        print(f"Błąd zapisu: {e}")