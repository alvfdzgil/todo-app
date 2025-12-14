import requests

def obtener_ticker(nombre: str):
    url = "https://query1.finance.yahoo.com/v1/finance/search"
    params = {"q": nombre}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    resp = requests.get(url, params=params, headers=headers, timeout=10)

    if resp.status_code != 200:
        print("Error HTTP:", resp.status_code)
        print("Contenido inicial de la respuesta:")
        print(resp.text[:300])
        return None

    try:
        data = resp.json()
    except ValueError:
        print("La respuesta no es JSON. Contenido inicial:")
        print(resp.text[:300])
        return None

    quotes = data.get("quotes", [])
    if not quotes:
        print("No se han encontrado resultados para:", nombre)
        return None

    symbol = quotes[0].get("symbol")

    return symbol

if __name__ == "__main__":
    print("Ticker NVIDIA:", obtener_ticker("NVIDIA CORPORATION"))
