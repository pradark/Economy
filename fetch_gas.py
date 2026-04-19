"""Fetch FRED leading economic indicators and build index.html."""
import os
import json
import time
import urllib.request
import urllib.error
from datetime import date, timedelta

SERIES = [
    {"id": "GASREGW",      "label": "US Regular Gasoline Price",       "unit": "$/gal",    "color": "#2a6df4"},
    {"id": "T10Y2Y",       "label": "10Y-2Y Treasury Spread",          "unit": "%",        "color": "#e67e22"},
    {"id": "T10Y3M",       "label": "10Y-3M Treasury Spread",          "unit": "%",        "color": "#d35400"},
    {"id": "ICSA",         "label": "Initial Jobless Claims",          "unit": "persons",  "color": "#c0392b"},
    {"id": "PERMIT",       "label": "Building Permits",                "unit": "thousands","color": "#27ae60"},
    {"id": "SP500",        "label": "S&P 500",                         "unit": "index",    "color": "#8e44ad"},
    {"id": "UMCSENT",      "label": "Consumer Sentiment (UMich)",      "unit": "index",    "color": "#16a085"},
    {"id": "BAMLH0A0HYM2", "label": "High-Yield Credit Spread (OAS)",  "unit": "%",        "color": "#b03a2e"},
    {"id": "M2SL",         "label": "M2 Money Supply",                 "unit": "$B",       "color": "#2980b9"},
    {"id": "AWHMAN",       "label": "Avg Weekly Hours, Manufacturing", "unit": "hours",    "color": "#7f8c8d"},
]


def load_api_key():
    key = os.environ.get("FRED_API_KEY")
    if key:
        return key
    p = os.path.join(os.path.dirname(__file__), "FRED_API_Key.txt")
    if os.path.exists(p):
        return open(p).read().strip()
    raise SystemExit("FRED_API_KEY not set and FRED_API_Key.txt not found")


def fetch(series_id, api_key, start, end):
    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={api_key}&file_type=json"
        f"&observation_start={start.isoformat()}&observation_end={end.isoformat()}"
    )
    last_err = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            return [
                {"date": o["date"], "value": float(o["value"])}
                for o in data.get("observations", [])
                if o.get("value") not in (".", "", None)
            ]
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code < 500:
                raise
            time.sleep(2 ** attempt)
        except urllib.error.URLError as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise SystemExit(f"failed to fetch {series_id}: {last_err}")


def recession_ranges(obs):
    ranges, start = [], None
    for o in obs:
        if o["value"] == 1 and start is None:
            start = o["date"]
        elif o["value"] == 0 and start is not None:
            ranges.append({"start": start, "end": o["date"]})
            start = None
    if start is not None and obs:
        ranges.append({"start": start, "end": obs[-1]["date"]})
    return ranges


def slice_since(obs, cutoff_iso):
    return [o for o in obs if o["date"] >= cutoff_iso]


def build_html(series_data, recessions):
    gen = date.today().isoformat()
    cards, scripts = "", ""
    for i, s in enumerate(series_data):
        latest_str = f"{s['latest']['value']:.2f} ({s['latest']['date']})" if s["latest"] else "—"
        if s["change"] is None:
            change_str, change_cls = "—", ""
        else:
            change_cls = "up" if s["change"] >= 0 else "down"
            change_str = f"{'+' if s['change'] >= 0 else ''}{s['change']:.2f}"
        cards += f"""
<section class="indicator">
  <header>
    <h2>{s['label']} <small>({s['id']}, {s['unit']})</small></h2>
    <div class="meta">Latest: <b>{latest_str}</b> &middot; Change: <b class="{change_cls}">{change_str}</b> &middot; <a href="https://fred.stlouisfed.org/series/{s['id']}">FRED</a></div>
  </header>
  <div class="row">
    <div class="chart-wrap"><div class="caption">Last 1 year</div><canvas id="c1_{i}"></canvas></div>
    <div class="chart-wrap"><div class="caption">Last 20 years</div><canvas id="c20_{i}"></canvas></div>
  </div>
</section>"""
        data1 = [{"x": o["date"], "y": o["value"]} for o in s["obs1"]]
        data20 = [{"x": o["date"], "y": o["value"]} for o in s["obs20"]]
        scripts += (
            f"renderChart('c1_{i}', {json.dumps(data1)}, {json.dumps(s['label'])}, {json.dumps(s['color'])});\n"
            f"renderChart('c20_{i}', {json.dumps(data20)}, {json.dumps(s['label'])}, {json.dumps(s['color'])});\n"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>US Leading Economic Indicators</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem auto; max-width: 1200px; color: #222; padding: 0 1rem; }}
  h1 {{ margin-bottom: 0.25rem; }}
  .page-meta {{ color: #666; font-size: 0.9rem; margin-bottom: 0.5rem; }}
  .legend {{ font-size: 0.8rem; color: #666; margin-bottom: 1rem; }}
  .legend .swatch {{ display: inline-block; width: 14px; height: 10px; background: rgba(160,160,160,0.4); border: 1px solid rgba(160,160,160,0.6); vertical-align: middle; margin-right: 4px; }}
  section.indicator {{ border-top: 1px solid #eee; padding-top: 1rem; margin-top: 1.25rem; }}
  section.indicator header h2 {{ margin: 0 0 0.25rem; font-size: 1.05rem; }}
  section.indicator header h2 small {{ font-weight: normal; color: #888; font-size: 0.8rem; }}
  .meta {{ font-size: 0.85rem; color: #555; margin-bottom: 0.6rem; }}
  .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
  @media (max-width: 800px) {{ .row {{ grid-template-columns: 1fr; }} }}
  .chart-wrap {{ background: #fafafa; border: 1px solid #eee; border-radius: 6px; padding: 0.5rem; }}
  .caption {{ font-size: 0.7rem; color: #888; text-align: center; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  canvas {{ width: 100% !important; height: 200px !important; }}
  .up {{ color: #0a8a3a; }}
  .down {{ color: #c0392b; }}
  footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #eee; font-size: 0.8rem; color: #888; }}
</style>
</head>
<body>
<h1>US Leading Economic Indicators</h1>
<div class="page-meta">Auto-updated from FRED via GitHub Actions. Generated {gen}.</div>
<div class="legend"><span class="swatch"></span>Shaded bands mark NBER recession periods (<a href="https://fred.stlouisfed.org/series/USREC">USREC</a>). Each row shows the last 1 year (left) and the last 20 years (right).</div>
{cards}
<footer>Source: Federal Reserve Bank of St. Louis (FRED). Series links above go to the source page. This file is regenerated daily.</footer>
<script>
const recessions = {json.dumps(recessions)};
function renderChart(canvasId, data, label, color) {{
  const ctx = document.getElementById(canvasId);
  if (!data.length) {{
    ctx.parentElement.innerHTML += '<div style="text-align:center;color:#999;padding:2rem">no data</div>';
    return;
  }}
  const first = data[0].x, last = data[data.length - 1].x;
  const visible = recessions
    .filter(r => r.end >= first && r.start <= last)
    .map(r => ({{
      type: 'box',
      xMin: r.start < first ? first : r.start,
      xMax: r.end > last ? last : r.end,
      backgroundColor: 'rgba(160,160,160,0.35)',
      borderWidth: 0,
      drawTime: 'beforeDatasetsDraw'
    }}));
  new Chart(ctx, {{
    type: 'line',
    data: {{ datasets: [{{ label, data, borderColor: color, backgroundColor: color + '22', fill: true, tension: 0.15, pointRadius: 0, borderWidth: 1.5 }}] }},
    options: {{
      responsive: true, maintainAspectRatio: false, animation: false,
      scales: {{
        x: {{ type: 'time', time: {{ tooltipFormat: 'yyyy-MM-dd' }}, ticks: {{ maxTicksLimit: 6 }} }},
        y: {{ beginAtZero: false }}
      }},
      plugins: {{
        legend: {{ display: false }},
        annotation: {{ annotations: visible }},
        tooltip: {{ callbacks: {{ title: items => items[0].parsed.x ? new Date(items[0].parsed.x).toISOString().slice(0,10) : '' }} }}
      }},
      interaction: {{ mode: 'index', intersect: false }}
    }}
  }});
}}
{scripts}
</script>
</body>
</html>
"""


def main():
    api_key = load_api_key()
    end = date.today()
    start20 = end - timedelta(days=365 * 20 + 7)
    cutoff_1y = (end - timedelta(days=365)).isoformat()

    usrec = fetch("USREC", api_key, start20, end)
    recessions = recession_ranges(usrec)

    series_data = []
    for s in SERIES:
        try:
            obs20 = fetch(s["id"], api_key, start20, end)
        except SystemExit as e:
            print(f"WARN {s['id']}: {e}")
            continue
        obs1 = slice_since(obs20, cutoff_1y)
        latest = obs20[-1] if obs20 else None
        prior = obs20[-2] if len(obs20) >= 2 else None
        change = (latest["value"] - prior["value"]) if latest and prior else None
        series_data.append({**s, "obs20": obs20, "obs1": obs1, "latest": latest, "change": change})

    html = build_html(series_data, recessions)
    out = os.path.join(os.path.dirname(__file__), "index.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"wrote {out}: {len(series_data)} series, {len(recessions)} recession bands")


if __name__ == "__main__":
    main()
