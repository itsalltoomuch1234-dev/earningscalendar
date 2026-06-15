import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ── Tickers to track ──────────────────────────────────────────────────────────
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD",
    "NFLX", "CRM", "ORCL", "INTC", "QCOM", "AVGO", "TXN", "MU",
    "JPM", "GS", "MS", "BAC", "WFC", "C", "V", "MA", "PYPL",
    "JNJ", "PFE", "MRNA", "ABBV", "UNH",
    "AMGN", "CVX", "XOM", "BA", "CAT", "GE", "MMM", "HON",
    "WMT", "TGT", "COST", "HD", "NKE", "MCD", "SBUX", "DIS",
    "T", "VZ", "TMUS", "UBER", "LYFT", "SNAP", "TWTR", "PINS",
    "SQ", "SHOP", "ZM", "DOCU", "PLTR", "COIN", "RBLX", "HOOD"
]

# ── Fetch from NASDAQ (primary source) ───────────────────────────────────────
def get_nasdaq_date(ticker):
    try:
        url = f"https://api.nasdaq.com/api/quote/{ticker}/info?assetclass=stocks"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        date_str = data["data"]["earningsInfo"]["nextEarningsDate"]
        if date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        pass
    return None

# ── Fetch from Yahoo Finance (secondary source) ───────────────────────────────
def get_yahoo_date(ticker):
    try:
        stock = yf.Ticker(ticker)
        cal = stock.calendar
        if cal is not None and not cal.empty:
            date = cal.iloc[0]["Earnings Date"]
            if hasattr(date, "date"):
                return date.date()
            return date
    except:
        pass
    return None

# ── Build earnings data ───────────────────────────────────────────────────────
def build_earnings():
    results = []
    today = datetime.now(ZoneInfo("America/New_York")).date()
    cutoff = today + timedelta(weeks=8)

    for ticker in TICKERS:
        nasdaq_date = get_nasdaq_date(ticker)
        yahoo_date = get_yahoo_date(ticker)

        # Determine display date (prefer NASDAQ, fallback to Yahoo)
        display_date = nasdaq_date or yahoo_date

        if not display_date:
            continue
        if display_date < today or display_date > cutoff:
            continue

        # Mismatch signal
        mismatch = False
        if nasdaq_date and yahoo_date and nasdaq_date != yahoo_date:
            mismatch = True

        results.append({
            "ticker": ticker,
            "date": display_date,
            "nasdaq_date": str(nasdaq_date) if nasdaq_date else "N/A",
            "yahoo_date": str(yahoo_date) if yahoo_date else "N/A",
            "mismatch": mismatch
        })

    results.sort(key=lambda x: x["date"])
    return results

# ── Generate calendar weeks ───────────────────────────────────────────────────
def get_calendar_weeks(earnings):
    today = datetime.now(ZoneInfo("America/New_York")).date()
    start = today - timedelta(days=today.weekday())  # Monday of current week
    weeks = []
    for w in range(8):
        week_start = start + timedelta(weeks=w)
        week = []
        for d in range(5):  # Mon–Fri only
            day = week_start + timedelta(days=d)
            day_earnings = [e for e in earnings if e["date"] == day]
            week.append({"date": day, "earnings": day_earnings})
        weeks.append(week)
    return weeks

# ── HTML Generation ───────────────────────────────────────────────────────────
def generate_html(weeks):
    today = datetime.now(ZoneInfo("America/New_York")).date()

    cards_html = ""
    modal_html = ""

    for week in weeks:
        week_label = week[0]["date"].strftime("%b %d") + " – " + week[4]["date"].strftime("%b %d, %Y")
        cards_html += f'<div class="week-label">{week_label}</div>'
        cards_html += '<div class="week-row">'

        for day in week:
            date_str = day["date"].strftime("%A, %b %d")
            is_today = " today" if day["date"] == today else ""
            cards_html += f'<div class="day-card{is_today}">'
            cards_html += f'<div class="day-title">{date_str}</div>'

            if not day["earnings"]:
                cards_html += '<div class="no-earnings">—</div>'
            else:
                for e in day["earnings"]:
                    badge = ' <span class="badge-warn" title="Date mismatch between NASDAQ and Yahoo Finance">⚠</span>' if e["mismatch"] else ""
                    modal_id = f"modal-{e['ticker']}"
                    cards_html += f'''
                        <div class="ticker-chip" onclick="openModal('{modal_id}')">
                            {e["ticker"]}{badge}
                        </div>
                    '''
                    modal_html += f'''
                        <div class="modal" id="{modal_id}">
                            <div class="modal-box">
                                <h2>{e["ticker"]}</h2>
                                <table>
                                    <tr><td>NASDAQ Date</td><td>{e["nasdaq_date"]}</td></tr>
                                    <tr><td>Yahoo Date</td><td>{e["yahoo_date"]}</td></tr>
                                    <tr><td>Mismatch</td><td>{"⚠ Yes — dates differ" if e["mismatch"] else "✅ No"}</td></tr>
                                </table>
                                <button onclick="closeModal('{modal_id}')">Close</button>
                            </div>
                        </div>
                    '''

            cards_html += '</div>'
        cards_html += '</div>'

    updated = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M ET")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Earnings Calendar</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: #0f1117;
            color: #e0e0e0;
            padding: 24px;
        }}
        h1 {{
            text-align: center;
            font-size: 1.8rem;
            margin-bottom: 4px;
            color: #ffffff;
        }}
        .updated {{
            text-align: center;
            font-size: 0.8rem;
            color: #666;
            margin-bottom: 24px;
        }}
        .week-label {{
            font-size: 0.85rem;
            color: #888;
            margin: 20px 0 6px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .week-row {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin-bottom: 10px;
        }}
        .day-card {{
            background: #1a1d27;
            border-radius: 10px;
            padding: 12px;
            min-height: 80px;
            border: 1px solid #2a2d3a;
        }}
        .day-card.today {{
            border-color: #4f8ef7;
            background: #1a2340;
        }}
        .day-title {{
            font-size: 0.75rem;
            color: #888;
            margin-bottom: 8px;
        }}
        .no-earnings {{
            color: #444;
            font-size: 0.85rem;
        }}
        .ticker-chip {{
            display: inline-block;
            background: #2a2d3a;
            border-radius: 6px;
            padding: 4px 8px;
            margin: 3px 2px;
            font-size: 0.8rem;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .ticker-chip:hover {{ background: #3a3f55; }}
        .badge-warn {{
            font-size: 0.75rem;
            color: #f5a623;
        }}
        .modal {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.7);
            z-index: 999;
            justify-content: center;
            align-items: center;
        }}
        .modal.active {{ display: flex; }}
        .modal-box {{
            background: #1a1d27;
            border: 1px solid #2a2d3a;
            border-radius: 12px;
            padding: 28px;
            min-width: 300px;
        }}
        .modal-box h2 {{
            margin-bottom: 16px;
            color: #fff;
        }}
        .modal-box table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 16px;
        }}
        .modal-box td {{
            padding: 8px;
            border-bottom: 1px solid #2a2d3a;
            font-size: 0.9rem;
        }}
        .modal-box td:first-child {{ color: #888; }}
        .modal-box button {{
            background: #4f8ef7;
            color: white;
            border: none;
            padding: 8px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
        }}
        .modal-box button:hover {{ background: #3a7de0; }}
    </style>
</head>
<body>
    <h1>📅 Earnings Calendar</h1>
    <div class="updated">Last updated: {updated}</div>
    {cards_html}
    {modal_html}
    <script>
        function openModal(id) {{
            document.getElementById(id).classList.add('active');
        }}
        function closeModal(id) {{
            document.getElementById(id).classList.remove('active');
        }}
        window.addEventListener('click', function(e) {{
            document.querySelectorAll('.modal.active').forEach(m => {{
                if (e.target === m) m.classList.remove('active');
            }});
        }});
    </script>
</body>
</html>"""

    return html

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Fetching earnings data...")
    earnings = build_earnings()
    print(f"Found {len(earnings)} upcoming earnings.")
    weeks = get_calendar_weeks(earnings)
    html = generate_html(weeks)
    with open("index.html", "w") as f:
        f.write(html)
    print("index.html generated successfully.")
