"""
Tim.fin Personal OS — Trade & Investment Dashboard
"""
import json
import os
from datetime import date

import streamlit as st
import plotly.graph_objects as go

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Tim.fin OS", page_icon="📊", layout="wide")

DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE      = os.path.join(DIR, "trades.json")
INVESTMENTS_FILE = os.path.join(DIR, "investments.json")
STRATEGY_PRESETS = ["Breakout", "Swing", "Buy on dip", "Others"]

# ── Theme ─────────────────────────────────────────────────────────────────────
st.markdown("""<style>
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 16px 20px;
}
[data-testid="stFormSubmitButton"] button {
    background: #5865f2; color: white;
    border-radius: 8px; font-weight: 600; width: 100%;
}
[data-testid="stFormSubmitButton"] button:hover { background: #4752c4; }
</style>""", unsafe_allow_html=True)

# ── Data Layer ────────────────────────────────────────────────────────────────
def _load(path: str) -> list:
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8") as f: return json.load(f)

def _save(path: str, data: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_trades() -> list:       return _load(TRADES_FILE)
def save_trades(d: list):        _save(TRADES_FILE, d)
def load_investments() -> list:  return _load(INVESTMENTS_FILE)
def save_investments(d: list):   _save(INVESTMENTS_FILE, d)

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
    """รองรับทั้ง field ใหม่ (shares) และเก่า (size)"""
    return item.get("shares") or item.get("size") or "1"

def get_currency(item: dict) -> str:
    """ถ้าไม่มี currency field ให้ guess จาก ticker"""
    if item.get("currency"):
        return item["currency"]
    ticker = item.get("ticker", "")
    return "THB" if ticker.endswith(".BK") else "USD"

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
    thb  = diff * s * (rate if trade_currency == "USD" else 1)
    return round(thb, 2)

def auto_rr(entry, sl, tp) -> str:
    e, s, t = parse(entry), parse(sl), parse(tp)
    if None in (e, s, t) or abs(e - s) == 0: return "—"
    return f"1:{abs(t-e)/abs(e-s):.1f}"

def fmt_pct(val) -> str:
    if not isinstance(val, (int, float)): return "—"
    return f"{'+' if val>=0 else ''}{val:.2f}%"

def fmt_money(val_thb: float | None, disp: str, rate: float, sign: bool = True) -> str:
    """sign=True → +/- prefix (P&L)  |  sign=False → ไม่มี prefix (Amount, Position size)"""
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

CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e2e8f0", size=13),
    showlegend=False,
    margin=dict(t=16, b=8, l=8, r=8),
    xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#94a3b8")),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
               tickfont=dict(size=11, color="#64748b"), zeroline=True,
               zerolinecolor="rgba(255,255,255,0.15)"),
)

def pnl_bar_chart(labels: list, vals_thb: list, disp: str, rate: float,
                  title: str, height: int = 280) -> go.Figure:
    vals = [to_display(v, disp, rate) for v in vals_thb]
    texts = [fmt_money(v, disp, rate) for v in vals_thb]
    colors = ["#22c55e" if (v or 0) >= 0 else "#ef4444" for v in vals_thb]

    fig = go.Figure(go.Bar(
        x=labels, y=vals,
        marker=dict(color=colors, opacity=0.85,
                    line=dict(color="rgba(255,255,255,0.1)", width=1)),
        text=texts,
        textposition="outside",
        textfont=dict(size=13, color="#e2e8f0"),
        cliponaxis=False,
    ))
    sym = "฿" if disp == "THB" else "$"
    layout = {**CHART_LAYOUT,
              "title": dict(text=title, font=dict(size=15, color="#cbd5e1"), x=0),
              "yaxis_title": f"P&L ({sym})",
              "height": height,
              "yaxis_tickformat": ",.0f",
              }
    fig.update_layout(**layout)
    # padding ด้านบน/ล่างให้ text ไม่ถูกตัด
    if vals:
        maxv = max(abs(v) for v in vals if v is not None) or 1
        fig.update_yaxes(range=[-maxv*1.35, maxv*1.35])
    return fig

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

def currency_badge(disp: str) -> str:
    return "฿ THB" if disp == "THB" else "$ USD"

# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar() -> tuple[str, str, float]:
    with st.sidebar:
        st.title("📊 Tim.fin OS")
        st.markdown("---")
        page = st.radio("เมนู", ["📊 Overview", "💼 Investment", "📈 Trade", "📓 Log"],
                        label_visibility="collapsed")
        st.markdown("---")
        st.caption("แสดงมูลค่าเป็น")
        disp = st.radio("Currency", ["THB", "USD"], horizontal=True,
                        key="display_currency",
                        label_visibility="collapsed")
        rate = get_usd_thb()
        st.caption(f"อัตราแลกเปลี่ยน: 1 USD = ฿{rate:.2f}")
        st.markdown("---")
        st.caption("Tim.fin Personal OS")
    return page, disp, rate

# ── Pages ─────────────────────────────────────────────────────────────────────

def page_overview(trades: list, investments: list, disp: str, rate: float):
    st.title("📊 Overview")
    sym = "฿" if disp == "THB" else "$"

    open_trades   = [t for t in trades      if t.get("status") == "open"]
    closed_trades = [t for t in trades      if t.get("status") == "closed"]
    open_inv      = [i for i in investments if i.get("status") == "open"]
    wins      = [t for t in closed_trades if t.get("win_loss") == "Win"]
    win_rate  = len(wins) / len(closed_trades) * 100 if closed_trades else None

    # realized P&L in THB (stored in trade)
    realized_thb = sum(t.get("pnl_thb", 0) or 0 for t in closed_trades)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Open Positions", len(open_trades) + len(open_inv))
    c2.metric("Closed Trades",  len(closed_trades))
    c3.metric("Win Rate",       f"{win_rate:.1f}%" if win_rate is not None else "—")
    c4.metric(f"Realized P&L ({disp})",
              fmt_money(realized_thb if realized_thb else None, disp, rate))

    st.markdown("---")

    # ── Unrealized P&L chart ──────────────────────────────────────────────────
    unreal = []
    for t in open_trades:
        price = get_price(t.get("ticker",""))
        if price is None: continue
        pnl_thb = calc_pnl_thb(t.get("entry_price"), price, get_shares(t),
                                get_currency(t), rate, t.get("direction","Long"))
        if pnl_thb is not None:
            unreal.append({"label": f"{t['ticker']} (Trade)", "pnl_thb": pnl_thb})
    for inv in open_inv:
        price = get_price(inv.get("ticker",""))
        if price is None: continue
        pnl_thb = calc_pnl_thb(inv.get("entry_price"), price,
                                get_shares(inv), get_currency(inv), rate)
        if pnl_thb is not None:
            unreal.append({"label": f"{inv['ticker']} (Hold)", "pnl_thb": pnl_thb})

    if unreal:
        st.plotly_chart(
            pnl_bar_chart([d["label"] for d in unreal],
                          [d["pnl_thb"] for d in unreal],
                          disp, rate, "Unrealized P&L", height=300),
            use_container_width=True)

    # ── Closed trade history chart ────────────────────────────────────────────
    closed_with_pnl = [t for t in closed_trades if t.get("pnl_thb") is not None]
    if closed_with_pnl:
        st.plotly_chart(
            pnl_bar_chart([f"#{t['id']} {t['ticker']}" for t in closed_with_pnl],
                          [t["pnl_thb"] for t in closed_with_pnl],
                          disp, rate, "Trade History P&L", height=300),
            use_container_width=True)

    if not unreal and not closed_with_pnl:
        st.info("เพิ่ม Trade หรือ Investment ก่อนเพื่อดู chart นะ")


def page_investment(investments: list, disp: str, rate: float):
    st.title("💼 Investment")

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
            if st.form_submit_button("✅ บันทึก"):
                e, s = parse(entry), parse(shares)
                if not ticker or e is None or s is None:
                    st.error("กรุณากรอก Ticker, จำนวนหุ้น และ Entry Price")
                else:
                    pos_thb = s * e * (rate if currency == "USD" else 1)
                    investments.append({
                        "id": next_id(investments), "type": "investment", "status": "open",
                        "ticker": ticker.upper().strip(), "shares": shares,
                        "currency": currency, "entry_price": entry,
                        "entry_date": str(entry_date), "thesis": thesis,
                        "position_thb": round(pos_thb, 2),
                    })
                    save_investments(investments)
                    st.success(f"✅ บันทึก {ticker.upper()} | "
                               f"Position: {fmt_money(pos_thb, disp, rate, sign=False)}")
                    st.rerun()

    open_inv   = [i for i in investments if i.get("status") == "open"]
    closed_inv = [i for i in investments if i.get("status") == "closed"]

    # ── Unrealized P&L bar chart ──────────────────────────────────────────────
    chart_data = []
    for inv in open_inv:
        price = get_price(inv.get("ticker",""))
        if price is None: continue
        pnl_thb = calc_pnl_thb(inv.get("entry_price"), price,
                                get_shares(inv), get_currency(inv), rate)
        if pnl_thb is not None:
            chart_data.append({"ticker": inv["ticker"], "pnl_thb": pnl_thb})

    if chart_data:
        st.plotly_chart(
            pnl_bar_chart([d["ticker"] for d in chart_data],
                          [d["pnl_thb"] for d in chart_data],
                          disp, rate, "Unrealized P&L", height=280),
            use_container_width=True)

    # ── Holdings list ─────────────────────────────────────────────────────────
    if not open_inv:
        st.info("ยังไม่มี Investment ที่เปิดอยู่")
    else:
        st.subheader(f"Holdings ({len(open_inv)})")
        for inv in open_inv:
            price   = get_price(inv.get("ticker",""))
            pnl_thb = calc_pnl_thb(inv.get("entry_price"), price,
                                    get_shares(inv), get_currency(inv), rate) if price else None
            pnl_pct = calc_pnl_pct(inv.get("entry_price"), price) if price else None
            pos_thb = calc_position_thb(inv.get("entry_price"), get_shares(inv),
                                        get_currency(inv), rate)
            icon      = "🟢" if (pnl_thb or 0) >= 0 else "🔴"
            money_str = fmt_money(pnl_thb, disp, rate)
            pct_str   = fmt_pct(pnl_pct)

            with st.expander(f"{icon} **{inv['ticker']}** ({get_currency(inv)}) "
                             f"| Entry: {inv['entry_price']} | {pct_str} | {money_str}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Entry",         inv.get("entry_price","—"))
                c2.metric("ราคาปัจจุบัน", f"{price:.2f}" if price else "—")
                c3.metric("P&L %",         pct_str)
                c4.metric("P&L",           money_str)
                st.caption(f"จำนวน: {get_shares(inv)} หุ้น | "
                           f"Position size: {fmt_money(pos_thb, disp, rate, sign=False)} | "
                           f"ซื้อ: {inv.get('entry_date','—')}")
                if inv.get("thesis"):
                    st.caption(f"เหตุผล: {inv['thesis']}")

                ca, _, cc = st.columns([2, 3, 1])
                if ca.button("🔒 ปิด Position", key=f"ci_{inv['id']}"):
                    st.session_state[f"close_inv_{inv['id']}"] = True
                if cc.button("🗑️", key=f"di_{inv['id']}"):
                    investments[:] = [x for x in investments if x["id"] != inv["id"]]
                    save_investments(investments)
                    st.rerun()

                if st.session_state.get(f"close_inv_{inv['id']}"):
                    with st.form(f"clf_inv_{inv['id']}"):
                        cc1, cc2 = st.columns(2)
                        exit_p = cc1.text_input("Exit Price *")
                        exit_d = cc2.date_input("วันที่ขาย", value=date.today())
                        if st.form_submit_button("ยืนยันปิด"):
                            ep = parse(exit_p)
                            pnl_pct_v = calc_pnl_pct(inv["entry_price"], ep) if ep else None
                            pnl_thb_v = calc_pnl_thb(inv["entry_price"], ep,
                                                      get_shares(inv),
                                                      get_currency(inv), rate) if ep else None
                            inv.update({"status": "closed", "exit_price": exit_p,
                                        "exit_date": str(exit_d),
                                        "pnl_pct": pnl_pct_v, "pnl_thb": pnl_thb_v})
                            save_investments(investments)
                            st.success("ปิด Position เรียบร้อย!")
                            st.rerun()

    if closed_inv:
        st.markdown("---")
        st.subheader(f"Closed ({len(closed_inv)})")
        closed_with_pnl = [i for i in closed_inv if i.get("pnl_thb") is not None]
        if closed_with_pnl:
            st.plotly_chart(
                pnl_bar_chart([i["ticker"] for i in closed_with_pnl],
                              [i["pnl_thb"] for i in closed_with_pnl],
                              disp, rate, "Realized P&L", height=240),
                use_container_width=True)
        for inv in closed_inv:
            icon = "✅" if (inv.get("pnl_thb") or 0) >= 0 else "❌"
            st.caption(f"{icon} **{inv['ticker']}** | Entry: {inv.get('entry_price')} → "
                       f"Exit: {inv.get('exit_price','—')} | "
                       f"{fmt_pct(inv.get('pnl_pct'))} | {fmt_money(inv.get('pnl_thb'), disp, rate)}")


def page_trade(trades: list, disp: str, rate: float):
    st.title("📈 Trade")

    with st.expander("➕ เปิด Trade ใหม่"):
        strategy = strategy_input("nt")
        with st.form("new_trade"):
            c1, c2, c3, c4 = st.columns(4)
            ticker    = c1.text_input("Ticker *", placeholder="เช่น AAPL, AOT.BK")
            direction = c2.selectbox("Direction", ["Long", "Short"])
            currency  = c3.selectbox("ราคาเป็น", ["THB", "USD"])
            shares    = c4.text_input("จำนวนหุ้น *", placeholder="เช่น 100")
            c5, c6, c7 = st.columns(3)
            entry     = c5.text_input("Entry Price *")
            sl        = c6.text_input("Stop Loss")
            tp        = c7.text_input("Take Profit")
            thesis    = st.text_area("Thesis — ทำไมถึงซื้อ *", height=80,
                                     placeholder="เหตุผลสั้นๆ ที่ชัดเจน")
            open_date = st.date_input("วันที่เปิด", value=date.today())

            if st.form_submit_button("✅ บันทึก Trade"):
                e, s = parse(entry), parse(shares)
                if not ticker or e is None or not thesis:
                    st.error("กรุณากรอก Ticker, Entry Price และ Thesis")
                elif not strategy:
                    st.error("กรุณาเลือก Strategy")
                else:
                    rr      = auto_rr(entry, sl, tp)
                    pos_thb = (s or 0) * e * (rate if currency == "USD" else 1)
                    trades.append({
                        "id": next_id(trades), "type": "trade", "status": "open",
                        "ticker": ticker.upper().strip(), "direction": direction,
                        "strategy": strategy, "currency": currency,
                        "entry_price": entry, "shares": shares,
                        "stop_loss": sl, "take_profit": tp, "rr": rr,
                        "thesis": thesis, "open_date": str(open_date),
                        "position_thb": round(pos_thb, 2),
                    })
                    save_trades(trades)
                    st.success(f"✅ บันทึกแล้ว! R:R = {rr} | "
                               f"Position size: {fmt_money(pos_thb, disp, rate, sign=False)}")
                    st.rerun()

    open_trades = [t for t in trades if t.get("status") == "open"]

    # ── Unrealized P&L chart ──────────────────────────────────────────────────
    chart_data = []
    for t in open_trades:
        price = get_price(t.get("ticker",""))
        if price is None: continue
        pnl_thb = calc_pnl_thb(t.get("entry_price"), price, get_shares(t),
                                get_currency(t), rate, t.get("direction","Long"))
        if pnl_thb is not None:
            chart_data.append({"ticker": t["ticker"], "pnl_thb": pnl_thb})

    if chart_data:
        st.plotly_chart(
            pnl_bar_chart([d["ticker"] for d in chart_data],
                          [d["pnl_thb"] for d in chart_data],
                          disp, rate, "Unrealized P&L", height=280),
            use_container_width=True)

    # ── Open trades list ──────────────────────────────────────────────────────
    if not open_trades:
        st.info("ยังไม่มี Trade ที่เปิดอยู่")
    else:
        st.subheader(f"Open Trades ({len(open_trades)})")
        for t in open_trades:
            price   = get_price(t.get("ticker",""))
            pnl_thb = calc_pnl_thb(t.get("entry_price"), price, get_shares(t),
                                    get_currency(t), rate, t.get("direction","Long")) if price else None
            pnl_pct = calc_pnl_pct(t.get("entry_price"), price, t.get("direction","Long")) if price else None
            icon    = "🟢" if (pnl_thb or 0) >= 0 else "🔴"
            arrow   = "↑" if t.get("direction") == "Long" else "↓"

            pos_thb = calc_position_thb(t.get("entry_price"), get_shares(t),
                                        get_currency(t), rate)

            # คำนวณ profit/loss ถ้าโดน TP หรือ SL
            tp_thb = calc_pnl_thb(t.get("entry_price"), parse(t.get("take_profit","")) or 0,
                                  get_shares(t), get_currency(t), rate, t.get("direction","Long"))
            sl_thb = calc_pnl_thb(t.get("entry_price"), parse(t.get("stop_loss","")) or 0,
                                  get_shares(t), get_currency(t), rate, t.get("direction","Long"))

            # header โชว์ข้อมูลสำคัญก่อน expand
            amount_str = fmt_money(pos_thb, disp, rate, sign=False)
            pnl_str    = f"{fmt_pct(pnl_pct)}  {fmt_money(pnl_thb, disp, rate)}"
            header = (f"{icon} **{t['ticker']}** {arrow}  ·  "
                      f"AVG {t.get('entry_price','—')}  ·  "
                      f"{get_shares(t)} shares  ·  {amount_str}  |  {pnl_str}")

            with st.expander(header):

                # ── Row 1: ข้อมูลหลัก ─────────────────────────────────────
                r1c1, r1c2, r1c3, r1c4 = st.columns(4)
                r1c1.metric("AVG Price",      t.get("entry_price","—"))
                r1c2.metric("Shares",         get_shares(t))
                r1c3.metric("Amount",         fmt_money(pos_thb, disp, rate, sign=False))
                r1c4.metric("Current Price",
                            f"{price:.2f}" if price else "—",
                            delta=fmt_pct(pnl_pct) if pnl_pct else None)

                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

                # ── Row 2: TP / P&L / SL ─────────────────────────────────
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
                st.caption(f"R:R {t.get('rr','—')}  ·  {get_currency(t)}  ·  "
                           f"เปิด {t.get('open_date','—')}")
                st.caption(f"Thesis: {t.get('thesis','—')}")
                st.divider()

                # ── Buttons ───────────────────────────────────────────────
                ca, cb, _ = st.columns([2, 2, 3])
                if ca.button("🔒 ปิด Trade", key=f"btn_close_{t['id']}"):
                    st.session_state[f"show_close_{t['id']}"] = True
                    st.session_state.pop(f"show_edit_{t['id']}", None)
                if cb.button("✏️ แก้ไข", key=f"btn_edit_{t['id']}"):
                    st.session_state[f"show_edit_{t['id']}"] = True
                    st.session_state.pop(f"show_close_{t['id']}", None)

                # ── Edit form ─────────────────────────────────────────────
                if st.session_state.get(f"show_edit_{t['id']}"):
                    st.markdown("**แก้ไข Trade**")
                    with st.form(f"form_edit_{t['id']}"):
                        ec1, ec2, ec3 = st.columns(3)
                        new_shares = ec1.text_input("Shares",      value=get_shares(t))
                        new_sl     = ec2.text_input("Stop Loss",   value=t.get("stop_loss",""))
                        new_tp     = ec3.text_input("Take Profit", value=t.get("take_profit",""))
                        ec4, ec5   = st.columns(2)
                        new_entry  = ec4.text_input("AVG Price (ถ้า avg down/up)",
                                                    value=t.get("entry_price",""))
                        new_thesis = ec5.text_input("Thesis", value=t.get("thesis",""))
                        if st.form_submit_button("💾 บันทึก"):
                            t.update({
                                "shares": new_shares, "stop_loss": new_sl,
                                "take_profit": new_tp, "entry_price": new_entry,
                                "thesis": new_thesis,
                                "rr": auto_rr(new_entry, new_sl, new_tp),
                            })
                            save_trades(trades)
                            st.session_state.pop(f"show_edit_{t['id']}", None)
                            st.success("แก้ไขเรียบร้อย!")
                            st.rerun()

                # ── Close form ────────────────────────────────────────────
                if st.session_state.get(f"show_close_{t['id']}"):
                    st.markdown("**ปิด Trade**")
                    with st.form(f"form_close_{t['id']}"):
                        cc1, cc2  = st.columns(2)
                        exit_p    = cc1.text_input("Exit Price *")
                        exit_d    = cc2.date_input("วันที่ปิด", value=date.today())
                        cc3, cc4  = st.columns(2)
                        thesis_ok = cc3.selectbox("Thesis ถูกไหม",
                                                  ["✅ ถูก", "❌ ผิด", "⚠️ บางส่วน"])
                        emotion   = cc4.selectbox("Emotion",
                                                  ["ปกติ", "กลัว", "โลภ", "FOMO"])
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
                            save_trades(trades)
                            st.success(f"ปิด Trade! P&L = {fmt_money(pnl_thb_v, disp, rate)}")
                            st.rerun()


def page_log(trades: list, investments: list, disp: str, rate: float):
    st.title("📓 Log")
    sym = "฿" if disp == "THB" else "$"

    rows = []
    for t in trades:
        pnl_thb = t.get("pnl_thb")
        rows.append({
            "Type": "Trade", "Ticker": t.get("ticker","—"),
            "Dir": t.get("direction","—"), "Strategy": t.get("strategy","—"),
            "Entry": t.get("entry_price","—"), "Exit": t.get("exit_price","—"),
            "P&L %": fmt_pct(t.get("pnl_pct")),
            f"P&L ({sym})": fmt_money(pnl_thb, disp, rate),
            "W/L": t.get("win_loss","open" if t.get("status")=="open" else "—"),
            "วันที่": t.get("open_date","—"), "Status": t.get("status","—"),
        })
    for inv in investments:
        pnl_thb = inv.get("pnl_thb")
        rows.append({
            "Type": "Investment", "Ticker": inv.get("ticker","—"),
            "Dir": "Long", "Strategy": "—",
            "Entry": inv.get("entry_price","—"), "Exit": inv.get("exit_price","—"),
            "P&L %": fmt_pct(inv.get("pnl_pct")),
            f"P&L ({sym})": fmt_money(pnl_thb, disp, rate),
            "W/L": "open" if inv.get("status")=="open" else fmt_pct(inv.get("pnl_pct")),
            "วันที่": inv.get("entry_date","—"), "Status": inv.get("status","—"),
        })

    if not rows:
        st.info("ยังไม่มีข้อมูล")
        return

    c1, c2 = st.columns(2)
    tf = c1.selectbox("ประเภท", ["ทั้งหมด", "Trade", "Investment"])
    sf = c2.selectbox("Status",  ["ทั้งหมด", "open", "closed"])
    if tf != "ทั้งหมด": rows = [r for r in rows if r["Type"] == tf]
    if sf != "ทั้งหมด": rows = [r for r in rows if r["Status"] == sf]

    st.dataframe(rows, use_container_width=True, hide_index=True)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    trades      = load_trades()
    investments = load_investments()
    page, disp, rate = render_sidebar()

    if   page == "📊 Overview":   page_overview(trades, investments, disp, rate)
    elif page == "💼 Investment": page_investment(investments, disp, rate)
    elif page == "📈 Trade":      page_trade(trades, disp, rate)
    elif page == "📓 Log":        page_log(trades, investments, disp, rate)


main()
