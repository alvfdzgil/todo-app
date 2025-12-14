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
def choose_put_ladder_rows(df_puts, spot):
    """
    Elige las ROWS para una PUT LADDER (solo buy):

    +1 Put K   (ATM)
    -1 Put K1  (OTM intermedia, más baja que K)
    +1 Put K2  (OTM más lejana, aún más baja)
    """
    row_K = choose_atm_strike(df_puts, spot)
    K = row_K["Precio de ejercicio"]

    row_K1 = best_otm_put(df_puts, spot)
    K1 = row_K1["Precio de ejercicio"]

    df = df_puts.copy().sort_values("Precio de ejercicio").reset_index(drop=True)

    #    K2_target = K1 - (K - K1) = 2*K1 - K
    K2_target = K1 - (K - K1)

    df_aux = df[df["Precio de ejercicio"] < K1].copy()
    if df_aux.empty:
        df_aux = df.copy()

    df_aux["diff"] = (df_aux["Precio de ejercicio"] - K2_target).abs()
    idx2 = df_aux["diff"].idxmin()
    row_K2 = df_aux.loc[idx2]

    row_K2 = row_K2.drop(labels=["diff"], errors="ignore")

    return row_K2


def payoff_long_put_otm_from_row(row_otm,
                                 factor_min=0.7, factor_max=1.1,
                                 n=400,
                                 ticker="AAPL"):
    K = row_otm["Precio de ejercicio"]
    p = row_otm["Último precio"]
    precio_actual = get_current_price(ticker)

    S = make_price_grid(precio_actual, factor_min, factor_max, n)
    payoff = payoff_put_long(S, K, p)
    return pd.DataFrame({"S": S, "payoff": payoff})


def payoff_long_put_atm_from_row(row_atm,
                                 factor_min=0.8, factor_max=1.2,
                                 n=400,
                                 ticker="AAPL"):
    K = row_atm["Precio de ejercicio"]
    p = row_atm["Último precio"]
    precio_actual = get_current_price(ticker)

    S = make_price_grid(precio_actual, factor_min, factor_max, n)
    payoff = payoff_put_long(S, K, p)
    return pd.DataFrame({"S": S, "payoff": payoff})


def payoff_put_ladder_from_rows(row_K, row_K1, row_K2, ticker="AAPL",
                                factor_min=0.7, factor_max=1.1, n=400):
    """
    PUT LADDER (solo buy, neto en débito)
    +1 Put K   (ATM)
    -1 Put K1  (OTM intermedia, más baja que K)
    +1 Put K2  (OTM más lejana, aún más baja)
    """
    K,  p  = row_K["Precio de ejercicio"],  row_K["Último precio"]
    K1, p1 = row_K1["Precio de ejercicio"], row_K1["Último precio"]
    K2, p2 = row_K2["Precio de ejercicio"], row_K2["Último precio"]

    # Para put ladder bajista: K2 < K1 < K
    assert K2 < K1 < K, "Para la PUT LADDER se requiere K2 < K1 < K"

    precio_actual = get_current_price(ticker)
    S = make_price_grid(precio_actual, factor_min, factor_max, n)

    P_long_K  = payoff_put_long(S, K,  p)   # +1 Put K
    P_long_K2 = payoff_put_long(S, K2, p2)  # +1 Put K2

    P_short_K1 = payoff_put_long(S, K1, p1)

    payoff_total = P_long_K - P_short_K1 + P_long_K2

    return pd.DataFrame({"S": S, "payoff": payoff_total})


def payoff_put_butterfly_from_rows(row_K1, row_K2, row_K3,
                                   factor_min=0.8, factor_max=1.2,
                                   n=400,
                                   ticker="AAPL"):
    """
    Mariposa LONG de PUTS:
    +1 Put K1   (strike alto)
    -2 Put K2   (strike medio, ATM)
    +1 Put K3   (strike bajo)
    """
    K1, p1 = row_K1["Precio de ejercicio"], row_K1["Último precio"]
    K2, p2 = row_K2["Precio de ejercicio"], row_K2["Último precio"]
    K3, p3 = row_K3["Precio de ejercicio"], row_K3["Último precio"]

    # Queremos K1 > K2 > K3
    assert K1 > K2 > K3, "Para la mariposa de PUTS se requiere K1 > K2 > K3"

    precio_actual = get_current_price(ticker)
    S = make_price_grid(precio_actual, factor_min, factor_max, n)

    P1_long = payoff_put_long(S, K1, p1)   # +1 Put K1
    P2_long = payoff_put_long(S, K2, p2)   # +1 Put K2
    P3_long = payoff_put_long(S, K3, p3)   # +1 Put K3

    payoff_total = P1_long - 2 * P2_long + P3_long

    return pd.DataFrame({"S": S, "payoff": payoff_total})


def payoff_long_put_itm_from_row(row_itm,
                                 factor_min=0.9, factor_max=1.3,
                                 n=400,
                                 ticker="AAPL"):
    K = row_itm["Precio de ejercicio"]
    p = row_itm["Último precio"]
    precio_actual = get_current_price(ticker)

    S = make_price_grid(precio_actual, factor_min, factor_max, n)
    payoff = payoff_put_long(S, K, p)
    return pd.DataFrame({"S": S, "payoff": payoff})


def payoff_put_backspread_from_rows(row_ATM, row_OTM,
                                    factor_min=0.75, factor_max=1.15,
                                    n=400,
                                    ticker="AAPL"):
    """
    Backspread bajista de PUTS:
        -1 Put ATM  (strike más alto)
        +2 Put OTM  (strike más bajo)
    """
    K_atm, p_atm = row_ATM["Precio de ejercicio"], row_ATM["Último precio"]
    K_otm, p_otm = row_OTM["Precio de ejercicio"], row_OTM["Último precio"]

    assert K_atm > K_otm, "Para un backspread de PUTS: K_ATM > K_OTM"

    precio_actual = get_current_price(ticker)
    S = make_price_grid(precio_actual, factor_min, factor_max, n)

    P_atm = payoff_put_long(S, K_atm, p_atm)
    P_otm = payoff_put_long(S, K_otm, p_otm)

    payoff_total = -P_atm + 2 * P_otm

    return pd.DataFrame({"S": S, "payoff": payoff_total})


def dashboard_app_put():
    st.title("📉 Payoffs de estrategias con opciones PUT")

    df_sp500 = scrape_series_data()
    Empresas = df_sp500['Company'].iloc[1:5].tolist()
    TICKERS = df_sp500['Symbol'].iloc[1:5].tolist()

    col1, col2 = st.columns(2)

    with col1:
        symbol_put = st.text_input(
            "Símbolo",
            value="AAPL",
            key="symbol_put"
        )

    with col2:
        max_intentos_put = st.number_input(
            "Máx. intentos descarga",
            min_value=1, max_value=20, value=5,
            key="max_intentos_put"
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
    
    if not symbol_put:
        return

    try:
        lista_fechas = fechas_unix(symbol_put)
        if not lista_fechas:
            if st.session_state.get("mostrar_texto_global", True):
                st.error("No se han encontrado vencimientos para este símbolo.")
            return

        opciones_fechas = [item["date"] for item in lista_fechas]
        fechas_dict = {item["date"]: item for item in lista_fechas}
        fecha_sel_put = st.selectbox("Fecha de vencimiento", opciones_fechas, key="fecha_sel_put")
        item_sel_put = fechas_dict[fecha_sel_put]

    except Exception as e:
        if st.session_state.get("mostrar_texto_global", True):
            st.error(f"Error obteniendo fechas de vencimiento: {e}")
        return

    st.markdown("---")

    if st.button("📥 Descargar PUTS para esta fecha", key="btn_descargar_put"):
        with st.spinner("Descargando opciones PUT..."):
            puts_df = load_puts_for_expiration(
                symbol_put,
                item_sel_put["timestamp"],
                max_intentos=max_intentos_put
            )

        if puts_df is None or puts_df.empty:
            if st.session_state.get("mostrar_texto_global", True):
                st.error("No se pudieron descargar opciones PUT para este símbolo/fecha.")
            return
        
        if st.session_state.get("mostrar_texto_global", True):
            st.success("Datos de PUTs descargados correctamente.")
        st.subheader("Vista previa de PUTs")
        st.dataframe(puts_df.head())

        spot = get_current_price(symbol_put)
        if st.session_state.get("mostrar_texto_global", True):
            st.info(f"Precio actual de {symbol_put}: {spot:.2f} $")

        try:
            row_ATM_put = choose_atm_strike(puts_df, spot=spot)
            row_OTM_put = best_otm_put(puts_df, spot=spot)
            row_ITM_put = choose_butterfly_put_rows(puts_df, spot=spot)
            row_OTM2_put = choose_put_ladder_rows(puts_df, spot=spot)
        except Exception as e:
            if st.session_state.get("mostrar_texto_global", True):
                st.error(f"Error al seleccionar strikes para estrategias: {e}")
            return

        st.markdown("### Strikes seleccionados")
        colA, colB, colC = st.columns(3)
        with colA:
            st.write("**ATM (K_ATM)**")
            st.write(row_ATM_put[["Precio de ejercicio", "Último precio", "Volatilidad implícita"]])
        with colB:
            st.write("**OTM (K_OTM)**")
            st.write(row_OTM_put[["Precio de ejercicio", "Último precio", "Volatilidad implícita"]])
        with colC:
            st.write("**Butterfly K1 / K2 / K3**")
            st.write(pd.DataFrame(
                [row_ITM_put, row_ATM_put, row_OTM_put],
                index=["K1 (alto)", "K2 (ATM)", "K3 (bajo)"]
            )[["Precio de ejercicio", "Último precio", "Volatilidad implícita"]])

        st.markdown("---")

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

        tabput_1, tabput_2, tabput_3, tabput_4, tabput_5, tabput_6 = st.tabs([
            "Long Put OTM",
            "Long Put ATM",
            "Put Ladder",
            "Put Butterfly",
            "Long Put ITM",
            "Put Ratio Backspread"
        ])

        with tabput_1:
            st.subheader("Long Put OTM")
            df_long_otm = payoff_long_put_otm_from_row(row_OTM_put, ticker=symbol_put)
            fig1 = plot_payoff(df_long_otm, "Long Put OTM", ticker=symbol_put)
            st.plotly_chart(fig1, width='stretch')   
            if st.session_state.get("mostrar_estrategias_global", True):  
                st.markdown("""
                ### 📘 ¿Qué es una Long Put OTM?

                Una **PUT OTM (out of the money)** tiene el strike por debajo del precio actual del subyacente.
                - Se **compra** una PUT OTM.
                - Estrategia bajista con coste reducido.
                - Alta convexidad: muy rentable si el precio cae con fuerza.

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Aprovechar caídas bruscas** | Mucho beneficio si el precio baja de forma acelerada. |
                | **Coste bajo** | La prima es menor que en una PUT ATM o ITM. |
                | **Apalancamiento** | Movimiento pequeño en el subyacente produce grandes variaciones en la prima. |

                #### 🧨 ¿Riesgos?
                - Alta probabilidad de que expire sin valor.
                - Si la caída es moderada o lenta, la pérdida temporal domina.
                - Pérdida máxima = prima pagada.

                Útil cuando se espera un **movimiento bajista fuerte** en poco tiempo.
                """)


        with tabput_2:
            st.subheader("Long Put ATM")
            df_long_atm = payoff_long_put_atm_from_row(row_ATM_put, ticker=symbol_put)
            fig2 = plot_payoff(df_long_atm, "Long Put ATM", ticker=symbol_put)
            st.plotly_chart(fig2, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es una Long Put ATM?

                Una **PUT ATM (at the money)** tiene strike aproximadamente igual al precio actual del subyacente.
                - Se **compra** una PUT ATM.
                - Balance entre coste, probabilidad y sensibilidad a la bajada.

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Protección o apuesta bajista directa** | Perfecta para cubrir posiciones largas o especular. |
                | **Mejor sensibilidad (delta)** | Responde mejor que una PUT OTM. |
                | **Equilibrio valor temporal / valor intrínseco** | Opción más eficiente en muchos escenarios. |

                #### 🧨 ¿Riesgos?
                - Prima más alta que una OTM.
                - Sensible al paso del tiempo y caídas de volatilidad.
                - Pérdida máxima = prima pagada.

                Es la forma “estándar” de tomar una posición **bajista con riesgo limitado**.
                """)

        
        with tabput_3:
            st.subheader("Put Ladder")
            df_ladder = payoff_put_ladder_from_rows(
                row_ATM_put, row_OTM_put, row_OTM2_put, ticker=symbol_put
            )
            fig3 = plot_payoff(df_ladder, "Put Ladder", ticker=symbol_put)
            st.plotly_chart(fig3, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es una Put Ladder?

                La **Put Ladder** combina PUTs con diferentes strikes:
                - Suelo incluir compras + ventas de PUTs ITM / ATM / OTM.
                - Busca moldear un payoff bajista más sofisticado.

                *(La implementación depende de los strikes elegidos.)*

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Optimizar coste** | Se reduce prima vendiendo PUTs de otros strikes. |
                | **Beneficio escalonado** | Payoff diseñado para diferentes niveles de caída. |
                | **Flexibilidad** | Permite ajustar agresividad y riesgo. |

                #### 🧨 ¿Riesgos?
                - Payoff más complejo y con posibles zonas de pérdida.
                - Muy sensible a los niveles concretos de strikes.
                - Requiere experiencia en estructuración.

                Útil cuando se tiene una visión **bajista matizada**, no simplemente lineal.
                """)


        with tabput_4:
            st.subheader("Put Butterfly (buy-only)")
            df_butterfly = payoff_put_butterfly_from_rows(
                row_ITM_put, row_ATM_put, row_OTM_put, ticker=symbol_put
            )
            fig4 = plot_payoff(df_butterfly, "Put Butterfly (buy-only)", ticker=symbol_put)
            st.plotly_chart(fig4, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es una Put Butterfly (buy-only)?

                La **Put Butterfly** combina:
                - Comprar 1 PUT ITM  
                - Vender 2 PUT ATM  
                - Comprar 1 PUT OTM

                Genera un payoff con forma de “mariposa invertida” en términos de ganancias máximas cerca del strike central.

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Ganar si el precio termina cerca del strike central** | Beneficio máximo en rango estrecho. |
                | **Coste bajo** | Más barata que varias PUT independientes. |
                | **Riesgo acotado** | Tanto ganancia como pérdida máxima son conocidas. |

                #### 🧨 ¿Riesgos?
                - Si el subyacente cae demasiado o sube demasiado, la ganancia desaparece. |
                - Movimiento fuerte puede ser desfavorable. |
                - Depende de estructura de volatilidad. |

                Se usa cuando se espera que el precio termine en un **rango concreto** de forma relativamente controlada.
                """)

        with tabput_5:
            st.subheader("Long Put ITM")
            df_long_itm = payoff_long_put_itm_from_row(row_ITM_put, ticker=symbol_put)
            fig5 = plot_payoff(df_long_itm, "Long Put ITM", ticker=symbol_put)
            st.plotly_chart(fig5, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es una Long Put ITM?

                Una **PUT ITM (in the money)** tiene strike mayor que el precio actual.
                - Se comporta casi como un futuro corto.
                - Alta sensibilidad a la caída del subyacente (delta alta).

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Protección seria** | Muy usada como hedge de carteras largas. |
                | **Mayor probabilidad de terminar ITM** | Más valor intrínseco desde el inicio. |
                | **Menor dependencia de volatilidad** | Vega más baja que en ATM/OTM. |

                #### 🧨 ¿Riesgos?
                - Prima cara (mucho valor intrínseco). |
                - Si la caída no ocurre, se pierde capital rápidamente. |
                - Resultado menos explosivo que OTM ante caídas extremas. |

                Ideal cuando se espera una **caída alta o moderada con probabilidad elevada**.
                """)

        with tabput_6:
            st.subheader("Put Ratio Backspread (buy-only)")
            df_backspread = payoff_put_backspread_from_rows(row_ATM_put, row_OTM_put, ticker=symbol_put)
            fig6 = plot_payoff(df_backspread, "Put Ratio Backspread (buy-only)", ticker=symbol_put)
            st.plotly_chart(fig6, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es un Put Ratio Backspread (buy-only)?

                El Put Ratio Backspread suele construirse:
                - Vendiendo 1 PUT ATM  
                - Comprando 2 (o más) PUTs OTM  

                Apuesta bajista agresiva con pérdidas acotadas arriba y gran potencial abajo.

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Ganar mucho en caídas fuertes** | Gran convexidad cuando el precio perfora strikes inferiores. |
                | **Riesgo limitado por encima del strike vendido** | Pérdida máxima acotada. |
                | **Exposición positiva a vega** | Se beneficia de subidas de volatilidad. |

                #### 🧨 ¿Riesgos?
                - Puede haber rango intermedio donde la estrategia pierda. |
                - Complejidad elevada para principiantes. |
                - Sensible a volatilidad y tiempo al vencimiento. |

                Es típica cuando se anticipa un **movimiento bajista violento**, pero se quiere riesgo limitado.
                """)

    else:
        if st.session_state.get("mostrar_texto_global", True):
            st.info("Pulsa el botón para descargar las PUTS y ver los payoffs.")

if __name__ == "__main__":
    dashboard_app_put()
