import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from datetime import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import csv


# ============================================================
#   LOAD FLIGHTS FOR ONE DAY
# ============================================================

def load_flights_for_date(date):
    headers = {"User-Agent": "Mozilla/5.0"}

    session = requests.Session()
    session.get("https://www.brno-airport.cz/vyhledavani-letu", headers=headers)

    url = (
        "https://www.brno-airport.cz/vyhledavani-letu"
        "?customContentRenderer-flights-0-tab=search"
        "&destination=0"
        f"&date={date}"
        "&line="
        "&arrivals=on"
        "&departures=on"
        "&do=customContentRenderer-flights-0-searchParametersForm-form-submit"
    )

    response = session.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "lxml")

    table_html = soup.find("table", class_="flight-table__table")
    if not table_html:
        return []

    rows = table_html.find("tbody").find_all("tr")
    results = []

    for r in rows:
        cols = r.find_all("td")

        time = cols[0].get_text(strip=True)
        company = cols[2].get_text(strip=True)
        destination = cols[3].find("span", class_="flight-table__destination-text").get_text(strip=True)
        flight_code = cols[4].get_text(strip=True)
        note = cols[5].get_text(" ", strip=True)

        icon = cols[3].find("img")["src"]
        typ = "PŘÍLET" if "arrival" in icon else "ODLET"

        # ⭐ Přidáme datum jako první položku
        results.append((date, typ, flight_code, destination, time, note, company))

    return results


# ============================================================
#   LOAD FLIGHTS (DATE OR MONTH)
# ============================================================

def load_flights():
    # 1) Pokud je vyplněné datum → načteme jen jeden den
    if date_var.get().strip():
        dates_to_load = [date_var.get().strip()]
        status_label.config(text=f"Načítám lety pro {dates_to_load[0]}…")

    else:
        # 2) Jinak načteme celý měsíc
        month_name = month_var.get()
        year = year_var.get()

        month_number = list(months.keys())[list(months.values()).index(month_name)]
        days_in_month = calendar.monthrange(year, month_number)[1]

        dates_to_load = [
            f"{year}-{month_number:02d}-{day:02d}"
            for day in range(1, days_in_month + 1)
        ]

        status_label.config(text=f"Načítám celý měsíc {month_name} {year}…")

    root.update_idletasks()

    # 3) Načteme všechny dny
    all_flights = []
    for d in dates_to_load:
        all_flights.extend(load_flights_for_date(d))

    # 4) Filtr přílety/odlety
    selected_filter = filter_var.get()
    if selected_filter != "Vše":
        all_flights = [
            f for f in all_flights
            if (selected_filter == "Přílety" and f[1] == "PŘÍLET") or
               (selected_filter == "Odlety" and f[1] == "ODLET")
        ]

    # 5) Filtr podle čísla letu
    search_text = search_var.get().strip().lower()
    if search_text:
        all_flights = [f for f in all_flights if search_text in f[2].lower()]

    # ⭐ 6) Seřadíme podle data + času
    def parse_datetime(date_str, time_str):
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except:
            return datetime.max

    all_flights.sort(key=lambda x: parse_datetime(x[0], x[4]))

    # 7) Zobrazíme v tabulce
    for row in table.get_children():
        table.delete(row)

    for f in all_flights:
        table.insert("", "end", values=f)

    status_label.config(text=f"Načteno {len(all_flights)} letů")


# ============================================================
#   EXPORT TO CSV (CP1250 – správná čeština v Excelu)
# ============================================================

def export_csv():
    rows = table.get_children()
    if not rows:
        status_label.config(text="Není co exportovat")
        return

    filename = "brno_flights_export.csv"

    with open(filename, "w", newline="", encoding="cp1250", errors="replace") as f:
        writer = csv.writer(f, delimiter=";")

        # hlavička
        writer.writerow(columns)

        # data
        for row in rows:
            writer.writerow(table.item(row)["values"])

    status_label.config(text=f"Exportováno do {filename}")


# ============================================================
#   GUI
# ============================================================

root = tk.Tk()
root.title("BRQ – Přílety a odlety podle data (Letiště Brno)")

style = ttk.Style()
style.theme_use("clam")  # macOS fix

frame = tk.Frame(root)
frame.pack(padx=20, pady=20)

# --- Datum přes DateEntry ---
date_var = tk.StringVar()

tk.Label(frame, text="Vyber datum:", font=("Arial", 14)).grid(row=0, column=0, sticky="w")

date_entry = DateEntry(
    frame,
    textvariable=date_var,
    date_pattern="yyyy-MM-dd",
    locale="cs_CZ",
    width=12,
    font=("Arial", 14),
    background="white",
    foreground="black",
    borderwidth=2
)
date_entry.grid(row=0, column=1, padx=10)

# --- Výběr měsíce ---
months = {
    1: "Leden", 2: "Únor", 3: "Březen", 4: "Duben",
    5: "Květen", 6: "Červen", 7: "Červenec", 8: "Srpen",
    9: "Září", 10: "Říjen", 11: "Listopad", 12: "Prosinec"
}

month_var = tk.StringVar(value=months[datetime.today().month])
year_var = tk.IntVar(value=datetime.today().year)

tk.Label(frame, text="Nebo celý měsíc:", font=("Arial", 14)).grid(row=1, column=0, sticky="w")

ttk.Combobox(frame, textvariable=month_var, values=list(months.values()),
             state="readonly", font=("Arial", 14), width=12).grid(row=1, column=1, padx=10)

ttk.Combobox(frame, textvariable=year_var, values=list(range(2020, 2035)),
             state="readonly", font=("Arial", 14), width=6).grid(row=1, column=2, padx=10)

# --- Filtry ---
filter_var = tk.StringVar(value="Vše")
ttk.Combobox(frame, textvariable=filter_var,
             values=["Vše", "Přílety", "Odlety"],
             state="readonly", font=("Arial", 14), width=10).grid(row=0, column=3, padx=10)

# --- Vyhledávání ---
tk.Label(frame, text="Hledat let:", font=("Arial", 14)).grid(row=2, column=0, sticky="w", pady=10)

search_var = tk.StringVar()
tk.Entry(frame, textvariable=search_var, font=("Arial", 14), width=15).grid(row=2, column=1, sticky="w")

tk.Button(frame, text="Filtrovat", font=("Arial", 14), command=load_flights).grid(row=2, column=2, padx=10)

# --- Načíst lety ---
tk.Button(frame, text="Načíst lety", font=("Arial", 14), command=load_flights).grid(row=0, column=4, padx=10)

# --- Export ---
tk.Button(frame, text="Export CSV", font=("Arial", 14), command=export_csv).grid(row=1, column=4, padx=10)

# --- Status ---
status_label = tk.Label(frame, text="", font=("Arial", 13))
status_label.grid(row=3, column=0, columnspan=5, pady=10)

# --- Tabulka ---
columns = ("Datum", "Typ", "Let", "Letiště", "Čas", "Poznámka", "Aerolinka")

table = ttk.Treeview(root, columns=columns, show="headings", height=20)

for col in columns:
    table.heading(col, text=col)
    table.column(col, width=150)

table.column("Datum", width=120)

table.pack(padx=20, pady=10)

table.tag_configure("departure", background="#d4f8d4")
table.tag_configure("arrival", background="#ffd6d6")

root.mainloop()

