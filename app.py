import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ----------------------------------------------------
# FUNKČNÍ ONEDRIVE DOWNLOAD LINK
# ----------------------------------------------------
URL = "https://onedrive.live.com/download?resid=%7BAC5E81DD-F4E9-4E13-BC66-247A825632AA%7D&file=Objednavky_New.xlsx"

# ----------------------------------------------------
# 1) Stáhnout Excel přes requests (funguje vždy)
# ----------------------------------------------------
@st.cache_data(ttl=60)
def load_data():
    r = requests.get(URL)
    r.raise_for_status()
    file_bytes = BytesIO(r.content)
    df = pd.read_excel(file_bytes, engine="openpyxl")
    return df

df = load_data()

st.title("🚗 Letištní rozvozy – GUI aplikace")

# ----------------------------------------------------
# 2) Filtrování podle data
# ----------------------------------------------------
df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")

available_dates = sorted(df["Datum"].dropna().unique())
selected_date = st.sidebar.date_input("Vyber datum", available_dates[0])

filtered = df[df["Datum"] == pd.to_datetime(selected_date)]

st.subheader(f"Záznamy pro datum: {selected_date.strftime('%d.%m.%Y')}")

# ----------------------------------------------------
# 3) Transformace dat
# ----------------------------------------------------
output = pd.DataFrame()

output["Jméno"] = filtered["Jméno"]
output["Počet osob"] = filtered["Počet osob"]
output["Datum"] = filtered["Datum"].dt.strftime("%d.%m.%Y")
output["Příjezd"] = filtered["Příjezd"]
output["Přílet"] = filtered["Přílet"]
output["Číslo letu"] = filtered["Číslo letu"]
output["SPZ"] = filtered["SPZ"]

output["Klíče"] = filtered["SPZ"].apply(
    lambda x: "✖" if isinstance(x, str) and x.startswith("*") else ""
)

output["Poznámka"] = (
    filtered["Poznámka 1"].fillna("") + " " + filtered["Poznámka 2"].fillna("")
).str.strip()

output["Vyřízeno"] = False

# ----------------------------------------------------
# 4) Tabulka
# ----------------------------------------------------
edited = st.data_editor(
    output,
    column_config={
        "Vyřízeno": st.column_config.CheckboxColumn("Vyřízeno"),
    },
    hide_index=True
)

st.success("Data načtena z OneDrivu a připravena.")
