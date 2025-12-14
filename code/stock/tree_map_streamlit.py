import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px
from scrapper.sp500 import scrape_series_data


def prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    df["% Chg Float"] = pd.to_numeric(df["% Chg Float"], errors="coerce")

    df = df.dropna(subset=["Symbol", "Weight", "% Chg Float", "% Chg String"])
    df = df[df["Weight"] > 0]

    df["tile"] = df["% Chg String"].astype(str)
    return df


def fig_treemap(df: pd.DataFrame):
    scale = [
        (0.0,  "#7f0000"),
        (0.45, "#d73027"),
        (0.50, "#2b2b2b"),
        (0.55, "#1a9850"),
        (1.0,  "#006837"),
    ]

    fig = px.treemap(
        df,
        path=["Symbol"],
        values="Weight",
        color="% Chg Float",
        color_continuous_scale=scale,
        range_color=(-0.02, 0.02),
    )

    fig.update_traces(
        customdata=df[["Company", "Price", "Chg", "% Chg String", "% Chg Float"]].to_numpy(),
        texttemplate="<b>%{label}</b><br>%{customdata[3]}",
        textposition="middle center",
        marker=dict(line=dict(width=0)),
        tiling=dict(pad=0),

        hovertemplate=(
            "<b>%{customdata[0]}</b> (%{label})<br>"
            "Weight: %{value:.4f}<br>"
            "Price: %{customdata[1]:.2f}<br>"
            "Chg: %{customdata[2]:+.0f}<br>"
            "% Chg: %{customdata[3]}<br>"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
    height=600,
    margin=dict(t=10, l=0, r=0, b=0),
)

    return fig



def dashboard_app_tree_map():
    
    df = prep(scrape_series_data())
    st.plotly_chart(fig_treemap(df), width='stretch')


if __name__ == "__main__":
    dashboard_app_tree_map()
