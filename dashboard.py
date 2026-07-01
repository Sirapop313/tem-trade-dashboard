"""
Tim.fin Personal OS — Investment & Trade Dashboard
"""
import io
import json
import os
import re
from datetime import date

import pandas as pd
import requests as _req
import streamlit as st
import plotly.graph_objects as go

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Tim.fin OS", page_icon="📊", layout="wide")

DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE      = os.path.join(DIR, "trades.json")
INVESTMENTS_FILE = os.path.join(DIR, "investments.json")
CASH_FILE        = os.path.join(DIR, "cash.json")
STRATEGY_PRESETS = ["Breakout", "Swing", "Buy on dip", "Others"]

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 18px 20px;
}
[data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 700; }
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    color: #64748b !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
[data-testid="stFormSubmitButton"] button {
    background: #5865f2; color: white;
    border-radius: 8px; font-weight: 600; width: 100%;
}
[data-testid="stFormSubmitButton"] button:hover { background: #4752c4; }
.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #475569;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 0.75rem;
}
.page-title   { font-size: 1.6rem; font-weight: 700; margin: 0; line-height: 1.2; }
.page-sub     { font-size: 0.82rem; color: #64748b; margin-top: 2px; }
#MainMenu, footer { visibility: hidden; }
.main .block-container { max-width: 1400px; padding-top: 1.5rem; }
</style>""", unsafe_allow_html=True)


# ── Data Layer ────────────────────────────────────────────────────────────────
def _load(path: str) -> list:
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8") as f: return json.load(f)

def _save(path: str, data: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── Supabase + Auth ───────────────────────────────────────────────────────────
def _use_sb() -> bool:
    try: return bool(st.secrets.get("SUPABASE_URL"))
    except Exception: return False

def _sb_url() -> str:
    return st.secrets["SUPABASE_URL"].rstrip("/")

def _sb_headers() -> dict:
    key = st.secrets["SUPABASE_KEY"]
    session = st.session_state.get("sb_session")
    token = session["access_token"] if session else key
    return {
        "apikey": key, "Authorization": f"Bearer {token}",
        "Content-Type": "application/json", "Prefer": "return=minimal",
    }

def _sb_base(table: str) -> str:
    return _sb_url() + f"/rest/v1/{table}"

def _sb_load(table: str) -> list:
    r = _req.get(f"{_sb_base(table)}?select=data", headers=_sb_headers())
    r.raise_for_status()
    rows = [row["data"] for row in r.json()]
    seen, deduped = set(), []
    for row in rows:
        rid = row.get("id")
        if rid not in seen:
            seen.add(rid)
            deduped.append(row)
    return deduped

def _sb_save(table: str, items: list) -> None:
    user_id = st.session_state.get("sb_session", {}).get("user", {}).get("id")
    if not user_id:
        return
    base, h = _sb_base(table), _sb_headers()
    _req.delete(f"{base}?user_id=eq.{user_id}", headers=h)
    if items:
        _req.post(base, headers={**h, "Prefer": "return=minimal"},
                  json=[{"data": item, "user_id": user_id} for item in items])

def sb_signin(email: str, password: str) -> dict | None:
    try:
        r = _req.post(f"{_sb_url()}/auth/v1/token?grant_type=password",
                      headers={"apikey": st.secrets["SUPABASE_KEY"], "Content-Type": "application/json"},
                      json={"email": email, "password": password}, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return "connection_error"

def sb_signup(email: str, password: str) -> tuple[dict | None, str]:
    r = _req.post(f"{_sb_url()}/auth/v1/signup",
                  headers={"apikey": st.secrets["SUPABASE_KEY"], "Content-Type": "application/json"},
                  json={"email": email, "password": password})
    data = r.json()
    if r.status_code in (200, 201):
        return data, ""
    return None, data.get("msg") or data.get("message") or str(data)

def is_logged_in() -> bool:
    return "sb_session" in st.session_state

# ── Public load/save ──────────────────────────────────────────────────────────
def load_trades() -> list:
    return _sb_load("trades") if _use_sb() else _load(TRADES_FILE)

def save_trades(d: list):
    if _use_sb(): _sb_save("trades", d)
    else: _save(TRADES_FILE, d)
    try:
        from journal import regenerate
        regenerate(d)
    except Exception:
        pass

def load_investments() -> list:
    return _sb_load("investments") if _use_sb() else _load(INVESTMENTS_FILE)

def save_investments(d: list):
    if _use_sb(): _sb_save("investments", d)
    else: _save(INVESTMENTS_FILE, d)

CASH_PRESETS = ["Dime", "Webull", "Binance", "Bitkub", "SCB", "KBank", "Others"]

def load_cash() -> list:
    if _use_sb():
        return _sb_load("cash_accounts")
    if not os.path.exists(CASH_FILE):
        return []
    with open(CASH_FILE, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        accounts = []
        if data.get("usd", 0): accounts.append({"id": 1, "name": "USD Cash", "currency": "USD", "amount": data["usd"]})
        if data.get("thb", 0): accounts.append({"id": 2, "name": "THB Cash", "currency": "THB", "amount": data["thb"]})
        return accounts
    return data

def save_cash(cash: list) -> None:
    if _use_sb(): _sb_save("cash_accounts", cash)
    else:
        with open(CASH_FILE, "w", encoding="utf-8") as f:
            json.dump(cash, f, ensure_ascii=False, indent=2)

def cash_deduct(cash: list, account_id, amount_thb: float, rate: float):
    for acc in cash:
        if acc["id"] == account_id:
            deduct = round(amount_thb / rate if acc["currency"] == "USD" else amount_thb, 2)
            acc["amount"] = round(acc["amount"] - deduct, 2)
            break

def cash_credit(cash: list, account_id, amount_thb: float, rate: float):
    for acc in cash:
        if acc["id"] == account_id:
            credit = round(amount_thb / rate if acc["currency"] == "USD" else amount_thb, 2)
            acc["amount"] = round(acc["amount"] + credit, 2)
            break

def acc_label(acc: dict) -> str:
    sym = "$" if acc["currency"] == "USD" else "฿"
    return f"{acc['name']} ({acc['currency']} {sym}{acc['amount']:,.0f})"

def source_selector(cash: list, form_key: str) -> tuple:
    """Returns (selectbox_index, other_name_input, other_currency_input) inside a form."""
    ids     = [a["id"] for a in cash] + ["other"]
    labels  = [acc_label(a) for a in cash] + ["💼 Other Cash (ระบุเอง)"]
    sc1, sc2, sc3 = st.columns(3)
    idx          = sc1.selectbox("จ่ายจากบัญชีไหน", range(len(ids)),
                                  format_func=lambda i: labels[i], key=f"src_{form_key}")
    other_name   = sc2.text_input("ชื่อบัญชี (ถ้าเลือก Other Cash)",
                                   placeholder="เช่น Dime", key=f"src_name_{form_key}")
    other_curr   = sc3.selectbox("สกุลเงิน Other Cash", ["THB", "USD"],
                                  key=f"src_curr_{form_key}")
    return ids[idx], other_name, other_curr

def resolve_source(cash: list, source_id, other_name: str, other_currency: str) -> int:
    """ถ้าเลือก other → สร้าง account ใหม่ แล้ว return id"""
    if source_id != "other":
        return source_id
    new_id = max((a["id"] for a in cash), default=0) + 1
    cash.append({"id": new_id, "name": other_name.strip() or "Other Cash",
                 "currency": other_currency, "amount": 0.0})
    return new_id


# ── Live Prices ───────────────────────────────────────────────────────────────
_DR_PATTERN = re.compile(r'^[A-Z]+\d{2}$')  # Thai DR: NINTENDO23, META24

@st.cache_data(ttl=300)
def _fetch_price(ticker: str) -> float | None:
    try:
        import yfinance as yf
        return yf.Ticker(ticker).fast_info.last_price
    except Exception:
        return None

def get_price(ticker: str) -> float | None:
    price = _fetch_price(ticker)
    if price is None and _DR_PATTERN.match(ticker.upper()):
        price = _fetch_price(ticker.upper() + ".BK")
    return price

@st.cache_data(ttl=60)
def get_usd_thb() -> float:
    try:
        import yfinance as yf
        rate = yf.Ticker("THB=X").fast_info.last_price
        return rate if rate and rate > 1 else 35.0
    except Exception:
        return 35.0


# ── Math Helpers ──────────────────────────────────────────────────────────────
def parse(val) -> float | None:
    try: return float(str(val).replace(",", "").strip())
    except Exception: return None

def get_shares(item: dict) -> str:
    return item.get("shares") or item.get("size") or "1"

def get_currency(item: dict) -> str:
    if item.get("currency"): return item["currency"]
    return "THB" if item.get("ticker","").endswith(".BK") else "USD"

def calc_position_thb(entry, shares, currency: str, rate: float) -> float | None:
    e, s = parse(entry), parse(shares)
    if e is None or s is None: return None
    return round(s * e * (rate if currency == "USD" else 1), 2)

def calc_pnl_pct(entry, current: float, direction: str = "Long") -> float | None:
    e = parse(entry)
    if e is None: return None
    pct = (current - e) / e * 100
    return round(-pct if direction == "Short" else pct, 2)

def calc_pnl_thb(entry, current: float, shares, trade_currency: str,
                 rate: float, direction: str = "Long") -> float | None:
    e, s = parse(entry), parse(shares)
    if e is None or s is None: return None
    diff = (current - e) * (-1 if direction == "Short" else 1)
    return round(diff * s * (rate if trade_currency == "USD" else 1), 2)

def auto_rr(entry, sl, tp) -> str:
    e, s, t = parse(entry), parse(sl), parse(tp)
    if None in (e, s, t) or abs(e - s) == 0: return "—"
    return f"1:{abs(t-e)/abs(e-s):.1f}"

def fmt_pct(val) -> str:
    if not isinstance(val, (int, float)): return "—"
    return f"{'+' if val>=0 else ''}{val:.2f}%"

def fmt_money(val_thb: float | None, disp: str, rate: float, sign: bool = True) -> str:
    if val_thb is None: return "—"
    if disp == "USD":
        v = val_thb / rate
        prefix = ("+" if v >= 0 else "-") if sign else ("" if v >= 0 else "-")
        return f"{prefix}${abs(v):,.2f}"
    prefix = ("+" if val_thb >= 0 else "-") if sign else ("" if val_thb >= 0 else "-")
    return f"{prefix}฿{abs(val_thb):,.0f}"

def to_display(val_thb: float | None, disp: str, rate: float) -> float | None:
    if val_thb is None: return None
    return val_thb / rate if disp == "USD" else val_thb

def get_inv_price(inv: dict) -> float | None:
    """manual_price ถ้าตั้งไว้ มิเช่นนั้น get_price (auto-.BK สำหรับ DR)"""
    mp = parse(inv.get("manual_price"))
    return mp if mp is not None else get_price(inv.get("ticker", ""))

def days_held_str(entry_date_str: str) -> str:
    try:
        d    = date.fromisoformat(str(entry_date_str))
        days = (date.today() - d).days
        if days < 0:   return "—"
        if days < 30:  return f"{days}d"
        months = days // 30
        if months < 12: return f"{months}m {days % 30}d"
        return f"{months // 12}y {months % 12}m"
    except Exception:
        return "—"


# ── Chart Helpers ─────────────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e2e8f0", size=13),
    showlegend=False,
    margin=dict(t=32, b=8, l=8, r=8),
    xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#94a3b8")),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
               tickfont=dict(size=11, color="#64748b"), zeroline=True,
               zerolinecolor="rgba(255,255,255,0.15)"),
)

def allocation_pie(labels, vals_thb, disp, rate, title, height=320):
    vals = [to_display(v, disp, rate) for v in vals_thb]
    total = sum(v for v in vals if v)
    colors = ["#5865f2","#22c55e","#f59e0b","#ef4444","#06b6d4",
              "#a855f7","#ec4899","#84cc16","#f97316","#14b8a6"]
    fig = go.Figure(go.Pie(
        labels=labels, values=vals, hole=0.45,
        textinfo="label+percent", textfont=dict(size=12, color="#e2e8f0"),
        marker=dict(colors=colors[:len(labels)],
                    line=dict(color="rgba(0,0,0,0.3)", width=1)),
    ))
    sym = "฿" if disp == "THB" else "$"
    fig.update_layout(**{**CHART_LAYOUT,
        "title": dict(text=title, font=dict(size=14, color="#94a3b8"), x=0),
        "height": height, "showlegend": True,
        "legend": dict(font=dict(color="#94a3b8", size=11), orientation="v"),
        "annotations": [dict(text=f"{sym}{total:,.0f}", x=0.5, y=0.5,
                              font=dict(size=15, color="#e2e8f0"), showarrow=False)],
    })
    return fig

@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker: str, period: str, interval: str):
    try:
        import yfinance as yf
        import pandas as pd
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        return df["Close"] if not df.empty else None
    except Exception:
        return None

def portfolio_line_chart(open_items: list, cash_thb: float, rate: float,
                         disp: str, period_label: str, height=300):
    import pandas as pd
    period_map = {"1D": ("1d","1h"), "1W": ("5d","1d"),
                  "1M": ("1mo","1d"), "1Y": ("1y","1wk")}
    period, interval = period_map.get(period_label, ("1mo","1d"))

    histories = {}
    for item in open_items:
        t = item.get("ticker","")
        if t and t not in histories:
            h = get_history(t, period, interval)
            if h is not None:
                histories[t] = h

    if not histories:
        return None

    combined = pd.DataFrame(histories).ffill().bfill()
    if combined.empty:
        return None

    port_vals = []
    for dt, row in combined.iterrows():
        v = cash_thb
        for item in open_items:
            t = item.get("ticker","")
            if t in row.index and pd.notna(row[t]):
                s = parse(get_shares(item)) or 0
                v += s * row[t] * (rate if get_currency(item) == "USD" else 1)
        port_vals.append(to_display(v, disp, rate))

    dates = list(combined.index)
    pct = (port_vals[-1] - port_vals[0]) / port_vals[0] * 100 if port_vals[0] else 0
    color_pct = "#22c55e" if pct >= 0 else "#ef4444"
    sym = "฿" if disp == "THB" else "$"
    sign = "+" if pct >= 0 else ""

    fig = go.Figure(go.Scatter(
        x=dates, y=port_vals, mode="lines",
        line=dict(color="#5865f2", width=2.5),
        fill="tozeroy", fillcolor="rgba(88,101,242,0.08)",
    ))
    fig.update_layout(**{**CHART_LAYOUT,
        "title": dict(
            text=f"Portfolio Value  "
                 f"<span style='color:{color_pct};font-size:14px'>{sign}{pct:.2f}%</span>",
            font=dict(size=14, color="#94a3b8"), x=0),
        "yaxis_title": f"Value ({sym})", "height": height,
        "yaxis_tickformat": ",.0f",
        "xaxis": dict(showgrid=False, tickfont=dict(size=11, color="#94a3b8")),
    })
    return fig

def portfolio_return_chart(open_items: list, rate: float, disp: str, period_label: str,
                           show_spy=False, show_qqq=False, height=300):
    import pandas as pd
    period_map = {"1D": ("1d","1h"), "1W": ("5d","1d"), "1M": ("1mo","1d"), "1Y": ("1y","1wk")}
    period, interval = period_map.get(period_label, ("1mo","1d"))

    histories = {}
    for item in open_items:
        t = item.get("ticker","")
        if t and t not in histories:
            h = get_history(t, period, interval)
            if h is not None:
                histories[t] = h
    if not histories:
        return None

    combined = pd.DataFrame(histories).ffill().bfill()
    if combined.empty:
        return None

    port_vals = []
    for _, row in combined.iterrows():
        v = 0.0
        for item in open_items:
            t = item.get("ticker","")
            if t in row.index and pd.notna(row[t]):
                s = parse(get_shares(item)) or 0
                v += s * float(row[t]) * (rate if get_currency(item) == "USD" else 1)
        port_vals.append(v)

    if not port_vals or port_vals[0] == 0:
        return None

    base   = port_vals[0]
    ret_pcts = [(v - base) / base * 100 for v in port_vals]
    dates    = list(combined.index)
    final    = ret_pcts[-1]
    col      = "#22c55e" if final >= 0 else "#ef4444"
    sign     = "+" if final >= 0 else ""

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=ret_pcts, mode="lines", name="Portfolio",
        line=dict(color="#5865f2", width=2.5),
        fill="tozeroy", fillcolor="rgba(88,101,242,0.08)",
    ))

    for ticker, label, color in [("SPY", "S&P 500", "#f59e0b"), ("QQQ", "NASDAQ 100", "#a78bfa")]:
        if (ticker == "SPY" and show_spy) or (ticker == "QQQ" and show_qqq):
            h = get_history(ticker, period, interval)
            if h is not None:
                h_al = h.reindex(combined.index, method="ffill").dropna()
                if len(h_al) > 0:
                    b0 = float(h_al.iloc[0])
                    fig.add_trace(go.Scatter(
                        x=list(h_al.index),
                        y=[(float(v) - b0) / b0 * 100 for v in h_al],
                        mode="lines", name=label,
                        line=dict(color=color, width=1.5, dash="dot"),
                    ))

    fig.update_layout(**{**CHART_LAYOUT,
        "title": dict(
            text=(f"Return %  <span style='color:{col};font-size:14px'>{sign}{final:.2f}%</span>"
                  f"<br><span style='font-size:10px;color:#64748b'>ราคา-based · ไม่นับเวลาที่ซื้อจริง</span>"),
            font=dict(size=14, color="#94a3b8"), x=0),
        "yaxis_title": "Return (%)", "height": height,
        "yaxis_tickformat": ".2f", "yaxis_ticksuffix": "%",
        "xaxis": dict(showgrid=False, tickfont=dict(size=11, color="#94a3b8")),
        "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    })
    return fig

def build_activity_log(investments: list, trades: list) -> list:
    events = []
    for inv in investments:
        ticker = inv.get("ticker","—")
        if inv.get("entry_date"):
            events.append({"วันที่": inv.get("entry_date",""), "ประเภท": "💼 Invest",
                "Action": "🟢 ซื้อ", "Ticker": ticker,
                "รายละเอียด": f"เปิด · {get_shares(inv)} shares @ {inv.get('entry_price','—')}"})
        for bh in inv.get("buy_history", []):
            events.append({"วันที่": bh.get("date",""), "ประเภท": "💼 Invest",
                "Action": "➕ ซื้อเพิ่ม", "Ticker": ticker,
                "รายละเอียด": f"+{bh.get('shares','?')} shares @ {bh.get('price','—')}"})
        for sh in inv.get("sell_history", []):
            pnl_s = f"฿{sh.get('pnl_thb',0):,.0f}" if sh.get("pnl_thb") is not None else "—"
            events.append({"วันที่": sh.get("date",""), "ประเภท": "💼 Invest",
                "Action": "🔴 ขายบางส่วน", "Ticker": ticker,
                "รายละเอียด": f"-{sh.get('shares','?')} shares @ {sh.get('price','—')} · P&L {pnl_s}"})
        if inv.get("status") == "closed" and inv.get("exit_date"):
            events.append({"วันที่": inv.get("exit_date",""), "ประเภท": "💼 Invest",
                "Action": "🔴 ปิด", "Ticker": ticker,
                "รายละเอียด": f"ปิด @ {inv.get('exit_price','—')} · P&L {fmt_pct(inv.get('pnl_pct'))}"})
    for t in trades:
        ticker = t.get("ticker","—")
        arr = "↑" if t.get("direction") == "Long" else "↓"
        if t.get("open_date"):
            events.append({"วันที่": t.get("open_date",""), "ประเภท": "📈 Trade",
                "Action": "🟢 เปิด", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"{get_shares(t)} shares @ {t.get('entry_price','—')} · SL {t.get('stop_loss','—')} · TP {t.get('take_profit','—')}"})
        for bh in t.get("buy_history", []):
            events.append({"วันที่": bh.get("date",""), "ประเภท": "📈 Trade",
                "Action": "➕ ซื้อเพิ่ม", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"+{bh.get('shares','?')} shares @ {bh.get('price','—')}"})
        for sh in t.get("sell_history", []):
            pnl_s = f"฿{sh.get('pnl_thb',0):,.0f}" if sh.get("pnl_thb") is not None else "—"
            events.append({"วันที่": sh.get("date",""), "ประเภท": "📈 Trade",
                "Action": "🔴 ขายบางส่วน", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"-{sh.get('shares','?')} shares @ {sh.get('price','—')} · P&L {pnl_s}"})
        if t.get("status") == "closed" and t.get("close_date"):
            events.append({"วันที่": t.get("close_date",""), "ประเภท": "📈 Trade",
                "Action": "🔴 ปิด", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"ปิด @ {t.get('exit_price','—')} · P&L {fmt_pct(t.get('pnl_pct'))} · {t.get('win_loss','')}"})
    events.sort(key=lambda e: e.get("วันที่",""), reverse=True)
    return events

def pnl_bar_chart(labels, vals_thb, disp, rate, title, height=280):
    vals   = [to_display(v, disp, rate) for v in vals_thb]
    texts  = [fmt_money(v, disp, rate) for v in vals_thb]
    colors = ["#22c55e" if (v or 0) >= 0 else "#ef4444" for v in vals_thb]
    fig = go.Figure(go.Bar(
        x=labels, y=vals,
        marker=dict(color=colors, opacity=0.85,
                    line=dict(color="rgba(255,255,255,0.1)", width=1)),
        text=texts, textposition="outside",
        textfont=dict(size=13, color="#e2e8f0"), cliponaxis=False,
    ))
    sym = "฿" if disp == "THB" else "$"
    fig.update_layout(**{**CHART_LAYOUT,
        "title": dict(text=title, font=dict(size=14, color="#94a3b8"), x=0),
        "yaxis_title": f"P&L ({sym})", "height": height, "yaxis_tickformat": ",.0f",
    })
    if vals:
        maxv = max(abs(v) for v in vals if v is not None) or 1
        fig.update_yaxes(range=[-maxv * 1.35, maxv * 1.35])
    return fig


# ── UI Helpers ────────────────────────────────────────────────────────────────
def section(title: str):
    st.markdown(f'<div class="section-label">{title}</div>', unsafe_allow_html=True)

def strategy_input(key: str, default: str = "") -> str:
    preset = default if default in STRATEGY_PRESETS else STRATEGY_PRESETS[0]
    choice = st.selectbox("Strategy", STRATEGY_PRESETS,
                          index=STRATEGY_PRESETS.index(preset), key=f"{key}_sel")
    if choice == "Others":
        cv = default if default not in STRATEGY_PRESETS else ""
        return st.text_input("พิมพ์ Strategy เอง", value=cv,
                             placeholder="เช่น Gap Fill, EMA Crossover...", key=f"{key}_txt")
    return choice

def next_id(items: list) -> int:
    return max((i["id"] for i in items), default=0) + 1

def page_header(title: str, subtitle: str = "") -> tuple[str, float]:
    """Page title (left) + currency toggle (right). Returns (disp, rate)."""
    rate = get_usd_thb()
    col_t, _, col_c = st.columns([6, 2, 2])
    with col_t:
        st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
        if subtitle:
            st.markdown(f'<div class="page-sub">{subtitle}</div>', unsafe_allow_html=True)
    with col_c:
        disp = st.radio("", ["THB", "USD"], horizontal=True,
                        key="display_currency", label_visibility="collapsed")
        st.caption(f"1 USD = ฿{rate:.2f}")
    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
    return disp, rate


# ── Login Page ────────────────────────────────────────────────────────────────
def page_login():
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("<div style='height:3rem'></div>", unsafe_allow_html=True)
        st.markdown("## 📊 Tim.fin OS")
        st.markdown("ระบบติดตาม Portfolio ส่วนตัว")
        st.markdown("---")
        tab_in, tab_up = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก"])

        with tab_in:
            with st.form("login_form"):
                email    = st.text_input("Email")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("เข้าสู่ระบบ", use_container_width=True):
                    if not email or not password:
                        st.error("กรุณากรอก Email และ Password")
                    else:
                        result = sb_signin(email.strip(), password)
                        if result == "connection_error":
                            st.error("⚠️ เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณารีเฟรชหน้าแล้วลองใหม่")
                        elif result and "access_token" in result:
                            st.session_state["sb_session"] = result
                            st.rerun()
                        else:
                            st.error("Email หรือ Password ไม่ถูกต้อง")

        with tab_up:
            with st.form("signup_form"):
                email    = st.text_input("Email")
                password = st.text_input("Password (อย่างน้อย 6 ตัวอักษร)", type="password")
                if st.form_submit_button("สมัครสมาชิก", use_container_width=True):
                    if not email or len(password) < 6:
                        st.error("กรุณากรอก Email และ Password อย่างน้อย 6 ตัว")
                    else:
                        result, err = sb_signup(email.strip(), password)
                        if result is not None:
                            st.success("✅ สมัครสมาชิกสำเร็จ! กรุณาตรวจสอบ Email เพื่อยืนยันตัวตน แล้วกลับมา Login")
                        else:
                            st.error(f"สมัครไม่สำเร็จ: {err}")


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar() -> str:
    with st.sidebar:
        st.markdown("### 📊 Tim.fin OS")
        if is_logged_in():
            email = st.session_state["sb_session"]["user"]["email"]
            st.caption(f"👤 {email}")
            if st.button("ออกจากระบบ", use_container_width=True):
                del st.session_state["sb_session"]
                st.rerun()
        st.markdown("---")
        page = st.radio("", ["📊 Overview", "💼 Investment", "📈 Trade", "💵 Cash", "📓 Log"],
                        label_visibility="collapsed")
        st.markdown("---")
        st.caption("Tim.fin Personal OS")
    return page


# ── Page 1: Overview ──────────────────────────────────────────────────────────
def page_overview(trades: list, investments: list, cash: list, disp: str, rate: float):
    # ── Account Filter ────────────────────────────────────────────────────────
    all_acct_names = sorted(set(
        i.get("source_account_name","") for i in investments if i.get("source_account_name")
    ) | set(a["name"] for a in cash))
    ov_filter = st.multiselect("แสดงพอร์ต", all_acct_names,
                               placeholder="Overall — แสดงทั้งหมด", key="ov_acct_filter")

    open_trades   = [t for t in trades      if t.get("status") == "open"]
    closed_trades = [t for t in trades      if t.get("status") == "closed"]
    open_inv      = [i for i in investments if i.get("status") == "open"]
    wins          = [t for t in closed_trades if t.get("win_loss") == "Win"]

    if ov_filter:
        open_inv    = [i for i in open_inv    if i.get("source_account_name") in ov_filter]
        cash        = [a for a in cash        if a["name"] in ov_filter]
        open_trades = [t for t in open_trades if t.get("source_account_name") in ov_filter]

    # Portfolio Value = positions + cash
    cash_thb = sum(a["amount"] * rate if a["currency"] == "USD" else a["amount"] for a in cash)
    port_thb = cash_thb
    for item in open_trades + open_inv:
        price = get_price(item.get("ticker",""))
        ref   = str(price) if price else item.get("entry_price")
        p     = calc_position_thb(ref, get_shares(item), get_currency(item), rate)
        if p: port_thb += p

    # Unrealized P&L
    unreal_thb  = 0.0
    unreal_items = []
    for item in open_trades + open_inv:
        price = get_price(item.get("ticker",""))
        if price is None: continue
        direction = item.get("direction", "Long")
        pnl = calc_pnl_thb(item.get("entry_price"), price, get_shares(item),
                            get_currency(item), rate, direction)
        if pnl is not None:
            unreal_thb += pnl
            label = f"{item['ticker']} ({'Trade' if item.get('type')=='trade' else 'Hold'})"
            unreal_items.append({"label": label, "pnl_thb": pnl})

    realized_thb = sum(t.get("pnl_thb", 0) or 0 for t in closed_trades)
    win_rate     = len(wins) / len(closed_trades) * 100 if closed_trades else None

    cost_basis_thb = 0.0
    for _item in open_trades + open_inv:
        _s = parse(get_shares(_item))
        _e = parse(_item.get("entry_price",""))
        if _s and _e:
            cost_basis_thb += _s * _e * (rate if get_currency(_item) == "USD" else 1)

    # ── KPI Row ───────────────────────────────────────────────────────────────
    section("Portfolio Summary")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Wealth (incl. Cash)",
              fmt_money(port_thb, disp, rate, sign=False) if port_thb else "No data yet")
    k2.metric("Deployed (Cost Basis)",
              fmt_money(cost_basis_thb if cost_basis_thb else None, disp, rate, sign=False)
              if cost_basis_thb else "No holdings")
    _unreal_ret_pct = unreal_thb / cost_basis_thb * 100 if cost_basis_thb and unreal_items else None
    k3.metric("Unrealized P&L",
              fmt_money(unreal_thb if unreal_items else None, disp, rate),
              delta=fmt_pct(_unreal_ret_pct))
    k4.metric("Realized P&L",
              fmt_money(realized_thb if closed_trades else None, disp, rate)
              if closed_trades else "No trades closed")

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── Return % Chart ────────────────────────────────────────────────────────
    open_all = open_trades + open_inv
    if open_all:
        section("Price Return — ช่วงเวลาที่เลือก")
        st.caption("📊 วัดว่า holdings ปัจจุบันเปลี่ยนราคาเท่าไหร่ในช่วงนั้น · ไม่ใช่ return ตั้งแต่วันที่ซื้อจริง · ดู Unrealized P&L ด้านบนสำหรับ return จากต้นทุนของคุณ")
        rc1, rc2, rc3 = st.columns([3, 4, 3])
        with rc1:
            ret_view = st.radio("", ["Overall","Investment","Trade"], horizontal=True,
                                key="ret_view", label_visibility="collapsed")
        with rc2:
            ret_period = st.radio("", ["1D","1W","1M","1Y"], horizontal=True,
                                  key="ret_period", index=2, label_visibility="collapsed")
        with rc3:
            cspy = st.checkbox("S&P 500", key="cmp_spy")
            cqqq = st.checkbox("NASDAQ 100", key="cmp_qqq")

        ret_items = (open_inv if ret_view == "Investment"
                     else open_trades if ret_view == "Trade"
                     else open_all)
        fig_ret = portfolio_return_chart(ret_items, rate, disp, ret_period,
                                         show_spy=cspy, show_qqq=cqqq, height=280)
        if fig_ret:
            st.plotly_chart(fig_ret, use_container_width=True)
        else:
            st.info("ไม่มีข้อมูลราคาย้อนหลัง")

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Allocation Pie + Portfolio Line ───────────────────────────────────────
    if open_all or cash_thb > 0:
        section("Portfolio Breakdown")
        col_pie, col_line = st.columns([4, 6])

        with col_pie:
            pie_labels, pie_vals = [], []
            for item in open_all:
                price = get_price(item.get("ticker",""))
                ref   = str(price) if price else item.get("entry_price")
                pos   = calc_position_thb(ref, get_shares(item), get_currency(item), rate)
                if pos:
                    pie_labels.append(item.get("ticker","?"))
                    pie_vals.append(pos)
            if cash_thb > 0:
                pie_labels.append("💵 Cash")
                pie_vals.append(cash_thb)
            if pie_labels:
                st.plotly_chart(allocation_pie(pie_labels, pie_vals, disp, rate,
                                               "Asset Allocation", height=320),
                                use_container_width=True)

        with col_line:
            period = st.radio("", ["1D","1W","1M","1Y"], horizontal=True,
                               key="port_period", index=2)
            fig_line = portfolio_line_chart(open_all, cash_thb, rate, disp, period)
            if fig_line:
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("ไม่มีข้อมูลราคาย้อนหลัง")

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── P&L Charts + Snapshot ─────────────────────────────────────────────────
    section("Performance")
    col_chart, col_snap = st.columns([7, 3])

    with col_chart:
        if unreal_items:
            st.plotly_chart(
                pnl_bar_chart([d["label"] for d in unreal_items],
                              [d["pnl_thb"] for d in unreal_items],
                              disp, rate, "Unrealized P&L by Position", height=280),
                use_container_width=True)
        closed_with_pnl = [t for t in closed_trades if t.get("pnl_thb") is not None]
        if closed_with_pnl:
            st.plotly_chart(
                pnl_bar_chart([t["ticker"] for t in closed_with_pnl],
                              [t["pnl_thb"] for t in closed_with_pnl],
                              disp, rate, "Realized P&L — Trade History", height=240),
                use_container_width=True)
        if not unreal_items and not closed_with_pnl:
            st.info("เพิ่ม Trade หรือ Investment เพื่อดู chart")

    with col_snap:
        st.markdown("**Portfolio Snapshot**")
        for label, val in [
            ("Investment Positions", len(open_inv)),
            ("Open Trades",          len(open_trades)),
            ("Closed Trades",        len(closed_trades)),
            ("Total Positions",      len(open_inv) + len(open_trades)),
        ]:
            a, b = st.columns([3, 1])
            a.caption(label)
            b.markdown(f"**{val}**")

        if open_inv + open_trades:
            st.divider()
            st.caption("Active Tickers")
            tickers = [i.get("ticker","") for i in open_inv + open_trades]
            st.markdown("  ·  ".join(tickers))

    # ── Recent Activity ───────────────────────────────────────────────────────
    recent_events = build_activity_log(investments, trades)
    if recent_events:
        section("Recent Activity")
        for ev in recent_events[:5]:
            st.caption(
                f"{ev['วันที่']}  ·  {ev['ประเภท']}  {ev['Action']}  "
                f"**{ev['Ticker']}**  ·  {ev['รายละเอียด']}"
            )

    # ── Winners & Losers ──────────────────────────────────────────────────────
    closed_with_pnl = [t for t in closed_trades if t.get("pnl_thb") is not None]
    if closed_with_pnl:
        section("Winners & Losers")
        sorted_pnl = sorted(closed_with_pnl, key=lambda x: x.get("pnl_thb", 0), reverse=True)
        winners = [t for t in sorted_pnl if (t.get("pnl_thb", 0) or 0) > 0][:3]
        losers  = [t for t in sorted_pnl if (t.get("pnl_thb", 0) or 0) < 0][-3:]

        w_col, l_col = st.columns(2)
        with w_col:
            st.markdown("**🏆 Top Winners**")
            if winners:
                for t in winners:
                    st.caption(f"{t['ticker']}  ·  {fmt_pct(t.get('pnl_pct'))}  ·  {fmt_money(t.get('pnl_thb'), disp, rate)}")
            else:
                st.caption("No winners yet")
        with l_col:
            st.markdown("**📉 Top Losers**")
            if losers:
                for t in reversed(losers):
                    st.caption(f"{t['ticker']}  ·  {fmt_pct(t.get('pnl_pct'))}  ·  {fmt_money(t.get('pnl_thb'), disp, rate)}")
            else:
                st.caption("No losses yet")


# ── Page 2: Investment ────────────────────────────────────────────────────────
def page_investment(investments: list, trades: list, cash: list, disp: str, rate: float):
    open_inv   = [i for i in investments if i.get("status") == "open"]
    closed_inv = [i for i in investments if i.get("status") == "closed"]
    sym = "฿" if disp == "THB" else "$"

    # ── Account Filter ────────────────────────────────────────────────────────
    inv_acct_names  = sorted({i.get("source_account_name","") for i in open_inv if i.get("source_account_name")})
    cash_acct_names = sorted({a["name"] for a in cash})
    acct_opts   = sorted(set(inv_acct_names) | set(cash_acct_names))
    acct_filter = st.multiselect("พอร์ต (เลือกได้หลายอัน)", acct_opts,
                                  placeholder="Overall — แสดงทั้งหมด", key="inv_acct_filter")

    if acct_filter:
        open_inv      = [i for i in open_inv if i.get("source_account_name") in acct_filter]
        filtered_cash = [a for a in cash      if a["name"] in acct_filter]
    else:
        filtered_cash = cash

    # ── Summary ───────────────────────────────────────────────────────────────
    section("Summary")
    total_val_thb, total_pnl_thb, total_cost_thb = 0.0, 0.0, 0.0
    best_ticker, best_pct = "—", None

    cash_usd_total = sum(a["amount"] for a in filtered_cash if a["currency"] == "USD")
    cash_thb_total = sum(a["amount"] for a in filtered_cash if a["currency"] == "THB")
    cash_total_thb = (cash_usd_total * rate) + cash_thb_total

    for inv in open_inv:
        price = get_inv_price(inv)
        ref   = str(price) if price else inv.get("entry_price")
        pos   = calc_position_thb(ref, get_shares(inv), get_currency(inv), rate)
        if pos: total_val_thb += pos
        s_val, e_val = parse(get_shares(inv)), parse(inv.get("entry_price",""))
        if s_val and e_val:
            total_cost_thb += s_val * e_val * (rate if get_currency(inv) == "USD" else 1)
        if price:
            pnl = calc_pnl_thb(inv.get("entry_price"), price, get_shares(inv), get_currency(inv), rate)
            pct = calc_pnl_pct(inv.get("entry_price"), price)
            if pnl: total_pnl_thb += pnl
            if pct is not None and (best_pct is None or pct > best_pct):
                best_pct, best_ticker = pct, inv.get("ticker","—")

    total_pnl_pct = total_pnl_thb / total_cost_thb * 100 if total_cost_thb else None

    _pnl_c  = "#22c55e" if (total_pnl_thb or 0) >= 0 else "#ef4444"
    _cost_s = fmt_money(total_cost_thb or None, disp, rate, sign=False) if total_cost_thb else "No holdings yet"
    _pnl_s  = fmt_money(total_pnl_thb or None, disp, rate) if open_inv else "No holdings yet"
    _pct_s  = f"<span style='font-size:12px;color:{_pnl_c}'>{fmt_pct(total_pnl_pct)}</span>" if total_pnl_pct is not None else ""
    _best_s = f"{best_ticker} {fmt_pct(best_pct)}" if best_pct is not None else "—"
    _card   = "background:rgba(30,41,59,0.6);border:1px solid rgba(148,163,184,0.12);border-radius:10px;padding:12px 16px"
    _lbl    = "font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px"
    st.markdown(f"""
<div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:6px 0 10px 0'>
  <div style='{_card}'><div style='{_lbl}'>Cost Basis (Deployed)</div>
    <div style='font-size:20px;font-weight:700;color:#f1f5f9'>{_cost_s}</div></div>
  <div style='{_card}'><div style='{_lbl}'>Unrealized Return</div>
    <div style='font-size:20px;font-weight:700;color:{_pnl_c}'>{_pnl_s}</div>{_pct_s}</div>
  <div style='{_card}'><div style='{_lbl}'>Holdings</div>
    <div style='font-size:24px;font-weight:700;color:#f1f5f9'>{len(open_inv)}</div></div>
  <div style='{_card}'><div style='{_lbl}'>Best Performer</div>
    <div style='font-size:16px;font-weight:700;color:#22c55e'>{_best_s}</div></div>
</div>""", unsafe_allow_html=True)

    # ── Cash + Account Total ──────────────────────────────────────────────────
    cash_parts = []
    if cash_thb_total: cash_parts.append(f"฿{cash_thb_total:,.0f} THB")
    if cash_usd_total: cash_parts.append(f"${cash_usd_total:,.2f} USD")
    cash_inline    = " &nbsp;·&nbsp; ".join(cash_parts) if cash_parts else "฿0"
    acct_total_thb = total_val_thb + cash_total_thb
    acct_total_s   = fmt_money(acct_total_thb, disp, rate, sign=False)
    st.markdown(
        f"<div style='background:rgba(88,101,242,0.08);border:1px solid rgba(88,101,242,0.25);"
        f"border-radius:8px;padding:8px 16px;margin:6px 0 4px 0;line-height:1.5'>"
        f"<span style='font-size:11px;color:#64748b;text-transform:uppercase;"
        f"letter-spacing:0.06em'>💵 Cash</span>"
        f"&nbsp;&nbsp;"
        f"<span style='font-size:15px;font-weight:600;color:#e2e8f0'>{cash_inline}</span>"
        f"&nbsp;&nbsp;<span style='font-size:11px;color:#64748b'>· จัดการที่หน้า 💵 Cash</span>"
        f"&nbsp;&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;"
        f"<span style='font-size:11px;color:#64748b;text-transform:uppercase;"
        f"letter-spacing:0.06em'>Account Total</span>"
        f"&nbsp;&nbsp;"
        f"<span style='font-size:15px;font-weight:700;color:#94a3b8'>{acct_total_s}</span>"
        f"<span style='font-size:10px;color:#475569'>&nbsp;(positions + cash)</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Holdings Table ────────────────────────────────────────────────────────
    if not open_inv:
        st.info("ยังไม่มี Investment — เพิ่มได้ด้านล่าง")
    else:
        # Build raw data first (for sorting)
        raw = []
        pie_labels_inv, pie_vals_inv = [], []
        for inv in open_inv:
            price   = get_inv_price(inv)
            pnl_thb = calc_pnl_thb(inv.get("entry_price"), price, get_shares(inv),
                                    get_currency(inv), rate) if price else None
            pnl_pct = calc_pnl_pct(inv.get("entry_price"), price) if price else None
            ref     = str(price) if price else inv.get("entry_price")
            pos_thb = calc_position_thb(ref, get_shares(inv), get_currency(inv), rate)
            if pos_thb:
                pie_labels_inv.append(inv.get("ticker","?"))
                pie_vals_inv.append(pos_thb)
            s_v = parse(get_shares(inv))
            e_v = parse(inv.get("entry_price",""))
            cost_thb_row = s_v * e_v * (rate if get_currency(inv) == "USD" else 1) if s_v and e_v else 0
            raw.append({
                "inv": inv, "price": price,
                "pnl_thb": pnl_thb or 0, "pnl_pct": pnl_pct or 0,
                "pos_thb": pos_thb or 0, "cost_thb": cost_thb_row,
            })

        # Pie chart + Return % chart
        col_pie_inv, col_ret_inv = st.columns([4, 6])
        with col_pie_inv:
            if pie_labels_inv:
                st.plotly_chart(allocation_pie(pie_labels_inv, pie_vals_inv, disp, rate,
                                               "Holdings Allocation", height=280),
                                use_container_width=True)
        with col_ret_inv:
            inv_rp1, inv_rp2, inv_rp3 = st.columns([5, 4, 3])
            with inv_rp1:
                inv_period = st.radio("", ["1D","1W","1M","1Y"], horizontal=True,
                                      key="inv_period", index=2, label_visibility="collapsed")
            with inv_rp2:
                inv_spy = st.checkbox("S&P 500", key="inv_spy")
            with inv_rp3:
                inv_qqq = st.checkbox("NASDAQ 100", key="inv_qqq")
            fig_inv_ret = portfolio_return_chart(open_inv, rate, disp, inv_period,
                                                  show_spy=inv_spy, show_qqq=inv_qqq, height=260)
            if fig_inv_ret:
                st.plotly_chart(fig_inv_ret, use_container_width=True)
            else:
                st.info("ไม่มีข้อมูลราคาย้อนหลัง")

        # ── Target Allocation ─────────────────────────────────────────────────────
        inv_with_target = [r for r in raw if r["inv"].get("target_pct") is not None]
        if inv_with_target and total_val_thb:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            section("🎯 Target Allocation")

            t_tickers  = [r["inv"]["ticker"] for r in inv_with_target]
            curr_pcts  = [r["pos_thb"] / total_val_thb * 100 if total_val_thb else 0
                          for r in inv_with_target]
            tgt_pcts   = [r["inv"].get("target_pct", 0) for r in inv_with_target]
            deltas     = [c - t for c, t in zip(curr_pcts, tgt_pcts)]
            total_tgt  = sum(t for t in tgt_pcts if t)

            def _tgt_color(d):
                if abs(d) <= 3: return "#22c55e"
                if abs(d) <= 8: return "#f59e0b"
                return "#ef4444"
            bar_colors = [_tgt_color(d) for d in deltas]

            fig_tgt = go.Figure()
            fig_tgt.add_trace(go.Bar(
                name="Target %", y=t_tickers, x=tgt_pcts, orientation="h",
                marker_color="rgba(148,163,184,0.25)",
                marker_line=dict(color="#94a3b8", width=1),
                text=[f"{p:.0f}%" for p in tgt_pcts], textposition="inside",
                textfont=dict(size=11, color="#94a3b8"),
            ))
            fig_tgt.add_trace(go.Bar(
                name="Current %", y=t_tickers, x=curr_pcts, orientation="h",
                marker_color=bar_colors, opacity=0.85,
                text=[f"{p:.1f}%" for p in curr_pcts], textposition="outside",
                textfont=dict(size=11, color="#e2e8f0"),
            ))
            fig_tgt.update_layout(
                **{**CHART_LAYOUT,
                   "barmode": "overlay",
                   "height": max(200, len(t_tickers) * 45 + 70),
                   "showlegend": True,
                   "legend": dict(orientation="h", y=1.1, x=0, font=dict(size=11, color="#94a3b8")),
                   "margin": dict(t=50, b=8, l=8, r=80),
                   "xaxis": dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                                 ticksuffix="%", tickfont=dict(size=11, color="#94a3b8")),
                   "yaxis": dict(showgrid=False, tickfont=dict(size=12, color="#e2e8f0")),
                   "title": dict(
                       text=(f"Current vs Target  "
                             f"<span style='font-size:11px;color:#64748b'>"
                             f"Target รวม {total_tgt:.0f}% · Cash {max(0, 100-total_tgt):.0f}%</span>"),
                       font=dict(size=13, color="#94a3b8"), x=0),
                }
            )
            st.plotly_chart(fig_tgt, use_container_width=True)

            sym_r = "฿" if disp == "THB" else "$"
            rebal_rows = []
            for r, curr_p, tgt_p, delta in zip(inv_with_target, curr_pcts, tgt_pcts, deltas):
                action_thb = abs(delta) / 100 * total_val_thb
                action_disp = to_display(action_thb, disp, rate)
                if tgt_p == 0:
                    action = "—"
                elif delta > 3:
                    action = f"🔴 ขายลด {sym_r}{action_disp:,.0f}"
                elif delta < -3:
                    action = f"🟢 ซื้อเพิ่ม {sym_r}{action_disp:,.0f}"
                else:
                    action = "✅ ใกล้เป้า"
                rebal_rows.append({
                    "Ticker":   r["inv"]["ticker"],
                    "Current":  f"{curr_p:.1f}%",
                    "Target":   f"{tgt_p:.0f}%",
                    "Δ":        f"{'+' if delta >= 0 else ''}{delta:.1f}%",
                    "Action":   action,
                })
            st.dataframe(rebal_rows, use_container_width=True, hide_index=True)

            no_target = [r["inv"]["ticker"] for r in raw if r["inv"].get("target_pct") is None]
            if no_target:
                st.caption(f"ยังไม่ตั้ง Target %: {', '.join(no_target)} — กดแก้ไขใน position เพื่อตั้งค่า")

        # Sort selector (above table)
        sort_by = st.selectbox("เรียงตาม", [
            "📊 Size (ใหญ่ → เล็ก)",
            "📈 Gain (มาก → น้อย)",
            "📉 Loss (มาก → น้อย)",
            "🔤 Ticker (A → Z)",
            f"💰 P&L {sym} (มาก → น้อย)",
        ], key="inv_sort")
        sort_fns = {
            "📊 Size (ใหญ่ → เล็ก)":    lambda r: -r["pos_thb"],
            "📈 Gain (มาก → น้อย)":      lambda r: -r["pnl_pct"],
            "📉 Loss (มาก → น้อย)":      lambda r:  r["pnl_pct"],
            "🔤 Ticker (A → Z)":          lambda r:  r["inv"].get("ticker",""),
            f"💰 P&L {sym} (มาก → น้อย)": lambda r: -r["pnl_thb"],
        }
        raw.sort(key=sort_fns.get(sort_by, lambda r: -r["pos_thb"]))

        # Build display rows
        section(f"Current Holdings ({len(open_inv)})")
        total_mv, total_pnl_disp, total_cost_disp = 0.0, 0.0, 0.0
        rows = []
        for i, r in enumerate(raw):
            inv, price = r["inv"], r["price"]
            mv     = to_display(r["pos_thb"] or 0, disp, rate)
            pnl_d  = to_display(r["pnl_thb"] or 0, disp, rate)
            cost_d = to_display(r["cost_thb"] or 0, disp, rate)
            if price:
                total_mv   += mv
                total_pnl_disp += pnl_d
            total_cost_disp += cost_d
            rows.append({
                "#":             i + 1,
                "Ticker":        inv.get("ticker","—"),
                "ถือมา":         days_held_str(inv.get("entry_date","")),
                "Shares":        get_shares(inv),
                "Avg Cost":      inv.get("entry_price","—"),
                "Total Cost":    fmt_money(r["cost_thb"] or None, disp, rate, sign=False) if r["cost_thb"] else "—",
                "Current Price": (f"📌 {price:.2f}" if inv.get("manual_price") else f"{price:.2f}") if price else "—",
                "Market Value":  fmt_money(r["pos_thb"] or None, disp, rate, sign=False),
                "P&L %":         fmt_pct(r["pnl_pct"]) if price else "—",
                f"P&L ({sym})":  fmt_money(r["pnl_thb"] or None, disp, rate) if price else "—",
                "Thesis":        inv.get("thesis","—"),
            })

        # Total row
        sym_p = "฿" if disp == "THB" else "$"
        total_pnl_pct_row = total_pnl_disp / (total_mv - total_pnl_disp) * 100 if (total_mv - total_pnl_disp) else 0
        rows.append({
            "#":             "—",
            "Ticker":        "📊 TOTAL",
            "Shares":        "—",
            "Avg Cost":      "—",
            "Total Cost":    f"{sym_p}{total_cost_disp:,.0f}",
            "Current Price": "—",
            "Market Value":  f"{sym_p}{total_mv:,.0f}",
            "ถือมา":         "—",
            "P&L %":         fmt_pct(total_pnl_pct_row),
            f"P&L ({sym})":  fmt_money(sum(r["pnl_thb"] for r in raw if r.get("price")), disp, rate),
            "Thesis":        "—",
        })

        pnl_cols = ["P&L %", f"P&L ({sym})"]

        def _color_pnl(val):
            if isinstance(val, str) and val.startswith("+"):
                return "color: #22c55e; font-weight: 600"
            if isinstance(val, str) and val.startswith("-"):
                return "color: #ef4444; font-weight: 600"
            return ""

        def _style_total(row):
            if row["Ticker"] == "📊 TOTAL":
                return ["background-color: rgba(88,101,242,0.12); font-weight: 700"] * len(row)
            return [""] * len(row)

        df_inv = pd.DataFrame(rows)
        try:
            styled = (df_inv.style
                      .map(_color_pnl, subset=pnl_cols)
                      .apply(_style_total, axis=1)
                      .hide(axis="index"))
        except AttributeError:
            styled = (df_inv.style
                      .applymap(_color_pnl, subset=pnl_cols)
                      .apply(_style_total, axis=1)
                      .hide(axis="index"))
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Position actions (ปิด/ลบ)
        section("Position Actions")
        for inv in open_inv:
            price   = get_price(inv.get("ticker",""))
            pnl_thb = calc_pnl_thb(inv.get("entry_price"), price, get_shares(inv),
                                    get_currency(inv), rate) if price else None
            pnl_pct = calc_pnl_pct(inv.get("entry_price"), price) if price else None
            icon    = "🟢" if (pnl_thb or 0) >= 0 else "🔴"

            _ihc = "green" if (pnl_thb or 0) >= 0 else "red"
            inv_label = (f"{icon} **{inv['ticker']}**  ·  "
                         f"AVG {inv.get('entry_price','—')}  ·  "
                         f"{get_shares(inv)} shares"
                         f"  |  :{_ihc}[{fmt_pct(pnl_pct)}  {fmt_money(pnl_thb, disp, rate)}]"
                         ).replace("$", r"\$")
            with st.expander(inv_label):
                # P&L banner
                _pc2 = "#22c55e" if (pnl_thb or 0) >= 0 else "#ef4444"
                _bg2 = "rgba(34,197,94,0.08)" if (pnl_thb or 0) >= 0 else "rgba(239,68,68,0.08)"
                _cp  = get_price(inv.get("ticker",""))
                _pos = calc_position_thb(str(_cp) if _cp else inv.get("entry_price"), get_shares(inv), get_currency(inv), rate)
                st.markdown(
                    f"<div style='background:{_bg2};border-left:3px solid {_pc2};"
                    f"border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:10px'>"
                    f"<div style='font-size:10px;color:#94a3b8;text-transform:uppercase;"
                    f"letter-spacing:0.07em;margin-bottom:2px'>Unrealized P&L</div>"
                    f"<span style='font-size:22px;font-weight:700;color:{_pc2}'>"
                    f"{fmt_money(pnl_thb, disp, rate) if pnl_thb is not None else '—'}</span>"
                    f"&nbsp;&nbsp;<span style='font-size:13px;color:{_pc2}'>{fmt_pct(pnl_pct)}</span>"
                    f"&nbsp;&nbsp;&nbsp;<span style='font-size:11px;color:#64748b'>"
                    f"Price {f'{_cp:.2f}' if _cp else '—'}  ·  Value {fmt_money(_pos, disp, rate, sign=False)}</span>"
                    f"</div>",
                    unsafe_allow_html=True)
                ca, cb, cc, _, cd = st.columns([2, 2, 2, 1, 1])
                if ca.button("🔴 ขาย", key=f"ci_{inv['id']}"):
                    st.session_state[f"sell_inv_{inv['id']}"] = True
                    st.session_state.pop(f"edit_inv_{inv['id']}", None)
                    st.session_state.pop(f"add_inv_{inv['id']}", None)
                if cb.button("✏️ แก้ไข", key=f"ei_{inv['id']}"):
                    st.session_state[f"edit_inv_{inv['id']}"] = True
                    st.session_state.pop(f"sell_inv_{inv['id']}", None)
                    st.session_state.pop(f"add_inv_{inv['id']}", None)
                if cc.button("➕ ซื้อเพิ่ม", key=f"ai_{inv['id']}"):
                    st.session_state[f"add_inv_{inv['id']}"] = True
                    st.session_state.pop(f"edit_inv_{inv['id']}", None)
                    st.session_state.pop(f"sell_inv_{inv['id']}", None)
                if cd.button("🗑️", key=f"di_{inv['id']}"):
                    investments[:] = [x for x in investments if x["id"] != inv["id"]]
                    save_investments(investments)
                    st.rerun()

                if st.session_state.get(f"add_inv_{inv['id']}"):
                    st.markdown("**➕ ซื้อเพิ่ม**")
                    with st.form(f"form_add_inv_{inv['id']}"):
                        aa1, aa2 = st.columns(2)
                        add_shares = aa1.text_input("จำนวนหุ้นที่ซื้อเพิ่ม *", placeholder="เช่น 5")
                        add_price  = aa2.text_input("ราคาที่ซื้อ *", placeholder="เช่น 80")
                        src_id, other_name, other_curr = source_selector(cash, f"add_inv_{inv['id']}")
                        if st.form_submit_button("✅ ซื้อเพิ่ม"):
                            s_add = parse(add_shares)
                            p_add = parse(add_price)
                            if s_add and p_add:
                                s_old = parse(get_shares(inv)) or 0
                                p_old = parse(inv.get("entry_price", "0")) or 0
                                s_new = s_old + s_add
                                p_avg = (s_old * p_old + s_add * p_add) / s_new
                                add_thb = s_add * p_add * (rate if get_currency(inv) == "USD" else 1)
                                resolved = resolve_source(cash, src_id, other_name, other_curr)
                                cash_deduct(cash, resolved, add_thb, rate)
                                save_cash(cash)
                                inv.update({
                                    "shares":       str(round(s_new, 8)),
                                    "entry_price":  str(round(p_avg, 4)),
                                    "position_thb": round((inv.get("position_thb") or 0) + add_thb, 2),
                                })
                                save_investments(investments)
                                st.session_state.pop(f"add_inv_{inv['id']}", None)
                                st.success(f"ซื้อเพิ่ม {add_shares} หุ้น @ {add_price} · AVG ใหม่ = {round(p_avg,4)}")
                                st.rerun()
                            else:
                                st.error("กรุณากรอกจำนวนหุ้นและราคา")

                if st.session_state.get(f"edit_inv_{inv['id']}"):
                    st.markdown("**แก้ไข Investment**")
                    with st.form(f"form_edit_inv_{inv['id']}"):
                        ei1, ei2, ei3 = st.columns(3)
                        new_ticker = ei1.text_input("Ticker",       value=inv.get("ticker",""))
                        new_shares = ei2.text_input("จำนวนหุ้น",    value=get_shares(inv))
                        new_entry  = ei3.text_input("Entry Price",  value=inv.get("entry_price",""))
                        ee1, ee2 = st.columns(2)
                        new_thesis  = ee1.text_input("Thesis", value=inv.get("thesis",""))
                        new_tgt_raw = ee2.text_input(
                            "Target % (สัดส่วนเป้าหมาย)",
                            value=str(inv["target_pct"]) if inv.get("target_pct") is not None else "",
                            placeholder="เช่น 20  (ว่าง = ไม่ตั้ง)",
                        )
                        new_manual_price = st.text_input(
                            "📌 Manual Price (DR / หุ้นที่ดึงราคาไม่ได้)",
                            value=str(inv["manual_price"]) if inv.get("manual_price") is not None else "",
                            placeholder="ใส่ราคาปัจจุบัน เช่น 85.50  (ว่าง = ดึงจาก yfinance)",
                        )
                        if st.form_submit_button("💾 บันทึก"):
                            upd = {
                                "ticker":      new_ticker.upper().strip(),
                                "shares":      new_shares,
                                "entry_price": new_entry,
                                "thesis":      new_thesis,
                            }
                            t_pct = parse(new_tgt_raw)
                            if t_pct is not None:
                                upd["target_pct"] = t_pct
                            elif not new_tgt_raw.strip() and "target_pct" in inv:
                                upd["target_pct"] = None
                            mp = parse(new_manual_price)
                            if mp is not None:
                                upd["manual_price"] = mp
                            elif not new_manual_price.strip():
                                upd["manual_price"] = None
                            inv.update(upd)
                            save_investments(investments)
                            st.session_state.pop(f"edit_inv_{inv['id']}", None)
                            st.success("แก้ไขเรียบร้อย!")
                            st.rerun()

                if st.session_state.get(f"sell_inv_{inv['id']}"):
                    st.markdown("**🔴 ขาย**")
                    s_current = parse(get_shares(inv)) or 0
                    st.caption(f"ถืออยู่ {s_current} หุ้น · AVG {inv.get('entry_price','—')} · ใส่ครบ = ปิด position")
                    with st.form(f"form_sell_inv_{inv['id']}"):
                        sv1, sv2, sv3 = st.columns(3)
                        sell_shares = sv1.text_input("จำนวนที่ขาย *", placeholder=f"สูงสุด {s_current}")
                        exit_p      = sv2.text_input("ราคาที่ขาย *", placeholder="เช่น 420")
                        exit_d      = sv3.date_input("วันที่ขาย", value=date.today())
                        sv4, sv5 = st.columns(2)
                        thesis_ok = sv4.selectbox("Thesis ถูกไหม (ถ้าปิด position)",
                                                   ["✅ ถูก", "❌ ผิด", "⚠️ บางส่วน"])
                        emotion   = sv5.selectbox("Emotion (ถ้าปิด position)",
                                                   ["ปกติ", "กลัว", "โลภ", "FOMO"])
                        lesson    = st.text_input("Lesson ที่ได้ (optional, ถ้าปิด position)")
                        if st.form_submit_button("✅ ยืนยันขาย"):
                            s_sell = parse(sell_shares)
                            ep     = parse(exit_p)
                            if not s_sell or not ep:
                                st.error("กรุณากรอกจำนวนหุ้นและราคาที่ขาย")
                            elif s_sell > s_current:
                                st.error(f"ขายได้สูงสุด {s_current} หุ้น")
                            else:
                                src_id   = inv.get("source_account_id")
                                currency = get_currency(inv)
                                exit_thb = s_sell * ep * (rate if currency == "USD" else 1)
                                if s_sell >= s_current:
                                    pnl_pct_v = calc_pnl_pct(inv["entry_price"], ep)
                                    pnl_thb_v = calc_pnl_thb(inv["entry_price"], ep, str(s_current), currency, rate)
                                    inv.update({"status": "closed", "exit_price": str(ep),
                                                "exit_date": str(exit_d),
                                                "pnl_pct": pnl_pct_v, "pnl_thb": pnl_thb_v,
                                                "thesis_correct": thesis_ok,
                                                "emotion": emotion, "lesson": lesson})
                                    if src_id:
                                        cash_credit(cash, src_id, exit_thb, rate)
                                        save_cash(cash)
                                    save_investments(investments)
                                    st.session_state.pop(f"sell_inv_{inv['id']}", None)
                                    st.success(f"ปิด Position ✅  P&L = {fmt_money(pnl_thb_v, disp, rate)}")
                                else:
                                    s_remain  = round(s_current - s_sell, 8)
                                    pnl_thb_p = calc_pnl_thb(inv["entry_price"], ep, str(s_sell), currency, rate)
                                    sell_hist = inv.get("sell_history", [])
                                    sell_hist.append({
                                        "date": str(exit_d), "shares": str(s_sell),
                                        "price": str(ep), "thb": round(exit_thb, 2),
                                        "pnl_thb": round(pnl_thb_p or 0, 2),
                                    })
                                    new_pos_thb = (inv.get("position_thb") or 0) * (s_remain / s_current)
                                    inv.update({
                                        "shares":       str(s_remain),
                                        "position_thb": round(new_pos_thb, 2),
                                        "sell_history": sell_hist,
                                    })
                                    if src_id:
                                        cash_credit(cash, src_id, exit_thb, rate)
                                        save_cash(cash)
                                    save_investments(investments)
                                    st.session_state.pop(f"sell_inv_{inv['id']}", None)
                                    st.success(f"ขาย {s_sell} หุ้น @ {ep} ✅  เหลือ {s_remain} หุ้น · P&L = {fmt_money(pnl_thb_p, disp, rate)}")
                                st.rerun()

    # ── Closed ────────────────────────────────────────────────────────────────
    if closed_inv:
        section(f"Closed ({len(closed_inv)})")
        st.dataframe([{
            "Ticker": i.get("ticker","—"), "Entry": i.get("entry_price","—"),
            "Exit":   i.get("exit_price","—"), "P&L %": fmt_pct(i.get("pnl_pct")),
            f"P&L ({sym})": fmt_money(i.get("pnl_thb"), disp, rate),
            "ซื้อ": i.get("entry_date","—"), "ขาย": i.get("exit_date","—"),
        } for i in closed_inv], use_container_width=True, hide_index=True)

    # ── Add Investment (collapsed) ────────────────────────────────────────────
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    with st.expander("➕ เพิ่ม / ซื้อเพิ่ม Investment"):
        existing_tickers = sorted({inv["ticker"] for inv in open_inv})
        ticker_options   = existing_tickers + ["➕ Ticker ใหม่"]
        selected_ticker  = st.selectbox("เลือก Ticker", ticker_options, key="new_inv_select")

        if selected_ticker != "➕ Ticker ใหม่":
            # ── ซื้อเพิ่มใน position ที่มีอยู่ ──────────────────────────────
            existing = next((inv for inv in investments
                             if inv["ticker"] == selected_ticker and inv["status"] == "open"), None)
            if existing:
                cur = get_currency(existing)
                st.caption(f"ถืออยู่: {get_shares(existing)} หุ้น  ·  AVG {existing.get('entry_price','—')}  ·  {cur}")
                with st.form("add_to_pos"):
                    b1, b2, b3 = st.columns(3)
                    add_shares = b1.text_input("จำนวนที่ซื้อเพิ่ม *", placeholder="เช่น 5")
                    add_price  = b2.text_input(f"ราคาที่ซื้อ ({cur}) *", placeholder="เช่น 420")
                    add_date   = b3.date_input("วันที่ซื้อ", value=date.today())
                    st.markdown("---")
                    src_id, other_name, other_curr = source_selector(cash, "add_pos")
                    is_import = st.checkbox("📥 ไม่หักเงินจาก Cash (Import เก่า)", key="import_add_pos")
                    if st.form_submit_button("✅ ซื้อเพิ่ม"):
                        s_add = parse(add_shares)
                        p_add = parse(add_price)
                        if not s_add or not p_add:
                            st.error("กรุณากรอกจำนวนและราคา")
                        else:
                            s_old = parse(get_shares(existing)) or 0
                            p_old = parse(existing.get("entry_price", "0")) or 0
                            s_new = s_old + s_add
                            p_avg = (s_old * p_old + s_add * p_add) / s_new
                            add_thb = s_add * p_add * (rate if cur == "USD" else 1)
                            resolved = resolve_source(cash, src_id, other_name, other_curr)
                            if not is_import:
                                cash_deduct(cash, resolved, add_thb, rate)
                                save_cash(cash)
                            # append buy log
                            history = existing.get("buy_history", [])
                            history.append({
                                "date": str(add_date), "shares": add_shares,
                                "price": add_price, "thb": round(add_thb, 2),
                                "note": "ซื้อเพิ่ม"
                            })
                            existing.update({
                                "shares":       str(round(s_new, 8)),
                                "entry_price":  str(round(p_avg, 4)),
                                "position_thb": round((existing.get("position_thb") or 0) + add_thb, 2),
                                "buy_history":  history,
                            })
                            save_investments(investments)
                            st.success(
                                f"✅ ซื้อเพิ่ม {add_shares} หุ้น @ {add_price}  ·  "
                                f"AVG ใหม่ = {round(p_avg, 4)} {cur}  ·  "
                                f"รวม {round(s_new, 4)} หุ้น"
                            )
                            st.rerun()
        else:
            # ── Ticker ใหม่ ──────────────────────────────────────────────────
            with st.form("new_inv"):
                c1, c2, c3 = st.columns(3)
                ticker     = c1.text_input("Ticker *", placeholder="เช่น AOT.BK, AAPL")
                shares     = c2.text_input("จำนวนหุ้น *", placeholder="เช่น 1000")
                currency   = c3.selectbox("ราคาเป็น", ["THB", "USD"])
                c4, c5     = st.columns(2)
                entry      = c4.text_input("Entry Price *", placeholder="ราคาที่ซื้อ")
                entry_date = c5.date_input("วันที่ซื้อ", value=date.today())
                ni1, ni2 = st.columns(2)
                thesis     = ni1.text_input("เหตุผลที่ลงทุน",
                                             placeholder="เช่น พื้นฐานดี dividend สม่ำเสมอ...")
                target_pct_inp = ni2.text_input("Target % (optional)",
                                                 placeholder="เช่น 20  — สัดส่วนเป้าหมายในพอร์ต")
                st.markdown("---")
                src_id, other_name, other_curr = source_selector(cash, "inv")
                is_import = st.checkbox("📥 Import position เก่า (ไม่หักเงินจาก Cash)", key="import_inv")
                if st.form_submit_button("✅ บันทึก"):
                    e, s = parse(entry), parse(shares)
                    if not ticker or e is None or s is None:
                        st.error("กรุณากรอก Ticker, จำนวนหุ้น และ Entry Price")
                    else:
                        pos_thb  = s * e * (rate if currency == "USD" else 1)
                        t_pct_v  = parse(target_pct_inp)
                        resolved = resolve_source(cash, src_id, other_name, other_curr)
                        if not is_import:
                            cash_deduct(cash, resolved, pos_thb, rate)
                            save_cash(cash)
                        new_inv = {
                            "id": next_id(investments), "type": "investment", "status": "open",
                            "ticker": ticker.upper().strip(), "shares": shares,
                            "currency": currency, "entry_price": entry,
                            "entry_date": str(entry_date), "thesis": thesis,
                            "position_thb": round(pos_thb, 2),
                            "source_account_id": resolved,
                            "source_account_name": next((a["name"] for a in cash if a["id"] == resolved), ""),
                            "buy_history": [{"date": str(entry_date), "shares": shares,
                                             "price": entry, "thb": round(pos_thb, 2), "note": "เปิด position"}],
                        }
                        if t_pct_v is not None:
                            new_inv["target_pct"] = t_pct_v
                        investments.append(new_inv)
                        save_investments(investments)
                        st.success(f"✅ บันทึก {ticker.upper()}")
                        st.rerun()


# ── Page 3: Trade ─────────────────────────────────────────────────────────────
def page_trade(trades: list, cash: list, disp: str, rate: float):
    open_trades   = [t for t in trades if t.get("status") == "open"]
    closed_trades = [t for t in trades if t.get("status") == "closed"]
    wins   = [t for t in closed_trades if t.get("win_loss") == "Win"]
    losses = [t for t in closed_trades if t.get("win_loss") == "Loss"]
    sym    = "฿" if disp == "THB" else "$"

    realized_thb   = sum(t.get("pnl_thb", 0) or 0 for t in closed_trades)
    win_rate       = len(wins) / len(closed_trades) * 100 if closed_trades else None
    total_win_thb  = sum(t.get("pnl_thb", 0) or 0 for t in wins)
    total_loss_thb = abs(sum(t.get("pnl_thb", 0) or 0 for t in losses))
    profit_factor  = round(total_win_thb / total_loss_thb, 2) if total_loss_thb > 0 else None

    # ── Performance KPIs ──────────────────────────────────────────────────────
    section("Performance")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Open Trades",   len(open_trades))
    k2.metric("Win Rate",      f"{win_rate:.1f}%" if win_rate is not None else "—")
    k3.metric("Profit Factor", f"{profit_factor:.2f}" if profit_factor else "—")
    k4.metric("Realized P&L",  fmt_money(realized_thb if closed_trades else None, disp, rate))
    k5.metric("Closed Trades", len(closed_trades))

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Open Trades ───────────────────────────────────────────────────────────
    if not open_trades:
        st.info("ไม่มี Open Trade ในขณะนี้")
    else:
        section(f"Open Trades ({len(open_trades)})")
        for t in open_trades:
            price   = get_price(t.get("ticker",""))
            pnl_thb = calc_pnl_thb(t.get("entry_price"), price, get_shares(t),
                                    get_currency(t), rate, t.get("direction","Long")) if price else None
            pnl_pct = calc_pnl_pct(t.get("entry_price"), price, t.get("direction","Long")) if price else None
            pos_thb = calc_position_thb(t.get("entry_price"), get_shares(t), get_currency(t), rate)
            tp_thb  = calc_pnl_thb(t.get("entry_price"), parse(t.get("take_profit","")) or 0,
                                    get_shares(t), get_currency(t), rate, t.get("direction","Long"))
            sl_thb  = calc_pnl_thb(t.get("entry_price"), parse(t.get("stop_loss","")) or 0,
                                    get_shares(t), get_currency(t), rate, t.get("direction","Long"))
            icon  = "🟢" if (pnl_thb or 0) >= 0 else "🔴"
            arrow = "↑" if t.get("direction") == "Long" else "↓"

            _hc = "green" if (pnl_thb or 0) >= 0 else "red"
            header = (f"{icon} **{t['ticker']}** {arrow}  ·  "
                      f"AVG {t.get('entry_price','—')}  ·  "
                      f"{get_shares(t)} shares  ·  {fmt_money(pos_thb, disp, rate, sign=False)}"
                      f"  |  :{_hc}[{fmt_pct(pnl_pct)}  {fmt_money(pnl_thb, disp, rate)}]"
                      ).replace("$", r"\$")

            with st.expander(header):
                # P&L banner
                _pc = "#22c55e" if (pnl_thb or 0) >= 0 else "#ef4444"
                _bg = "rgba(34,197,94,0.08)" if (pnl_thb or 0) >= 0 else "rgba(239,68,68,0.08)"
                st.markdown(
                    f"<div style='background:{_bg};border-left:3px solid {_pc};"
                    f"border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:10px'>"
                    f"<div style='font-size:10px;color:#94a3b8;text-transform:uppercase;"
                    f"letter-spacing:0.07em;margin-bottom:2px'>Unrealized P&L</div>"
                    f"<span style='font-size:22px;font-weight:700;color:{_pc}'>"
                    f"{fmt_money(pnl_thb, disp, rate) if pnl_thb is not None else '—'}</span>"
                    f"&nbsp;&nbsp;<span style='font-size:13px;color:{_pc}'>{fmt_pct(pnl_pct)}</span>"
                    f"</div>",
                    unsafe_allow_html=True)

                r1c1, r1c2, r1c3, r1c4 = st.columns(4)
                r1c1.metric("AVG Price",     t.get("entry_price","—"))
                r1c2.metric("Shares",        get_shares(t))
                r1c3.metric("Amount",        fmt_money(pos_thb, disp, rate, sign=False))
                r1c4.metric("Current Price", f"{price:.2f}" if price else "—",
                            delta=fmt_pct(pnl_pct) if pnl_pct else None)

                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

                r2c1, r2c2, r2c3 = st.columns(3)
                with r2c1:
                    st.markdown(
                        f"<div style='font-size:12px;color:#64748b;margin-bottom:2px'>TP</div>"
                        f"<div style='font-size:18px;font-weight:600'>{t.get('take_profit','—')}</div>"
                        f"<div style='font-size:12px;color:#22c55e'>"
                        f"Profit {fmt_money(tp_thb, disp, rate) if tp_thb else '—'}</div>",
                        unsafe_allow_html=True)
                with r2c2:
                    st.markdown(
                        f"<div style='font-size:12px;color:#64748b;margin-bottom:2px'>SL</div>"
                        f"<div style='font-size:18px;font-weight:600'>{t.get('stop_loss','—')}</div>"
                        f"<div style='font-size:12px;color:#ef4444'>"
                        f"Loss {fmt_money(sl_thb, disp, rate) if sl_thb else '—'}</div>",
                        unsafe_allow_html=True)
                with r2c3:
                    st.markdown(
                        f"<div style='font-size:12px;color:#64748b;margin-bottom:2px'>R:R &amp; Info</div>"
                        f"<div style='font-size:15px;font-weight:600'>{t.get('rr','—')}</div>"
                        f"<div style='font-size:11px;color:#64748b'>{get_currency(t)} · เปิด {t.get('open_date','—')}</div>",
                        unsafe_allow_html=True)

                st.caption(f"Thesis: {t.get('thesis','—')}")
                st.divider()

                ca, cb, cc, _, cd = st.columns([2, 2, 2, 1, 1])
                if ca.button("🔴 ขาย", key=f"btn_close_{t['id']}"):
                    st.session_state[f"show_close_{t['id']}"] = True
                    st.session_state.pop(f"show_edit_{t['id']}", None)
                    st.session_state.pop(f"show_add_{t['id']}", None)
                if cb.button("✏️ แก้ไข", key=f"btn_edit_{t['id']}"):
                    st.session_state[f"show_edit_{t['id']}"] = True
                    st.session_state.pop(f"show_close_{t['id']}", None)
                    st.session_state.pop(f"show_add_{t['id']}", None)
                if cc.button("➕ ซื้อเพิ่ม", key=f"btn_add_{t['id']}"):
                    st.session_state[f"show_add_{t['id']}"] = True
                    st.session_state.pop(f"show_close_{t['id']}", None)
                    st.session_state.pop(f"show_edit_{t['id']}", None)
                if cd.button("🗑️", key=f"btn_del_{t['id']}"):
                    trades[:] = [x for x in trades if x["id"] != t["id"]]
                    save_trades(trades)
                    st.rerun()

                if st.session_state.get(f"show_add_{t['id']}"):
                    st.markdown("**➕ ซื้อเพิ่ม**")
                    with st.form(f"form_add_{t['id']}"):
                        ta1, ta2 = st.columns(2)
                        add_shares = ta1.text_input("จำนวน Shares ที่ซื้อเพิ่ม *", placeholder="เช่น 2")
                        add_price  = ta2.text_input("ราคาที่ซื้อ *", placeholder="เช่น 420")
                        src_id, other_name, other_curr = source_selector(cash, f"add_trade_{t['id']}")
                        if st.form_submit_button("✅ ซื้อเพิ่ม"):
                            s_add = parse(add_shares)
                            p_add = parse(add_price)
                            if s_add and p_add:
                                s_old = parse(get_shares(t)) or 0
                                p_old = parse(t.get("entry_price", "0")) or 0
                                s_new = s_old + s_add
                                p_avg = (s_old * p_old + s_add * p_add) / s_new
                                add_thb = s_add * p_add * (rate if get_currency(t) == "USD" else 1)
                                resolved = resolve_source(cash, src_id, other_name, other_curr)
                                cash_deduct(cash, resolved, add_thb, rate)
                                save_cash(cash)
                                t.update({
                                    "shares":      str(round(s_new, 8)),
                                    "entry_price": str(round(p_avg, 4)),
                                    "position_thb": round((t.get("position_thb") or 0) + add_thb, 2),
                                    "rr": auto_rr(str(round(p_avg, 4)), t.get("stop_loss",""), t.get("take_profit","")),
                                })
                                save_trades(trades)
                                st.session_state.pop(f"show_add_{t['id']}", None)
                                st.success(f"ซื้อเพิ่ม {add_shares} shares @ {add_price} · AVG ใหม่ = {round(p_avg,4)}")
                                st.rerun()
                            else:
                                st.error("กรุณากรอกจำนวน shares และราคา")

                if st.session_state.get(f"show_edit_{t['id']}"):
                    st.markdown("**แก้ไข Trade**")
                    with st.form(f"form_edit_{t['id']}"):
                        ec1, ec2, ec3 = st.columns(3)
                        new_ticker = ec1.text_input("Ticker",      value=t.get("ticker",""))
                        new_shares = ec2.text_input("Shares",      value=get_shares(t))
                        new_entry  = ec3.text_input("AVG Price",   value=t.get("entry_price",""))
                        ec4, ec5, ec6 = st.columns(3)
                        new_sl     = ec4.text_input("Stop Loss",   value=t.get("stop_loss",""))
                        new_tp     = ec5.text_input("Take Profit", value=t.get("take_profit",""))
                        new_thesis = ec6.text_input("Thesis",      value=t.get("thesis",""))
                        ec7, ec8   = st.columns([3, 1])
                        _acct_opts = ["— ไม่ระบุ"] + [a["name"] for a in cash]
                        _curr_acct = t.get("source_account_name", "")
                        _acct_idx  = _acct_opts.index(_curr_acct) if _curr_acct in _acct_opts else 0
                        new_acct   = ec7.selectbox("พอร์ต / บัญชี", _acct_opts, index=_acct_idx)
                        new_dir    = ec8.selectbox("Direction", ["Long", "Short"],
                                                   index=0 if t.get("direction","Long") == "Long" else 1)
                        if st.form_submit_button("💾 บันทึก"):
                            _matched = next((a for a in cash if a["name"] == new_acct), None)
                            t.update({
                                "ticker": new_ticker.upper().strip(),
                                "shares": new_shares, "stop_loss": new_sl,
                                "take_profit": new_tp, "entry_price": new_entry,
                                "thesis": new_thesis,
                                "rr": auto_rr(new_entry, new_sl, new_tp),
                                "direction": new_dir,
                                "source_account_name": _matched["name"] if _matched else "",
                                "source_account_id":   _matched["id"]   if _matched else None,
                            })
                            save_trades(trades)
                            st.session_state.pop(f"show_edit_{t['id']}", None)
                            st.success("แก้ไขเรียบร้อย!")
                            st.rerun()

                if st.session_state.get(f"show_close_{t['id']}"):
                    st.markdown("**🔴 ขาย**")
                    s_current = parse(get_shares(t)) or 0
                    st.caption(f"ถืออยู่ {s_current} shares · AVG {t.get('entry_price','—')} · ใส่ครบ = ปิด trade")
                    with st.form(f"form_close_{t['id']}"):
                        tc1, tc2, tc3 = st.columns(3)
                        sell_shares = tc1.text_input("จำนวน Shares ที่ขาย *", placeholder=f"สูงสุด {s_current}")
                        exit_p      = tc2.text_input("Exit Price *")
                        exit_d      = tc3.date_input("วันที่ปิด", value=date.today())
                        tc4, tc5    = st.columns(2)
                        thesis_ok   = tc4.selectbox("Thesis ถูกไหม (ถ้าขายหมด)",
                                                     ["✅ ถูก", "❌ ผิด", "⚠️ บางส่วน"])
                        emotion     = tc5.selectbox("Emotion (ถ้าขายหมด)",
                                                     ["ปกติ", "กลัว", "โลภ", "FOMO"])
                        lesson      = st.text_input("Lesson ที่ได้ (ถ้าขายหมด)")
                        if st.form_submit_button("✅ ยืนยันขาย"):
                            s_sell = parse(sell_shares)
                            ep     = parse(exit_p)
                            if not s_sell or not ep:
                                st.error("กรุณากรอกจำนวน shares และ Exit Price")
                            elif s_sell > s_current:
                                st.error(f"ขายได้สูงสุด {s_current} shares")
                            else:
                                src_id    = t.get("source_account_id")
                                currency  = get_currency(t)
                                direction = t.get("direction", "Long")
                                if s_sell >= s_current:
                                    pnl_pct_v = calc_pnl_pct(t["entry_price"], ep, direction)
                                    pnl_thb_v = calc_pnl_thb(t["entry_price"], ep, str(s_current), currency, rate, direction)
                                    t.update({
                                        "status": "closed", "exit_price": str(ep),
                                        "close_date": str(exit_d), "thesis_correct": thesis_ok,
                                        "emotion": emotion, "lesson": lesson,
                                        "pnl_pct": pnl_pct_v, "pnl_thb": pnl_thb_v,
                                        "win_loss": "Win" if (pnl_thb_v or 0) > 0 else "Loss",
                                    })
                                    if src_id:
                                        exit_thb = s_current * ep * (rate if currency == "USD" else 1)
                                        if direction == "Short":
                                            entry_thb = s_current * (parse(t["entry_price"]) or 0) * (rate if currency == "USD" else 1)
                                            exit_thb  = 2 * entry_thb - exit_thb
                                        cash_credit(cash, src_id, exit_thb, rate)
                                        save_cash(cash)
                                    save_trades(trades)
                                    st.session_state.pop(f"show_close_{t['id']}", None)
                                    st.success(f"ปิด Trade ✅  P&L = {fmt_money(pnl_thb_v, disp, rate)}")
                                else:
                                    s_remain   = round(s_current - s_sell, 8)
                                    pnl_thb_p  = calc_pnl_thb(t["entry_price"], ep, str(s_sell), currency, rate, direction)
                                    exit_thb_p = s_sell * ep * (rate if currency == "USD" else 1)
                                    if direction == "Short":
                                        entry_thb_p = s_sell * (parse(t["entry_price"]) or 0) * (rate if currency == "USD" else 1)
                                        exit_thb_p  = 2 * entry_thb_p - exit_thb_p
                                    sell_hist = t.get("sell_history", [])
                                    sell_hist.append({
                                        "date": str(exit_d), "shares": str(s_sell),
                                        "price": str(ep), "pnl_thb": round(pnl_thb_p or 0, 2),
                                    })
                                    new_pos_thb = (t.get("position_thb") or 0) * (s_remain / s_current)
                                    t.update({
                                        "shares":       str(s_remain),
                                        "position_thb": round(new_pos_thb, 2),
                                        "sell_history": sell_hist,
                                        "rr": auto_rr(t["entry_price"], t.get("stop_loss",""), t.get("take_profit","")),
                                    })
                                    if src_id:
                                        cash_credit(cash, src_id, exit_thb_p, rate)
                                        save_cash(cash)
                                    save_trades(trades)
                                    st.session_state.pop(f"show_close_{t['id']}", None)
                                    st.success(f"ขาย {s_sell} shares @ {ep} ✅  เหลือ {s_remain} shares · P&L = {fmt_money(pnl_thb_p, disp, rate)}")
                                st.rerun()

    # ── Analytics ─────────────────────────────────────────────────────────────
    closed_with_pnl = [t for t in closed_trades if t.get("pnl_thb") is not None]
    if not closed_with_pnl and open_trades:
        st.info("📊 กราฟ Analytics จะขึ้นหลังจากปิด Trade แรก")
    if closed_with_pnl:
        section("Analytics")
        col_wl, col_strat = st.columns(2)

        with col_wl:
            win_count, loss_count = len(wins), len(losses)
            if win_count + loss_count > 0:
                fig_pie = go.Figure(go.Pie(
                    labels=["Win", "Loss"], values=[win_count, loss_count],
                    marker=dict(colors=["#22c55e", "#ef4444"]),
                    hole=0.5, textinfo="percent+value",
                    textfont=dict(size=13, color="#e2e8f0"),
                ))
                fig_pie.update_layout(**{**CHART_LAYOUT, "height": 240,
                    "title": dict(text="Win / Loss Distribution",
                                  font=dict(size=14, color="#94a3b8"), x=0),
                    "showlegend": True, "legend": dict(font=dict(color="#94a3b8")),
                })
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_strat:
            strat_pnl: dict[str, float] = {}
            for t in closed_with_pnl:
                s = t.get("strategy", "—")
                strat_pnl[s] = strat_pnl.get(s, 0) + (t.get("pnl_thb") or 0)
            if strat_pnl:
                st.plotly_chart(
                    pnl_bar_chart(list(strat_pnl.keys()), list(strat_pnl.values()),
                                  disp, rate, "P&L by Strategy", height=240),
                    use_container_width=True)

    # ── Closed Trades Table ───────────────────────────────────────────────────
    if closed_trades:
        section(f"Closed Trades ({len(closed_trades)})")
        st.dataframe([{
            "Ticker":       t.get("ticker","—"),
            "Strategy":     t.get("strategy","—"),
            "Entry":        t.get("entry_price","—"),
            "Exit":         t.get("exit_price","—"),
            "P&L %":        fmt_pct(t.get("pnl_pct")),
            f"P&L ({sym})": fmt_money(t.get("pnl_thb"), disp, rate),
            "W/L":          t.get("win_loss","—"),
            "Lesson":       t.get("lesson","—"),
        } for t in sorted(closed_trades, key=lambda x: x.get("close_date",""), reverse=True)],
        use_container_width=True, hide_index=True)

    # ── New Trade Form (collapsed) ────────────────────────────────────────────
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    with st.expander("➕ เปิด Trade ใหม่"):
        strategy = strategy_input("nt")
        with st.form("new_trade"):
            c1, c2, c3, c4 = st.columns(4)
            ticker    = c1.text_input("Ticker *", placeholder="เช่น AAPL, BTC-USD")
            direction = c2.selectbox("Direction", ["Long", "Short"])
            currency  = c3.selectbox("ราคาเป็น", ["THB", "USD"])
            shares    = c4.text_input("จำนวนหุ้น *", placeholder="เช่น 100")
            c5, c6, c7 = st.columns(3)
            entry     = c5.text_input("Entry Price *")
            sl        = c6.text_input("Stop Loss")
            tp        = c7.text_input("Take Profit")
            thesis    = st.text_area("Thesis *", height=80,
                                     placeholder="เหตุผลสั้นๆ ที่ชัดเจน")
            open_date = st.date_input("วันที่เปิด", value=date.today())
            st.markdown("---")
            src_id, other_name, other_curr = source_selector(cash, "trade")
            is_import = st.checkbox("📥 Import position เก่า (ไม่หักเงินจาก Cash)", key="import_trade")
            if st.form_submit_button("✅ บันทึก Trade"):
                e, s = parse(entry), parse(shares)
                if not ticker or e is None:
                    st.error("กรุณากรอก Ticker และ Entry Price")
                elif not strategy:
                    st.error("กรุณาเลือก Strategy")
                else:
                    rr       = auto_rr(entry, sl, tp)
                    pos_thb  = (s or 0) * e * (rate if currency == "USD" else 1)
                    resolved = resolve_source(cash, src_id, other_name, other_curr)
                    if not is_import:
                        cash_deduct(cash, resolved, pos_thb, rate)
                        save_cash(cash)
                    trades.append({
                        "id": next_id(trades), "type": "trade", "status": "open",
                        "ticker": ticker.upper().strip(), "direction": direction,
                        "strategy": strategy, "currency": currency,
                        "entry_price": entry, "shares": shares,
                        "stop_loss": sl, "take_profit": tp, "rr": rr,
                        "thesis": thesis, "open_date": str(open_date),
                        "position_thb": round(pos_thb, 2),
                        "source_account_id": resolved,
                        "source_account_name": next((a["name"] for a in cash if a["id"] == resolved), ""),
                    })
                    save_trades(trades)
                    st.success(f"✅ บันทึก! R:R = {rr} · Position: {fmt_money(pos_thb, disp, rate, sign=False)}")
                    st.rerun()


# ── Page 4: Cash ──────────────────────────────────────────────────────────────
def page_cash(trades: list, investments: list, cash: list, disp: str, rate: float):

    # ── Summary metrics ───────────────────────────────────────────────────────
    section("Summary")
    cash_usd = sum(a["amount"] for a in cash if a["currency"] == "USD")
    cash_thb = sum(a["amount"] for a in cash if a["currency"] == "THB")
    cash_total_thb = (cash_usd * rate) + cash_thb

    m1, m2, m3 = st.columns(3)
    m1.metric("Cash THB รวม", f"฿{cash_thb:,.0f}")
    m2.metric("Cash USD รวม", f"${cash_usd:,.2f}")
    m3.metric(f"Net Cash ({disp})", fmt_money(cash_total_thb, disp, rate, sign=False) if cash else "฿0")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Account list ──────────────────────────────────────────────────────────
    section(f"บัญชี Cash ({len(cash)})")
    if not cash:
        st.info("ยังไม่มีบัญชี Cash — เพิ่มได้ด้านล่าง")
    else:
        for acc in cash:
            amount_str = f"${acc['amount']:,.2f}" if acc["currency"] == "USD" else f"฿{acc['amount']:,.0f}"
            color = "🔴" if acc["amount"] < 0 else "🟢"
            with st.expander(f"{color} **{acc['name']}** · {acc['currency']} · {amount_str}"):
                col_r, col_a, col_d = st.columns(3)

                with col_r:
                    st.caption("แก้ชื่อ / ยอด")
                    with st.form(f"edit_acc_{acc['id']}"):
                        new_name   = st.text_input("ชื่อ", value=acc["name"])
                        new_amount = st.text_input("ยอด", value=str(acc["amount"]),
                                                   placeholder="เช่น 50000 หรือ 1500.50")
                        if st.form_submit_button("💾 บันทึก"):
                            acc["name"]   = new_name.strip() or acc["name"]
                            acc["amount"] = round(parse(new_amount) or 0, 2)
                            save_cash(cash)
                            st.rerun()

                other_accs = [a for a in cash if a["id"] != acc["id"]]
                if other_accs:
                    with col_a:
                        st.caption("🔀 Reassign → รวมกับบัญชีอื่น")
                        with st.form(f"reassign_{acc['id']}"):
                            t_idx = st.selectbox("ย้ายเข้า", range(len(other_accs)),
                                                  format_func=lambda i: acc_label(other_accs[i]))
                            if st.form_submit_button("ยืนยัน Reassign"):
                                target = other_accs[t_idx]
                                amt_thb = acc["amount"] * rate if acc["currency"] == "USD" else acc["amount"]
                                target["amount"] = round(target["amount"] + (amt_thb / rate if target["currency"] == "USD" else amt_thb), 2)
                                for item in trades + investments:
                                    if item.get("source_account_id") == acc["id"]:
                                        item["source_account_id"]   = target["id"]
                                        item["source_account_name"] = target["name"]
                                cash[:] = [a for a in cash if a["id"] != acc["id"]]
                                save_cash(cash)
                                save_trades(trades)
                                save_investments(investments)
                                st.success(f"ย้าย '{acc['name']}' เข้า '{target['name']}' เรียบร้อย!")
                                st.rerun()

                with col_d:
                    st.caption("ลบบัญชี")
                    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
                    if st.button("🗑️ ลบ", key=f"del_acc_{acc['id']}"):
                        cash[:] = [a for a in cash if a["id"] != acc["id"]]
                        save_cash(cash)
                        st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Add account ───────────────────────────────────────────────────────────
    with st.expander("➕ เพิ่มบัญชี Cash"):
        with st.form("add_cash_page"):
            fc1, fc2, fc3 = st.columns(3)
            preset      = fc1.selectbox("แหล่ง Cash", CASH_PRESETS)
            custom_name = fc2.text_input("หรือพิมพ์ชื่อเอง", placeholder="เช่น Binance Thai")
            currency    = fc3.selectbox("สกุลเงิน", ["THB", "USD"])
            amount_str  = st.text_input("ยอดเริ่มต้น", placeholder="เช่น 50000 หรือ 1500.50")
            if st.form_submit_button("💾 บันทึก"):
                name   = custom_name.strip() if custom_name.strip() else preset
                new_id = max((a["id"] for a in cash), default=0) + 1
                cash.append({"id": new_id, "name": name, "currency": currency,
                             "amount": round(parse(amount_str) or 0, 2)})
                save_cash(cash)
                st.success(f"เพิ่ม {name} ({currency}) เรียบร้อย!")
                st.rerun()

    # ── Cash Flow History ─────────────────────────────────────────────────────
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    section("Cash Flow History")

    flows = []
    for t in trades:
        src = t.get("source_account_name") or t.get("source_account_id") or "—"
        pos = calc_position_thb(t.get("entry_price"), get_shares(t), get_currency(t), rate)
        flows.append({
            "วันที่":   t.get("open_date","—"),
            "ประเภท":  "เปิด Trade",
            "Ticker":  t.get("ticker","—"),
            "บัญชี":   src,
            "Flow":    fmt_money(-(pos or 0), disp, rate),
        })
        if t.get("status") == "closed" and t.get("exit_price"):
            ep = parse(t.get("exit_price",""))
            exit_thb = parse(get_shares(t)) * (ep or 0) * (rate if get_currency(t) == "USD" else 1)
            flows.append({
                "วันที่":   t.get("close_date","—"),
                "ประเภท":  "ปิด Trade",
                "Ticker":  t.get("ticker","—"),
                "บัญชี":   src,
                "Flow":    fmt_money(exit_thb, disp, rate),
            })
    for inv in investments:
        src = inv.get("source_account_name") or inv.get("source_account_id") or "—"
        pos = calc_position_thb(inv.get("entry_price"), get_shares(inv), get_currency(inv), rate)
        flows.append({
            "วันที่":   inv.get("entry_date","—"),
            "ประเภท":  "ซื้อ Investment",
            "Ticker":  inv.get("ticker","—"),
            "บัญชี":   src,
            "Flow":    fmt_money(-(pos or 0), disp, rate),
        })
        if inv.get("status") == "closed" and inv.get("exit_price"):
            ep = parse(inv.get("exit_price",""))
            exit_thb = parse(get_shares(inv)) * (ep or 0) * (rate if get_currency(inv) == "USD" else 1)
            flows.append({
                "วันที่":   inv.get("exit_date","—"),
                "ประเภท":  "ขาย Investment",
                "Ticker":  inv.get("ticker","—"),
                "บัญชี":   src,
                "Flow":    fmt_money(exit_thb, disp, rate),
            })

    if flows:
        flows.sort(key=lambda x: x["วันที่"], reverse=True)
        st.dataframe(flows, use_container_width=True, hide_index=True)
    else:
        st.caption("ยังไม่มีรายการ — จะแสดงเมื่อมี trade/investment ที่เลือก source account")


# ── Page 5: Log ───────────────────────────────────────────────────────────────
def page_log(trades: list, investments: list, disp: str, rate: float):
    sym = "฿" if disp == "THB" else "$"

    # ── Activity Log ──────────────────────────────────────────────────────────
    section("Activity Log")
    activity = build_activity_log(investments, trades)
    if activity:
        st.dataframe(activity, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มี activity")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    rows = []
    for t in trades:
        rows.append({
            "Type": "Trade", "Ticker": t.get("ticker","—"),
            "Dir": t.get("direction","—"), "Strategy": t.get("strategy","—"),
            "Entry": t.get("entry_price","—"), "Exit": t.get("exit_price","—"),
            "P&L %": fmt_pct(t.get("pnl_pct")),
            f"P&L ({sym})": fmt_money(t.get("pnl_thb"), disp, rate),
            "W/L": t.get("win_loss", "open" if t.get("status")=="open" else "—"),
            "วันที่": t.get("open_date","—"), "Status": t.get("status","—"),
            "Lesson": t.get("lesson","—"),
        })
    for inv in investments:
        rows.append({
            "Type": "Investment", "Ticker": inv.get("ticker","—"),
            "Dir": "Long", "Strategy": "—",
            "Entry": inv.get("entry_price","—"), "Exit": inv.get("exit_price","—"),
            "P&L %": fmt_pct(inv.get("pnl_pct")),
            f"P&L ({sym})": fmt_money(inv.get("pnl_thb"), disp, rate),
            "W/L": "open" if inv.get("status")=="open" else fmt_pct(inv.get("pnl_pct")),
            "วันที่": inv.get("entry_date","—"), "Status": inv.get("status","—"),
            "Lesson": "—",
        })

    if not rows:
        st.info("ยังไม่มีข้อมูล")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    section("Filters")
    f1, f2, f3 = st.columns(3)
    tf = f1.selectbox("ประเภท", ["ทั้งหมด", "Trade", "Investment"])
    sf = f2.selectbox("Status",  ["ทั้งหมด", "open", "closed"])
    wf = f3.selectbox("W/L",     ["ทั้งหมด", "Win", "Loss", "open"])

    filtered = rows
    if tf != "ทั้งหมด": filtered = [r for r in filtered if r["Type"]   == tf]
    if sf != "ทั้งหมด": filtered = [r for r in filtered if r["Status"] == sf]
    if wf != "ทั้งหมด": filtered = [r for r in filtered if r["W/L"]    == wf]

    # ── Table ─────────────────────────────────────────────────────────────────
    section(f"History ({len(filtered)} entries)")
    st.dataframe(filtered, use_container_width=True, hide_index=True)

    # ── Export CSV ────────────────────────────────────────────────────────────
    if filtered:
        csv = pd.DataFrame(filtered).to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Export CSV", data=csv,
            file_name=f"timfin_log_{date.today()}.csv",
            mime="text/csv",
        )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if _use_sb() and not is_logged_in():
        page_login()
        return

    trades      = load_trades()
    investments = load_investments()
    cash        = load_cash()
    page        = render_sidebar()

    subtitles = {
        "📊 Overview":   "How is my portfolio doing?",
        "💼 Investment": "What do I currently own?",
        "📈 Trade":      "How am I performing as a trader?",
        "💵 Cash":       "บัญชีเงินสดและ Cash Flow",
        "📓 Log":        "What happened historically?",
    }
    disp, rate = page_header(
        title    = page.split(" ", 1)[1] if " " in page else page,
        subtitle = subtitles.get(page, ""),
    )

    if   page == "📊 Overview":   page_overview(trades, investments, cash, disp, rate)
    elif page == "💼 Investment": page_investment(investments, trades, cash, disp, rate)
    elif page == "📈 Trade":      page_trade(trades, cash, disp, rate)
    elif page == "💵 Cash":       page_cash(trades, investments, cash, disp, rate)
    elif page == "📓 Log":        page_log(trades, investments, disp, rate)


main()
