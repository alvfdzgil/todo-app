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
def match_strike_row(df, K):
    """
    Devuelve la fila de df con strike más cercano a K.
    """
    df = df.copy().sort_values("Precio de ejercicio").reset_index(drop=True)
    df["diff"] = (df["Precio de ejercicio"] - K).abs()
    idx = df["diff"].idxmin()
    return df.loc[idx]


def payoff_long_strangle_from_rows(row_call_otm, row_put_otm,
                                   factor_min=0.8, factor_max=1.2,
                                   n=4000,
                                   ticker="AAPL"):
    Kc, pc = row_call_otm["Precio de ejercicio"], row_call_otm["Último precio"]
    Kp, pp = row_put_otm["Precio de ejercicio"], row_put_otm["Último precio"]

    spot = get_current_price(ticker)
    center = spot
    S = make_price_grid(center, factor_min, factor_max, n)

    payoff_total = payoff_call_long(S, Kc, pc) + payoff_put_long(S, Kp, pp)
    return pd.DataFrame({"S": S, "payoff": payoff_total})


def payoff_long_guts_from_rows(row_call_itm, row_put_itm,
                               factor_min=0.8, factor_max=1.2,
                               n=4000,
                               ticker="AAPL"):
    Kc, pc = row_call_itm["Precio de ejercicio"], row_call_itm["Último precio"]
    Kp, pp = row_put_itm["Precio de ejercicio"], row_put_itm["Último precio"]

    spot = get_current_price(ticker)
    center = spot
    S = make_price_grid(center, factor_min, factor_max, n)

    payoff_total = payoff_call_long(S, Kc, pc) + payoff_put_long(S, Kp, pp)
    return pd.DataFrame({"S": S, "payoff": payoff_total})

def payoff_long_straddle_from_rows(row_call_atm, row_put_atm,
                                   factor_min=0.8, factor_max=1.2,
                                   n=4000,
                                   ticker="AAPL"):
    Kc, pc = row_call_atm["Precio de ejercicio"], row_call_atm["Último precio"]
    Kp, pp = row_put_atm["Precio de ejercicio"], row_put_atm["Último precio"]

    spot = get_current_price(ticker)
    center = spot
    S = make_price_grid(center, factor_min, factor_max, n)

    payoff_total = payoff_call_long(S, Kc, pc) + payoff_put_long(S, Kp, pp)
    return pd.DataFrame({"S": S, "payoff": payoff_total})


def payoff_long_box_from_rows(row_call_K1, row_call_K2,
                              row_put_K1, row_put_K2,
                              factor_min=0.8, factor_max=1.2,
                              n=4000,
                              ticker="AAPL"):
    """
    Long Box (CALL + PUT) misma expiración:
        Bull Call Spread:  +Call(K1) -Call(K2)
        Bear Put Spread:   +Put(K2)  -Put(K1)
    con K1 < K2.
    """
    K1c, p1c = row_call_K1["Precio de ejercicio"], row_call_K1["Último precio"]
    K2c, p2c = row_call_K2["Precio de ejercicio"], row_call_K2["Último precio"]
    K1p, p1p = row_put_K1["Precio de ejercicio"], row_put_K1["Último precio"]
    K2p, p2p = row_put_K2["Precio de ejercicio"], row_put_K2["Último precio"]

    assert K1c < K2c, "Se requiere K1 < K2 para la Box."

    spot = get_current_price(ticker)
    center = spot
    S = make_price_grid(center, factor_min, factor_max, n)

    C1 = payoff_call_long(S, K1c, p1c)
    C2 = payoff_call_long(S, K2c, p2c)
    P1 = payoff_put_long(S, K1p, p1p)
    P2 = payoff_put_long(S, K2p, p2p)

    payoff_total = (C1 - C2) + (P2 - P1)
    return pd.DataFrame({"S": S, "payoff": payoff_total})

def dashboard_app_movement():
    st.title("⚡ Estrategias de movimiento fuerte")

    df_sp500 = scrape_series_data()
    Empresas = df_sp500['Company'].iloc[1:5].tolist()
    TICKERS = df_sp500['Symbol'].iloc[1:5].tolist()

    col1, col2 = st.columns(2)

    with col1:
        symbol_mov = st.text_input(
            "Símbolo",
            value="AAPL",
            key="symbol_mov"
        )

    with col2:
        max_intentos_opt = st.number_input(
            "Máx. intentos descarga",
            min_value=1, max_value=20, value=5,
            key="max_intentos_mov"
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

    if not symbol_mov:
        return

    try:
        lista_fechas = fechas_unix(symbol_mov)

        if lista_fechas is None or len(lista_fechas) == 0:
            if st.session_state.get("mostrar_texto_global", True):
                st.error("No se han encontrado vencimientos para este símbolo.")
            return

        lista_fechas = sorted(lista_fechas, key=lambda x: x["timestamp"])
        opciones_fechas = [item["date"] for item in lista_fechas]
        fechas_dict = {item["date"]: item for item in lista_fechas}

        fecha_sel_mov = st.selectbox(
            "Fecha de vencimiento",
            opciones_fechas,
            key="fecha_sel_mov"
        )
        item_sel_mov = fechas_dict[fecha_sel_mov]

    except Exception as e:
        if st.session_state.get("mostrar_texto_global", True):
            st.error(f"Error obteniendo fechas de vencimiento: {e}")
        return

    st.markdown("---")

    # --- Botón para descargar datos de opciones ---
    if st.button("📥 Descargar CALLS y PUTS para esta fecha", key="btn_descargar_mov"):

        with st.spinner("Descargando opciones CALL y PUT..."):
            calls_df = load_calls_for_expiration(
                symbol_mov,
                item_sel_mov["timestamp"],
                max_intentos=max_intentos_opt
            )
            puts_df = load_puts_for_expiration(
                symbol_mov,
                item_sel_mov["timestamp"],
                max_intentos=max_intentos_opt
            )

        if calls_df is None or calls_df.empty:
            if st.session_state.get("mostrar_texto_global", True):
                st.error("No se pudieron descargar CALLS para este símbolo/fecha.")
            return
        if puts_df is None or puts_df.empty:
            if st.session_state.get("mostrar_texto_global", True):
                st.error("No se pudieron descargar PUTS para este símbolo/fecha.")
            return
        if st.session_state.get("mostrar_texto_global", True):
            st.success("Datos de opciones descargados correctamente.")
        st.subheader("Vista previa CALLs")
        st.dataframe(calls_df.head())
        st.subheader("Vista previa PUTs")
        st.dataframe(puts_df.head())

        spot = get_current_price(symbol_mov)
        if st.session_state.get("mostrar_texto_global", True):
            st.info(f"Precio actual de {symbol_mov}: {spot:.2f} $")

        try:
            row_call_atm = choose_atm_strike(calls_df, spot)
            K_atm = row_call_atm["Precio de ejercicio"]
            row_put_atm = match_strike_row(puts_df, K_atm)

            row_call_otm = best_otm_call(calls_df, spot)
            row_put_otm = best_otm_put(puts_df, spot)

            row_call_itm = choose_butterfly_call_rows(calls_df, spot)
            row_put_itm = choose_butterfly_put_rows(puts_df, spot)

            row_call_K1 = row_call_itm
            row_call_K2 = row_call_otm

            K1_box = row_call_K1["Precio de ejercicio"]
            K2_box = row_call_K2["Precio de ejercicio"]
            if K1_box > K2_box:
                K1_box, K2_box = K2_box, K1_box
                row_call_K1, row_call_K2 = row_call_K2, row_call_K1

            row_put_K1 = match_strike_row(puts_df, K1_box)
            row_put_K2 = match_strike_row(puts_df, K2_box)

        except Exception as e:
            st.error(f"Error al seleccionar strikes para estrategias de movimiento: {e}")
            return

        st.markdown("### Strikes seleccionados")

        colA, colB, colC = st.columns(3)

        with colA:
            st.write("**Straddle ATM**")
            st.write(pd.DataFrame(
                [row_call_atm, row_put_atm],
                index=["Call ATM", "Put ATM"]
            )[["Precio de ejercicio", "Último precio", "Volatilidad implícita"]])

        with colB:
            st.write("**Strangle OTM / Guts**")
            st.write(pd.DataFrame(
                [row_call_otm, row_put_otm, row_call_itm, row_put_itm],
                index=["Call OTM (Strangle)", "Put OTM (Strangle)",
                       "Call ITM (Guts)", "Put ITM (Guts)"]
            )[["Precio de ejercicio", "Último precio", "Volatilidad implícita"]])

        with colC:
            st.write("**Box (CALLs/PUTs)**")
            st.write(pd.DataFrame(
                [row_call_K1, row_call_K2, row_put_K1, row_put_K2],
                index=["Call K1 (Box)", "Call K2 (Box)", "Put K1 (Box)", "Put K2 (Box)"]
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
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(3),
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(4) {
            color: #FF0000 !important;  /* rojo */
        }
        </style>
        """, unsafe_allow_html=True)

        tabm_1, tabm_2, tabm_3, tabm_4 = st.tabs([
            "Long Strangle OTM",
            "Long Guts",
            "Long Straddle ATM",
            "Long Box (solo buy)"
        ])

        with tabm_1:
            st.subheader("Long Strangle OTM")
            df_strangle = payoff_long_strangle_from_rows(
                row_call_otm, row_put_otm, ticker=symbol_mov
            )
            fig1 = plot_payoff(df_strangle, "Long Strangle OTM", ticker=symbol_mov)
            st.plotly_chart(fig1, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es un Long Strangle OTM?

                El **Long Strangle OTM** consiste en:
                - Comprar una **CALL OTM**.
                - Comprar una **PUT OTM**.
                - Ambas con el **mismo vencimiento**, pero strikes distintos alrededor del precio actual.

                Es una apuesta a un **movimiento fuerte del subyacente**, sin necesidad de acertar la dirección.

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Aprovechar movimientos bruscos** | Se gana si el precio se aleja mucho por arriba o por abajo. |
                | **Neutral en dirección** | No importa si el movimiento es alcista o bajista. |
                | **Exposición a volatilidad** | Se beneficia de aumentos de volatilidad implícita. |

                #### 🧨 ¿Riesgos?
                - Si el subyacente se queda en un rango estrecho, ambas opciones pierden valor temporal.
                - Requiere un movimiento **relevante** para superar el coste de las primas.
                - Pérdida máxima limitada a la **suma de las primas pagadas**.

                Es típico cuando se espera **noticia / evento** que pueda disparar el precio en cualquier dirección.
                """)

        with tabm_2:
            st.subheader("Long Guts")
            df_guts = payoff_long_guts_from_rows(
                row_call_itm, row_put_itm, ticker=symbol_mov
            )
            fig2 = plot_payoff(df_guts, "Long Guts", ticker=symbol_mov)
            st.plotly_chart(fig2, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es un Long Guts?

                El **Long Guts** es similar al strangle, pero:
                - Se compra una **CALL ITM**.
                - Se compra una **PUT ITM**.
                - Ambas con el mismo vencimiento, con strikes dentro del dinero.

                Es otra forma de apostar por un **gran movimiento**, pero usando opciones ITM.

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Mayor sensibilidad al precio** | Las opciones ITM tienen delta más alta. |
                | **Rango efectivo más amplio** | El payoff empieza a ser relevante con movimientos algo menores que en el strangle OTM. |
                | **Perfil más “suave”** | El comportamiento del payoff es más continuo alrededor del precio actual. |

                #### 🧨 ¿Riesgos?
                - Coste en primas **más alto** que en el strangle OTM.
                - Aun así, si el movimiento no es suficiente, se pierde valor temporal en ambas patas.
                - Pérdida máxima limitada a la suma de las primas, pero esa suma es mayor.

                Es útil cuando se espera un **movimiento fuerte**, pero no extremadamente violento, y se quiere más sensibilidad cerca del precio actual.
                """)


        with tabm_3:
            st.subheader("Long Straddle ATM")
            df_straddle = payoff_long_straddle_from_rows(
                row_call_atm, row_put_atm, ticker=symbol_mov
            )
            fig4 = plot_payoff(df_straddle, "Long Straddle ATM", ticker=symbol_mov)
            st.plotly_chart(fig4, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es un Long Straddle ATM?

                El **Long Straddle** ATM consiste en:
                - Comprar una **CALL ATM**.
                - Comprar una **PUT ATM**.
                - Ambas con el mismo strike (≈ precio actual) y mismo vencimiento.

                Es la apuesta “pura” a **movimiento fuerte y/o aumento de volatilidad**, sin sesgo direccional.

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Movimiento grande, arriba o abajo** | Gana si el subyacente se aleja bastante del strike. |
                | **Apuesta a la volatilidad** | Muy sensible a cambios en la volatilidad implícita. |
                | **Simetría** | El payoff es prácticamente simétrico a ambos lados del strike. |

                #### 🧨 ¿Riesgos?
                - Es cara: se pagan dos primas ATM, con bastante valor temporal. |
                - Si el precio se queda cerca del strike, ambas opciones pierden valor (time decay). |
                - Sensible a “crush” de volatilidad tras eventos (resultados, noticias, etc.).

                Es típica cuando se espera un **evento clave** (resultados, anuncio importante…) pero no se sabe en qué dirección se moverá el mercado.
                """)

        with tabm_4:
            st.subheader("Long Box (solo buy)")
            df_box = payoff_long_box_from_rows(
                row_call_K1, row_call_K2, row_put_K1, row_put_K2, ticker=symbol_mov
            )
            fig5 = plot_payoff(df_box, "Long Box (solo buy)", ticker=symbol_mov)
            st.plotly_chart(fig5, width='stretch')
            if st.session_state.get("mostrar_estrategias_global", True):
                st.markdown("""
                ### 📘 ¿Qué es una Long Box (solo buy)?

                La **Long Box** combina:
                - Un **bull call spread** (CALL K1–K2).
                - Un **bear put spread** (PUT K1–K2).
                - Mismos strikes y mismo vencimiento.

                En teoría, crea un payoff casi “fijo” (similar a un bono), con beneficio/pérdida prácticamente independiente del precio final.

                #### 🎯 ¿Qué busca esta estrategia?
                | Aspecto | Explicación |
                |---------|------------|
                | **Arbitraje teórico** | En mercados ideales, el valor de la box debería estar ligado a tipos de interés. |
                | **Perfil casi constante** | El payoff final es prácticamente el mismo para cualquier precio del subyacente (dentro de un rango amplio). |
                | **Construir “bonos sintéticos”** | Se puede interpretar como un préstamo o depósito sintético usando opciones. |

                #### 🧨 ¿Riesgos?
                - En la práctica, comisiones, spreads y desajustes de precios pueden eliminar el “arbitraje”. |
                - Sensible a la liquidez de las opciones en cada strike. |
                - Puede implicar un consumo importante de margen, dependiendo del bróker. |

                Se usa más como **herramienta teórica / de arbitraje** que como apuesta direccional o de volatilidad.
                """)

    else:
        if st.session_state.get("mostrar_texto_global", True):
            st.info("Pulsa el botón para descargar las opciones y ver los payoffs.")


# Para probar este fichero directamente si quieres
if __name__ == "__main__":
    dashboard_app_movement()
