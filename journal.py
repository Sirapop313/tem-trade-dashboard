"""
สร้าง trade-journal.md อัตโนมัติจาก trades list
"""
import os

DIR = os.path.dirname(os.path.abspath(__file__))
JOURNAL_FILE = os.path.join(DIR, "trade-journal.md")


def regenerate(trades: list) -> None:
    closed = [t for t in trades if t["status"] == "closed"]
    open_  = [t for t in trades if t["status"] == "open"]
    wins   = [t for t in closed if t.get("win_loss") == "Win"]
    pnls   = [t["pnl_pct"] for t in closed if isinstance(t.get("pnl_pct"), (int, float))]

    win_rate = f"{len(wins)/len(closed)*100:.1f}%" if closed else "—"
    best     = f"+{max(pnls):.2f}%" if pnls else "—"
    worst    = f"{min(pnls):.2f}%" if pnls else "—"
    avg_pnl  = f"{sum(pnls)/len(pnls):+.2f}%" if pnls else "—"

    lines = [
        "# Trade Journal — Tim.fin\n\n---\n\n",
        "## 📊 Stats Overview\n\n",
        "| Metric | Value |\n|---|---|\n",
        f"| Total Trades | {len(closed)} |\n",
        f"| Open | {len(open_)} |\n",
        f"| Win | {len(wins)} |\n",
        f"| Loss | {len(closed) - len(wins)} |\n",
        f"| Win Rate | {win_rate} |\n",
        f"| Best Trade | {best} |\n",
        f"| Worst Trade | {worst} |\n",
        f"| Avg P&L | {avg_pnl} |\n\n---\n\n",
        "## 📋 Trade Log\n\n",
        "| # | Date | Ticker | Direction | Entry | Exit | P&L | W/L | Strategy |\n",
        "|---|---|---|---|---|---|---|---|---|\n",
    ]

    for t in trades:
        pnl = f"{t['pnl_pct']:+.2f}%" if isinstance(t.get("pnl_pct"), (int, float)) else "open"
        lines.append(
            f"| {t['id']} | {t['open_date']} | {t['ticker']} | {t['direction']} "
            f"| {t['entry_price']} | {t.get('exit_price','—')} | {pnl} "
            f"| {t.get('win_loss','open')} | {t.get('strategy','—')} |\n"
        )

    lines.append("\n---\n\n## 📝 Trade Details\n\n")

    for t in trades:
        badge = (
            "🟢 OPEN" if t["status"] == "open"
            else ("✅ WIN" if t.get("win_loss") == "Win" else "❌ LOSS")
        )
        lines.append(f"### TRADE #{t['id']} — {t['ticker']} — {t['open_date']} | {badge}\n\n")
        lines.append("**[ PRE-TRADE ]**\n\n")
        for label, key in [
            ("Direction", "direction"), ("Strategy", "strategy"),
            ("Timeframe", "timeframe"), ("Entry Price", "entry_price"),
            ("Size", "size"), ("Stop Loss", "stop_loss"),
            ("Take Profit", "take_profit"), ("R:R", "rr"),
            ("Thesis", "thesis"), ("Entry Trigger", "entry_trigger"),
            ("Invalidation", "invalidation"),
        ]:
            lines.append(f"- **{label}:** {t.get(key, '—')}\n")
        lines.append("\n")

        if t["status"] == "closed":
            lines.append("**[ POST-TRADE ]**\n\n")
            pnl_d = f"{t['pnl_pct']:+.2f}%" if isinstance(t.get("pnl_pct"), (int, float)) else "—"
            for label, key in [
                ("Exit Date", "close_date"), ("Exit Price", "exit_price"),
                ("Exit Reason", "exit_reason"), ("Thesis ถูกไหม", "thesis_correct"),
                ("Execution", "execution"), ("Emotion", "emotion"),
                ("Mistake", "mistake"), ("Lesson", "lesson"),
            ]:
                lines.append(f"- **{label}:** {t.get(key, '—')}\n")
            lines.append(f"- **P&L:** {pnl_d}\n- **Win/Loss:** {t.get('win_loss','—')}\n\n")

        lines.append("---\n\n")

    with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
