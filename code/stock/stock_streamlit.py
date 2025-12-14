import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import datetime
import pandas as pd
import yfinance as yf

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from scrapper.sp500_fechas import load_sp500
from scrapper.symbols import obtener_ticker

ICONS = {
    "1": "./icons/layout_1.png",
    "2v": "./icons/layout_2_vertical.png",
    "2h": "./icons/layout_2_horizontal.png",
    "3_lr": "./icons/layout_3.png",     
    "3_tb": "./icons/layout_3_alt.png",  
    "4": "./icons/layout_4.png",
}

OPCIONES_INDICADORES = ["SMA20", "SMA50", "Volumen", "RSI", "MACD"]

DEFAULT_CONFIG = {
    "sma20": False,
    "sma50": False,
    "volume": True,
    "rsi": False,
    "macd": False
}

@st.cache_data
def load_data(ticker: str):
    data = yf.download(
        ticker,
        start="2020-01-01",
        end=datetime.datetime.now().strftime("%Y-%m-%d"),
        interval="1d"
    )

    data.reset_index(inplace=True)
    data.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
    data["Date"] = pd.to_datetime(data["Date"])
    data.set_index("Date", inplace=True)
    return data


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()

    df["EMA12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    window = 14
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    df["RSI14"] = 100 - (100 / (1 + rs))

    return df

def build_figure(
    df: pd.DataFrame,
    sma20: bool,
    sma50: bool,
    volume: bool,
    rsi: bool,
    macd: bool
):

    rows = 1 + int(volume) + int(rsi) + int(macd)

    if rows == 1:
        row_heights = [1.0]
    else:
        row_heights = [0.55] 
        if volume:
            row_heights.append(0.15)
        if rsi:
            row_heights.append(0.15)
        if macd:
            row_heights.append(0.15)

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=row_heights
    )

    row_id = 1

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Precio"
    ), row=row_id, col=1)

    if sma20:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["SMA20"],
            mode="lines",
            name="SMA20"
        ), row=row_id, col=1)

    if sma50:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["SMA50"],
            mode="lines",
            name="SMA50"
        ), row=row_id, col=1)

    if volume:
        row_id += 1
        fig.add_trace(go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Volumen"
        ), row=row_id, col=1)
        fig.update_yaxes(title_text="Volumen", row=row_id, col=1)

    if rsi:
        row_id += 1
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["RSI14"],
            mode="lines",
            name="RSI14"
        ), row=row_id, col=1)
        fig.add_hrect(
            y0=30, y1=70,
            fillcolor="lightgray",
            opacity=0.3,
            line_width=0,
            row=row_id, col=1
        )
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=row_id, col=1)

    if macd:
        row_id += 1
        fig.add_trace(go.Bar(
            x=df.index,
            y=df["MACD_hist"],
            name="MACD Hist"
        ), row=row_id, col=1)
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["MACD"],
            mode="lines",
            name="MACD"
        ), row=row_id, col=1)
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["MACD_signal"],
            mode="lines",
            name="MACD Signal"
        ), row=row_id, col=1)
        fig.update_yaxes(title_text="MACD", row=row_id, col=1)

    fig.update_yaxes(title_text="Precio", row=1, col=1)

    fig.update_layout(
        height=250 * rows + 300,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )

    return fig


def show_chart(slot_key: str, ticker: str, config: dict, n_rows: int = 1):
    df = load_data(ticker)
    df = add_indicators(df)

    fig = build_figure(
        df,
        sma20=config["sma20"],
        sma50=config["sma50"],
        volume=config["volume"],
        rsi=config["rsi"],
        macd=config["macd"]
    )

    base_height = 600  
    height = base_height // n_rows

    fig.update_layout(height=height)

    st.plotly_chart(
        fig,
        width='stretch',
        key=f"chart_{slot_key}"
    )



def init_tickers(TICKERS=None, num_empresas=4):
    """
    Inicializa la lista de TICKERS.
    Si TICKERS es None, se cargan las primeras empresas del S&P 500
    y se obtienen sus tickers correspondientes.
    """
    if TICKERS is None:
        df_sp500 = load_sp500()
        empresas = df_sp500["activo"].iloc[1:1 + num_empresas].tolist()
        TICKERS = [obtener_ticker(empresa) for empresa in empresas]

    return TICKERS


def ticker_and_indicators(
    slot_prefix: str,
    label_ticker: str,
    default_config: dict | None = None
):
    """
    Crea dos columnas: izquierda ticker, derecha indicadores.
    Devuelve (ticker, config_indicadores).
    """
    if default_config is None:
        default_config = DEFAULT_CONFIG

    if f"{slot_prefix}_modo_sugerencias" not in st.session_state:
        st.session_state[f"{slot_prefix}_modo_sugerencias"] = False

    col_c, col_t, col_i = st.columns([1, 1, 2])

    with col_c:
        if st.button("Sugerencias S&P 500", key=f"{slot_prefix}_btn"):
            st.session_state[f"{slot_prefix}_modo_sugerencias"] = not st.session_state[f"{slot_prefix}_modo_sugerencias"]

    with col_t:
        if st.session_state[f"{slot_prefix}_modo_sugerencias"]:
            TICKERS = init_tickers(TICKERS=None, num_empresas=10)
            ticker = st.selectbox(
                label_ticker,
                TICKERS,
                key=f"{slot_prefix}_ticker"
            )

        else:

            ticker = st.text_input(
                "Símbolo",
                value="AAPL",
                key=f"{slot_prefix}_symbol_calendar"
            )

    default_selection = []
    if default_config.get("sma20", False):
        default_selection.append("SMA20")
    if default_config.get("sma50", False):
        default_selection.append("SMA50")
    if default_config.get("volume", False):
        default_selection.append("Volumen")
    if default_config.get("rsi", False):
        default_selection.append("RSI")
    if default_config.get("macd", False):
        default_selection.append("MACD")

    with col_i:
        seleccion = st.multiselect(
            "Indicadores",
            options=OPCIONES_INDICADORES,
            default=default_selection,
            key=f"{slot_prefix}_ind"
        )

    config = {
        "sma20":  "SMA20"   in seleccion,
        "sma50":  "SMA50"   in seleccion,
        "volume": "Volumen" in seleccion,
        "rsi":    "RSI"     in seleccion,
        "macd":   "MACD"    in seleccion,
    }

    return ticker, config


def dashboard_app_velas():

    if "layout" not in st.session_state:
        st.session_state.layout = "1"

    if "show_menu" not in st.session_state:
        st.session_state.show_menu = False

    st.title("📊 Dashboard con indicadores técnicos")

    col_icon, _ = st.columns([0.2, 0.8])

    with col_icon:
        st.image(ICONS[st.session_state.layout], width=40)
        if st.button(" ", key="toggle_menu"):
            st.session_state.show_menu = not st.session_state.show_menu

    if st.session_state.show_menu:
        cols = st.columns(len(ICONS))
        for col, key in zip(cols, ICONS.keys()):
            with col:
                if st.button(" ", key=f"opt_{key}"):
                    st.session_state.layout = key
                    st.session_state.show_menu = False
                st.image(ICONS[key], width=35)

    st.markdown("---")

    layout = st.session_state.layout

    if layout == "1":
        t, cfg = ticker_and_indicators(
            slot_prefix="l1_main",
            label_ticker="Ticker",
            default_config=DEFAULT_CONFIG
        )
        show_chart("1_main", t, cfg)

    elif layout == "2v":
        TICKERS = init_tickers(TICKERS=None, num_empresas=10)

        col1, col2 = st.columns(2)
        with col1:
            t1 = st.selectbox("Ticker Top", TICKERS, key="t2v_top")

        with col2:
            t2 = st.selectbox("Ticker Bottom", TICKERS, key="t2v_bottom")

        show_chart("2v_top", t1, DEFAULT_CONFIG, n_rows=2)
        show_chart("2v_bottom", t2, DEFAULT_CONFIG, n_rows=2)

    elif layout == "2h":
        col1, col2 = st.columns(2)
        with col1:
            t1, cfg1 = ticker_and_indicators(
                slot_prefix="l2h_left",
                label_ticker="Ticker izquierda",
                default_config=DEFAULT_CONFIG
            )
            show_chart("2h_left", t1, cfg1)
        with col2:
            t2, cfg2 = ticker_and_indicators(
                slot_prefix="l2h_right",
                label_ticker="Ticker derecha",
                default_config=DEFAULT_CONFIG
            )
            show_chart("2h_right", t2, cfg2)

        
    elif layout == "3_lr":
        TICKERS = init_tickers(TICKERS=None, num_empresas=10)
        
        col_left, col_right = st.columns([2, 1])
        with col_left:
            t1, cfg1 = ticker_and_indicators(
                slot_prefix="l3lr_left",
                label_ticker="Ticker grande izquierda",
                default_config=DEFAULT_CONFIG
            )
            show_chart("3lr_left", t1, cfg1)
            
        with col_right:
            col_r1, col_r2 = st.columns([1, 1])
            with col_r1:
                t1 = st.selectbox("Ticker RTop", TICKERS, key="t3v_top")
                
            with col_r2:
                t2 = st.selectbox("Ticker RBottom", TICKERS, key="t3v_bottom")

            show_chart("3v_top", t1, DEFAULT_CONFIG, n_rows=2)
            show_chart("3v_bottom", t2, DEFAULT_CONFIG, n_rows=2)
        

    elif layout == "3_tb":
        TICKERS = init_tickers(TICKERS=None, num_empresas=10)
    
        t = st.selectbox("Ticker TL", TICKERS, key="t3tb_top")
        show_chart("3tb_top", t, DEFAULT_CONFIG, n_rows=2)

        col1, col2 = st.columns(2)
        with col1:
            t2, cfg2 = ticker_and_indicators(
                slot_prefix="l3tb_bottom_left",
                label_ticker="Ticker abajo izq",
                default_config=DEFAULT_CONFIG,
                n_rows=2

            )
            show_chart("3tb_bottom_left", t2, cfg2)
        with col2:
            t3, cfg3 = ticker_and_indicators(
                slot_prefix="l3tb_bottom_right",
                label_ticker="Ticker abajo der",
                default_config=DEFAULT_CONFIG,
                n_rows=2
            )
            show_chart("3tb_bottom_right", t3, cfg3)

    elif layout == "4":
        TICKERS = init_tickers(TICKERS=None, num_empresas=10)
    
        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)

        with col1:
            coltleft, colbleft = st.columns(2)
            with coltleft:
                ttl = st.selectbox("Ticker TopLeft", TICKERS, key="t4_1")
            with colbleft:
                tbl = st.selectbox("Ticker BottomLeft", TICKERS, key="t4_3")
            show_chart("4_tl", ttl, DEFAULT_CONFIG, n_rows=2)
        with col2:
            coltright, colbright = st.columns(2)
            with coltright:
                ttr = st.selectbox("Ticker TopRight", TICKERS, key="t4_2")
            with colbright:
                tbr = st.selectbox("Ticker BottomRight", TICKERS, key="t4_4")
            show_chart("4_tr", ttr, DEFAULT_CONFIG, n_rows=2)
        with col3:
            show_chart("4_bl", tbl, DEFAULT_CONFIG, n_rows=2)
        with col4:
            show_chart("4_br", tbr, DEFAULT_CONFIG, n_rows=2)

if __name__ == "__main__":
    dashboard_app_velas()
