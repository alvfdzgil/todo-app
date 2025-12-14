import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from scrapper.sp500 import scrape_series_data

st.set_page_config(layout="wide")

data = [
    # 🇺🇸 USA - Índices y volatilidad
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "Índice",        "Nombre": "S&P 500",                         "Ticker": "^GSPC",     "Opciones": "SPX",                 "Comentario": "Usar SPX o SPY para opciones"},
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "ETF índice",   "Nombre": "SPDR S&P 500",                    "Ticker": "SPY",       "Opciones": "SPY",                 "Comentario": "El rey de la liquidez"},
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "ETF índice",   "Nombre": "iShares S&P 500",                 "Ticker": "IVV",       "Opciones": "IVV",                 "Comentario": "Alternativa a SPY"},
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "ETF índice",   "Nombre": "Vanguard S&P 500",                "Ticker": "VOO",       "Opciones": "VOO",                 "Comentario": "Muy usado a largo plazo"},
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "Índice",       "Nombre": "NASDAQ 100",                      "Ticker": "^NDX",      "Opciones": "NDX / XND / QQQ",     "Comentario": "Opciones sobre NDX o QQQ"},
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "ETF índice",   "Nombre": "Invesco QQQ",                     "Ticker": "QQQ",       "Opciones": "QQQ",                 "Comentario": "Tech-heavy, opciones muy líquidas"},
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "ETF índice",   "Nombre": "Invesco QQQM",                    "Ticker": "QQQM",      "Opciones": "QQQM",                "Comentario": "Versión mini"},
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "Índice",       "Nombre": "Dow Jones Industrial Average",    "Ticker": "^DJI",      "Opciones": "DIA",                 "Comentario": "Opciones sobre ETF DIA"},
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "ETF índice",   "Nombre": "SPDR Dow Jones Industrial Average","Ticker": "DIA",      "Opciones": "DIA",                 "Comentario": "Opciones decentes"},
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "Índice",       "Nombre": "Russell 2000",                    "Ticker": "^RUT",      "Opciones": "RUT / IWM",           "Comentario": "Opciones muy líquidas"},
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "ETF índice",   "Nombre": "iShares Russell 2000",            "Ticker": "IWM",       "Opciones": "IWM",                 "Comentario": "Small caps"},
    {"Categoría": "🇺🇸 Índice USA", "Tipo": "ETF índice",   "Nombre": "iShares Russell 1000",            "Ticker": "IWB",       "Opciones": "IWB",                 "Comentario": "Large caps USA"},

    {"Categoría": "🇺🇸 Volatilidad", "Tipo": "Índice",         "Nombre": "CBOE Volatility Index",        "Ticker": "^VIX",      "Opciones": "Futuros VIX",         "Comentario": "Opciones avanzadas sobre futuros VIX"},
    {"Categoría": "🇺🇸 Volatilidad", "Tipo": "ETN",            "Nombre": "iPath S&P 500 VIX Short-Term", "Ticker": "VXX",       "Opciones": "VXX",                 "Comentario": "Exposición a volatilidad"},
    {"Categoría": "🇺🇸 Volatilidad", "Tipo": "ETF apalancado","Nombre": "ProShares Ultra VIX Short-Term","Ticker": "UVXY",      "Opciones": "UVXY",                "Comentario": "Muy agresivo"},
    {"Categoría": "🇺🇸 Volatilidad", "Tipo": "ETF apalancado","Nombre": "ProShares Short VIX Short-Term","Ticker": "SVXY",      "Opciones": "SVXY",                "Comentario": "Short vol suavizado"},

    # 🇺🇸 Sectores
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "Tech Select Sector SPDR",          "Ticker": "XLK",  "Opciones": "XLK",  "Comentario": "Tecnología"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "Financial Select Sector SPDR",      "Ticker": "XLF",  "Opciones": "XLF",  "Comentario": "Finanzas"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "Health Care Select Sector SPDR",    "Ticker": "XLV",  "Opciones": "XLV",  "Comentario": "Salud"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "Energy Select Sector SPDR",         "Ticker": "XLE",  "Opciones": "XLE",  "Comentario": "Energía"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "Industrial Select Sector SPDR",     "Ticker": "XLI",  "Opciones": "XLI",  "Comentario": "Industriales"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "Consumer Discretionary SPDR",       "Ticker": "XLY",  "Opciones": "XLY",  "Comentario": "Consumo cíclico"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "Consumer Staples SPDR",             "Ticker": "XLP",  "Opciones": "XLP",  "Comentario": "Consumo defensivo"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "Utilities Select Sector SPDR",      "Ticker": "XLU",  "Opciones": "XLU",  "Comentario": "Utilities"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "Materials Select Sector SPDR",      "Ticker": "XLB",  "Opciones": "XLB",  "Comentario": "Materiales"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "Real Estate Select Sector",         "Ticker": "XLRE", "Opciones": "XLRE", "Comentario": "Inmobiliario"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "SPDR S&P Oil & Gas Exploration",    "Ticker": "XOP",  "Opciones": "XOP",  "Comentario": "Exploración petróleo"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "SPDR S&P Retail",                   "Ticker": "XRT",  "Opciones": "XRT",  "Comentario": "Retail"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "SPDR S&P Homebuilders",             "Ticker": "XHB",  "Opciones": "XHB",  "Comentario": "Constructoras"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "SPDR S&P Metals & Mining",          "Ticker": "XME",  "Opciones": "XME",  "Comentario": "Mineras"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "VanEck Semiconductor ETF",          "Ticker": "SMH",  "Opciones": "SMH",  "Comentario": "Semiconductores"},
    {"Categoría": "🇺🇸 Sectores", "Tipo": "ETF sectorial", "Nombre": "iShares Semiconductor ETF",         "Ticker": "SOXX", "Opciones": "SOXX", "Comentario": "Alternativa a SMH"},

    # 🇺🇸 Estilo / Size
    {"Categoría": "🇺🇸 Estilo/Size", "Tipo": "ETF estilo",      "Nombre": "iShares Russell 1000 Growth",      "Ticker": "IWF",  "Opciones": "IWF",  "Comentario": "Growth USA"},
    {"Categoría": "🇺🇸 Estilo/Size", "Tipo": "ETF estilo",      "Nombre": "iShares Russell 1000 Value",       "Ticker": "IWD",  "Opciones": "IWD",  "Comentario": "Value USA"},
    {"Categoría": "🇺🇸 Estilo/Size", "Tipo": "ETF tamaño",      "Nombre": "iShares Core S&P Mid-Cap",         "Ticker": "IJH",  "Opciones": "IJH",  "Comentario": "Mid caps"},
    {"Categoría": "🇺🇸 Estilo/Size", "Tipo": "ETF tamaño",      "Nombre": "iShares Core S&P Small-Cap",       "Ticker": "IJR",  "Opciones": "IJR",  "Comentario": "Small caps USA"},
    {"Categoría": "🇺🇸 Estilo/Size", "Tipo": "ETF multifactor", "Nombre": "Invesco S&P 500 Equal Weight",     "Ticker": "RSP",  "Opciones": "RSP",  "Comentario": "S&P 500 equiponderado"},
    {"Categoría": "🇺🇸 Estilo/Size", "Tipo": "ETF dividendo",   "Nombre": "Vanguard High Dividend Yield",     "Ticker": "VYM",  "Opciones": "VYM",  "Comentario": "Alto dividendo"},
    {"Categoría": "🇺🇸 Estilo/Size", "Tipo": "ETF dividendo",   "Nombre": "iShares Select Dividend",          "Ticker": "DVY",  "Opciones": "DVY",  "Comentario": "Enfoque dividendos USA"},

    # 🇺🇸 Bonos
    {"Categoría": "🇺🇸 Bonos", "Tipo": "ETF bonos", "Nombre": "iShares 20+ Year Treasury",          "Ticker": "TLT", "Opciones": "TLT", "Comentario": "Bonos largos USA"},
    {"Categoría": "🇺🇸 Bonos", "Tipo": "ETF bonos", "Nombre": "iShares 7-10 Year Treasury",         "Ticker": "IEF", "Opciones": "IEF", "Comentario": "Tramo medio"},
    {"Categoría": "🇺🇸 Bonos", "Tipo": "ETF bonos", "Nombre": "iShares iBoxx High Yield Corporate", "Ticker": "HYG", "Opciones": "HYG", "Comentario": "High yield"},
    {"Categoría": "🇺🇸 Bonos", "Tipo": "ETF bonos", "Nombre": "iShares Inv. Grade Corporate",       "Ticker": "LQD", "Opciones": "LQD", "Comentario": "Grado inversión"},
    {"Categoría": "🇺🇸 Bonos", "Tipo": "ETF bonos", "Nombre": "SPDR High Yield Bond",               "Ticker": "JNK", "Opciones": "JNK", "Comentario": "High yield"},
    {"Categoría": "🇺🇸 Bonos", "Tipo": "ETF bonos", "Nombre": "iShares TIPS Bond",                  "Ticker": "TIP", "Opciones": "TIP", "Comentario": "Bonos ligados a inflación"},

    # 🇺🇸 REIT
    {"Categoría": "🇺🇸 REIT / Inmo", "Tipo": "ETF REIT", "Nombre": "Vanguard Real Estate",   "Ticker": "VNQ", "Opciones": "VNQ", "Comentario": "Inmobiliario USA"},
    {"Categoría": "🇺🇸 REIT / Inmo", "Tipo": "ETF REIT", "Nombre": "iShares U.S. Real Estate","Ticker": "IYR", "Opciones": "IYR", "Comentario": "Alternativa a VNQ"},

    # 🇪🇺 Europa
    {"Categoría": "🇪🇺 Europa",       "Tipo": "Índice",    "Nombre": "Euro Stoxx 50",             "Ticker": "^STOXX50E", "Opciones": "OESX (Eurex)",  "Comentario": "Opciones Eurex"},
    {"Categoría": "🇪🇺 Europa",       "Tipo": "ETF índice","Nombre": "SPDR Euro Stoxx 50",        "Ticker": "FEZ",        "Opciones": "FEZ",           "Comentario": "ETF con opciones"},
    {"Categoría": "🇩🇪 Alemania",     "Tipo": "Índice",    "Nombre": "DAX 40",                    "Ticker": "^GDAXI",     "Opciones": "ODAX (Eurex)", "Comentario": "Opciones DAX muy líquidas"},
    {"Categoría": "🇩🇪 Alemania",     "Tipo": "ETF país",  "Nombre": "iShares MSCI Germany",      "Ticker": "EWG",        "Opciones": "EWG",           "Comentario": "Exposición a Alemania"},
    {"Categoría": "🇫🇷 Francia",      "Tipo": "Índice",    "Nombre": "CAC 40",                    "Ticker": "^FCHI",      "Opciones": "FCE (Euronext)","Comentario": "Opciones Euronext"},
    {"Categoría": "🇫🇷 Francia",      "Tipo": "ETF país",  "Nombre": "iShares MSCI France",       "Ticker": "EWQ",        "Opciones": "EWQ",           "Comentario": "ETF país Francia"},
    {"Categoría": "🇬🇧 Reino Unido",  "Tipo": "Índice",    "Nombre": "FTSE 100",                  "Ticker": "^FTSE",      "Opciones": "UKX (ICE)",     "Comentario": "Opciones ICE"},
    {"Categoría": "🇬🇧 Reino Unido",  "Tipo": "ETF país",  "Nombre": "iShares MSCI United Kingdom","Ticker": "EWU",       "Opciones": "EWU",           "Comentario": "Exposición UK"},
    {"Categoría": "🇪🇸 España",       "Tipo": "Índice",    "Nombre": "IBEX 35",                   "Ticker": "^IBEX",      "Opciones": "IBEX (MEFF)",   "Comentario": "Opciones en MEFF"},
    {"Categoría": "🇪🇸 España",       "Tipo": "ETF país",  "Nombre": "iShares MSCI Spain",        "Ticker": "EWP",        "Opciones": "EWP",           "Comentario": "ETF España (USA)"},
    {"Categoría": "🇮🇹 Italia",       "Tipo": "Índice",    "Nombre": "FTSE MIB",                  "Ticker": "FTSEMIB.MI", "Opciones": "MIBO (IDEM)",   "Comentario": "Opciones IDEM"},
    {"Categoría": "🇮🇹 Italia",       "Tipo": "ETF país",  "Nombre": "iShares MSCI Italy",        "Ticker": "EWI",        "Opciones": "EWI",           "Comentario": "ETF país Italia"},
    {"Categoría": "🇨🇭 Suiza",        "Tipo": "Índice",    "Nombre": "SMI 20",                    "Ticker": "^SSMI",      "Opciones": "SMI (SIX)",     "Comentario": "Opciones SIX"},
    {"Categoría": "🇨🇭 Suiza",        "Tipo": "ETF país",  "Nombre": "iShares MSCI Switzerland",  "Ticker": "EWL",        "Opciones": "EWL",           "Comentario": "ETF país Suiza"},
    {"Categoría": "🇳🇱 Países Bajos", "Tipo": "Índice",    "Nombre": "AEX 25",                    "Ticker": "^AEX",       "Opciones": "AEX (Euronext)","Comentario": "Opciones Euronext"},
    {"Categoría": "🇳🇱 Países Bajos", "Tipo": "ETF país",  "Nombre": "iShares MSCI Netherlands",  "Ticker": "EWN",        "Opciones": "EWN",           "Comentario": "ETF país Países Bajos"},
    {"Categoría": "🇸🇪 Suecia",       "Tipo": "Índice",    "Nombre": "OMX Stockholm 30",          "Ticker": "^OMX",       "Opciones": "OMXS30",        "Comentario": "Opciones locales"},
    {"Categoría": "🇸🇪 Suecia",       "Tipo": "ETF país",  "Nombre": "iShares MSCI Sweden",       "Ticker": "EWD",        "Opciones": "EWD",           "Comentario": "ETF país Suecia"},

    # 🌏 Asia-Pacífico
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "Índice",    "Nombre": "Nikkei 225",                 "Ticker": "^N225", "Opciones": "NK225 Options", "Comentario": "Opciones muy activas"},
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "ETF país",  "Nombre": "iShares MSCI Japan",         "Ticker": "EWJ",   "Opciones": "EWJ",           "Comentario": "Exposición Japón"},
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "Índice",    "Nombre": "TOPIX",                      "Ticker": "^TOPX", "Opciones": "TPX Options",   "Comentario": "Opciones en Japón"},
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "Índice",    "Nombre": "Hang Seng Index",            "Ticker": "^HSI",  "Opciones": "HSI (HKEX)",    "Comentario": "Opciones en HKEX"},
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "ETF país",  "Nombre": "iShares MSCI Hong Kong",     "Ticker": "EWH",   "Opciones": "EWH",           "Comentario": "ETF país Hong Kong"},
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "ETF país",  "Nombre": "iShares China Large-Cap",    "Ticker": "FXI",   "Opciones": "FXI",           "Comentario": "China grandes compañías"},
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "ETF país",  "Nombre": "iShares MSCI China",         "Ticker": "MCHI",  "Opciones": "MCHI",          "Comentario": "Exposición amplia a China"},
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "ETF país",  "Nombre": "iShares MSCI South Korea",   "Ticker": "EWY",   "Opciones": "EWY",           "Comentario": "Corea del Sur"},
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "ETF país",  "Nombre": "iShares MSCI Taiwan",        "Ticker": "EWT",   "Opciones": "EWT",           "Comentario": "Taiwán"},
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "ETF país",  "Nombre": "iShares MSCI India",         "Ticker": "INDA",  "Opciones": "INDA",          "Comentario": "Exposición a India"},
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "ETF país",  "Nombre": "iShares MSCI Australia",     "Ticker": "EWA",   "Opciones": "EWA",           "Comentario": "Exposición Australia"},
    {"Categoría": "🌏 Asia-Pacífico", "Tipo": "ETF país",  "Nombre": "iShares MSCI Singapore",     "Ticker": "EWS",   "Opciones": "EWS",           "Comentario": "Exposición Singapur"},

    # 🌎 Global
    {"Categoría": "🌎 Global", "Tipo": "ETF global",      "Nombre": "iShares MSCI ACWI",             "Ticker": "ACWI", "Opciones": "ACWI", "Comentario": "Mundo completo"},
    {"Categoría": "🌎 Global", "Tipo": "ETF global",      "Nombre": "iShares MSCI World",            "Ticker": "URTH", "Opciones": "URTH", "Comentario": "Países desarrollados"},
    {"Categoría": "🌎 Global", "Tipo": "ETF emergentes",  "Nombre": "iShares MSCI Emerging Markets", "Ticker": "EEM",  "Opciones": "EEM",  "Comentario": "Emergentes muy líquido"},
    {"Categoría": "🌎 Global", "Tipo": "ETF emergentes",  "Nombre": "Vanguard FTSE Emerging Markets","Ticker": "VWO",  "Opciones": "VWO",  "Comentario": "Alternativa a EEM"},

    # 🛢️ Commodities
    {"Categoría": "🛢️ Commodities", "Tipo": "ETF commodity", "Nombre": "SPDR Gold Trust",            "Ticker": "GLD",  "Opciones": "GLD",  "Comentario": "Oro muy líquido"},
    {"Categoría": "🛢️ Commodities", "Tipo": "ETF commodity", "Nombre": "iShares Silver Trust",       "Ticker": "SLV",  "Opciones": "SLV",  "Comentario": "Plata"},
    {"Categoría": "🛢️ Commodities", "Tipo": "ETF commodity", "Nombre": "VanEck Gold Miners",         "Ticker": "GDX",  "Opciones": "GDX",  "Comentario": "Mineras de oro"},
    {"Categoría": "🛢️ Commodities", "Tipo": "ETF commodity", "Nombre": "VanEck Junior Gold Miners",  "Ticker": "GDXJ", "Opciones": "GDXJ", "Comentario": "Mineras pequeñas, más volátiles"},
    {"Categoría": "🛢️ Commodities", "Tipo": "ETF commodity", "Nombre": "United States Oil Fund",     "Ticker": "USO",  "Opciones": "USO",  "Comentario": "ETF sobre WTI"},
    {"Categoría": "🛢️ Commodities", "Tipo": "ETF commodity", "Nombre": "United States Natural Gas",  "Ticker": "UNG",  "Opciones": "UNG",  "Comentario": "Gas natural agresivo"},
    {"Categoría": "🛢️ Commodities", "Tipo": "ETF commodity", "Nombre": "Invesco DB Commodity Index", "Ticker": "DBC",  "Opciones": "DBC",  "Comentario": "Cesta de materias primas"},
    {"Categoría": "🛢️ Commodities", "Tipo": "ETF commodity", "Nombre": "Invesco DB Agriculture",     "Ticker": "DBA",  "Opciones": "DBA",  "Comentario": "Agrícolas"},

    # ₿ Cripto
    {"Categoría": "₿ Cripto", "Tipo": "ETF futuro BTC", "Nombre": "ProShares Bitcoin Strategy",       "Ticker": "BITO", "Opciones": "BITO", "Comentario": "Basado en futuros CME"},
    {"Categoría": "₿ Cripto", "Tipo": "ETF futuro BTC", "Nombre": "VanEck Bitcoin Strategy",          "Ticker": "XBTF", "Opciones": "XBTF", "Comentario": "Alternativa a BITO"},
    {"Categoría": "₿ Cripto", "Tipo": "ETF spot BTC",   "Nombre": "iShares Bitcoin Trust",            "Ticker": "IBIT", "Opciones": "—",    "Comentario": "ETF spot BTC (USA)"},
    {"Categoría": "₿ Cripto", "Tipo": "ETF spot BTC",   "Nombre": "Fidelity Wise Origin Bitcoin",     "Ticker": "FBTC", "Opciones": "—",    "Comentario": "Otro spot BTC"},
]


def build_universe_df(data: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(data)


def load_sp500_df() -> pd.DataFrame:
    return scrape_series_data()


def render_tables(df_universe: pd.DataFrame, df_sp500: pd.DataFrame) -> None:
    col1, col2 = st.columns([2, 2])

    with col1:
        st.subheader("Mercados y ETFs")
        st.dataframe(df_universe, use_container_width=True)

    with col2:
        st.subheader("Acciones S&P 500")
        st.dataframe(df_sp500, use_container_width=True)


def dashboard_universe_vs_sp500():
    df_universe = build_universe_df(data)
    df_sp500 = load_sp500_df()
    render_tables(df_universe, df_sp500)


if __name__ == "__main__":
    dashboard_universe_vs_sp500()
