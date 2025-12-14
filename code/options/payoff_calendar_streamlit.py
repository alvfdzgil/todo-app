import math
import numpy as np
import pandas as pd
import streamlit as st

from .tabla import dashboard_universe_vs_sp500

from scrapper.fecha import fechas_unix

from scrapper.sp500 import scrape_series_data

from .payoff_utils import (
    load_calls_for_expiration,
    load_puts_for_expiration,
    choose_atm_strike,
    best_otm_call,
    best_otm_put,
    choose_butterfly_call_rows,
    choose_butterfly_put_rows,
    get_current_price,
    make_price_grid,
    payoff_put_long,
    payoff_call_long,
    plot_payoff
)

@st.cache_data(show_spinner=False)
def choose_symmetric_strikes(df, spot):
    """
    Elige dos strikes alrededor del spot en el vencimiento corto:
    - K1: strike inmediatamente inferior al spot
    - K2: strike inmediatamente superior al spot
    Devuelve (row_K1, row_K2).
    """
    df = df.copy().sort_values("Precio de ejercicio").reset_index(drop=True)
    df["dist"] = (df["Precio de ejercicio"] - spot).abs()
    idx_atm = df["dist"].idxmin()

    idx_low = max(idx_atm - 1, 0)
    idx_high = min(idx_atm + 1, len(df) - 1)

    row_K1 = df.loc[idx_low]
    row_K2 = df.loc[idx_high]

    # aseguramos K1 < K2
    if row_K1["Precio de ejercicio"] > row_K2["Precio de ejercicio"]:
        row_K1, row_K2 = row_K2, row_K1

    return row_K1, row_K2


def choose_condor_strikes_calls(df_calls, spot):
    """
    Elige 4 strikes para una Long Condor con CALLs:
    K1 < K2 < K3 < K4.
    """
    df = df_calls.copy().sort_values("Precio de ejercicio").reset_index(drop=True)
    df["dist"] = (df["Precio de ejercicio"] - spot).abs()
    idx_atm = df["dist"].idxmin()

    idx1 = max(idx_atm - 1, 0)
    idx2 = idx_atm
    idx3 = min(idx_atm + 1, len(df) - 1)
    idx4 = min(idx_atm + 2, len(df) - 1)

    filas = pd.DataFrame([
        df.loc[idx1],
        df.loc[idx2],
        df.loc[idx3],
        df.loc[idx4],
    ])
    filas = filas.sort_values("Precio de ejercicio").reset_index(drop=True)

    row_K1 = filas.loc[0]
    row_K2 = filas.loc[1]
    row_K3 = filas.loc[2]
    row_K4 = filas.loc[3]

    return row_K1, row_K2, row_K3, row_K4


def match_strike_row(df, K):
    """
    Devuelve la fila de df cuya 'Precio de ejercicio' coincida con K
    (o la más cercana si no existe exactamente).
    """
    df = df.copy().sort_values("Precio de ejercicio").reset_index(drop=True)
    df["diff"] = (df["Precio de ejercicio"] - K).abs()
    idx = df["diff"].idxmin()
    return df.loc[idx]


def norm_cdf(x):
    x = np.asarray(x, dtype=float)
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2))) if x.ndim == 0 else \
        0.5 * (1.0 + np.fromiter((math.erf(v) for v in x / math.sqrt(2)), float))


def bs_call_value(S, K, sigma, T, r=0.0):
    """
    Valor de una call europea (Black–Scholes) para cada S.
    S puede ser array.
    """
    S = np.asarray(S, dtype=float)
    sigma = float(sigma)
    T = float(T)

    if T <= 0 or sigma <= 0:
        return np.maximum(S - K, 0.0)

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * norm_cdf(d1) - K * np.exp(-r * T) * norm_cdf(d2)


def _clean_sigma(raw_sigma):
    """
    Normaliza la sigma: si viene en % (20) → 0.20.
    Y evita sigma=0 o NaN poniendo un mínimo razonable.
    """
    try:
        sigma = float(raw_sigma)
    except Exception:
        sigma = 0.2  # fallback

    sigma = abs(sigma)

    if sigma > 1.0:
        sigma = sigma / 100.0

    if sigma < 1e-4 or math.isnan(sigma):
        sigma = 0.2

    return sigma


def payoff_long_calendar_from_rows(row_short, row_long,
                                   tau_remain,
                                   factor_min=0.8, factor_max=1.2,
                                   n=4000,
                                   ticker="AAPL"):
    K_short, p_short = row_short["Precio de ejercicio"], row_short["Último precio"]
    K_long,  p_long  = row_long["Precio de ejercicio"],  row_long["Último precio"]

    assert abs(K_short - K_long) / K_short < 0.01, "Los strikes del calendar deben ser prácticamente iguales"
    K = (K_short + K_long) / 2

    sigma_long = _clean_sigma(row_long["Volatilidad implícita"])

    spot = get_current_price(ticker)
    center = spot
    S = make_price_grid(center, factor_min, factor_max, n)

    short_T1 = -np.maximum(S - K, 0.0)
    long_T1  = bs_call_value(S, K, sigma_long, tau_remain, r=0.0)

    net_premium = p_long - p_short

    payoff_total = short_T1 + long_T1 - net_premium

    return pd.DataFrame({"S": S, "payoff": payoff_total})


def payoff_long_condor_from_rows(row_K1, row_K2, row_K3, row_K4,
                                 factor_min=0.8, factor_max=1.2,
                                 n=4000,
                                 ticker="AAPL"):
    """
    Long Condor con CALLs:
        +1 Call K1
        -1 Call K2
        -1 Call K3
        +1 Call K4
    con K1 < K2 < K3 < K4.
    """
    K1, p1 = row_K1["Precio de ejercicio"], row_K1["Último precio"]
    K2, p2 = row_K2["Precio de ejercicio"], row_K2["Último precio"]
    K3, p3 = row_K3["Precio de ejercicio"], row_K3["Último precio"]
    K4, p4 = row_K4["Precio de ejercicio"], row_K4["Último precio"]

    assert K1 < K2 < K3 < K4, "Se requiere K1 < K2 < K3 < K4 para la Condor."

    spot = get_current_price(ticker)
    center = spot
    S = make_price_grid(center, factor_min, factor_max, n)

    C1 = payoff_call_long(S, K1, p1)
    C2 = payoff_call_long(S, K2, p2)
    C3 = payoff_call_long(S, K3, p3)
    C4 = payoff_call_long(S, K4, p4)

    payoff_total = C1 - C2 - C3 + C4
    return pd.DataFrame({"S": S, "payoff": payoff_total})


def payoff_double_diagonal_from_rows(row_short_K1, row_long_K1,
                                     row_short_K2, row_long_K2,
                                     tau_remain,
                                     factor_min=0.8, factor_max=1.2,
                                     n=4000,
                                     ticker="AAPL"):

    K1_short, p1_short = row_short_K1["Precio de ejercicio"], row_short_K1["Último precio"]
    K1_long,  p1_long  = row_long_K1["Precio de ejercicio"],  row_long_K1["Último precio"]

    K2_short, p2_short = row_short_K2["Precio de ejercicio"], row_short_K2["Último precio"]
    K2_long,  p2_long  = row_long_K2["Precio de ejercicio"],  row_long_K2["Último precio"]

    K1 = (K1_short + K1_long) / 2
    K2 = (K2_short + K2_long) / 2
    assert K1 < K2, "Se requiere K1 < K2 para la Double Diagonal"

    sigma1 = _clean_sigma(row_long_K1["Volatilidad implícita"])
    sigma2 = _clean_sigma(row_long_K2["Volatilidad implícita"])

    center = (K1 + K2) / 2
    S = make_price_grid(center, factor_min, factor_max, n)

    short1_T1 = -np.maximum(S - K1, 0.0)
    long1_T1  = bs_call_value(S, K1, sigma1, tau_remain, r=0.0)
    net1 = p1_long - p1_short
    payoff1 = short1_T1 + long1_T1 - net1

    short2_T1 = -np.maximum(S - K2, 0.0)
    long2_T1  = bs_call_value(S, K2, sigma2, tau_remain, r=0.0)
    net2 = p2_long - p2_short
    payoff2 = short2_T1 + long2_T1 - net2

    payoff_total = payoff1 + payoff2

    return pd.DataFrame({"S": S, "payoff": payoff_total})


def dashboard_app_calendar():
    st.title("📆 Estrategias laterales: Calendar & Double Diagonal")

    # Por si quieres usar los tickers del SP500
    df_sp500 = scrape_series_data(verbose=False)
    Empresas = df_sp500['Company'].tolist()
    TICKERS = df_sp500['Symbol'].tolist()

    col1, col2 = st.columns(2)

    with col1:
        symbol_cal = st.text_input(
            "Símbolo",
            value="AAPL",
            key="symbol_calendar"
        )

    with col2:
        max_intentos_call = st.number_input(
            "Máx. intentos descarga",
            min_value=1, max_value=20, value=5,
            key="max_intentos_call"
        )

    st.markdown("---")

    if "mostrar_resumen" not in st.session_state:
        st.session_state.mostrar_resumen = False

    if not st.session_state.mostrar_resumen:

        if st.button(
            "📊 Mostrar resumen del universo vs S&P 500",
            key="btn_mostrar_resumen"
        ):
            st.session_state.mostrar_resumen = True
        
        if st.session_state.get("mostrar_texto_global", True):
            st.info(
                "Vista del **universo de mercados, índices y ETFs** con sus **tickers y opciones disponibles**, "
                "junto a las **acciones del S&P 500** y sus **símbolos correspondientes**."
            )

    else:
        dashboard_universe_vs_sp500()


    st.markdown("---")

    if not symbol_cal:
        return

    try:
        lista_fechas = fechas_unix(symbol_cal)

        if lista_fechas is None or len(lista_fechas) == 0:
            if st.session_state.get("mostrar_texto_global", True):
                st.error("No se han encontrado vencimientos para este símbolo.")
            return

        lista_fechas = sorted(lista_fechas, key=lambda x: x["timestamp"])

        opciones_fechas = [item["date"] for item in lista_fechas]
        fechas_dict = {item["date"]: item for item in lista_fechas}

        if len(opciones_fechas) < 2:
            if st.session_state.get("mostrar_texto_global", True):
                st.error("Se necesitan al menos 2 vencimientos para calendar/double diagonal.")
            return

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_corta = st.selectbox(
                "Vencimiento corto (short leg)",
                opciones_fechas,
                index=0,
                key="fecha_corta_calendar"
            )
        with col_f2:
            fecha_larga = st.selectbox(
                "Vencimiento largo (long leg)",
                opciones_fechas,
                index=1,
                key="fecha_larga_calendar"
            )

        item_corto = fechas_dict[fecha_corta]
        item_largo = fechas_dict[fecha_larga]

    except Exception as e:
        if st.session_state.get("mostrar_texto_global", True):
            st.error(f"Error obteniendo fechas de vencimiento (calendar): {e}")
        return

    st.markdown("---")

    if st.button("📥 Descargar CALLS para estos vencimientos", key="btn_descargar_calls_calendar"):

        if item_largo["timestamp"] <= item_corto["timestamp"]:
            if st.session_state.get("mostrar_texto_global", True):
                st.error("El vencimiento largo debe ser posterior al corto.")
            return

        with st.spinner("Descargando opciones CALL (corto y largo plazo)..."):
            calls_short = load_calls_for_expiration(
                symbol_cal,
                item_corto["timestamp"],
                max_intentos=max_intentos_call
            )
            calls_long = load_calls_for_expiration(
                symbol_cal,
                item_largo["timestamp"],
                max_intentos=max_intentos_call
            )

        if calls_short is None or calls_short.empty:
            if st.session_state.get("mostrar_texto_global", True):
                st.error("No se pudieron descargar CALLS para el vencimiento corto.")
            return
        if calls_long is None or calls_long.empty:
            if st.session_state.get("mostrar_texto_global", True):
                st.error("No se pudieron descargar CALLS para el vencimiento largo.")
            return

        if st.session_state.get("mostrar_texto_global", True):
            st.success("Datos de CALLs descargados correctamente.")
        
        st.subheader("Vista previa de CALLs (corto plazo)")
        st.dataframe(calls_short.head())
        st.subheader("Vista previa de CALLs (largo plazo)")
        st.dataframe(calls_long.head())

        spot = get_current_price(symbol_cal)
        if st.session_state.get("mostrar_texto_global", True):
            st.info(f"Precio actual de {symbol_cal}: {spot:.2f} $")

        try:
            row_ATM_short = choose_atm_strike(calls_short, spot=spot)
            K_ATM = row_ATM_short["Precio de ejercicio"]
            row_ATM_long = match_strike_row(calls_long, K_ATM)

            row_K1_c, row_K2_c, row_K3_c, row_K4_c = choose_condor_strikes_calls(calls_long, spot)

            row_K1_short, row_K2_short = choose_symmetric_strikes(calls_short, spot=spot)
            K1 = row_K1_short["Precio de ejercicio"]
            K2 = row_K2_short["Precio de ejercicio"]

            row_K1_long = match_strike_row(calls_long, K1)
            row_K2_long = match_strike_row(calls_long, K2)

        except Exception as e:
            st.error(f"Error al seleccionar strikes para estrategias laterales: {e}")
            return

        seconds_year = 365 * 24 * 60 * 60
        delta_seconds = item_largo["timestamp"] - item_corto["timestamp"]
        tau_remain = max(delta_seconds / seconds_year, 1e-6)

        st.markdown("### Strikes seleccionados")

        colA, colB, colC = st.columns(3)

        with colA:
            st.write("**Calendar ATM (K)**")
            st.write(pd.DataFrame(
                [row_ATM_short, row_ATM_long],
                index=["Short (corto plazo)", "Long (largo plazo)"]
            )[["Precio de ejercicio", "Último precio", "Volatilidad implícita"]])

        with colB:
            st.write("**Double Diagonal (K1 / K2)**")
            st.write(pd.DataFrame(
                [row_K1_short, row_K1_long, row_K2_short, row_K2_long],
                index=["K1 short", "K1 long", "K2 short", "K2 long"]
            )[["Precio de ejercicio", "Último precio", "Volatilidad implícita"]])

        with colC:
            st.write("**Condor (CALLs/PUTs)**")
            st.write(pd.DataFrame(
                [row_K1_c, row_K2_c, row_K3_c, row_K4_c,],
                index=["Condor K1", "Condor K2", "Condor K3", "Condor K4"]
            )[["Precio de ejercicio", "Último precio", "Volatilidad implícita"]])

        st.markdown("---")

        st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(1) {
            color: #00CC44 !important;  /* verde */
        }
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(2) {
            color: #FFD700 !important;  /* amarillo */
        }
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(3) {
            color: #FF0000 !important;  /* rojo */
        }
        </style>
        """, unsafe_allow_html=True)

        tabcal_1, tabcal_2, tabcal_3 = st.tabs([
            "Long Calendar Spread",
            "Long Condor (solo buy)",
            "Double Diagonal (solo buy)"
        ])

        with tabcal_1:
            st.subheader("Long Calendar Spread (CALLs)")
            df_calendar = payoff_long_calendar_from_rows(
                row_ATM_short, row_ATM_long,
                tau_remain=tau_remain,
                ticker=symbol_cal
            )
            fig1 = plot_payoff(df_calendar, "Long Calendar Spread (CALLs)", ticker=symbol_cal)
            st.plotly_chart(fig1, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es un Long Calendar Spread (CALL)?

                Consiste en:
                - **Comprar** una CALL con vencimiento lejano.  
                - **Vender** una CALL con vencimiento cercano.  
                - Ambas con **el mismo strike**.

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Valor temporal** | La opción corta pierde valor más rápido → beneficio potencial. |
                | **Volatilidad** | Un aumento de la IV favorece a la opción larga. |
                | **Movimiento del precio** | Mejor resultado cuando el subyacente se mantiene alrededor del strike. |

                #### 🧨 ¿Riesgos?
                - El beneficio está limitado.
                - La pérdida máxima es la prima neta pagada.
                - Si el precio se mueve fuerte lejos del strike, la estrategia pierde valor.

                Es una estrategia popular cuando se espera **movimiento moderado** o **aumento de volatilidad**.
                """)

        with tabcal_2:
            st.subheader("Long Condor (solo buy, CALLs)")
            df_condor = payoff_long_condor_from_rows(
                row_K1_c, row_K2_c, row_K3_c, row_K4_c, ticker=symbol_cal
            )
            fig3 = plot_payoff(df_condor, "Long Condor (solo buy)", ticker=symbol_cal)
            st.plotly_chart(fig3, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es un Long Condor (solo buy, CALLs)?

                El **Long Condor** con CALLs utiliza cuatro strikes:
                - Comprar 1 CALL de strike bajo (K1).
                - Vender 1 CALL de strike intermedio (K2).
                - Vender 1 CALL de otro strike intermedio (K3).
                - Comprar 1 CALL de strike alto (K4).

                (La versión *solo buy* que representas está estructurada para que el coste y el payoff queden acotados.)

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Beneficio en un rango intermedio** | Máximo beneficio si el subyacente termina entre los strikes centrales. |
                | **Riesgo y beneficio acotados** | Pérdida máxima y ganancia máxima conocidas desde el inicio. |
                | **Perfil más ancho que la butterfly** | El rango de beneficios puede ser más amplio que en una mariposa estándar. |

                #### 🧨 ¿Riesgos?
                - Si el precio termina muy por debajo de K1 o muy por encima de K4, se acerca a la pérdida máxima. |
                - Beneficio máximo limitado, incluso si el subyacente se mueve “demasiado bien”. |
                - La elección de strikes es crucial: mala elección → rango útil muy estrecho.

                Se utiliza cuando se espera que el precio termine en una **franja concreta**, con algo más de margen que en una butterfly clásica.
                """)

        with tabcal_3:
            st.subheader("Double Diagonal (aprox. double calendar)")
            df_dd = payoff_double_diagonal_from_rows(
                row_K1_short, row_K1_long,
                row_K2_short, row_K2_long,
                tau_remain=tau_remain,
                ticker=symbol_cal
            )
            fig2 = plot_payoff(df_dd, "Double Diagonal (solo buy)", ticker=symbol_cal)
            st.plotly_chart(fig2, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es una Double Diagonal?

                Es una extensión del calendar/diagonal spread:
                - Se combinan **dos spreads diagonales** (uno OTM por arriba y otro OTM por abajo).
                - Se usan **distintos strikes** y **distintos vencimientos**, tanto para las opciones largas como para las cortas.

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Rango de beneficio** | Generar una “zona” de beneficio alrededor del precio actual. |
                | **Ingreso por valor temporal** | Las opciones cortas pierden valor más rápido. |
                | **Aprovechar la volatilidad** | Un aumento de IV en las opciones largas puede mejorar el payoff. |

                #### 🧨 ¿Riesgos?
                - Estructura más compleja que un calendar simple.
                - Beneficio limitado y pérdidas acotadas, pero pueden ser mayores que en un solo calendar.
                - Sensible tanto al movimiento del subyacente como a cambios en la volatilidad y el paso del tiempo.

                Suele utilizarse cuando se espera que el precio permanezca en un **rango** razonable, pero con cierta asimetría o sesgo.
                """)
    else:
        if st.session_state.get("mostrar_texto_global", True):
            st.info("Pulsa el botón para descargar las CALLS y ver los payoffs.")

if __name__ == "__main__":
    dashboard_app_calendar()
