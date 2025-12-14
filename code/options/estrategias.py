import streamlit as st
import pandas as pd

st.set_page_config(page_title="Estrategias de opciones", layout="wide")

estrategias_compra = [
    ("Subida", "Bajo",     "Long Call OTM"),
    ("Subida", "Moderado", "Long Call ATM"),
    ("Subida", "Moderado", "Call Ladder (solo buy)"),
    ("Subida", "Moderado", "Call Butterfly (solo buy)"),
    ("Subida", "Alto",     "Long Call ITM"),
    ("Subida", "Alto",     "Call Ratio Backspread (solo buy)"),

    ("Bajada", "Bajo",     "Long Put OTM"),
    ("Bajada", "Moderado", "Long Put ATM"),
    ("Bajada", "Moderado", "Put Ladder (solo buy)"),
    ("Bajada", "Moderado", "Put Butterfly (solo buy)"),
    ("Bajada", "Alto",     "Long Put ITM"),
    ("Bajada", "Alto",     "Put Ratio Backspread (solo buy)"),

    ("Lateral", "Bajo", "Long Calendar Spread"),
    ("Movimiento", "Moderado", "Long Condor (solo buy)"),
    ("Lateral", "Alto",     "Double Diagonal (solo buy)"),

    ("Movimiento", "Bajo",     "Long Strangle OTM"),
    ("Movimiento", "Moderado", "Long Guts"),
    ("Movimiento", "Alto",     "Long Straddle ATM"),
    ("Movimiento", "Alto",     "Long Box (solo buy)"),
]

df_estrategias = pd.DataFrame(
    estrategias_compra,
    columns=["Creencia", "Riesgo", "Estrategia"]
)

# ---------- SIDEBAR A LA IZQUIERDA ----------
st.sidebar.title("Filtro de estrategia")

creencia_sel = st.sidebar.selectbox(
    "Creencia sobre el mercado",
    options=df_estrategias["Creencia"].unique()
)

riesgo_sel = st.sidebar.radio(
    "Nivel de riesgo (prima pagada)",
    options=["Bajo", "Moderado", "Alto"]
)

st.sidebar.markdown("---")
st.sidebar.write("Más adelante aquí metemos:")
st.sidebar.write("- Selección de activo")
st.sidebar.write("- Vencimiento")
st.sidebar.write("- Strikes, etc.")

st.title("Estrategias de opciones (solo compra)")
st.write("Selecciona tu **creencia de mercado** y **nivel de riesgo** en la barra lateral.")

filtro = (
    (df_estrategias["Creencia"] == creencia_sel) &
    (df_estrategias["Riesgo"] == riesgo_sel)
)
df_filtrado = df_estrategias[filtro]

if df_filtrado.empty:
    st.warning("No hay estrategias para esa combinación de creencia y riesgo.")
else:
    st.subheader(f"Estrategias para: {creencia_sel} + riesgo {riesgo_sel}")
    st.dataframe(df_filtrado.reset_index(drop=True))
    st.write("Más adelante aquí metemos gráficos de payoff de cada estrategia.")

