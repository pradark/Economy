# Economy — US Leading Economic Indicators

Auto-updated daily dashboard of US leading economic indicators, built from [FRED](https://fred.stlouisfed.org/) data.

## Live site

**👉 [https://pradark.github.io/Economy/](https://pradark.github.io/Economy/)**

Each indicator is shown as two charts: the last 1 year on the left, the last 20 years on the right. NBER recession periods are shaded in gray.

## Indicators tracked

| Series | Description | Frequency |
|---|---|---|
| [GASREGW](https://fred.stlouisfed.org/series/GASREGW) | US Regular Gasoline Price | Weekly |
| [T10Y2Y](https://fred.stlouisfed.org/series/T10Y2Y) | 10Y–2Y Treasury Spread | Daily |
| [T10Y3M](https://fred.stlouisfed.org/series/T10Y3M) | 10Y–3M Treasury Spread | Daily |
| [ICSA](https://fred.stlouisfed.org/series/ICSA) | Initial Jobless Claims | Weekly |
| [PERMIT](https://fred.stlouisfed.org/series/PERMIT) | Building Permits | Monthly |
| [SP500](https://fred.stlouisfed.org/series/SP500) | S&P 500 | Daily |
| [UMCSENT](https://fred.stlouisfed.org/series/UMCSENT) | Consumer Sentiment (UMich) | Monthly |
| [BAMLH0A0HYM2](https://fred.stlouisfed.org/series/BAMLH0A0HYM2) | High-Yield Credit Spread (OAS) | Daily |
| [M2SL](https://fred.stlouisfed.org/series/M2SL) | M2 Money Supply | Monthly |
| [AWHMAN](https://fred.stlouisfed.org/series/AWHMAN) | Avg Weekly Hours, Manufacturing | Monthly |
| [USREC](https://fred.stlouisfed.org/series/USREC) | NBER Recession Indicator (shading only) | Monthly |

## How it works

- [`fetch_gas.py`](fetch_gas.py) pulls the latest 20 years of each series from the FRED API and regenerates `index.html` (a self-contained page using Chart.js + the annotation plugin).
- [`.github/workflows/update.yml`](.github/workflows/update.yml) runs the script on a daily schedule (06:00 UTC = 1am EST), commits any changes, and pushes them.
- GitHub Pages serves `index.html` from the `main` branch root.
- An interactive [Streamlit version](app.py) is also available for deployment to Streamlit Community Cloud.

## Local development

```bash
export FRED_API_KEY=your_key_here
python3 fetch_gas.py    # regenerates index.html

# optional: run the Streamlit app
pip install -r requirements.txt
streamlit run app.py
```

## Source

Federal Reserve Bank of St. Louis (FRED). Recession dates per NBER.
