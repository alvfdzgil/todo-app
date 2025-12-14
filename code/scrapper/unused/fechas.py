import requests
from bs4 import BeautifulSoup

def get_indice_page_url(symbol):
    return f"https://es.finance.yahoo.com/quote/{symbol}/options/"

def obtener_fechas_vencimiento(symbol, verbose=False):
    url_expansion = get_indice_page_url(symbol)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url_expansion, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        if verbose:
            print("Error de conexión:", e)
        return []      

    if resp.status_code != 200:
        if verbose:
            print("Error HTTP:", resp.status_code)
            print("Contenido inicial de la respuesta:")
            print(resp.text[:300])
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')

    if verbose:
        print("HTML general de la página:")
        print(soup.prettify()[:2000])

    valores = []

    for nodo in soup.select('div.itm[role="option"][data-value]'):
        valores.append(nodo.get("data-value"))

    return valores

if __name__ == "__main__":
    print(obtener_fechas_vencimiento("NVDA", verbose=True))
