#!/usr/bin/env python3
import json
import os
from datetime import datetime

DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE = os.path.join(DIR, 'trades.json')
JOURNAL_FILE = os.path.join(DIR, 'trade-journal.md')


def load_trades():
    if not os.path.exists(TRADES_FILE):
        return []
    with open(TRADES_FILE, encoding='utf-8') as f:
        return json.load(f)


def save_trades(trades):
    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)
    regenerate_journal(trades)


def ask(prompt, default=None):
    hint = f" [{default}]" if default else ""
    val = input(f"  {prompt}{hint}: ").strip()
    return val if val else (default or "")


def add_trade(trades):
    print("\n📝 บันทึก Trade ใหม่")
    print("-" * 40)
    trade = {
        'id': len(trades) + 1,
        'status': 'open',
        'open_date': datetime.now().strftime('%Y-%m-%d'),
    }
    trade['ticker']         = ask("Ticker / Asset (เช่น AAPL, BTC)")
    trade['direction']      = ask("Direction", "Long")
    trade['strategy']       = ask("Strategy (Breakout / Value / Swing / Trend)")
    trade['timeframe']      = ask("Timeframe (Short / Mid / Long-term)")
    trade['entry_price']    = ask("Entry Price")
    trade['size']           = ask("Position Size (จำนวนหุ้น หรือ เงิน)")
    trade['stop_loss']      = ask("Stop Loss (ราคา)")
    trade['take_profit']    = ask("Take Profit Target (ราคา)")
    trade['rr']             = ask("R:R Ratio (เช่น 1:2)")
    trade['thesis']         = ask("Thesis — ทำไมถึงซื้อ")
    trade['entry_trigger']  = ask("Entry Trigger — อะไรทำให้กดซื้อวันนี้")
    trade['invalidation']   = ask("Invalidation — อะไรทำให้ thesis ผิด ต้องออก")

    trades.append(trade)
    save_trades(trades)
    print(f"\n✅ บันทึก Trade #{trade['id']} — {trade['ticker']} เรียบร้อย!")


def close_trade(trades):
    open_trades = [t for t in trades if t['status'] == 'open']
    if not open_trades:
        print("\n❌ ไม่มี trade ที่เปิดอยู่")
        return

    print("\n🔒 ปิด Trade")
    print("-" * 40)
    for t in open_trades:
        print(f"  [{t['id']}] {t['ticker']} | Entry: {t['entry_price']} | เปิด: {t['open_date']}")

    try:
        trade_id = int(ask("\nเลือก Trade ID ที่จะปิด"))
        trade = next(t for t in trades if t['id'] == trade_id)
    except (ValueError, StopIteration):
        print("❌ ไม่พบ trade")
        return

    trade['close_date']     = datetime.now().strftime('%Y-%m-%d')
    trade['exit_price']     = ask("Exit Price")
    trade['exit_reason']    = ask("Exit Reason (TP hit / SL hit / Manual)")
    trade['thesis_correct'] = ask("Thesis ถูกไหม (ถูก / ผิด / บางส่วน)")
    trade['execution']      = ask("Execution ดีไหม (ดี / พอใช้ / แย่)")
    trade['emotion']        = ask("Emotion ตอนถือ (ปกติ / กลัว / โลภ)")
    trade['mistake']        = ask("Mistake (ถ้าไม่มีพิมพ์ -)", "-")
    trade['lesson']         = ask("Lesson ที่ได้")

    try:
        entry = float(trade['entry_price'].replace(',', ''))
        exit_ = float(trade['exit_price'].replace(',', ''))
        pnl_pct = (exit_ - entry) / entry * 100
        if trade['direction'].lower() == 'short':
            pnl_pct = -pnl_pct
        trade['pnl_pct'] = round(pnl_pct, 2)
        trade['win_loss'] = 'Win' if pnl_pct > 0 else 'Loss'
    except Exception:
        trade['pnl_pct'] = 0
        trade['win_loss'] = ask("Win / Loss")

    trade['status'] = 'closed'
    save_trades(trades)
    pnl_str = f"{trade['pnl_pct']:+.2f}%"
    print(f"\n✅ ปิด Trade #{trade['id']} — {trade['ticker']} | {trade['win_loss']} | {pnl_str}")


def show_stats(trades):
    closed = [t for t in trades if t['status'] == 'closed']
    open_  = [t for t in trades if t['status'] == 'open']
    wins   = [t for t in closed if t.get('win_loss') == 'Win']
    pnls   = [t['pnl_pct'] for t in closed if isinstance(t.get('pnl_pct'), (int, float))]

    print("\n📊 Stats Overview")
    print("-" * 40)
    print(f"  Total Closed : {len(closed)}")
    print(f"  Open         : {len(open_)}")
    if closed:
        print(f"  Win          : {len(wins)}")
        print(f"  Loss         : {len(closed) - len(wins)}")
        print(f"  Win Rate     : {len(wins)/len(closed)*100:.1f}%")
    if pnls:
        print(f"  Best Trade   : +{max(pnls):.2f}%")
        print(f"  Worst Trade  : {min(pnls):.2f}%")
        print(f"  Avg P&L      : {sum(pnls)/len(pnls):+.2f}%")
    if not closed:
        print("  (ยังไม่มี trade ที่ปิดแล้ว)")


def list_trades(trades):
    print("\n📋 Trade Log")
    print("-" * 60)
    if not trades:
        print("  ยังไม่มี trade")
        return
    for t in trades:
        if t['status'] == 'open':
            icon, pnl = "🟢", "open"
        elif t.get('win_loss') == 'Win':
            icon = "✅"
            pnl  = f"+{t['pnl_pct']:.2f}%"
        else:
            icon = "❌"
            pnl  = f"{t['pnl_pct']:.2f}%"
        print(f"  {icon} #{t['id']:>2} {t['ticker']:<8} {t['direction']:<5} "
              f"Entry:{t['entry_price']:>10}  {pnl}")


def edit_trade(trades):
    list_trades(trades)
    try:
        trade_id = int(ask("\nเลือก Trade ID ที่จะแก้ไข (0 = ยกเลิก)"))
        if trade_id == 0:
            return
        trade = next(t for t in trades if t['id'] == trade_id)
    except (ValueError, StopIteration):
        print("❌ ไม่พบ trade")
        return

    print(f"\n✏️  แก้ไข Trade #{trade_id} — {trade['ticker']}")
    print("  (กด Enter เพื่อข้ามช่องที่ไม่แก้)")
    fields = [
        ('ticker', 'Ticker'), ('direction', 'Direction'),
        ('strategy', 'Strategy'), ('entry_price', 'Entry Price'),
        ('stop_loss', 'Stop Loss'), ('take_profit', 'Take Profit'),
        ('thesis', 'Thesis'), ('lesson', 'Lesson'),
    ]
    for key, label in fields:
        new_val = ask(f"{label}", trade.get(key, ''))
        if new_val:
            trade[key] = new_val

    save_trades(trades)
    print(f"✅ แก้ไข Trade #{trade_id} เรียบร้อย")


def delete_trade(trades):
    list_trades(trades)
    try:
        trade_id = int(ask("\nเลือก Trade ID ที่จะลบ (0 = ยกเลิก)"))
        if trade_id == 0:
            return
        trade = next(t for t in trades if t['id'] == trade_id)
        confirm = ask(f"ยืนยันลบ Trade #{trade_id} — {trade['ticker']}? (yes/no)")
        if confirm.lower() == 'yes':
            trades.remove(trade)
            save_trades(trades)
            print(f"✅ ลบ Trade #{trade_id} แล้ว")
    except (ValueError, StopIteration):
        print("❌ ไม่พบ trade")


def regenerate_journal(trades):
    closed = [t for t in trades if t['status'] == 'closed']
    open_  = [t for t in trades if t['status'] == 'open']
    wins   = [t for t in closed if t.get('win_loss') == 'Win']
    pnls   = [t['pnl_pct'] for t in closed if isinstance(t.get('pnl_pct'), (int, float))]
    win_rate = f"{len(wins)/len(closed)*100:.1f}%" if closed else "—"
    best  = f"+{max(pnls):.2f}%" if pnls else "—"
    worst = f"{min(pnls):.2f}%" if pnls else "—"

    lines = [
        "# Trade Journal — Tim.fin\n\n",
        "---\n\n",
        "## 📊 Stats Overview\n",
        "> อัปเดตอัตโนมัติโดย trade.py\n\n",
        "| Metric | Value |\n|---|---|\n",
        f"| Total Trades | {len(closed)} |\n",
        f"| Open | {len(open_)} |\n",
        f"| Win | {len(wins)} |\n",
        f"| Loss | {len(closed)-len(wins)} |\n",
        f"| Win Rate | {win_rate} |\n",
        f"| Best Trade | {best} |\n",
        f"| Worst Trade | {worst} |\n\n",
        "---\n\n",
        "## 📋 Trade Log\n\n",
        "| # | Date | Ticker | Direction | Entry | Exit | P&L | W/L | Strategy |\n",
        "|---|---|---|---|---|---|---|---|---|\n",
    ]

    for t in trades:
        if isinstance(t.get('pnl_pct'), (int, float)):
            pnl_str = f"{t['pnl_pct']:+.2f}%"
        else:
            pnl_str = "open"
        wl = t.get('win_loss', 'open')
        exit_p = t.get('exit_price', '—')
        lines.append(
            f"| {t['id']} | {t['open_date']} | {t['ticker']} | {t['direction']} "
            f"| {t['entry_price']} | {exit_p} | {pnl_str} | {wl} | {t.get('strategy','—')} |\n"
        )

    lines.append("\n---\n\n## 📝 Trade Details\n\n")

    for t in trades:
        if t['status'] == 'open':
            badge = "🟢 OPEN"
        elif t.get('win_loss') == 'Win':
            badge = "✅ WIN"
        else:
            badge = "❌ LOSS"

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

        if t['status'] == 'closed':
            lines.append("**[ POST-TRADE ]**\n\n")
            pnl_display = f"{t['pnl_pct']:+.2f}%" if isinstance(t.get('pnl_pct'), (int, float)) else "—"
            for label, key in [
                ("Exit Date", "close_date"), ("Exit Price", "exit_price"),
                ("Exit Reason", "exit_reason"), ("Thesis ถูกไหม", "thesis_correct"),
                ("Execution", "execution"), ("Emotion", "emotion"),
                ("Mistake", "mistake"), ("Lesson", "lesson"),
            ]:
                lines.append(f"- **{label}:** {t.get(key, '—')}\n")
            lines.append(f"- **P&L:** {pnl_display}\n")
            lines.append(f"- **Win/Loss:** {t.get('win_loss', '—')}\n\n")

        lines.append("---\n\n")

    with open(JOURNAL_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def main():
    trades = load_trades()
    while True:
        print("\n🗂️  Trade Journal")
        print("=" * 40)
        print("  [1] บันทึก Trade ใหม่")
        print("  [2] ปิด Trade  (กรอก post-trade)")
        print("  [3] ดู Trades ทั้งหมด")
        print("  [4] Stats สรุป")
        print("  [5] แก้ไข Trade")
        print("  [6] ลบ Trade")
        print("  [0] ออก")

        choice = input("\nเลือก: ").strip()
        if choice == '1':
            add_trade(trades)
        elif choice == '2':
            close_trade(trades)
        elif choice == '3':
            list_trades(trades)
        elif choice == '4':
            show_stats(trades)
        elif choice == '5':
            edit_trade(trades)
        elif choice == '6':
            delete_trade(trades)
        elif choice == '0':
            print("👋 Bye!")
            break


if __name__ == '__main__':
    main()
