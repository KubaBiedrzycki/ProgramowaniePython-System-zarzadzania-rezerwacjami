import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg #wstawia wykres matplotliba do okna tkinter
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker #formatowanie osi y
import datetime
import io_txt
import io_json
import mongo_utils

#===DARK MODE=== (stale kolory)
COL_BG = "#2E2E2E"       #ciemne tło główne okna
COL_PANEL = "#3C3F41"    #tło paneli (lewy i prawy nieco jaśniejsze)
COL_FG = "#E0E0E0"       #jasny tekst (widoczna na ciemnym tle)
COL_ACCENT = "#00ADB5"   #akcent (niebieski) (do przycisków, wykresu)
COL_ENTRY = "#45494A"    #tło pól tekstowych
COL_BTN = "#505050"      #tło przycisków
COL_BTN_RED = "#CF6679"  #czerwony dla usuwania

#===KALENDARZ===
try:
    from tkcalendar import Calendar
    TKCALENDAR_DOSTEPNY = True
except ImportError:
    TKCALENDAR_DOSTEPNY = False

#===KONFIGURACJA=== (ustawienia domyslne)
PLIK_DOMYSLNY_TXT = "baza_rezerwacji.txt"
PLIK_DOMYSLNY_JSON = "baza_rezerwacji.json"
LISTA_GABINETOW = ["Gabinet 1", "Gabinet 2", "Gabinet 3"] #na sztywno - daje kolejność na wykresie

#==================================================================
class AplikacjaPrzychodnia:
    def __init__(self, root):
        self.root = root #głowne okno
        self.root.title("System Rezerwacji - Dark Edition (Final)")
        self.root.geometry("1400x950")
        self.root.configure(bg=COL_BG) #ustawienie tła głównego okna
        
        self.konfiguruj_style() #funkcja stylizująca

        self.rezerwacje = [] #główna lista, która trzyma dane (rezerwacje)
        self.data_podgladu = datetime.date.today() #podgląd (deafultowo dzisiejszy)
        
        #===zmienne formularza===
        self.var_id = tk.IntVar(value=1)
        self.var_gabinet = tk.StringVar(value=LISTA_GABINETOW[0]) #deafultowo odnosi sie do pierwszego elementu listy - gabinet 1
        self.var_pracownik = tk.StringVar()
        self.var_data = tk.StringVar(value=str(datetime.date.today()))
        
        #===zmienne czasu===
        self.var_start_str = tk.StringVar(value="08:30") #przykładowe, startowe godziny
        self.var_koniec_str = tk.StringVar(value="09:45") #przykładowe, końcowe godziny
        
        #===zmienne wyszukiwania i usuwania===
        self.var_szukaj_pracownika = tk.StringVar()
        self.var_usun_id = tk.StringVar()
        
        self.var_data_podgladu_str = tk.StringVar(value=str(self.data_podgladu)) #wykres jest podglądem, można wpisywać rezerwacje na inna date niż jest wyświetlany wykres

        self.buduj_interfejs() #główna funkcja, ktora buduje wykres
        self.akcja_wczytaj_txt_silent() #automatyczne wczytanie danych na starcie programu (bez komunikatu o tym)

    def konfiguruj_style(self):
        style = ttk.Style()
        style.theme_use("clam") #wybraliśmy ten motyw bo dobrze pasuje i obsługuje zmiany kolorów
        
        #===konfiguracja tabeli (Treeview)=== (darkmode)
        style.configure("Treeview", 
                        background=COL_ENTRY, 
                        foreground=COL_FG, 
                        fieldbackground=COL_ENTRY,
                        font=("Segoe UI", 10))
        #nagłówki tabeli
        style.configure("Treeview.Heading", 
                        background=COL_PANEL, 
                        foreground=COL_FG, 
                        font=("Segoe UI", 10, "bold"))
        #kolor zaznaczenia
        style.map("Treeview", background=[("selected", COL_ACCENT)])

        #kofiguracja listy rozwijanej - wybor gabinetu
        style.configure("TCombobox", 
                        fieldbackground=COL_ENTRY, 
                        background=COL_BTN, 
                        foreground=COL_FG,
                        arrowcolor=COL_ACCENT)
        
        #ustawienie czarnego podświetlenia wyboru (selectbackground)
        style.map("TCombobox", 
                  fieldbackground=[("readonly", COL_ENTRY)],
                  selectbackground=[("readonly", "black")], 
                  selectforeground=[("readonly", COL_FG)])

    #===OBSŁUGA CZASU===
    def czas_na_float(self, godzina_str):
        #zmiana "8:30" na 8.5 aby łatwiej sie to rysowało
        try:
            h, m = map(int, godzina_str.split(':'))
            return h + m / 60.0
        except ValueError:
            return None

    def float_na_czas(self, godzina_float):
        #z powrotem zmiana z 8.5 na "8:30" - łatwiejsze do wyświetlania/odczytu
        h = int(godzina_float)
        m = int((godzina_float - h) * 60)
        return f"{h:02d}:{m:02d}"

    def buduj_interfejs(self):
        #===LEWY PANEL===
        panel_lewy = tk.Frame(self.root, width=400, bg=COL_PANEL)
        panel_lewy.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        def lbl(parent, text, color=COL_FG):
            tk.Label(parent, text=text, bg=COL_PANEL, fg=color, font=("Segoe UI", 10)).pack(anchor="w", pady=(5,0)) #anchor "W" - west(lewo); pad - margines
        
        def entry(parent, var, width=None):
            e = tk.Entry(parent, textvariable=var, bg=COL_ENTRY, fg=COL_FG, insertbackground="white", relief="flat", font=("Segoe UI", 10)) #relief - obramowanie widzetów
            if width: e.config(width=width)
            e.pack(fill="x", pady=2, ipady=3) #internalpady
            return e

        def btn(parent, text, cmd, bg=COL_BTN, fg=COL_FG):
            tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, relief="flat", 
                      activebackground=COL_ACCENT, activeforeground="white", cursor="hand2", font=("Segoe UI", 10, "bold")
                      ).pack(fill="x", pady=5, ipady=3)

        #===DODAWANIE REZERWACJI===
        tk.Label(panel_lewy, text="DODAJ REZERWACJĘ", font=("Segoe UI", 12, "bold"), bg=COL_PANEL, fg=COL_ACCENT).pack(pady=(10,5))
        
        #ID
        lbl(panel_lewy, "ID:")
        e_id = entry(panel_lewy, self.var_id)
        e_id.config(state="readonly", readonlybackground=COL_ENTRY, fg=COL_FG)
        
        #data
        lbl(panel_lewy, "Data (RRRR-MM-DD):")
        entry(panel_lewy, self.var_data)

        #gabinet
        lbl(panel_lewy, "Gabinet:")
        cb = ttk.Combobox(panel_lewy, textvariable=self.var_gabinet, values=LISTA_GABINETOW, state="readonly") #użytkownik musi wybrać gabinet z listy, zapobiega tworzeniu nowych gabinetów z poziomu aplikacji
        cb.pack(fill="x", pady=2)

        #pracownik     
        lbl(panel_lewy, "Pracownik:")
        entry(panel_lewy, self.var_pracownik)

        #godziny        
        frame_godz = tk.Frame(panel_lewy, bg=COL_PANEL)
        frame_godz.pack(fill="x", pady=5)

        #start rezerwacji        
        f_start = tk.Frame(frame_godz, bg=COL_PANEL)
        f_start.pack(side=tk.LEFT, fill="x", expand=True, padx=(0,5))
        lbl(f_start, "Od (HH:MM):")
        entry(f_start, self.var_start_str)

        #koniec rezerwacji
        f_koniec = tk.Frame(frame_godz, bg=COL_PANEL)
        f_koniec.pack(side=tk.RIGHT, fill="x", expand=True, padx=(5,0))
        lbl(f_koniec, "Do (HH:MM):")
        entry(f_koniec, self.var_koniec_str)

        #zatwierdzenie - przycisk
        btn(panel_lewy, "ZATWIERDŹ", self.akcja_dodaj, bg=COL_ACCENT, fg="white")

        #===USUWANIE REZERWACJI===
        tk.Frame(panel_lewy, height=1, bg="gray").pack(fill="x", pady=15)
        tk.Label(panel_lewy, text="USUWANIE", font=("Segoe UI", 12, "bold"), bg=COL_PANEL, fg=COL_BTN_RED).pack(pady=(5,5))
        
        #ID do usuniecia
        lbl(panel_lewy, "Podaj ID do usunięcia:")
        frame_del = tk.Frame(panel_lewy, bg=COL_PANEL)
        frame_del.pack(fill="x")
        
        e_del = tk.Entry(frame_del, textvariable=self.var_usun_id, bg=COL_ENTRY, fg=COL_FG, width=10, insertbackground="white", relief="flat")
        e_del.pack(side=tk.LEFT, fill="y", padx=(0, 5))
        
        #usunięcie - przycisk
        tk.Button(frame_del, text="USUŃ", command=self.akcja_usun_po_id, bg=COL_BTN_RED, fg="black", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, fill="x", expand=True)

        #czyszczenie całej bazy
        btn(panel_lewy, "WYCZYŚĆ CAŁĄ BAZĘ", self.akcja_wyczysc, bg=COL_BTN, fg=COL_BTN_RED)

        #===SZUKANIE===
        tk.Frame(panel_lewy, height=1, bg="gray").pack(fill="x", pady=15)
        lbl(panel_lewy, "Szukaj pracownika:")
        entry(panel_lewy, self.var_szukaj_pracownika)
        btn(panel_lewy, "POKAŻ RAPORT", self.akcja_szukaj)

        #===DZIAŁANIE NA PLIKACH===
        tk.Frame(panel_lewy, height=1, bg="gray").pack(fill="x", pady=15)
        
        frame_btns = tk.Frame(panel_lewy, bg=COL_PANEL)
        frame_btns.pack(fill="x")
        
        #przyciski do obdługi plików i bazy
        tk.Button(frame_btns, text="Zapisz TXT", command=self.akcja_zapisz_txt, bg=COL_BTN, fg=COL_FG).grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        tk.Button(frame_btns, text="Wczytaj TXT", command=self.akcja_wczytaj_txt, bg=COL_BTN, fg=COL_FG).grid(row=0, column=1, sticky="ew", padx=1, pady=1)
        tk.Button(frame_btns, text="Zapisz JSON", command=self.akcja_zapisz_json, bg=COL_BTN, fg=COL_FG).grid(row=1, column=0, sticky="ew", padx=1, pady=1)
        tk.Button(frame_btns, text="Wczytaj JSON", command=self.akcja_wczytaj_json, bg=COL_BTN, fg=COL_FG).grid(row=1, column=1, sticky="ew", padx=1, pady=1)
        tk.Button(frame_btns, text="Export Mongo", command=self.akcja_mongo_export, bg=COL_BTN, fg=COL_FG).grid(row=2, column=0, sticky="ew", padx=1, pady=1)
        tk.Button(frame_btns, text="Import Mongo", command=self.akcja_mongo_import, bg=COL_BTN, fg=COL_FG).grid(row=2, column=1, sticky="ew", padx=1, pady=1)
        frame_btns.columnconfigure(0, weight=1)
        frame_btns.columnconfigure(1, weight=1)

        #===PRAWY PANEL (WIZUALIZACJA)===
        panel_prawy = tk.Frame(self.root, bg=COL_BG)
        panel_prawy.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        #===NAWIGACJA (panel na górze)===
        panel_nav = tk.Frame(panel_prawy, bg=COL_PANEL, bd=0)
        panel_nav.pack(fill="x", pady=(0, 10), ipady=5)
        
        def nav_btn(text, cmd):
            tk.Button(panel_nav, text=text, command=cmd, bg=COL_BTN, fg=COL_FG, relief="flat", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)

        nav_btn("< Poprzedni", lambda: self.zmien_date(-1)) #poprzedni dzień
        
        #data podglądu
        self.entry_data_podgladu = tk.Entry(panel_nav, textvariable=self.var_data_podgladu_str, 
                                            bg=COL_ENTRY, fg=COL_FG, width=12, font=("Segoe UI", 11, "bold"), justify="center", insertbackground="white")
        self.entry_data_podgladu.pack(side=tk.LEFT, padx=5)
        
        nav_btn("Kalendarz", self.otworz_kalendarz)
        nav_btn("Odśwież", self.odswiez_wykres_z_pola)
        nav_btn("Następny >", lambda: self.zmien_date(1)) #następny dzien

        #===WYKRES===
        plt.style.use('dark_background')
        
        self.fig, self.ax = plt.subplots(figsize=(5, 4), dpi=100)
        self.fig.patch.set_facecolor(COL_BG)
        self.ax.set_facecolor(COL_PANEL)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=panel_prawy) #wyświetlanie matplotliba w tkinterze
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.get_tk_widget().configure(bg=COL_BG, highlightthickness=0)
        
        self.odswiez_wykres()

    #===SPRAWDZENIE POKRYWANIA SIĘ REZERWACJI===
    def sprawdz_konflikt(self, nowy_gabinet, nowa_data, start, koniec):
        for r in self.rezerwacje: #pętla po wszystkich istniejących rezerwacjach
            if r['gabinet'] == nowy_gabinet and r['data'] == nowa_data: #sprawdzamy tylko jeden gabinet w jednej dacie (z godziną)
                if max(start, r['godzina_rozp']) < min(koniec, r['godzina_zako']): #nakładanie się przedziałów czasowych
                    return True, r['pracownik'] #informacja o kolizji w harmonogramie + kto zajmuje
        return False, None

    def akcja_dodaj(self): #pobieranie danych z formularza + konwersja na liczby
        start_str = self.var_start_str.get()
        koniec_str = self.var_koniec_str.get()
        start = self.czas_na_float(start_str)
        koniec = self.czas_na_float(koniec_str)
        data_str = self.var_data.get()
        gabinet = self.var_gabinet.get()
        pracownik = self.var_pracownik.get()

        #===WALIDACJA DANYCH=== (zapezpieczenie)
        if start is None or koniec is None:
            messagebox.showerror("Błąd", "Niepoprawny format godziny! (HH:MM)")
            return
        try:
            datetime.datetime.strptime(data_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Błąd", "Niepoprawny format daty (RRRR-MM-DD).")
            return
        if not pracownik:
            messagebox.showwarning("Błąd", "Podaj nazwisko pracownika!")
            return
        if start < 7.0 or koniec > 20.0: #możlwiość rezerwacji tylko w godzinach pracy przychodni
            messagebox.showwarning("Błąd", "Przychodnia czynna 07:00 - 20:00.")
            return
        if koniec <= start:
            messagebox.showwarning("Błąd", "Godzina zakończenia musi być późniejsza.")
            return

        #sprawdzenie czy termin i gabinet jest wolny
        konflikt, kto = self.sprawdz_konflikt(gabinet, data_str, start, koniec)
        if konflikt:
            messagebox.showerror("Kolizja", f"Gabinet zajęty przez: {kto}")
            return

        #tworzenie słownika z danymi (rezerwacjami)
        rekord = {
            "id": self.var_id.get(),
            "gabinet": gabinet,
            "pracownik": pracownik,
            "data": data_str,
            "godzina_rozp": start, #jako float - 8.5 dla wygody
            "godzina_zako": koniec
        }
        
        self.rezerwacje.append(rekord) #dodanie do listy 
        self.var_id.set(self.var_id.get() + 1) #licznik ID
        
        if data_str != self.var_data_podgladu_str.get(): #przełączenie podglądu, gdy jest rozbieżność daty wpisywanej a wyświetlanej
            self.var_data_podgladu_str.set(data_str)
        
        self.odswiez_wykres()

    def akcja_usun_po_id(self):
        id_str = self.var_usun_id.get().strip()
        if not id_str.isdigit(): #walidacja wpisanego ID do usunięcia
            messagebox.showwarning("Błąd", "Podaj poprawny numer ID (liczba całkowita).")
            return

        id_to_del = int(id_str)
        
        znaleziono = False #szukanie podanego ID w danych
        for r in self.rezerwacje:
            if r['id'] == id_to_del:
                znaleziono = True
                break
        if not znaleziono:
            messagebox.showwarning("Błąd", f"Nie znaleziono rezerwacji o ID: {id_to_del}")
            return

        #tworzy nową listę, zachowując elementy, ktorych ID jest inne niż to, które podalismy do usuniecia
        if messagebox.askyesno("Potwierdzenie", f"Czy na pewno usunąć rezerwację ID {id_to_del}?"):
            self.rezerwacje = [r for r in self.rezerwacje if r['id'] != id_to_del]
            self.var_usun_id.set("")
            self.odswiez_wykres()
            messagebox.showinfo("Sukces", "Rezerwacja usunięta.")

    #wyszukiwanie raportów po danych pracownika
    def akcja_szukaj(self): #nieistotne czy mała czy wielka litera
        fraza = self.var_szukaj_pracownika.get().lower()
        wyniki = [r for r in self.rezerwacje if fraza in r['pracownik'].lower()]
        
        if not wyniki:
            messagebox.showinfo("Info", "Brak wyników.")
            return

        #konfiguracja okna raportu
        okno = tk.Toplevel(self.root)
        okno.title(f"Raport: {fraza}")
        okno.geometry("850x500")
        okno.configure(bg=COL_BG)

        cols = ("ID", "Data", "Gabinet", "Godziny", "Czas")
        tree = ttk.Treeview(okno, columns=cols, show="tree headings")
        
        tree.heading("#0", text="Pracownik")
        tree.heading("ID", text="ID")
        tree.column("ID", width=50, anchor="center")
        for c in cols[1:]: tree.heading(c, text=c)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        pracownicy_mapa = {} #grupowanie danych dla poszczególnego pracownika
        for r in wyniki:
            osoba = r['pracownik']
            if osoba not in pracownicy_mapa: pracownicy_mapa[osoba] = []
            pracownicy_mapa[osoba].append(r)

        for osoba, lista in pracownicy_mapa.items():
            suma = sum((r['godzina_zako'] - r['godzina_rozp']) for r in lista)
            h_sum = int(suma)
            m_sum = int((suma - h_sum) * 60)
            
            parent = tree.insert("", "end", text=f"{osoba} (Suma: {h_sum}h {m_sum}m)", open=True) #stworzenie 'rodzica' - wiersz głowny - suma godzin rezerwacji
            
            for r in lista: #szczegółowe informacje o poszczególnych rezerwacjach - 'dzieci' 
                start_s = self.float_na_czas(r['godzina_rozp'])
                koniec_s = self.float_na_czas(r['godzina_zako'])
                
                czas_float = r['godzina_zako'] - r['godzina_rozp']
                h_dur = int(czas_float)
                m_dur = int((czas_float - h_dur)*60)

                tree.insert(parent, "end", values=(
                    r['id'],
                    r['data'],
                    r['gabinet'],
                    f"{start_s} - {koniec_s}",
                    f"{h_dur}h {m_dur}m"
                ))

    #===WIZUALIZACJA=== (prawy panel)
    def odswiez_wykres(self):
        self.ax.clear() #czyszcenie wykresu przed narysowaniem nowego
        
        wybrana_data = self.var_data_podgladu_str.get() #pobiera date
        
        #tytuły
        self.ax.set_title(f"Grafik: {wybrana_data}", fontsize=14, color=COL_ACCENT, pad=15)
        self.ax.set_ylabel("Godzina", fontsize=11, color=COL_FG)
        self.ax.set_xlabel("Gabinet", fontsize=11, color=COL_FG)
        
        self.ax.set_ylim(20, 7) #oś Y - odwrócenie, aby 7:00 była na górze wykresu
        self.ax.set_yticks(range(7, 21)) #podział co godzine
        
        def format_godzin(x, pos): #zmiana formatu z 8 na 8:00
            return f"{int(x)}:00"
        self.ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_godzin))
        
        #wykres
        self.ax.grid(True, axis='y', linestyle='--', alpha=0.3, color="gray")
        self.ax.tick_params(colors=COL_FG, labelsize=10)
        for spine in self.ax.spines.values():
            spine.set_edgecolor(COL_FG)

        #wymuszenie na osi X - niewidzialne alpha=0, słupki dla kazdego gabinetu. Stąd wiadoma jest kolejność gabinetów -> 1, 2, 3 (nawet jeśli których jest pusty w danym dniu)
        self.ax.bar(LISTA_GABINETOW, [0,0,0], bottom=7, alpha=0)

        dane_dnia = [r for r in self.rezerwacje if r.get('data') == wybrana_data] #dane tylko dla wybranego dnia

        for r in dane_dnia:
            if r['gabinet'] in LISTA_GABINETOW: #obliczenia do rysowania paska (zajęcia gabinetu)
                start, koniec = r['godzina_rozp'], r['godzina_zako']
                dlugosc = koniec - start #wysokośc słupka
                
                start_s = self.float_na_czas(start)
                koniec_s = self.float_na_czas(koniec)
                
                #obliczanie czasu i dodanie do etykiety
                h_dur = int(dlugosc)
                m_dur = int((dlugosc - h_dur) * 60)
                czas_str = f"({h_dur}h {m_dur}m)"

                #etykieta wewnątrz slupka
                label = f"{r['pracownik']} (ID: {r['id']})\n{start_s}-{koniec_s}\n{czas_str}"
                
                #kolory gabinetów
                kolor = COL_ACCENT
                if r['gabinet'] == "Gabinet 2": kolor = "#CF6679"
                if r['gabinet'] == "Gabinet 3": kolor = "#FFB74D"

                #rysowanie odpowiedniego słupka (bar) ---> x=gabinet, height=długość, bottom=punkt startu (godzina rozpoczecia)
                p = self.ax.bar(r['gabinet'], dlugosc, bottom=start, width=0.5, 
                                color=kolor, edgecolor='white', linewidth=0.5, alpha=0.9,
                                capstyle='round') #końce zaokrąglone
                
                #tekst na słupku
                self.ax.bar_label(p, labels=[label], label_type='center', color='black', fontsize=8, fontweight='bold')

        self.canvas.draw() #finalne wyświetlenie zmian na ekranie

    #===PLIKI===
    def aktualizuj_id(self): #aktualizuje ID po kazdym wpisie
        if self.rezerwacje: self.var_id.set(max(r['id'] for r in self.rezerwacje) + 1)

    def akcja_wyczysc(self): #usuwanie danych - czyszczenie listy rezerwacji
        if messagebox.askyesno("Potwierdź", "Usunąć wszystkie dane z pamięci?"):
            self.rezerwacje = []
            self.odswiez_wykres()

    def akcja_zapisz_txt(self): #zapisuje rezerwacje do txt
        io_txt.zapisz_txt(PLIK_DOMYSLNY_TXT, self.rezerwacje)
        messagebox.showinfo("Sukces", "Zapisano TXT.")

    def akcja_wczytaj_txt(self): #wczytuje rezerwacje z txt
        d = io_txt.wczytaj_txt(PLIK_DOMYSLNY_TXT)
        if d: 
            self.rezerwacje = d; self.aktualizuj_id(); self.odswiez_wykres()
            messagebox.showinfo("Sukces", "Wczytano TXT.")
            
    def akcja_wczytaj_txt_silent(self): #początkowe wczytanie danych na wykres
        d = io_txt.wczytaj_txt(PLIK_DOMYSLNY_TXT)
        if d: self.rezerwacje = d; self.aktualizuj_id(); self.odswiez_wykres()

    def akcja_zapisz_json(self): #zapisuje rezerwacje do JSON
        io_json.zapisz_json(PLIK_DOMYSLNY_JSON, self.rezerwacje)
        messagebox.showinfo("Sukces", "Zapisano JSON.")

    def akcja_wczytaj_json(self): #wczytuje rezerwacje z JSON
        d = io_json.wczytaj_json(PLIK_DOMYSLNY_JSON)
        if d: 
            self.rezerwacje = d; self.aktualizuj_id(); self.odswiez_wykres()
            messagebox.showinfo("Sukces", "Wczytano JSON.")

    def akcja_mongo_export(self): #eksport do Mongo
        mongo_utils.eksport_do_mongo(self.rezerwacje)
        messagebox.showinfo("Mongo", "Wysłano dane.")

    def akcja_mongo_import(self): #import z Mongo
        d = mongo_utils.import_z_mongo()
        if d: 
            self.rezerwacje = d; self.aktualizuj_id(); self.odswiez_wykres()
            messagebox.showinfo("Mongo", "Pobrano dane.")

    def otworz_kalendarz(self): #kalendarz do wyboru wyświetlanego dnia na wykresie
        if not TKCALENDAR_DOSTEPNY:
            messagebox.showwarning("Brak", "Zainstaluj: pip install tkcalendar")
            return
        top = tk.Toplevel(self.root)
        top.configure(bg=COL_BG)
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd', 
                       background=COL_BG, foreground=COL_FG, headersbackground=COL_PANEL, headersforeground=COL_FG)
        cal.pack(pady=20, padx=20)
        def wybierz():
            self.var_data_podgladu_str.set(cal.get_date())
            self.odswiez_wykres()
            top.destroy()
        tk.Button(top, text="WYBIERZ", command=wybierz, bg=COL_ACCENT, fg="white").pack(pady=10)

    def zmien_date(self, d): #zmiana daty na górnym pasku do wyswietlania wykresu
        try:
            cur = datetime.datetime.strptime(self.var_data_podgladu_str.get(), "%Y-%m-%d").date()
            self.var_data_podgladu_str.set(str(cur + datetime.timedelta(days=d)))
            self.odswiez_wykres()
        except: pass

    def odswiez_wykres_z_pola(self): self.odswiez_wykres()

if __name__ == "__main__":
    root = tk.Tk()
    app = AplikacjaPrzychodnia(root)
    root.mainloop()