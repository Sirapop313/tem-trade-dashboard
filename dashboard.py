"""
Tim.fin Personal OS — Investment & Trade Dashboard
"""
import io
import json
import os
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
    r = _req.post(f"{_sb_url()}/auth/v1/token?grant_type=password",
                  headers={"apikey": st.secrets["SUPABASE_KEY"], "Content-Type": "application/json"},
                  json={"email": email, "password": password})
    return r.json() if r.status_code == 200 else None

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
@st.cache_data(ttl=300)
def get_price(ticker: str) -> float | None:
    try:
        import yfinance as yf
        return yf.Ticker(ticker).fast_info.last_price
    except Exception:
        return None

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
        prefix = ("+" if v >= 0 else "") if sign else ""
        return f"{prefix}${abs(v):,.2f}"
    prefix = ("+" if val_thb >= 0 else "") if sign else ""
    return f"{prefix}฿{abs(val_thb):,.0f}"

def to_display(val_thb: float | None, disp: str, rate: float) -> float | None:
    if val_thb is None: return None
    return val_thb / rate if disp == "USD" else val_thb


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
                        if result and "access_token" in result:
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
def page_overview(trades: list, investments: list, cash: dict, disp: str, rate: float):
    open_trades   = [t for t in trades      if t.get("status") == "open"]
    closed_trades = [t for t in trades      if t.get("status") == "closed"]
    open_inv      = [i for i in investments if i.get("status") == "open"]
    wins          = [t for t in closed_trades if t.get("win_loss") == "Win"]

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

    # ── KPI Row ───────────────────────────────────────────────────────────────
    section("Portfolio Summary")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Portfolio Value",
              fmt_money(port_thb, disp, rate, sign=False) if port_thb else "No data yet")
    k2.metric("Unrealized P&L",
              fmt_money(unreal_thb if unreal_items else None, disp, rate),
              delta=fmt_pct(unreal_thb / port_thb * 100 if port_thb and unreal_items else None))
    k3.metric("Realized P&L",
              fmt_money(realized_thb if closed_trades else None, disp, rate)
              if closed_trades else "No closed trades yet")
    k4.metric("Win Rate",
              f"{win_rate:.1f}%" if win_rate is not None else "No closed trades yet")

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── Allocation Pie + Portfolio Line ───────────────────────────────────────
    open_all = open_trades + open_inv
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
    all_items = []
    for t in trades:
        icon  = "🔒" if t.get("status") == "closed" else "📈"
        label = f"{icon} **{t.get('ticker')}** — Trade {'ปิด' if t.get('status')=='closed' else 'เปิด'}"
        all_items.append({"date": t.get("open_date",""), "label": label})
    for inv in investments:
        all_items.append({
            "date":  inv.get("entry_date",""),
            "label": f"💼 **{inv.get('ticker')}** — Investment เพิ่ม",
        })
    all_items.sort(key=lambda x: x["date"], reverse=True)

    if all_items:
        section("Recent Activity")
        for item in all_items[:5]:
            st.caption(f"{item['date']}  ·  {item['label']}")

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

    # ── Summary ───────────────────────────────────────────────────────────────
    section("Summary")
    total_val_thb, total_pnl_thb = 0.0, 0.0
    best_ticker, best_pct = "—", None

    cash_usd_total = sum(a["amount"] for a in cash if a["currency"] == "USD")
    cash_thb_total = sum(a["amount"] for a in cash if a["currency"] == "THB")
    cash_total_thb = (cash_usd_total * rate) + cash_thb_total

    for inv in open_inv:
        price = get_price(inv.get("ticker",""))
        ref   = str(price) if price else inv.get("entry_price")
        pos   = calc_position_thb(ref, get_shares(inv), get_currency(inv), rate)
        if pos: total_val_thb += pos
        if price:
            pnl = calc_pnl_thb(inv.get("entry_price"), price, get_shares(inv), get_currency(inv), rate)
            pct = calc_pnl_pct(inv.get("entry_price"), price)
            if pnl: total_pnl_thb += pnl
            if pct is not None and (best_pct is None or pct > best_pct):
                best_pct, best_ticker = pct, inv.get("ticker","—")

    total_with_cash_thb = total_val_thb + cash_total_thb

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Value (incl. Cash)", fmt_money(total_with_cash_thb or None, disp, rate, sign=False) if total_with_cash_thb else "No data yet")
    s2.metric("Total P&L",     fmt_money(total_pnl_thb or None, disp, rate) if open_inv else "No holdings yet")
    s3.metric("Holdings",      len(open_inv))
    s4.metric("Best Performer", f"{best_ticker}  {fmt_pct(best_pct)}" if best_pct is not None else "—")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Cash Summary (link to Cash page) ──────────────────────────────────────
    section("Cash")
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Cash THB รวม", f"฿{cash_thb_total:,.0f}")
    cc2.metric("Cash USD รวม", f"${cash_usd_total:,.2f}")
    cc3.metric(f"Total Cash ({disp})", fmt_money(cash_total_thb or None, disp, rate, sign=False) if cash_total_thb else "฿0")
    st.caption("จัดการบัญชี Cash ได้ที่หน้า 💵 Cash")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Holdings Table ────────────────────────────────────────────────────────
    if not open_inv:
        st.info("ยังไม่มี Investment — เพิ่มได้ด้านล่าง")
    else:
        # Build raw data first (for sorting)
        raw = []
        pie_labels_inv, pie_vals_inv = [], []
        for inv in open_inv:
            price   = get_price(inv.get("ticker",""))
            pnl_thb = calc_pnl_thb(inv.get("entry_price"), price, get_shares(inv),
                                    get_currency(inv), rate) if price else None
            pnl_pct = calc_pnl_pct(inv.get("entry_price"), price) if price else None
            ref     = str(price) if price else inv.get("entry_price")
            pos_thb = calc_position_thb(ref, get_shares(inv), get_currency(inv), rate)
            if pos_thb:
                pie_labels_inv.append(inv.get("ticker","?"))
                pie_vals_inv.append(pos_thb)
            raw.append({
                "inv": inv, "price": price,
                "pnl_thb": pnl_thb or 0, "pnl_pct": pnl_pct or 0,
                "pos_thb": pos_thb or 0,
            })

        # Pie chart + Sort selector
        col_pie_inv, col_sort_inv = st.columns([4, 6])
        with col_pie_inv:
            if pie_labels_inv:
                st.plotly_chart(allocation_pie(pie_labels_inv, pie_vals_inv, disp, rate,
                                               "Holdings Allocation", height=280),
                                use_container_width=True)
        with col_sort_inv:
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
        rows = []
        for r in raw:
            inv, price = r["inv"], r["price"]
            rows.append({
                "Ticker":        inv.get("ticker","—"),
                "Shares":        get_shares(inv),
                "Avg Cost":      inv.get("entry_price","—"),
                "Current Price": f"{price:.2f}" if price else "—",
                "Market Value":  fmt_money(r["pos_thb"] or None, disp, rate, sign=False),
                "P&L %":         fmt_pct(r["pnl_pct"]) if price else "—",
                f"P&L ({sym})":  fmt_money(r["pnl_thb"] or None, disp, rate) if price else "—",
                "Thesis":        inv.get("thesis","—"),
            })

        # Style P&L columns
        df_inv = pd.DataFrame(rows)
        pnl_cols = ["P&L %", f"P&L ({sym})"]

        def _color_pnl(val):
            if isinstance(val, str) and val.startswith("+"):
                return "color: #22c55e; font-weight: 600"
            if isinstance(val, str) and val.startswith("-"):
                return "color: #ef4444; font-weight: 600"
            return ""

        try:
            styled = df_inv.style.map(_color_pnl, subset=pnl_cols).hide(axis="index")
        except AttributeError:
            styled = df_inv.style.applymap(_color_pnl, subset=pnl_cols).hide(axis="index")
        st.dataframe(styled, use_container_width=True)

        # Position actions (ปิด/ลบ)
        section("Position Actions")
        for inv in open_inv:
            price   = get_price(inv.get("ticker",""))
            pnl_thb = calc_pnl_thb(inv.get("entry_price"), price, get_shares(inv),
                                    get_currency(inv), rate) if price else None
            pnl_pct = calc_pnl_pct(inv.get("entry_price"), price) if price else None
            icon    = "🟢" if (pnl_thb or 0) >= 0 else "🔴"

            with st.expander(f"{icon} {inv['ticker']} · {fmt_pct(pnl_pct)} · {fmt_money(pnl_thb, disp, rate)}"):
                ca, cb, _, cc = st.columns([2, 2, 2, 1])
                if ca.button("🔒 ปิด Position", key=f"ci_{inv['id']}"):
                    st.session_state[f"close_inv_{inv['id']}"] = True
                    st.session_state.pop(f"edit_inv_{inv['id']}", None)
                if cb.button("✏️ แก้ไข", key=f"ei_{inv['id']}"):
                    st.session_state[f"edit_inv_{inv['id']}"] = True
                    st.session_state.pop(f"close_inv_{inv['id']}", None)
                if cc.button("🗑️", key=f"di_{inv['id']}"):
                    investments[:] = [x for x in investments if x["id"] != inv["id"]]
                    save_investments(investments)
                    st.rerun()

                if st.session_state.get(f"edit_inv_{inv['id']}"):
                    st.markdown("**แก้ไข Investment**")
                    with st.form(f"form_edit_inv_{inv['id']}"):
                        ei1, ei2, ei3 = st.columns(3)
                        new_ticker = ei1.text_input("Ticker",       value=inv.get("ticker",""))
                        new_shares = ei2.text_input("จำนวนหุ้น",    value=get_shares(inv))
                        new_entry  = ei3.text_input("Entry Price",  value=inv.get("entry_price",""))
                        new_thesis = st.text_input("Thesis",        value=inv.get("thesis",""))
                        if st.form_submit_button("💾 บันทึก"):
                            inv.update({
                                "ticker":      new_ticker.upper().strip(),
                                "shares":      new_shares,
                                "entry_price": new_entry,
                                "thesis":      new_thesis,
                            })
                            save_investments(investments)
                            st.session_state.pop(f"edit_inv_{inv['id']}", None)
                            st.success("แก้ไขเรียบร้อย!")
                            st.rerun()

                if st.session_state.get(f"close_inv_{inv['id']}"):
                    with st.form(f"clf_inv_{inv['id']}"):
                        cc1, cc2 = st.columns(2)
                        exit_p = cc1.text_input("Exit Price *")
                        exit_d = cc2.date_input("วันที่ขาย", value=date.today())
                        if st.form_submit_button("ยืนยันปิด"):
                            ep        = parse(exit_p)
                            pnl_pct_v = calc_pnl_pct(inv["entry_price"], ep) if ep else None
                            pnl_thb_v = calc_pnl_thb(inv["entry_price"], ep, get_shares(inv),
                                                      get_currency(inv), rate) if ep else None
                            inv.update({"status": "closed", "exit_price": exit_p,
                                        "exit_date": str(exit_d),
                                        "pnl_pct": pnl_pct_v, "pnl_thb": pnl_thb_v})
                            # คืนเงิน + กำไรกลับ cash
                            src_id = inv.get("source_account_id")
                            if src_id and ep:
                                exit_thb = parse(get_shares(inv)) * ep * (rate if get_currency(inv) == "USD" else 1)
                                cash_credit(cash, src_id, exit_thb or 0, rate)
                                save_cash(cash)
                            save_investments(investments)
                            st.success("ปิด Position เรียบร้อย!")
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
    with st.expander("➕ เพิ่ม Investment ใหม่"):
        with st.form("new_inv"):
            c1, c2, c3 = st.columns(3)
            ticker     = c1.text_input("Ticker *", placeholder="เช่น AOT.BK, AAPL")
            shares     = c2.text_input("จำนวนหุ้น *", placeholder="เช่น 1000")
            currency   = c3.selectbox("ราคาเป็น", ["THB", "USD"])
            c4, c5     = st.columns(2)
            entry      = c4.text_input("Entry Price *", placeholder="ราคาที่ซื้อ")
            entry_date = c5.date_input("วันที่ซื้อ", value=date.today())
            thesis     = st.text_input("เหตุผลที่ลงทุน",
                                       placeholder="เช่น พื้นฐานดี dividend สม่ำเสมอ...")
            st.markdown("---")
            src_id, other_name, other_curr = source_selector(cash, "inv")
            is_import = st.checkbox("📥 Import position เก่า (ไม่หักเงินจาก Cash)", key="import_inv")
            if st.form_submit_button("✅ บันทึก"):
                e, s = parse(entry), parse(shares)
                if not ticker or e is None or s is None:
                    st.error("กรุณากรอก Ticker, จำนวนหุ้น และ Entry Price")
                else:
                    pos_thb = s * e * (rate if currency == "USD" else 1)
                    resolved = resolve_source(cash, src_id, other_name, other_curr)
                    if not is_import:
                        cash_deduct(cash, resolved, pos_thb, rate)
                        save_cash(cash)
                    investments.append({
                        "id": next_id(investments), "type": "investment", "status": "open",
                        "ticker": ticker.upper().strip(), "shares": shares,
                        "currency": currency, "entry_price": entry,
                        "entry_date": str(entry_date), "thesis": thesis,
                        "position_thb": round(pos_thb, 2),
                        "source_account_id": resolved,
                        "source_account_name": next((a["name"] for a in cash if a["id"] == resolved), ""),
                    })
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

            header = (f"{icon} **{t['ticker']}** {arrow}  ·  "
                      f"AVG {t.get('entry_price','—')}  ·  "
                      f"{get_shares(t)} shares  ·  {fmt_money(pos_thb, disp, rate, sign=False)}"
                      f"  |  {fmt_pct(pnl_pct)}  {fmt_money(pnl_thb, disp, rate)}")

            with st.expander(header):
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
                    pnl_color = "#22c55e" if (pnl_thb or 0) >= 0 else "#ef4444"
                    st.markdown(
                        f"<div style='font-size:12px;color:#64748b;margin-bottom:2px'>P&L</div>"
                        f"<div style='font-size:22px;font-weight:700;color:{pnl_color}'>"
                        f"{fmt_money(pnl_thb, disp, rate)}</div>"
                        f"<div style='font-size:12px;color:{pnl_color}'>{fmt_pct(pnl_pct)}</div>",
                        unsafe_allow_html=True)
                with r2c3:
                    st.markdown(
                        f"<div style='font-size:12px;color:#64748b;margin-bottom:2px'>SL</div>"
                        f"<div style='font-size:18px;font-weight:600'>{t.get('stop_loss','—')}</div>"
                        f"<div style='font-size:12px;color:#ef4444'>"
                        f"Loss {fmt_money(sl_thb, disp, rate) if sl_thb else '—'}</div>",
                        unsafe_allow_html=True)

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                st.caption(f"R:R {t.get('rr','—')}  ·  {get_currency(t)}  ·  เปิด {t.get('open_date','—')}")
                st.caption(f"Thesis: {t.get('thesis','—')}")
                st.divider()

                ca, cb, cc, _ = st.columns([2, 2, 1, 2])
                if ca.button("🔒 ปิด Trade", key=f"btn_close_{t['id']}"):
                    st.session_state[f"show_close_{t['id']}"] = True
                    st.session_state.pop(f"show_edit_{t['id']}", None)
                if cb.button("✏️ แก้ไข", key=f"btn_edit_{t['id']}"):
                    st.session_state[f"show_edit_{t['id']}"] = True
                    st.session_state.pop(f"show_close_{t['id']}", None)
                if cc.button("🗑️", key=f"btn_del_{t['id']}"):
                    trades[:] = [x for x in trades if x["id"] != t["id"]]
                    save_trades(trades)
                    st.rerun()

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
                        if st.form_submit_button("💾 บันทึก"):
                            t.update({
                                "ticker": new_ticker.upper().strip(),
                                "shares": new_shares, "stop_loss": new_sl,
                                "take_profit": new_tp, "entry_price": new_entry,
                                "thesis": new_thesis,
                                "rr": auto_rr(new_entry, new_sl, new_tp),
                            })
                            save_trades(trades)
                            st.session_state.pop(f"show_edit_{t['id']}", None)
                            st.success("แก้ไขเรียบร้อย!")
                            st.rerun()

                if st.session_state.get(f"show_close_{t['id']}"):
                    st.markdown("**ปิด Trade**")
                    with st.form(f"form_close_{t['id']}"):
                        cc1, cc2  = st.columns(2)
                        exit_p    = cc1.text_input("Exit Price *")
                        exit_d    = cc2.date_input("วันที่ปิด", value=date.today())
                        cc3, cc4  = st.columns(2)
                        thesis_ok = cc3.selectbox("Thesis ถูกไหม",
                                                  ["✅ ถูก", "❌ ผิด", "⚠️ บางส่วน"])
                        emotion   = cc4.selectbox("Emotion", ["ปกติ", "กลัว", "โลภ", "FOMO"])
                        lesson    = st.text_input("Lesson ที่ได้")
                        if st.form_submit_button("ยืนยันปิด"):
                            ep        = parse(exit_p)
                            pnl_pct_v = calc_pnl_pct(t["entry_price"], ep, t["direction"]) if ep else None
                            pnl_thb_v = calc_pnl_thb(t["entry_price"], ep, get_shares(t),
                                                      get_currency(t), rate, t["direction"]) if ep else None
                            t.update({
                                "status": "closed", "exit_price": exit_p,
                                "close_date": str(exit_d), "thesis_correct": thesis_ok,
                                "emotion": emotion, "lesson": lesson,
                                "pnl_pct": pnl_pct_v, "pnl_thb": pnl_thb_v,
                                "win_loss": "Win" if (pnl_thb_v or 0) > 0 else "Loss",
                            })
                            # คืนเงิน + กำไรกลับ cash
                            src_id = t.get("source_account_id")
                            if src_id and ep:
                                exit_thb = parse(get_shares(t)) * ep * (rate if get_currency(t) == "USD" else 1)
                                if t.get("direction") == "Short":
                                    entry_thb = parse(get_shares(t)) * parse(t["entry_price"]) * (rate if get_currency(t) == "USD" else 1)
                                    exit_thb = 2 * (entry_thb or 0) - (exit_thb or 0)
                                cash_credit(cash, src_id, exit_thb or 0, rate)
                                save_cash(cash)
                            save_trades(trades)
                            st.success(f"ปิด Trade! P&L = {fmt_money(pnl_thb_v, disp, rate)}")
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
                if not ticker or e is None or not thesis:
                    st.error("กรุณากรอก Ticker, Entry Price และ Thesis")
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
