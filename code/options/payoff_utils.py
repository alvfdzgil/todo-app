import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import time
from scrapper.options import scrape_options_data

def load_calls_for_expiration(symbol: str, timestamp: int, max_intentos: int = 10):
    """
    Descarga datos de opciones CALL para un symbol y un timestamp concreto.
    Devuelve (df_calls) o None si no se pudo.
    """
    calls_df = None
    for intento in range(max_intentos):
        options_compra, _ = scrape_options_data(symbol, timestamp, verbose=False)
        if options_compra is not None and not options_compra.empty:
            calls_df = options_compra
            break
        else:
            time.sleep(2*intento)
    return calls_df


def load_puts_for_expiration(symbol: str, timestamp: int, max_intentos: int = 10):
    """
    Descarga datos de opciones PUT para un symbol y un timestamp concreto.
    Devuelve (df_puts) o None si no se pudo.
    """
    puts_df = None
    for intento in range(max_intentos):
        _, options_venta = scrape_options_data(symbol, timestamp, verbose=False)
        if options_venta is not None and not options_venta.empty:
            puts_df = options_venta
            break
        else:
            time.sleep(2*intento)
    return puts_df


def choose_atm_strike(df, spot):
    """
    Devuelve la ROW (Series) de la opción ATM:
    la que tiene strike más cercano al spot.
    """
    df = df.copy().sort_values("Precio de ejercicio").reset_index(drop=True)
    df["dist"] = (df["Precio de ejercicio"] - spot).abs()
    idx_atm = df["dist"].idxmin()
    return df.loc[idx_atm]


def best_otm_call(df, spot):
    """
    Devuelve la ROW (Series) de la mejor Call OTM:
    - strike > spot
    - IV en [Volatilidad_implícita_min, Volatilidad_implícita_max]
    - score = distance / (Último precio * |IV|), minimizado
    """
    row_atm = choose_atm_strike(df, spot)
    K_atm = row_atm["Precio de ejercicio"]

    df = df[df["Precio de ejercicio"] > K_atm]
    if df.empty:
        raise ValueError("No hay CALLs OTM más allá de la ATM.")
    
    df = df.copy()

    df["distance"] = df["Precio de ejercicio"] - spot
    df = df[df["distance"] > 0] 

    Volatilidad_implícita_min = df["Volatilidad implícita"].abs().quantile(0)
    Volatilidad_implícita_max = df["Volatilidad implícita"].abs().quantile(0.25)
    df = df[
        (df["Volatilidad implícita"].abs() >= Volatilidad_implícita_min) &
        (df["Volatilidad implícita"].abs() <= Volatilidad_implícita_max)
    ]

    if df.empty:
        raise ValueError("No hay CALLs OTM que cumplan los filtros de IV.")

    df["score"] = df["distance"] / (
        df["Último precio"] *
        df["Volatilidad implícita"].abs()
    )

    return df.sort_values("score", ascending=True).iloc[0]


def best_otm_put(df, spot):
    """
    Devuelve la ROW (Series) de la mejor Put OTM:
    - strike < spot
    - IV en [Volatilidad_implícita_min, Volatilidad_implícita_max]
    - score = distance / (Último precio * |IV|), minimizado
    """
    row_atm = choose_atm_strike(df, spot)
    K_atm = row_atm["Precio de ejercicio"]

    df = df[df["Precio de ejercicio"] < K_atm]
    if df.empty:
        raise ValueError("No hay PUTs OTM más allá de la ATM.")
    
    df = df.copy()

    df["distance"] = spot - df["Precio de ejercicio"]
    df = df[df["distance"] > 0]  

    Volatilidad_implícita_min = df["Volatilidad implícita"].abs().quantile(0)
    Volatilidad_implícita_max = df["Volatilidad implícita"].abs().quantile(0.25)
    df = df[
        (df["Volatilidad implícita"].abs() >= Volatilidad_implícita_min) &
        (df["Volatilidad implícita"].abs() <= Volatilidad_implícita_max)
    ]

    if df.empty:
        raise ValueError("No hay PUTS OTM que cumplan los filtros de IV.")

    df["score"] = df["distance"] / (
        df["Último precio"] *
        df["Volatilidad implícita"].abs()
    )

    return df.sort_values("score", ascending=True).iloc[0]


def choose_butterfly_call_rows(df_calls, spot):
    """
    Elige las ROWS para una CALL BUTTERFLY (solo compras):
    - row_K2: Call ATM (centro)
    - row_K3: mejor Call OTM (ala superior)
    - row_K1: strike simétrico a K3 respecto a K2 pero por FILAS (ala inferior)
    """
    row_K2 = choose_atm_strike(df_calls, spot)
    K2 = row_K2["Precio de ejercicio"]

    row_K3 = best_otm_call(df_calls, spot)
    K3 = row_K3["Precio de ejercicio"]

    df = df_calls.copy().sort_values("Precio de ejercicio").reset_index(drop=True)

    try:
        idx2 = df.index[df["Precio de ejercicio"] == K2][0]
        idx3 = df.index[df["Precio de ejercicio"] == K3][0]
    except IndexError:
        raise ValueError("K2 o K3 no se encuentran en la tabla de strikes")

    d = idx3 - idx2
    idx1 = idx2 - d
    if idx1 < 0:
        idx1 = 0  

    row_K1 = df.loc[idx1]

    return row_K1


def choose_butterfly_put_rows(df_puts, spot):
    """
    Elige las ROWS para una PUT BUTTERFLY (solo compras):
    - row_K2: Put ATM (centro)
    - row_K3: mejor Put OTM (strike más bajo)
    - row_K1: strike simétrico a K3 respecto a K2 pero por FILAS (strike más alto)
    Queremos finalmente K1 > K2 > K3.
    """
    row_K2 = choose_atm_strike(df_puts, spot)
    K2 = row_K2["Precio de ejercicio"]

    row_K3 = best_otm_put(df_puts, spot)
    K3 = row_K3["Precio de ejercicio"]

    df = df_puts.copy().sort_values("Precio de ejercicio").reset_index(drop=True)

    try:
        idx2 = df.index[df["Precio de ejercicio"] == K2][0]
        idx3 = df.index[df["Precio de ejercicio"] == K3][0]
    except IndexError:
        raise ValueError("K2 o K3 no se encuentran en la tabla de strikes")

    d = idx2 - idx3
    idx1 = idx2 + d
    if idx1 >= len(df):
        idx1 = len(df) - 1  

    row_K1 = df.loc[idx1]

    return row_K1

def get_current_price(indicador="AAPL"):
    """
    Obtiene el precio actual del subyacente usando yfinance.
    """
    precio_actual = yf.Ticker(indicador).history(period="1d")["Close"].iloc[-1]
    return precio_actual


def make_price_grid(center, factor_min=0.8, factor_max=1.2, n=4000):
    """
    Genera un array de precios S alrededor de 'center'
    entre factor_min*center y factor_max*center.
    """
    return np.linspace(center * factor_min, center * factor_max, n)


def payoff_call_long(S, strike, premium):
    """
    Payoff de UNA Call comprada:
    max(S - K, 0) - prima
    """
    return np.maximum(S - strike, 0) - premium

def payoff_put_long(S, strike, premium):
    """
    Payoff de UNA Put comprada:
    max(K - S, 0) - prima
    """
    return np.maximum(strike - S, 0) - premium

import plotly.graph_objects as go

def plot_payoff(df, title="Payoff", ticker="AAPL"):
    df_plot = df.copy()
    precio_actual = float(get_current_price(ticker))
    df_plot["ratio"] = (df_plot["S"] / precio_actual - 1) * 100

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_plot["S"],
        y=df_plot["payoff"].where(df_plot["payoff"] >= 0),
        fill="tozeroy",
        mode="none",
        fillcolor="rgba(0,200,0,0.3)",
        opacity=0.4,
        name="Payoff positivo"
    ))

    fig.add_trace(go.Scatter(
        x=df_plot["S"],
        y=df_plot["payoff"].where(df_plot["payoff"] < 0),
        fill="tozeroy",
        mode="none",
        fillcolor="rgba(200,0,0,0.3)",
        opacity=0.4,
        name="Payoff negativo"
    ))

    fig.add_trace(go.Scatter(
        x=df_plot["S"],
        y=df_plot["payoff"],
        mode="lines",
        line=dict(width=2),
        name="Payoff",
        customdata=df_plot["ratio"],
        hovertemplate=(
            "Precio subyacente: %{x:.2f}$<br>"
            "Payoff: %{y:.2f}$<br>"
            "Cambio vs spot: %{customdata:.2f}%<br>"
            "<extra></extra>"
        )
    ))

    fig.add_vline(
        x=precio_actual,
        line_dash="dash",
        line_color="blue",
        annotation_text=f"Spot ({ticker}) = {precio_actual:.2f}$",
        annotation_position="top",
        annotation_font=dict(size=12),
    )

    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        xaxis_title="Precio subyacente en vencimiento corto (S)",
        yaxis_title="Payoff",
        template="plotly_white",
        hovermode="x unified"
    )

    return fig
