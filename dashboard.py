"""
Trade Journal Dashboard — Tim.fin
แก้ design ได้ง่ายๆ:
  - เปลี่ยนสี/ฟอนต์  → แก้ THEME_CSS (ด้านล่าง)
  - เพิ่ม/ลด field    → แก้ page_open_trade() หรือ page_close_trade()
  - เปลี่ยน data storage → แก้ data.py อย่างเดียว
"""
import streamlit as st
import pandas as pd
from datetime import date

from data import load_trades, save_trades, calc_pnl

# ── ตัวเลือก Strategy ─────────────────────────────────────────────────────────
STRATEGY_PRESETS = ["Breakout", "Swing", "Value", "Trend Follow", "Scalp", "MACD", "อื่นๆ (พิมพ์เอง)"]

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Trade Journal", page_icon="📈", layout="wide")

# ── Theme CSS ─────────────────────────────────────────────────────────────────
# แก้ตรงนี้เพื่อเปลี่ยน look & feel ทั้งหน้า
THEME_CSS = """
<style>
    /* metric cards */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 16px 20px;
    }
    /* sidebar header */
    [data-testid="stSidebar"] h1 { font-size: 1.3rem; }
    /* table alternating rows */
    [data-testid="stDataFrame"] tr:nth-child(even) td { background: rgba(255,255,255,0.03); }
    /* form submit button */
    [data-testid="stFormSubmitButton"] button {
        background: #5865f2;
        color: white;
        border-radius: 8px;
        font-weight: 600;
    }
    [data-testid="stFormSubmitButton"] button:hover { background: #4752c4; }
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def strategy_input(key_prefix: str, default: str = "") -> str:
    """Strategy field: เลือก preset หรือพิมพ์เอง"""
    preset_idx = 0
    if default and default not in STRATEGY_PRESETS[:-1]:
        preset_idx = len(STRATEGY_PRESETS) - 1  # "อื่นๆ"
    elif default in STRATEGY_PRESETS:
        preset_idx = STRATEGY_PRESETS.index(default)

    choice = st.selectbox("Strategy", STRATEGY_PRESETS, index=preset_idx, key=f"{key_prefix}_preset")
    if choice == "อื่นๆ (พิมพ์เอง)":
        return st.text_input("ระบุ Strategy", value=default if default not in STRATEGY_PRESETS else "",
                             placeholder="เช่น Gap Fill, EMA Crossover...", key=f"{key_prefix}_custom")
    return choice


def pnl_color(pnl) -> str:
    if not isinstance(pnl, (int, float)):
        return "—"
    sign = "+" if pnl >= 0 else ""
    color = "#4ade80" if pnl >= 0 else "#f87171"
    return f'<span style="color:{color};font-weight:600">{sign}{pnl:.2f}%</span>'


def trade_by_id(trades: list, trade_id: int) -> dict | None:
    return next((t for t in trades if t["id"] == trade_id), None)


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("📈 Trade Journal")
page = st.sidebar.radio("เมนู", [
    "📊 Overview",
    "➕ เปิด Trade ใหม่",
    "🔒 ปิด Trade",
    "📋 Trade Log",
    "✏️ แก้ไข / ลบ",
])
st.sidebar.divider()
st.sidebar.caption("Tim.fin Personal OS")

trades = load_trades()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Overview
# ─────────────────────────────────────────────────────────────────────────────

def page_overview(trades: list):
    st.title("📊 Overview")

    closed = [t for t in trades if t["status"] == "closed"]
    open_  = [t for t in trades if t["status"] == "open"]
    wins   = [t for t in closed if t.get("win_loss") == "Win"]
    pnls   = [t["pnl_pct"] for t in closed if isinstance(t.get("pnl_pct"), (int, float))]

    win_rate = len(wins) / len(closed) * 100 if closed else None
    avg_pnl  = sum(pnls) / len(pnls) if pnls else None

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Trades", len(closed))
    c2.metric("Open", len(open_))
    c3.metric("Win Rate", f"{win_rate:.1f}%" if win_rate is not None else "—",
              delta=f"{win_rate:.1f}%" if win_rate is not None else None)
    c4.metric("Best", f"+{max(pnls):.2f}%" if pnls else "—")
    c5.metric("Avg P&L", f"{avg_pnl:+.2f}%" if avg_pnl is not None else "—",
              delta=f"{avg_pnl:.2f}" if avg_pnl is not None else None)

    st.divider()

    if pnls:
        st.subheader("P&L ต่อ Trade")
        df_chart = pd.DataFrame([
            {"Trade": f"#{t['id']} {t['ticker']}", "P&L (%)": t["pnl_pct"]}
            for t in closed if isinstance(t.get("pnl_pct"), (int, float))
        ])
        st.bar_chart(df_chart.set_index("Trade"))

    if open_:
        st.subheader("🟢 Open Positions")
        df_open = pd.DataFrame([{
            "#": t["id"], "Ticker": t["ticker"], "Direction": t["direction"],
            "Entry": t["entry_price"], "Size": t.get("size", "—"),
            "Strategy": t.get("strategy", "—"), "วันที่เปิด": t["open_date"],
            "Stop Loss": t.get("stop_loss", "—"), "Take Profit": t.get("take_profit", "—"),
        } for t in open_])
        st.dataframe(df_open, use_container_width=True, hide_index=True)

    if not trades:
        st.info("ยังไม่มี trade — เริ่มบันทึก trade แรกได้เลย!")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: เปิด Trade ใหม่
# ─────────────────────────────────────────────────────────────────────────────

def page_open_trade(trades: list):
    st.title("➕ เปิด Trade ใหม่")

    with st.form("open_trade"):
        col1, col2 = st.columns(2)
        with col1:
            ticker      = st.text_input("Ticker / Asset *", placeholder="เช่น AAPL, BTC, PTT")
            direction   = st.selectbox("Direction", ["Long", "Short"])
            strategy    = strategy_input("open")
            timeframe   = st.selectbox("Timeframe", ["Short-term", "Mid-term", "Long-term"])
            open_date   = st.date_input("วันที่ซื้อ", value=date.today())
        with col2:
            entry_price = st.text_input("Entry Price *", placeholder="เช่น 185.50")
            size        = st.text_input("Position Size", placeholder="เช่น 50,000 บาท หรือ 100 หุ้น")
            stop_loss   = st.text_input("Stop Loss", placeholder="ราคาที่จะยอมขาดทุน")
            take_profit = st.text_input("Take Profit", placeholder="ราคาเป้าหมาย")
            rr          = st.text_input("R:R Ratio", placeholder="เช่น 1:2")

        st.markdown("---")
        thesis        = st.text_area("Thesis — ทำไมถึงซื้อ *", height=80,
                                     placeholder="ทำไมถึงเลือก asset นี้ตอนนี้?")
        entry_trigger = st.text_input("Entry Trigger — อะไรทำให้กดซื้อวันนี้",
                                      placeholder="เช่น แท่งเทียน close เหนือ resistance")
        invalidation  = st.text_input("Invalidation — thesis ผิดเมื่อไร ต้องออก",
                                      placeholder="เช่น ราคาหลุด SL หรือ thesis เปลี่ยน")

        submitted = st.form_submit_button("✅ บันทึก Trade", use_container_width=True)

    if submitted:
        if not ticker or not entry_price or not thesis:
            st.error("กรุณากรอก Ticker, Entry Price และ Thesis ก่อนบันทึก")
            return
        if not strategy:
            st.error("กรุณาระบุ Strategy")
            return

        new_id = max((t["id"] for t in trades), default=0) + 1  # safe แม้ลบ trade ไปแล้ว
        trade = {
            "id": new_id, "status": "open",
            "open_date": str(open_date), "ticker": ticker.upper().strip(),
            "direction": direction, "strategy": strategy,
            "timeframe": timeframe, "entry_price": entry_price,
            "size": size, "stop_loss": stop_loss,
            "take_profit": take_profit, "rr": rr,
            "thesis": thesis, "entry_trigger": entry_trigger,
            "invalidation": invalidation,
        }
        trades.append(trade)
        save_trades(trades)
        st.success(f"✅ บันทึก Trade #{trade['id']} — {trade['ticker']} เรียบร้อย!")
        st.balloons()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: ปิด Trade
# ─────────────────────────────────────────────────────────────────────────────

def page_close_trade(trades: list):
    st.title("🔒 ปิด Trade")

    open_trades = [t for t in trades if t["status"] == "open"]
    if not open_trades:
        st.info("ไม่มี trade ที่เปิดอยู่")
        return

    options = {
        f"#{t['id']} — {t['ticker']} | Entry: {t['entry_price']} | เปิด: {t['open_date']}": t["id"]
        for t in open_trades
    }
    selected_label = st.selectbox("เลือก Trade ที่จะปิด", list(options.keys()))
    trade = trade_by_id(trades, options[selected_label])

    with st.container(border=True):
        st.markdown(f"**Thesis เดิม:** {trade.get('thesis','—')}")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Stop Loss:** {trade.get('stop_loss','—')}")
        with col2:
            st.write(f"**Take Profit:** {trade.get('take_profit','—')}")

    with st.form("close_trade"):
        col1, col2 = st.columns(2)
        with col1:
            exit_price     = st.text_input("Exit Price *", placeholder="ราคาที่ขาย")
            close_date     = st.date_input("วันที่ขาย", value=date.today())
            exit_reason    = st.selectbox("Exit Reason", ["TP hit", "SL hit", "Manual", "อื่นๆ"])
        with col2:
            thesis_correct = st.selectbox("Thesis ถูกไหม?", ["✅ ถูก", "❌ ผิด", "⚠️ บางส่วน"])
            execution      = st.selectbox("Execution", ["ดี", "พอใช้", "แย่"])
            emotion        = st.selectbox("Emotion ตอนถือ", ["ปกติ", "กลัว", "โลภ", "ไม่แน่ใจ"])

        mistake = st.text_input("Mistake (ถ้าไม่มีใส่ -)", value="-")
        lesson  = st.text_area("Lesson ที่ได้", height=80,
                               placeholder="เรียนรู้อะไรจาก trade นี้?")

        submitted = st.form_submit_button("🔒 ปิด Trade", use_container_width=True)

    if submitted:
        if not exit_price:
            st.error("กรุณากรอก Exit Price")
            return

        pnl = calc_pnl(trade["entry_price"], exit_price, trade["direction"])
        trade.update({
            "status": "closed", "close_date": str(close_date),
            "exit_price": exit_price, "exit_reason": exit_reason,
            "thesis_correct": thesis_correct, "execution": execution,
            "emotion": emotion, "mistake": mistake, "lesson": lesson,
            "pnl_pct": pnl,
            "win_loss": "Win" if (pnl or 0) > 0 else "Loss",
        })
        save_trades(trades)

        if trade["win_loss"] == "Win":
            st.success(f"✅ Win! P&L: {pnl:+.2f}%" if pnl is not None else "✅ Win! บันทึกแล้ว")
            st.balloons()
        else:
            st.error(f"❌ Loss | P&L: {pnl:+.2f}%" if pnl is not None else "❌ Loss | บันทึกแล้ว")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Trade Log
# ─────────────────────────────────────────────────────────────────────────────

def page_trade_log(trades: list):
    st.title("📋 Trade Log")

    if not trades:
        st.info("ยังไม่มี trade")
        return

    rows = []
    for t in trades:
        pnl_raw = t.get("pnl_pct")
        pnl_str = f"{pnl_raw:+.2f}%" if isinstance(pnl_raw, (int, float)) else "open"
        rows.append({
            "#": t["id"], "วันที่": t["open_date"], "Ticker": t["ticker"],
            "Direction": t["direction"], "Strategy": t.get("strategy", "—"),
            "Entry": t["entry_price"], "Exit": t.get("exit_price", "—"),
            "P&L": pnl_str, "W/L": t.get("win_loss", "open"),
            "Lesson": t.get("lesson", "—"),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("ดูรายละเอียด Trade")

    trade_options = {f"#{t['id']} — {t['ticker']} ({t['status']})": t["id"] for t in trades}
    selected = st.selectbox("เลือก Trade", list(trade_options.keys()))
    t = trade_by_id(trades, trade_options[selected])  # lookup by ID, ไม่ใช่ array index

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**PRE-TRADE**")
            for label, key in [
                ("Ticker", "ticker"), ("Direction", "direction"), ("Strategy", "strategy"),
                ("Timeframe", "timeframe"), ("Entry Price", "entry_price"),
                ("Size", "size"), ("Stop Loss", "stop_loss"),
                ("Take Profit", "take_profit"), ("R:R", "rr"),
                ("Thesis", "thesis"), ("Entry Trigger", "entry_trigger"),
                ("Invalidation", "invalidation"),
            ]:
                st.write(f"**{label}:** {t.get(key,'—')}")

    with col2:
        if t["status"] == "closed":
            with st.container(border=True):
                st.markdown("**POST-TRADE**")
                pnl_raw = t.get("pnl_pct")
                pnl_d = f"{pnl_raw:+.2f}%" if isinstance(pnl_raw, (int, float)) else "—"
                for label, key in [
                    ("Exit Price", "exit_price"), ("Exit Date", "close_date"),
                    ("Exit Reason", "exit_reason"), ("Thesis ถูกไหม", "thesis_correct"),
                    ("Execution", "execution"), ("Emotion", "emotion"),
                    ("Mistake", "mistake"), ("Lesson", "lesson"),
                ]:
                    st.write(f"**{label}:** {t.get(key,'—')}")
                st.markdown(f"**P&L:** {pnl_d}")
                st.markdown(f"**Win/Loss:** {t.get('win_loss','—')}")
        else:
            st.info("🟢 Trade ยังเปิดอยู่")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: แก้ไข / ลบ
# ─────────────────────────────────────────────────────────────────────────────

def page_edit(trades: list):
    st.title("✏️ แก้ไข / ลบ Trade")

    if not trades:
        st.info("ยังไม่มี trade")
        return

    options = {f"#{t['id']} — {t['ticker']} ({t['status']})": t["id"] for t in trades}
    selected = st.selectbox("เลือก Trade", list(options.keys()))
    t = trade_by_id(trades, options[selected])

    tab_edit, tab_delete = st.tabs(["✏️ แก้ไข", "🗑️ ลบ"])

    with tab_edit:
        with st.form("edit_trade"):
            col1, col2 = st.columns(2)
            with col1:
                ticker      = st.text_input("Ticker", value=t.get("ticker", ""))
                entry_price = st.text_input("Entry Price", value=t.get("entry_price", ""))
                stop_loss   = st.text_input("Stop Loss", value=t.get("stop_loss", ""))
                take_profit = st.text_input("Take Profit", value=t.get("take_profit", ""))
                rr          = st.text_input("R:R", value=t.get("rr", ""))
            with col2:
                strategy    = strategy_input("edit", default=t.get("strategy", ""))
                size        = st.text_input("Position Size", value=t.get("size", ""))
            thesis        = st.text_area("Thesis", value=t.get("thesis", ""), height=80)
            entry_trigger = st.text_input("Entry Trigger", value=t.get("entry_trigger", ""))
            invalidation  = st.text_input("Invalidation", value=t.get("invalidation", ""))
            lesson        = st.text_area("Lesson", value=t.get("lesson", ""), height=60)

            if st.form_submit_button("💾 บันทึกการแก้ไข", use_container_width=True):
                t.update({
                    "ticker": ticker.upper(), "entry_price": entry_price,
                    "stop_loss": stop_loss, "take_profit": take_profit,
                    "strategy": strategy, "size": size, "rr": rr,
                    "thesis": thesis, "entry_trigger": entry_trigger,
                    "invalidation": invalidation, "lesson": lesson,
                })
                save_trades(trades)
                st.success("✅ แก้ไขเรียบร้อย!")

    with tab_delete:
        st.warning(f"จะลบ Trade #{t['id']} — {t['ticker']} ออกจากระบบถาวร")
        if st.button("🗑️ ยืนยันลบ", type="primary", use_container_width=True):
            trades[:] = [x for x in trades if x["id"] != t["id"]]
            save_trades(trades)
            st.success("ลบเรียบร้อย!")
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

if page == "📊 Overview":
    page_overview(trades)
elif page == "➕ เปิด Trade ใหม่":
    page_open_trade(trades)
elif page == "🔒 ปิด Trade":
    page_close_trade(trades)
elif page == "📋 Trade Log":
    page_trade_log(trades)
elif page == "✏️ แก้ไข / ลบ":
    page_edit(trades)
