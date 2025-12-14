import streamlit as st
from PIL import Image 

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent          # .../todo-app/code
ROOT_DIR = APP_DIR.parent                           # .../todo-app

# Candidatos típicos (elige el que coincida con tu repo)
CANDIDATES = [
    APP_DIR / "data" / "logo.png",                  # code/data/logo.png
    ROOT_DIR / "data" / "logo.png"               # data/logo.png
]

logo_path = next((p for p in CANDIDATES if p.exists()), None)

if logo_path is None:
    st.warning(
        "No se encontró el logo. Rutas comprobadas:\n" +
        "\n".join(f"- {p}" for p in CANDIDATES)
    )
    black_logo = None
else:
    black_logo = Image.open(logo_path)

black_logo = Image.open('./data/logo.png')

st.set_page_config(
    page_title="Market Scavenger Hunt",
    page_icon=black_logo,
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #08121f;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

col1, col2 = st.columns([1, 9])

with col1:
    st.image("./data/logo.png", width=100)

with col2:
    st.markdown(
        "<h1 style='margin-bottom: 0;'>Scavenger Hunt</h1>",
        unsafe_allow_html=True
    )


st.sidebar.header("Navegación")

seccion = st.sidebar.radio(
    "Ir a sección:",
    ["📈 Velas / Indicadores", "🧮 Opciones CALL", "🧮 Opciones PUT", "🗓️ Estrategias laterales", "⚡ Estrategias de movimiento fuerte"],
    key="seccion_principal"
)

st.sidebar.header("Opciones de riesgo")

st.sidebar.markdown(
    """
    **Riesgo**
    - <span style="color:#00CC44"> Suave</span>
    - <span style="color:#FFD700"> Moderado</span>
    - <span style="color:#FF0000"> Alto</span>
    """,
    unsafe_allow_html=True
)


mostrar_texto = st.sidebar.checkbox(
    "Mostrar texto adicional",
    key="mostrar_texto_global",
    value=True
)

mostrar_explicacion = st.sidebar.checkbox(
    "Mostrar explicación estratégias",
    key="mostrar_estrategias_global",
    value=True
)

if seccion == "📈 Velas / Indicadores":

    from stock.stock_streamlit import dashboard_app_velas
    dashboard_app_velas()

    ver_tree_map = st.sidebar.checkbox(
        "Ver Tree Map del S&P 500",
        key="ver_tree_map",
        value=False
    )

    if ver_tree_map:
        st.markdown("---")

        from stock.tree_map_streamlit import dashboard_app_tree_map
        dashboard_app_tree_map()

    else:

        if st.session_state.get("mostrar_texto_global", True):
            st.info(
                "Puedes activar el Tree Map del S&P 500 desde la barra lateral."
            )

elif seccion == "🧮 Opciones CALL":

    from options.payoff_call_streamlit import dashboard_app_call
    dashboard_app_call()

elif seccion == "🧮 Opciones PUT":

    from options.payoff_put_streamlit import dashboard_app_put
    dashboard_app_put()

elif seccion == "🗓️ Estrategias laterales":

    from options.payoff_calendar_streamlit import dashboard_app_calendar
    dashboard_app_calendar()

elif seccion == "⚡ Estrategias de movimiento fuerte":

    from options.payoff_movement_streamlit import dashboard_app_movement
    dashboard_app_movement()