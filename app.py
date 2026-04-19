import os
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st
import altair as alt

st.set_page_config(page_title="US Leading Economic Indicators", layout="wide")

SERIES = [
    {"id": "GASREGW",      "label": "US Regular Gasoline Price",       "unit": "$/gal"},
    {"id": "T10Y2Y",       "label": "10Y-2Y Treasury Spread",          "unit": "%"},
    {"id": "T10Y3M",       "label": "10Y-3M Treasury Spread",          "unit": "%"},
    {"id": "ICSA",         "label": "Initial Jobless Claims",          "unit": "persons"},
    {"id": "PERMIT",       "label": "Building Permits",                "unit": "thousands"},
    {"id": "SP500",        "label": "S&P 500",                         "unit": "index"},
    {"id": "UMCSENT",      "label": "Consumer Sentiment (UMich)",      "unit": "index"},
    {"id": "BAMLH0A0HYM2", "label": "High-Yield Credit Spread (OAS)",  "unit": "%"},
    {"id": "M2SL",         "label": "M2 Money Supply",                 "unit": "$B"},
    {"id": "AWHMAN",       "label": "Avg Weekly Hours, Manufacturing", "unit": "hours"},
]


def get_api_key():
    key = st.secrets.get("FRED_API_KEY") if hasattr(st, "secrets") else None
    if not key:
        key = os.environ.get("FRED_API_KEY")
    if not key:
        local = os.path.join(os.path.dirname(__file__), "FRED_API_Key.txt")
        if os.path.exists(local):
            key = open(local).read().strip()
    if not key:
        st.error("FRED_API_KEY not configured. Add it under App settings → Secrets.")
        st.stop()
    return key


@st.cache_data(ttl=60 * 60 * 6)
def fetch_series(series_id: str, start: str, end: str, api_key: str) -> pd.DataFrame:
    r = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
        },
        timeout=30,
    )
    r.raise_for_status()
    obs = r.json().get("observations", [])
    df = pd.DataFrame(obs)
    if df.empty:
        return df
    df = df[df["value"] != "."].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = df["value"].astype(float)
    return df[["date", "value"]]


@st.cache_data(ttl=60 * 60 * 24)
def fetch_recessions(start: str, end: str, api_key: str) -> list[dict]:
    df = fetch_series("USREC", start, end, api_key)
    if df.empty:
        return []
    df = df.sort_values("date").reset_index(drop=True)
    ranges, rec_start = [], None
    for _, row in df.iterrows():
        if row["value"] == 1 and rec_start is None:
            rec_start = row["date"]
        elif row["value"] == 0 and rec_start is not None:
            ranges.append({"start": rec_start, "end": row["date"]})
            rec_start = None
    if rec_start is not None:
        ranges.append({"start": rec_start, "end": df["date"].iloc[-1]})
    return ranges


def chart(df: pd.DataFrame, recessions: list[dict], label: str) -> alt.Chart:
    if df.empty:
        return alt.Chart(pd.DataFrame({"date": [], "value": []})).mark_line()
    first, last = df["date"].min(), df["date"].max()
    visible = [
        {"start": max(r["start"], first), "end": min(r["end"], last)}
        for r in recessions
        if r["end"] >= first and r["start"] <= last
    ]
    rec_df = pd.DataFrame(visible)
    base = alt.Chart(df).mark_line(color="#2a6df4", strokeWidth=1.5).encode(
        x=alt.X("date:T", title=None),
        y=alt.Y("value:Q", title=label, scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("date:T"), alt.Tooltip("value:Q", format=",.2f")],
    )
    layers = [base]
    if not rec_df.empty:
        rec_layer = alt.Chart(rec_df).mark_rect(opacity=0.25, color="#888").encode(
            x="start:T", x2="end:T"
        )
        layers = [rec_layer, base]
    return alt.layer(*layers).properties(height=220).interactive()


st.title("US Leading Economic Indicators")
st.caption("Live from FRED. Shaded bands are NBER recession periods (USREC).")

api_key = get_api_key()
end = date.today()

with st.sidebar:
    st.header("Controls")
    years = st.slider("20-year window: history length (years)", 5, 30, 20)
    short_window = st.selectbox("Short window", ["6 months", "1 year", "2 years", "5 years"], index=1)
    selected_ids = st.multiselect(
        "Indicators",
        [s["id"] for s in SERIES],
        default=[s["id"] for s in SERIES],
        format_func=lambda x: next(s["label"] for s in SERIES if s["id"] == x),
    )

short_days = {"6 months": 182, "1 year": 365, "2 years": 730, "5 years": 1826}[short_window]
start_long = (end - timedelta(days=int(365 * years + 7))).isoformat()
cutoff_short = (end - timedelta(days=short_days))

recessions = fetch_recessions(start_long, end.isoformat(), api_key)

for s in [x for x in SERIES if x["id"] in selected_ids]:
    try:
        df = fetch_series(s["id"], start_long, end.isoformat(), api_key)
    except Exception as e:
        st.warning(f"{s['label']} ({s['id']}): {e}")
        continue

    st.subheader(f"{s['label']}  \u00b7  [{s['id']}](https://fred.stlouisfed.org/series/{s['id']}) ({s['unit']})")
    if df.empty:
        st.info("no data")
        continue

    latest = df.iloc[-1]
    prior = df.iloc[-2] if len(df) >= 2 else None
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("Latest", f"{latest['value']:,.2f}", help=str(latest["date"].date()))
    if prior is not None:
        delta = latest["value"] - prior["value"]
        c2.metric("Change", f"{delta:+.2f}")
    c3.caption(f"{len(df):,} observations · {df['date'].min().date()} → {df['date'].max().date()}")

    df_short = df[df["date"] >= pd.Timestamp(cutoff_short)]
    left, right = st.columns(2)
    left.markdown(f"**Last {short_window}**")
    left.altair_chart(chart(df_short, recessions, s["label"]), use_container_width=True)
    right.markdown(f"**Last {years} years**")
    right.altair_chart(chart(df, recessions, s["label"]), use_container_width=True)
    st.divider()

st.caption("Source: Federal Reserve Bank of St. Louis (FRED).")
