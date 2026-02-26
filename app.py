import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import calendar
import csv
from io import StringIO

st.set_page_config(page_title="BRQ – Přílety a odlety", layout="wide")

# ----------------------------------------------------
# SCRAPING – načtení letů pro jeden den
# ----------------------------------------------------
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

        results.append((date, typ, flight_code, destination, time, note, company))

    return results


# ----------------------------------------------------
# CACHE – aby se data nestahovala pořád dokola
# ----------------------------------------------------
@st.cache_data(ttl=300)
def load_flights(dates_to_load):
    all_flights = []
    for d in dates_to_load:
        all_flights.extend(load_flights_for_date(d))
    return all_flights


# ----------------------------------------------------
# UI – Sidebar
# ----------------------------------------------------
st.sidebar.header("Filtry")

mode = st.sidebar.radio("Režim načítání", ["Konkrétní datum", "Celý měsíc"])

if mode == "Konkrétní datum":
    selected_date = st.sidebar.date_input("Vyber datum")
    dates_to_load = [selected_date.strftime("%Y-%m-%d")]
else:
    year = st.sidebar.selectbox("Rok", list(range(2020, 2035)), index=6)
    months = {
        1: "Leden", 2: "Únor", 3: "Březen", 4: "Duben",
        5: "Květen", 6: "Červen", 7: "Červenec", 8: "Srpen",
        9: "Září", 10: "Říjen", 11: "Listopad", 12: "Prosinec"
    }
    month_name = st.sidebar.selectbox("Měsíc", list(months.values()))
    month_number = list(months.keys())[list(months.values()).index(month_name)]

    days = calendar.monthrange(year, month_number)[1]
    dates_to_load = [
        f"{year}-{month_number:02d}-{day:02d}"
        for day in range(1, days + 1)
    ]

filter_type = st.sidebar.selectbox("Typ letu", ["Vše", "Přílety", "Odlety"])
search_text = st.sidebar.text_input("Hledat číslo letu")

# ----------------------------------------------------
# Načtení dat
# ----------------------------------------------------
with st.spinner("Načítám data z letiště…"):
    flights = load_flights(dates_to_load)

df = pd.DataFrame(flights, columns=["Datum", "Typ", "Let", "Letiště", "Čas", "Poznámka", "Aerolinka"])

# ----------------------------------------------------
# Filtry
# ----------------------------------------------------
if filter_type != "Vše":
    df = df[df["Typ"] == ("PŘÍLET" if filter_type == "Přílety" else "ODLET")]

if search_text.strip():
    df = df[df["Let"].str.contains(search_text.strip(), case=False)]

# ----------------------------------------------------
# Seřazení podle data + času
# ----------------------------------------------------
df["Datetime"] = pd.to_datetime(df["Datum"] + " " + df["Čas"], errors="coerce")
df = df.sort_values("Datetime").drop(columns=["Datetime"])

# ----------------------------------------------------
# Výstup
# ----------------------------------------------------
st.title("✈️ BRQ – Přílety a odlety")
st.write(f"**Nalezeno {len(df)} letů**")

# ❗️ Odstranění prvního prázdného sloupce (index)
df_display = df.reset_index(drop=True)

st.dataframe(df_display, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# Export CSV
# ----------------------------------------------------
csv_buffer = StringIO()
df_display.to_csv(csv_buffer, sep=";", index=False, encoding="cp1250")

st.download_button(
    label="📥 Stáhnout CSV",
    data=csv_buffer.getvalue(),
    file_name="brno_flights_export.csv",
    mime="text/csv"
)
