import time
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from io import StringIO
import datetime
import streamlit as st  

BASE_URL = "https://www.slickcharts.com/sp500"

def percentage_to_float(perc):
    if isinstance(perc, str):
        if '%' in perc:
            perc = perc.replace('%', '').replace(',', '.')
            perc = float(perc) / 100
            return perc
        else:
            perc = perc.replace(',', '.')
            try:
                return float(perc)
            except:
                return None
    return perc


def scrape_series_data(verbose=False):

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; WOW64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/109.0.0.0 Safari/537.36'
        )
    }

    indice_page_request = requests.get(BASE_URL, headers=headers)

    if indice_page_request.status_code != 200:
        raise ValueError(f"Error {indice_page_request.status_code} al cargar la página.")

    indice_page_web = BeautifulSoup(indice_page_request.content, 'html.parser')

    table = indice_page_web.select_one("table.table.table-hover.table-borderless.table-sm")

    if table is None:
        raise ValueError("No se encontró ninguna tabla en la página.")

    sp500 = pd.read_html(StringIO(str(table)), decimal=',', thousands='.')[0]

    if verbose:
        print("Tabla descargada con forma:", sp500.shape)

    sp500.columns = ['Rank', 'Company', 'Symbol', 'Weight', 'Price', 'Chg', '% Chg']
    sp500['Weight'] = sp500['Weight'].apply(percentage_to_float)
    sp500['% Chg String'] = ( sp500['% Chg']
    .str.replace('(', '', regex=False)
    .str.replace(')', '', regex=False)
)
    sp500['% Chg Float'] = ( sp500['% Chg String']
    .apply(percentage_to_float)
)
    return sp500

@st.cache_data
def load_data(
    ticker: str,
    start: str = "2020-01-01",
    end: str | None = None,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Descarga datos de un ticker concreto y los cachea por (ticker, start, end, interval).
    """
    if end is None:
        end = datetime.datetime.now().strftime("%Y-%m-%d")

    data = yf.download(
        ticker,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=True, 
    )

    if data.empty:
        return pd.DataFrame(
            columns=["Open", "High", "Low", "Close", "Volume"],
            index=pd.DatetimeIndex([], name="Date"),
        )

    data.reset_index(inplace=True)
    data.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
    data["Date"] = pd.to_datetime(data["Date"])
    data.set_index("Date", inplace=True)

    return data
if __name__ == "__main__":
    df_sp500 = scrape_series_data(verbose=True)
    print(df_sp500.head())