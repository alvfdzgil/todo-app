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
def choose_ladder_call_rows(df_calls, spot):
    """
    Elige las ROWS para una CALL LADDER (solo buy):

    Estructura (típica):
    - row_K:  Call ATM (base, comprada)
    - row_K1: mejor Call OTM (primera ala)
    - row_K2: Call OTM más lejana (segunda ala), con strike:
              K2_target = K1 + (K1 - K)
    """
    row_K = choose_atm_strike(df_calls, spot)
    K = row_K["Precio de ejercicio"]

    row_K1 = best_otm_call(df_calls, spot)
    K1 = row_K1["Precio de ejercicio"]

    df = df_calls.copy().sort_values("Precio de ejercicio").reset_index(drop=True)

    K2_target = K1 + (K1 - K)

    df_aux = df[df["Precio de ejercicio"] > K1].copy()
    if df_aux.empty:
        df_aux = df.copy()

    df_aux["diff"] = (df_aux["Precio de ejercicio"] - K2_target).abs()
    idx2 = df_aux["diff"].idxmin()
    row_K2 = df_aux.loc[idx2]
    row_K2 = row_K2.drop(labels=["diff"], errors="ignore")

    return row_K2


def payoff_long_call_otm_from_row(row_otm, ticker="AAPL",
                                  n=400, factor_min=0.9, factor_max=1.3):
    K = row_otm["Precio de ejercicio"]
    p = row_otm["Último precio"]
    precio_actual = get_current_price(ticker)
    S = make_price_grid(precio_actual, factor_min, factor_max, n)
    payoff = payoff_call_long(S, K, p)
    return pd.DataFrame({"S": S, "payoff": payoff})


def payoff_long_call_atm_from_row(row_atm, ticker="AAPL",
                                  n=400, factor_min=0.8, factor_max=1.2):
    K = row_atm["Precio de ejercicio"]
    p = row_atm["Último precio"]
    precio_actual = get_current_price(ticker)
    S = make_price_grid(precio_actual, factor_min, factor_max, n)
    payoff = payoff_call_long(S, K, p)
    return pd.DataFrame({"S": S, "payoff": payoff})


def payoff_call_ladder_from_rows(row_K, row_K1, row_K2, ticker="AAPL",
                                 factor_min=0.9, factor_max=1.3, n=400):
    """
    Estructura: CALL LADDER (solo buy, neto en débito)
    +1 Call K   (strike base, ATM)
    -1 Call K1  (strike OTM intermedio)
    +1 Call K2  (strike OTM más lejana)
    """
    K,  p  = row_K["Precio de ejercicio"],  row_K["Último precio"]
    K1, p1 = row_K1["Precio de ejercicio"], row_K1["Último precio"]
    K2, p2 = row_K2["Precio de ejercicio"], row_K2["Último precio"]

    assert K < K1 < K2, "Para la ladder se requiere K < K1 < K2"

    precio_actual = get_current_price(ticker)
    S = make_price_grid(precio_actual, factor_min, factor_max, n)

    P_long_K  = payoff_call_long(S, K,  p)   # +1 Call K
    P_long_K2 = payoff_call_long(S, K2, p2)  # +1 Call K2

    P_short_K1 = payoff_call_long(S, K1, p1)  
    payoff_total = P_long_K - P_short_K1 + P_long_K2

    return pd.DataFrame({"S": S, "payoff": payoff_total})


def payoff_call_butterfly_from_rows(row_K1, row_K2, row_K3, ticker="AAPL",
                                    factor_min=0.8, factor_max=1.2, n=400):
    """
    Estructura: mariposa LONG de calls
    +1 Call K1   (strike bajo)
    -2 Call K2   (strike medio)
    +1 Call K3   (strike alto)
    """
    K1, p1 = row_K1["Precio de ejercicio"], row_K1["Último precio"]
    K2, p2 = row_K2["Precio de ejercicio"], row_K2["Último precio"]
    K3, p3 = row_K3["Precio de ejercicio"], row_K3["Último precio"]

    assert K1 < K2 < K3, "Para la mariposa se requiere K1 < K2 < K3"

    precio_actual = get_current_price(ticker)
    S = make_price_grid(precio_actual, factor_min, factor_max, n)

    P1_long = payoff_call_long(S, K1, p1)   # +1 Call K1
    P2_long = payoff_call_long(S, K2, p2)   # +1 Call K2
    P3_long = payoff_call_long(S, K3, p3)   # +1 Call K3

    payoff_total = P1_long - 2 * P2_long + P3_long

    return pd.DataFrame({"S": S, "payoff": payoff_total})


def payoff_long_call_itm_from_row(row_itm, ticker="AAPL",
                                  n=400, factor_min=0.7, factor_max=1.1):
    K = row_itm["Precio de ejercicio"]
    p = row_itm["Último precio"]
    precio_actual = get_current_price(ticker)
    S = make_price_grid(precio_actual, factor_min, factor_max, n)
    payoff = payoff_call_long(S, K, p)
    return pd.DataFrame({"S": S, "payoff": payoff})


def payoff_call_backspread_from_rows(row_ATM, row_OTM,
                                     ticker="AAPL",
                                     factor_min=0.85, factor_max=1.25, n=400):
    """
    Backspread de CALLS estándar (ratio spread alcista):
        -1 Call ATM
        +2 Calls OTM
    """
    K_atm, p_atm = row_ATM["Precio de ejercicio"], row_ATM["Último precio"]
    K_otm, p_otm = row_OTM["Precio de ejercicio"], row_OTM["Último precio"]

    assert K_atm < K_otm, "Para un backspread: K_ATM < K_OTM"

    precio_actual = get_current_price(ticker)
    S = make_price_grid(precio_actual, factor_min, factor_max, n)

    P_atm = payoff_call_long(S, K_atm, p_atm)
    P_otm = payoff_call_long(S, K_otm, p_otm)

    payoff_total = -P_atm + 2 * P_otm

    return pd.DataFrame({"S": S, "payoff": payoff_total})


def dashboard_app_call():

    st.title("📈 Payoffs de estrategias con opciones CALL")

    df_sp500 = scrape_series_data()
    Empresas = df_sp500['Company'].tolist()
    TICKERS = df_sp500['Symbol'].tolist()

    # --- Inputs básicos ---
    col1, col2 = st.columns(2)

    with col1:
        symbol_call = st.text_input(
            "Símbolo",
            value="AAPL",
            key="symbol_call"
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

    if symbol_call:
        try:
            lista_fechas = fechas_unix(symbol_call)
            if not lista_fechas:
                if st.session_state.get("mostrar_texto_global", True):
                    st.error("No se han encontrado vencimientos para este símbolo.")
                return

            opciones_fechas = [item["date"] for item in lista_fechas]
            fechas_dict = {item["date"]: item for item in lista_fechas}
            fecha_sel_call = st.selectbox("Fecha de vencimiento", opciones_fechas, key="fecha_sel_call")
            item_sel_call = fechas_dict[fecha_sel_call]

        except Exception as e:
            if st.session_state.get("mostrar_texto_global", True):
                st.error(f"Error obteniendo fechas de vencimiento: {e}")
            return
    else:
        return

    st.markdown("---")

    # --- Botón para descargar datos de opciones ---
    if st.button("📥 Descargar CALLS para esta fecha", key="btn_descargar_call"):
        with st.spinner("Descargando opciones CALL..."):
            calls_df = load_calls_for_expiration(
                symbol_call,
                item_sel_call["timestamp"],
                max_intentos=max_intentos_call
            )

        if calls_df is None or calls_df.empty:
            if st.session_state.get("mostrar_texto_global", True):
                st.error("No se pudieron descargar opciones CALL para este símbolo/fecha.")
            return
        else:
            if st.session_state.get("mostrar_texto_global", True):
                st.success("Datos de CALLs descargados correctamente.")

            st.subheader("Vista previa de CALLs")
            st.dataframe(calls_df.head())

            # ==============================
            # Cálculo de estrategias
            # ==============================

            spot = get_current_price(symbol_call)
            if st.session_state.get("mostrar_texto_global", True):
                st.info(f"Precio actual de {symbol_call}: {spot:.2f} $")

            try:
                row_ATM_call = choose_atm_strike(calls_df, spot=spot)
                row_OTM_call = best_otm_call(calls_df, spot=spot)
                row_ITM_call = choose_butterfly_call_rows(calls_df, spot=spot)
                row_OTM2_call = choose_ladder_call_rows(calls_df, spot=spot)
            except Exception as e:
                if st.session_state.get("mostrar_texto_global", True):
                    st.error(f"Error al seleccionar strikes para estrategias: {e}")
                return

            # Mostrar strikes elegidos
            st.markdown("### Strikes seleccionados")
            colA, colB, colC = st.columns(3)
            with colA:
                st.write("**ATM (K_ATM)**")
                st.write(row_ATM_call[["Precio de ejercicio", "Último precio", "Volatilidad implícita"]])
            with colB:
                st.write("**OTM (K_OTM)**")
                st.write(row_OTM_call[["Precio de ejercicio", "Último precio", "Volatilidad implícita"]])
            with colC:
                st.write("**Butterfly K1 / K2 / K3**")
                st.write(pd.DataFrame(
                    [row_ITM_call, row_ATM_call, row_OTM_call],
                    index=["K1", "K2 (ATM)", "K3 (OTM)"]
                )[["Precio de ejercicio", "Último precio", "Volatilidad implícita"]])

            st.markdown("---")

            # ==============================
            # Payoffs y gráficos en pestañas
            # ==============================

            st.markdown("""
            <style>
            /* 1º tab → VERDE */
            .stTabs [data-baseweb="tab-list"] button:nth-of-type(1) {
                color: #00CC44 !important;
            }

            /* 2º, 3º y 4º → AMARILLO */
            .stTabs [data-baseweb="tab-list"] button:nth-of-type(2),
            .stTabs [data-baseweb="tab-list"] button:nth-of-type(3),
            .stTabs [data-baseweb="tab-list"] button:nth-of-type(4) {
                color: #FFD700 !important;
            }

            /* 5º y 6º → ROJO */
            .stTabs [data-baseweb="tab-list"] button:nth-of-type(5),
            .stTabs [data-baseweb="tab-list"] button:nth-of-type(6) {
                color: #FF0000 !important;
            }
            </style>
            """, unsafe_allow_html=True)

            tabcall_1, tabcall_2, tabcall_3, tabcall_4, tabcall_5, tabcall_6 = st.tabs(
                ["Long Call OTM",
                 "Long Call ATM",
                 "Call Ladder",
                 "Call Butterfly",
                 "Long Call ITM",
                 "Call Ratio Backspread"]
            )

            with tabcall_1:
                st.subheader("Long Call OTM")
                df_long_otm = payoff_long_call_otm_from_row(row_OTM_call, ticker=symbol_call)
                fig1 = plot_payoff(df_long_otm, "Long Call OTM", ticker=symbol_call)
                st.plotly_chart(fig1, width='stretch')
                if st.session_state.get("mostrar_estrategias_global", True):
                    st.markdown("""
                    ### 📘 ¿Qué es una Long Call OTM?

                    Una **CALL OTM (out of the money)** tiene el strike por encima del precio actual del subyacente.
                    - Se **compra** una CALL OTM.
                    - Es la forma más apalancada de apostar por una subida fuerte del precio.
                    - Prima relativamente baja, pero menor probabilidad de terminar ITM.

                    #### 🎯 ¿Qué busca esta estrategia?
                    | Aspecto | Explicación |
                    |---------|------------|
                    | **Aprovechar grandes subidas** | Beneficio potencial alto si el subyacente sube fuerte. |
                    | **Coste bajo** | La prima es más barata que en ATM/ITM. |
                    | **Apalancamiento** | Pequeños cambios relativos en el precio pueden generar grandes variaciones porcentuales en la prima. |

                    #### 🧨 ¿Riesgos?
                    - Alta probabilidad de que la opción expire sin valor.
                    - Si el movimiento alcista es moderado o lento, puede no compensar la pérdida de valor temporal.
                    - Pérdida máxima igual a la prima pagada.

                    Es una estrategia típica cuando se espera un **movimiento alcista explosivo** en poco tiempo.
                    """)

            with tabcall_2:
                st.subheader("Long Call ATM")
                df_long_atm = payoff_long_call_atm_from_row(row_ATM_call, ticker=symbol_call)
                fig2 = plot_payoff(df_long_atm, "Long Call ATM", ticker=symbol_call)
                st.plotly_chart(fig2, width='stretch')
                if st.session_state.get("mostrar_estrategias_global", True):
                    st.markdown("""
                    ### 📘 ¿Qué es una Long Call ATM?

                    Una **CALL ATM (at the money)** tiene el strike aproximadamente igual al precio actual del subyacente.
                    - Se **compra** una CALL ATM.
                    - Es un compromiso entre coste, probabilidad de terminar ITM y sensibilidad (delta) al movimiento del subyacente.

                    #### 🎯 ¿Qué busca esta estrategia?
                    | Aspecto | Explicación |
                    |---------|------------|
                    | **Apuesta alcista directa** | Beneficia de subidas del subyacente con un perfil sencillo. |
                    | **Buen equilibrio delta/vega** | La prima no es tan alta como en ITM, pero la opción es bastante sensible al precio. |
                    | **Estructura simple** | Fácil de entender y gestionar. |

                    #### 🧨 ¿Riesgos?
                    - Si el precio no sube lo suficiente dentro del plazo, la opción pierde valor temporal.
                    - La pérdida máxima es la prima pagada, que suele ser mayor que en una OTM.
                    - Sensible a caídas de volatilidad implícita.

                    Es una de las formas más comunes de posicionarse **alcista** con riesgo limitado.
                    """)

            with tabcall_3:
                st.subheader("Call Ladder")
                df_ladder = payoff_call_ladder_from_rows(
                    row_ATM_call, row_OTM_call, row_OTM2_call,
                    ticker=symbol_call
                )
                fig3 = plot_payoff(df_ladder, "Call Ladder", ticker=symbol_call)
                st.plotly_chart(fig3, width='stretch')
                if st.session_state.get("mostrar_estrategias_global", True):
                    st.markdown("""
                    ### 📘 ¿Qué es una Call Ladder?

                    La **Call Ladder** es una combinación de varias CALLs con distintos strikes:
                    - Suele implicar comprar y/o vender CALLs ITM/ATM/OTM.
                    - Busca moldear el payoff para beneficiarse más de ciertos rangos de precio.

                    *(La implementación concreta puede variar, pero la idea general es “escalar” el payoff con varios strikes.)*

                    #### 🎯 ¿Qué busca esta estrategia?
                    | Aspecto | Explicación |
                    |---------|------------|
                    | **Perfil de beneficio escalonado** | Permite ganar más en ciertas zonas de precio y limitar otras. |
                    | **Gestión de coste** | Se puede reducir la prima neta vendiendo algunas CALLs. |
                    | **Flexibilidad** | Muy configurable según la visión del trader. |

                    #### 🧨 ¿Riesgos?
                    - La estructura es más compleja que una simple long call.
                    - Puede haber rangos de precios donde el payoff sea peor que una estrategia más sencilla.
                    - Requiere entender bien el efecto de cada strike en el perfil final.

                    Es útil cuando se tiene una visión **matizada** del posible movimiento del subyacente.
                    """)

            with tabcall_4:
                st.subheader("Call Butterfly (buy-only)")
                df_butterfly = payoff_call_butterfly_from_rows(
                    row_ITM_call, row_ATM_call, row_OTM_call,
                    ticker=symbol_call
                )
                fig4 = plot_payoff(df_butterfly, "Call Butterfly (buy-only)", ticker=symbol_call)
                st.plotly_chart(fig4, width='stretch')   
                if st.session_state.get("mostrar_estrategias_global", True):         
                    st.markdown("""
                    ### 📘 ¿Qué es una Call Butterfly (buy-only)?

                    La **Call Butterfly** (comprada) combina tres strikes:
                    - Comprar 1 CALL ITM.
                    - Vender 2 CALLs ATM.
                    - Comprar 1 CALL OTM.

                    El resultado es un payoff con forma de “mariposa”.

                    #### 🎯 ¿Qué busca esta estrategia?
                    | Aspecto | Explicación |
                    |---------|------------|
                    | **Rango de beneficio definido** | Máximo beneficio alrededor del strike central. |
                    | **Coste relativamente bajo** | Más barata que una simple long call ITM+OTM sin ventas. |
                    | **Apuesta de baja volatilidad** | Ideal cuando se espera que el precio termine cerca del strike central. |

                    #### 🧨 ¿Riesgos?
                    - Si el subyacente se mueve mucho (muy arriba o muy abajo), el beneficio se reduce o desaparece.
                    - Beneficio máximo limitado.
                    - Sensible a la relación entre tiempo a vencimiento y volatilidad.

                    Es una estrategia típica cuando se espera un **rango estrecho** de precios al vencimiento.
                    """)

            with tabcall_5:
                st.subheader("Long Call ITM")
                df_long_itm = payoff_long_call_itm_from_row(row_ITM_call, ticker=symbol_call)
                fig5 = plot_payoff(df_long_itm, "Long Call ITM", ticker=symbol_call)
                st.plotly_chart(fig5, width='stretch')
                if st.session_state.get("mostrar_estrategias_global", True):
                    st.markdown("""
                    ### 📘 ¿Qué es una Long Call ITM?

                    Una **CALL ITM (in the money)** tiene strike por debajo del precio actual del subyacente.
                    - Se **compra** una CALL ITM.
                    - Se comporta más parecido a la propia acción (delta alta).
                    - Gran parte de la prima es valor intrínseco, no solo valor temporal.

                    #### 🎯 ¿Qué busca esta estrategia?
                    | Aspecto | Explicación |
                    |---------|------------|
                    | **Exposición alcista “segura”** | Mayor probabilidad de tener valor intrínseco en vencimiento. |
                    | **Menos dependencia de la volatilidad** | El componente intrínseco domina sobre el temporal. |
                    | **Alternativa a comprar la acción** | Con menor desembolso inicial. |

                    #### 🧨 ¿Riesgos?
                    - Prima más alta que en ATM/OTM.
                    - Pérdida máxima sigue siendo la prima, pero es una cantidad mayor de capital.
                    - Si el precio cae, se pierde valor rápidamente.

                    Es una forma de tomar una posición **alcista fuerte**, pero con riesgo acotado.
                    """)

            with tabcall_6:
                st.subheader("Call Ratio Backspread (buy-only)")
                df_backspread = payoff_call_backspread_from_rows(
                    row_ATM_call, row_OTM_call,
                    ticker=symbol_call
                )
                fig6 = plot_payoff(df_backspread, "Call Ratio Backspread (buy-only)", ticker=symbol_call)
                st.plotly_chart(fig6, width='stretch')
                if st.session_state.get("mostrar_estrategias_global", True):
                    st.markdown("""
                    ### 📘 ¿Qué es un Call Ratio Backspread (buy-only)?

                    El **Call Ratio Backspread** (comprado) suele construirse:
                    - Vendiendo 1 CALL más cercana al dinero (ATM o ligeramente ITM).
                    - Comprando 2 (o más) CALLs OTM.

                    Normalmente con la misma fecha de vencimiento.

                    #### 🎯 ¿Qué busca esta estrategia?
                    | Aspecto | Explicación |
                    |---------|------------|
                    | **Beneficio grande en subidas fuertes** | Ganancias crecientes si el subyacente se dispara al alza. |
                    | **Riesgo acotado por debajo** | Según la estructura, la pérdida está limitada a cierto rango de precios. |
                    | **Explotar volatilidad** | Favorecida por subidas de volatilidad y movimientos bruscos. |

                    #### 🧨 ¿Riesgos?
                    - Puede haber un rango intermedio de precios donde la posición pierda dinero.
                    - Estructura más compleja, difícil de gestionar sin entender bien el payoff.
                    - Sensible a la elección de strikes y ratios (número de opciones compradas vs vendidas).

                    Se usa cuando se espera un **gran movimiento alcista** (o fuerte aumento de volatilidad) y se acepta un riesgo limitado en escenarios moderados.
                    """)

    else:
        if st.session_state.get("mostrar_texto_global", True):
            st.info("Pulsa el botón para descargar las opciones y ver los payoffs.")


# Opcional: para probar este archivo directamente
if __name__ == "__main__":
    dashboard_app_call()
