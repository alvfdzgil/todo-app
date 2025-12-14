import time
import pandas as pd

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

BASE_URL = "https://es.marketscreener.com/cotizacion/indice/S-P-500-4985/componentes/"

def get_indice_page_url(page):
    return f"{BASE_URL}?p={page}"

def capitalizacion_to_float(cap):
    if not isinstance(cap, str):
        return None

    cap = cap.strip()

    if cap in ("", "-", "—"):
        return None

    cap = cap.replace('.', '').replace(',', '.')

    if 'mil' in cap and 'M' in cap:
        cap = cap.replace('mil', '').replace('M', '').strip()
        try:
            return float(cap) * 1e9
        except:
            return None
        
    if 'M' in cap:
        cap = cap.replace('M', '').strip()
        try:
            return float(cap) * 1e6
        except:
            return None

    try:
        return float(cap)
    except:
        return None

        
def percentage_to_float(perc):
    if isinstance(perc, str):
        if '%' in perc:
            perc = perc.replace('%', '').replace(',', '.')
            perc = float(perc)/100
            return perc
        else:
            perc = perc.replace(',', '.')
            try:
                return float(perc)
            except:
                return None

def scrape_series_data(verbose=False):
    sp500 = []
    page = 1

    while True:
        if verbose:
            print(f'Descargando página {page}')

        indice_page_url = get_indice_page_url(page)

        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; WOW64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/109.0.0.0 Safari/537.36'
            )
        }
        indice_page_request = requests.get(indice_page_url, headers=headers)

        if indice_page_request.status_code != 200:
            print(indice_page_request.status_code)
            print(f'Error descargando página {page}')
            break

        indice_page_web = BeautifulSoup(indice_page_request.content, 'html.parser')

        tables = indice_page_web.select("table#stocks_table")

        if not tables:
            raise ValueError("No se encontró ninguna tabla en la página. Puede que el sitio bloquee el scraping.")

        df = pd.read_html(str(tables[0]), decimal=',', thousands='.')[0]
        sp500.append(df)
        next_page_button = indice_page_web.select_one('a.link.px-5.mx-5.link--blue[title="Siguiente"]')
        

        if not next_page_button:
            if verbose:
                print("No hay más páginas.")
            break
        break 
        page += 1
        time.sleep(1)

    return pd.concat(sp500, ignore_index=True)

def load_sp500():
    sp500 = scrape_series_data(verbose=True)
    sp500 = sp500.iloc[:, 1:]
    sp500.columns = ['activo','Capi. USD', 'Variación', 'Varia. 5d.', 'Varia. 1 de ene.']
    sp500 = sp500.dropna(how='all')
    print(sp500)
    print(f'Total activos S&P 500: {len(sp500)}')
    sp500['Capi. USD'] = sp500['Capi. USD'].apply(capitalizacion_to_float)
    sp500['Variación'] = sp500['Variación'].apply(percentage_to_float)
    sp500['Varia. 5d.'] = sp500['Varia. 5d.'].apply(percentage_to_float)
    sp500['Varia. 1 de ene.'] = sp500['Varia. 1 de ene.'].apply(percentage_to_float)
    return sp500