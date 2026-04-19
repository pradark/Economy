import os
import json
import time
import urllib.request
import urllib.error
from datetime import date, timedelta

SERIES_ID = "DHHNGSP"
SERIES_LABEL = "Henry Hub Natural Gas Spot Price (USD/MMBtu)"

api_key = os.environ.get("FRED_API_KEY")
if not api_key:
    key_path = os.path.join(os.path.dirname(__file__), "FRED_API_Key.txt")
    if os.path.exists(key_path):
        with open(key_path) as f:
            api_key = f.read().strip()

if not api_key:
    raise SystemExit("FRED_API_KEY not set and FRED_API_Key.txt not found")

end = date.today()
start = end - timedelta(days=365)

url = (
    "https://api.stlouisfed.org/fred/series/observations"
    f"?series_id={SERIES_ID}"
    f"&api_key={api_key}"
    "&file_type=json"
    f"&observation_start={start.isoformat()}"
    f"&observation_end={end.isoformat()}"
)

last_err = None
for attempt in range(5):
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
        break
    except urllib.error.HTTPError as e:
        last_err = e
        if e.code >= 500:
            time.sleep(2 ** attempt)
            continue
        raise
    except urllib.error.URLError as e:
        last_err = e
        time.sleep(2 ** attempt)
else:
    raise SystemExit(f"FRED request failed after retries: {last_err}")

rows = [
    {"date": o["date"], "value": float(o["value"])}
    for o in payload.get("observations", [])
    if o.get("value") not in (".", "", None)
]

labels = [r["date"] for r in rows]
values = [r["value"] for r in rows]
latest = rows[-1] if rows else {"date": "n/a", "value": None}
prior = rows[-2] if len(rows) >= 2 else None
change = None
if prior and latest["value"] is not None:
    change = latest["value"] - prior["value"]

generated_at = date.today().isoformat()

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{SERIES_LABEL}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem auto; max-width: 960px; color: #222; }}
  h1 {{ margin-bottom: 0.25rem; }}
  .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }}
  .stats {{ display: flex; gap: 2rem; margin-bottom: 1.5rem; }}
  .stat .label {{ font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.05em; }}
  .stat .value {{ font-size: 1.6rem; font-weight: 600; }}
  .up {{ color: #0a8a3a; }}
  .down {{ color: #c0392b; }}
  footer {{ margin-top: 2rem; font-size: 0.8rem; color: #888; }}
</style>
</head>
<body>
  <h1>{SERIES_LABEL}</h1>
  <div class="meta">FRED series <a href="https://fred.stlouisfed.org/series/{SERIES_ID}">{SERIES_ID}</a> — last 365 days. Generated {generated_at}.</div>
  <div class="stats">
    <div class="stat"><div class="label">Latest ({latest["date"]})</div><div class="value">{'' if latest['value'] is None else f'${latest["value"]:.2f}'}</div></div>
    <div class="stat"><div class="label">Day change</div><div class="value {'up' if change and change >= 0 else 'down' if change else ''}">{'—' if change is None else f'{"+" if change >= 0 else ""}{change:.2f}'}</div></div>
    <div class="stat"><div class="label">Observations</div><div class="value">{len(rows)}</div></div>
  </div>
  <canvas id="chart" height="120"></canvas>
  <footer>Source: U.S. Energy Information Administration via FRED. Auto-updated daily via GitHub Actions.</footer>
<script>
const labels = {json.dumps(labels)};
const values = {json.dumps(values)};
new Chart(document.getElementById('chart'), {{
  type: 'line',
  data: {{ labels, datasets: [{{ label: '{SERIES_LABEL}', data: values, borderColor: '#2a6df4', backgroundColor: 'rgba(42,109,244,0.08)', fill: true, tension: 0.15, pointRadius: 0 }}] }},
  options: {{ responsive: true, scales: {{ x: {{ ticks: {{ maxTicksLimit: 8 }} }}, y: {{ beginAtZero: false }} }}, plugins: {{ legend: {{ display: false }} }} }}
}});
</script>
</body>
</html>
"""

out_path = os.path.join(os.path.dirname(__file__), "index.html")
with open(out_path, "w") as f:
    f.write(html)

print(f"Wrote {out_path} with {len(rows)} observations")
