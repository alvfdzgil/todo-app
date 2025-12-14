import requests
import pandas as pd

API_KEY = "8108e4a380004143a6fa7f836a20b927"

BASE = "https://api.profit.com/data-api/reference/stocks"

def get_page(skip, limit=1000):
    r = requests.get(BASE, params={"token": API_KEY, "skip": skip, "limit": limit}, timeout=60)
    print("HTTP", r.status_code, "skip", skip)
    r.raise_for_status()
    data = r.json()
    return data.get("data", data) 

rows = []
skip = 0
limit = 1000

while True:
    page = get_page(skip, limit)
    if not page:
        break
    rows.extend(page)
    skip += len(page)

df = pd.DataFrame(rows)

name_col = next((c for c in ["name", "companyName", "securityName"] if c in df.columns), None)
sym_col  = next((c for c in ["symbol", "ticker", "code"] if c in df.columns), None)

print("Columnas:", df.columns.tolist())

if not name_col or not sym_col:

    print("Ejemplo fila:", rows[0])
    raise SystemExit("No encuentro columnas de nombre/símbolo.")

df2 = df[[name_col, sym_col]].rename(columns={name_col:"name", sym_col:"symbol"})
df2.to_csv("tickers_us_stocks.csv", index=False, encoding="utf-8")
print("OK -> tickers_us_stocks.csv", len(df2))
