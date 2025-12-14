import numpy as np
import pandas as pd
import re
import requests

from bs4 import BeautifulSoup
from datetime import datetime
from io import StringIO

def process_percentage(value):
    if pd.isna(value):
        return value
    str_value = str(value).replace('%', '').replace(',', '.')
    try:
        return float(str_value) / 100
    except ValueError:
        return np.nan


def process_timestamp(value):
    timestamp_format = '%d/%m/%Y %H:%M:%S'
    if pd.isnull(value):
        element = np.nan
    elif re.search(r'^[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}$', value) is not None:
        value = value + ' 23:59:59'
        element = datetime.strptime(value, timestamp_format)
    elif re.search(r'^[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}$', value) is not None:
        value = datetime.now().strftime('%d/%m/%Y') + ' ' + value
        element = datetime.strptime(value, timestamp_format)
    else:
        element = datetime.now()
    return element

def get_indice_page_url(symbol,timestamp=None):
    return f"https://es.finance.yahoo.com/quote/{symbol}/options/?date={timestamp}"

def scrape_options_data(symbol, timestamp, verbose=False):
    url_expansion = get_indice_page_url(symbol, timestamp)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        expansion_request = requests.get(url_expansion, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        if verbose:
            print("Error de conexión:", e)
        return None, None

    if expansion_request.status_code != 200:
        if verbose:
            print("Error HTTP:", expansion_request.status_code)
            print("Contenido inicial de la respuesta:")
            print(expansion_request.text[:300])
        return None, None

    expansion_web = BeautifulSoup(expansion_request.text, 'html.parser')

    if verbose:
        print("HTML general de la página:")
        print(expansion_web.prettify()[:2000])

    tables = expansion_web.select('div.tableContainer')

    if not tables:
        if verbose:
            print("No se encontró ninguna tabla de opciones para", symbol)
        return None, None

    try:
        options_compra = pd.read_html(
            StringIO(str(tables[0])),
            header=0,
            encoding="utf-8"
        )[0]
    except Exception as e:
        if verbose:
            print("Error leyendo tabla de CALLS:", e)
        options_compra = None

    options_venta = None
    if len(tables) > 1:
        try:
            options_venta = pd.read_html(
                StringIO(str(tables[1])),
                header=0,
                encoding="utf-8"
            )[0]
        except Exception as e:
            if verbose:
                print("Error leyendo tabla de PUTS:", e)
            options_venta = None

    if verbose and options_compra is not None:
        print("CALLS:")
        print(options_compra.head())
    if verbose and options_venta is not None:
        print("PUTS:")
        print(options_venta.head())
    
    options_compra['Cambio de %'] = options_compra['Cambio de %'].apply(process_percentage)
    options_venta['Cambio de %'] = options_venta['Cambio de %'].apply(process_percentage)
    options_compra['Volatilidad implícita'] = options_compra['Volatilidad implícita'].apply(process_percentage)
    options_venta['Volatilidad implícita'] = options_venta['Volatilidad implícita'].apply(process_percentage)
    #options_compra['Fecha de última transacción (GMT-5)'] = options_compra['Fecha de última transacción (GMT-5)'].apply(process_timestamp).str.split('.').str[0]
    #options_venta['Fecha de última transacción (GMT-5)'] = options_venta['Fecha de última transacción (GMT-5)'].apply(process_timestamp).str.split('.').str[0]


    return options_compra, options_venta

"""Ejemplo de uso:
Descarga todas las opciones CALL y PUT para un símbolo dado (AAPL)"""
"""
if __name__ == "__main__":
    symbol = "AAPL"  
    max_intentos = 10
    calls = {"AAPL": {}}
    puts = {"AAPL": {}}
    for item in fechas_unix(symbol):
        for intento in range(max_intentos):
            options_compra, options_venta = scrape_options_data(symbol, item["timestamp"], verbose=False)
            time.sleep(5)  
            if options_compra is not None:
                calls["AAPL"][item["date"]] = options_compra
                #options_compra.to_csv(f'../data/options_compra_{item["date"]}.csv', index=False)
                #options_compra.to_json(f'../data/options_compra_{item["date"]}.json',orient='records',indent=4,force_ascii=False)
                print(f"Guardados CALLS en options_compra_{item['date']}.csv / .json")
            else:
                print("No se pudieron descargar las opciones CALLS para", symbol)

            if options_venta is not None:
                puts["AAPL"][item["date"]] = options_venta
                #options_venta.to_csv(f'../data/options_venta_{item["date"]}.csv', index=False)
                #options_venta.to_json(f'../data/options_venta_{item["date"]}.json',orient='records',indent=4,force_ascii=False)
                print(f"Guardados PUTS en options_venta_{item['date']}.csv / .json")
                break  # salir del bucle de reintentos si tuvo éxito
            else:
                print("No se pudieron descargar las opciones PUTS para", symbol)
"""
