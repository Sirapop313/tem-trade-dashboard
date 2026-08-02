# Investment OS — Project Context

> source of truth ของ project — อัปเดตทุกครั้งที่มีการเปลี่ยนแปลงสำคัญ
> ใครก็ตาม (คน / AI) ที่อ่านไฟล์นี้ควรเข้าใจ project ได้ทันทีโดยไม่ต้องถามเพิ่ม

---

## จุดประสงค์

เว็บแอปส่วนตัวสำหรับบันทึกและติดตาม portfolio การลงทุน รองรับ multi-user
- **Investment** — long-term holdings
- **Trade** — short/medium-term trades (entry, SL, TP, thesis)
- **Cash** — ติดตามเงินสดแต่ละบัญชี + cash flow อัตโนมัติ

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit (Python) |
| Hosting | Streamlit Cloud (auto-deploy จาก GitHub push) |
| Database | Supabase (PostgreSQL + Auth) |
| Live prices | yfinance |
| Charts | Plotly |

---

## โครงสร้างไฟล์

```
investing/
├── dashboard.py          ← MAIN FILE — ทุกอย่างอยู่ที่นี่
├── CONTEXT.md            ← ไฟล์นี้
├── journal.py            ← generate trade-journal.md อัตโนมัติทุก save
├── trade-journal.md      ← Obsidian อ่านไฟล์นี้ (auto-generated ห้ามแก้มือ)
├── trades.json           ← local fallback เมื่อไม่มี Supabase
├── investments.json      ← local fallback
├── cash.json             ← local fallback สำหรับ cash accounts
├── data.py               ← DEPRECATED ไม่ได้ใช้แล้ว อย่าแก้
├── trade.py              ← DEPRECATED ไม่ได้ใช้แล้ว อย่าแก้
├── dashboard_v1_backup.py ← backup เก่า อย่าแก้
├── requirements.txt
└── .streamlit/
    ├── config.toml           ← dark theme, primaryColor #5865f2
    ├── secrets.toml          ← อยู่ใน .gitignore ห้าม push
    └── secrets.toml.example
```

---

## Supabase Setup

**Project:** Tim's Trade
**URL:** `https://nmjsbdjjziwhcjuxdvsx.supabase.co`
**Key type:** anon/public (ไม่ใช่ service_role)
**Email confirmation:** ปิดอยู่ (สำหรับ trusted users)

### Tables (ทั้งหมด RLS enabled)
| Table | บทบาท |
|---|---|
| `trades` | trade แต่ละรายการ |
| `investments` | long-term holdings |
| `cash_accounts` | cash account แต่ละบัญชี |

### Schema (ทุก table เหมือนกัน)
```sql
create table trades (
  id bigint generated always as identity primary key,
  user_id uuid,   ← ผูกกับ auth.users
  data jsonb not null
);
-- RLS policy: auth.uid() = user_id
```

### วิธี save (delete by user_id + re-insert)
```python
DELETE /table?user_id=eq.{user_id}   # ลบเฉพาะของ user นี้
POST   /table                          # insert ใหม่พร้อม user_id
```

---

## Auth System

- Supabase Auth (email + password)
- Login page แสดงก่อนเข้าแอปเสมอ (ถ้า Supabase secrets พร้อม)
- Session เก็บใน `st.session_state["sb_session"]`
- JWT token ส่งไปทุก Supabase request → RLS filter อัตโนมัติ
- Local mode (ไม่มี secrets) → ข้าม login → อ่าน/เขียน JSON local

---

## Features ปัจจุบัน (verified ทำงานได้)

### Navigation: Overview | Investment | Trade | Cash | Log

### Overview
- KPI: Portfolio Value, Unrealized P&L, Realized P&L, Win Rate
- **Allocation Pie chart** — แต่ละ position + Cash
- **Portfolio Line chart** — 1D / 1W / 1M / 1Y filter
- P&L bar charts (unrealized + realized)
- Recent Activity, Winners & Losers

### Investment
- **Summary metrics**: Total Value (incl. Cash), Total P&L + % delta, Holdings count, Best Performer
- **Holdings Pie chart** — สัดส่วน holdings
- **Sortable table**: Size (default) / Gain / Loss / Ticker / P&L THB
- **Colored P&L**: สีเขียว (+) สีแดง (-) ใน P&L % และ P&L ฿
- **Row numbering**: เริ่มจาก 1
- **TOTAL row**: ท้ายสุด แสดง market value รวม + P&L รวม
- Edit / Close / Delete position
- Cash summary (link ไปหน้า Cash)

### Trade
- Open trades: card แสดง TP/SL/R:R/P&L live
- Edit (ticker, shares, entry, SL, TP, thesis) / Close / Delete
- Analytics: Win/Loss pie, P&L by Strategy
- Closed trades table

### Cash (💵)
- Summary: ยอดรวม THB / USD / Net
- Account list: แต่ละอันมี ชื่อ, currency, ยอด, สีแดง=ติดลบ
- Actions: แก้ชื่อ+ยอด / Reassign รวมกับบัญชีอื่น (ย้ายยอด + update trades/investments) / ลบ
- เพิ่มบัญชีใหม่: preset (Dime/Webull/Binance/Bitkub/SCB/KBank) หรือพิมพ์เอง
- **Cash Flow History**: ดูเงินเข้า/ออกแต่ละบัญชีผ่าน trade/investment

### Cash Flow Logic
```
เปิด trade/investment:
  → เลือก "จ่ายจากบัญชีไหน" (existing หรือ Other Cash = สร้างใหม่)
  → cash.amount -= position_value (แปลงตาม currency ของ account)
  → บันทึก source_account_id ใน trade/investment

ปิด trade/investment:
  → cash_credit(source_account_id, exit_value)
  → เงิน + กำไรกลับบัญชีเดิม

Import mode (📥 checkbox):
  → บันทึก source_account แต่ไม่หักเงิน
  → ใช้สำหรับ position ที่มีอยู่แล้วก่อนเริ่มใช้ระบบ
```

### Log
- ประวัติ trades + investments รวม
- Filter: ประเภท / status / W/L
- Export CSV

---

## Data Structures

### Trade
```json
{
  "id": 1, "type": "trade", "status": "open",
  "ticker": "ISRG", "direction": "Long", "strategy": "Breakout",
  "currency": "USD", "entry_price": "430.78", "shares": "1.25",
  "stop_loss": "408", "take_profit": "480", "rr": "1:2.2",
  "thesis": "...", "open_date": "2026-05-27",
  "source_account_id": 1, "source_account_name": "Webull",
  "position_thb": 15000.0,
  // เมื่อปิด:
  "exit_price": "...", "close_date": "...",
  "pnl_pct": 5.2, "pnl_thb": 2340.0, "win_loss": "Win",
  "emotion": "ปกติ", "lesson": "..."
}
```

### Investment
```json
{
  "id": 1, "type": "investment", "status": "open",
  "ticker": "BTC-USD", "shares": "0.05", "currency": "USD",
  "entry_price": "68413", "entry_date": "2026-06-02",
  "thesis": "...", "position_thb": 137000.0,
  "source_account_id": 2, "source_account_name": "Bitkub"
}
```

### Cash Account
```json
{"id": 1, "name": "Webull", "currency": "USD", "amount": 1500.0}
```

---

## Deployment

**Live URL:** https://tem-trade-dashboard-bkxoooe4i3pp3x7unexdgu.streamlit.app/

### วิธี deploy ใหม่ (ถ้าต้องตั้งจากศูนย์)
1. Push code ขึ้น GitHub `Sirapop313/tem-trade-dashboard`
2. Login Streamlit Cloud → New app → ชี้ที่ repo
3. Settings → Secrets → ใส่:
   ```toml
   SUPABASE_URL = "https://nmjsbdjjziwhcjuxdvsx.supabase.co"
   SUPABASE_KEY = "eyJ..."
   ```
4. Deploy → เข้าหน้า Login → สมัครหรือ Login ได้เลย

### วิธีรัน local
```bash
cd /Users/tem/Documents/tem-os/investing
streamlit run dashboard.py
```
→ http://localhost:8501 → ใช้ secrets.toml local → Supabase

---

## Decisions Log

| Decision | เหตุผล | วันที่ |
|---|---|---|
| Supabase แทน JSON | persistent + multi-user | 2026-06-01 |
| jsonb ทั้งก้อน | flexible ไม่ต้อง migrate schema | 2026-06-01 |
| Cash เป็น list of accounts | รองรับหลาย platform | 2026-06-01 |
| Cash flow deduct/credit | track เงินได้จริง | 2026-06-02 |
| Import mode checkbox | port เก่าไม่กระทบ cash | 2026-06-02 |
| Cash page แยก | cash เชื่อมทั้ง trade+investment ไม่ควรอยู่ใน Investment เท่านั้น | 2026-06-02 |
| Email confirmation ปิด | trusted users, ง่ายกว่า | 2026-06-02 |
| ไม่ทำ Auth ด้วย service_role | anon key + RLS เพียงพอ | 2026-06-02 |

---

## อย่าทำ (ตัดสินใจออก / เคยลองแล้วไม่ work)

- **อย่าแก้ `data.py`** — deprecated ไม่ได้ใช้ใน dashboard.py
- **อย่า push `secrets.toml`** — มี API key อยู่ใน .gitignore แล้ว
- **อย่าใช้ number_input กับ currency selector ใน form เดียวกัน** — step/format ไม่ dynamic ในขณะที่ form ยังไม่ submit → ใช้ text_input แทน
- **อย่าใช้ `Styler.applymap()`** ใน pandas 2.x → ใช้ `.map()` แทน (พร้อม try/except fallback)
- **อย่า DELETE Supabase table ทั้งหมดโดยไม่ filter** — ต้องใช้ `?user_id=eq.{uid}` มิฉะนั้น delete ไม่ทำงาน (PostgREST requirement)

---

## Known Issues / ต้องแก้ทีหลัง

- **UI polish**: Pie chart label ซ้อนกันเมื่อมีหลาย holdings, ตัวหนังสือ label ตกขอบ
- **Portfolio line chart**: ใช้ current positions ย้อนหลัง ไม่ได้ track ว่าซื้อ/ขายระหว่างทาง (approximation)
- **Performance**: yfinance + Supabase calls ทุก page load ทำให้ช้า — ควรทำ session_state caching
- **Password reset**: redirect ไป localhost แทน Streamlit URL — ยังไม่ได้แก้ Site URL ใน Supabase

## Planned Next

1. UI polish — chart sizing, label overlap, layout
2. Import port ที่มีอยู่ทั้งหมดด้วย Import mode
3. Performance caching ถ้า laggy เกินไป
4. Auth: Password reset flow (แก้ Site URL ใน Supabase → ชี้ไป Streamlit Cloud URL)
5. Multi-user: RLS ทำงานแล้ว → share URL ให้แฟน/เพื่อนสมัครได้เลย

