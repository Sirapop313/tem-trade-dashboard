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

## Features ปัจจุบัน (verified ทำงานได้ — อัปเดต 2026-10-19)

### Look & feel (redesign 15–17 ต.ค.)
- ฟอนต์ **IBM Plex Sans Thai + IBM Plex Mono** อยู่ใน `static/fonts/` ตั้งผ่าน `.streamlit/config.toml` (`[[theme.fontFaces]]`, `enableStaticServing`)
- สี graphite + ทองหม่น (`--it-*` tokens ใน CSS ต้นไฟล์ ต้องตรงกับ config.toml) · ไม่มีอีโมจิใน label · radio = segmented control
- Navbar (inject เข้า parent document) — แท็บ text, ไอคอน SVG ตา/บัญชี, THB/USD · มือถือ ≤960px แท็บไปอยู่แถบล่าง
- Login 2 คอลัมน์ สลับ Dark/Light · แท็บ เข้าสู่ระบบ/สมัครสมาชิก มองเห็นแล้ว (เดิมโดน CSS ซ่อน)
- ปิดการจางของ Streamlit ระหว่าง rerun (`[data-stale]`) — ไม่กระพริบ

### Overview
- KPI: Total Wealth, Deployed, Unrealized, Realized (Trade/Invest), Cash Out
- กราฟ Return % (Overall/Investment/Trade × 1D–1Y, เทียบ S&P/NASDAQ) เต็มความกว้าง
- **"ถืออะไรอยู่"** = `allocation_panel()` — Pie (default) / Treemap
  - Pie เป็น component ใน browser (`alloc_component.html` ผ่าน `components.html`): คลิกชิ้นหรือรายการ → ที่เหลือจาง ตรงกลางโชว์ชื่อ/%/มูลค่า/P&L · รายการ 2 คอลัมน์เลื่อนหาเอง · คลิกที่อื่นในหน้า = reset · ปุ่มขยายเปิดวงใหญ่ (ชื่ออยู่ในชิ้น) ใน parent document
- Portfolio Snapshot, Recent Activity

### Investment
- KPI + แถบ Cash/Account Total · Pie/Treemap · Return chart · Target Allocation (bar + ตาราง rebalance)
- **Current Holdings** = ตารางเดียว ติ๊กเลือกแถว (`on_select`, key `inv_hold_tbl`) + **แถบปุ่มเหนือตาราง**:
  `+ ซื้อหุ้นใหม่` (ทอง) │ เลือก X │ ซื้อเพิ่ม · แก้ไข · ขาย (แดง) · ลบ (ต้องยืนยัน)
  - แต่ละปุ่มเปิด `st.dialog` ตรงเข้าฟอร์มนั้น · ทุก action ล้าง selection ก่อน rerun (ตารางเรียงตาม P&L แถวสลับได้)
  - ทั้ง section เป็น `@st.fragment` — ติ๊ก/กดปุ่ม rerun แค่ส่วนนี้ (ไม่โหลด Supabase/ไม่คำนวณ 5 หน้า) · บันทึกจริงค่อย rerun ทั้งแอป
- ขาย: ช่อง **Max** (ติ๊ก = ขายหมด) · Closed อยู่ล่างสุด

### Trade
- ปุ่ม `+ เปิด Trade ใหม่` บนสุด (dialog) · Open trades (ยังเป็น expander — **ยังไม่ได้ทำแบบตาราง+แถบปุ่ม**)
- ขายบางส่วนใส่ Lesson ได้ + แก้ย้อนหลังได้ · Max · Leverage/ROE
- Analytics: สรุปผลงาน (ชนะ/แพ้/สุทธิ นับทุกครั้งที่ขาย) · Realized สะสม + Drawdown · P&L รายเทรด · แยกตาม Strategy
- **Past Performance** (1 แถว = 1 trade รวมทุกการขาย, หน้าละ 15) · Closed Trades (ทุกครั้งที่ขาย) พับไว้

### Cash
- Summary: THB/USD/Net, Deposit, Cash Out (+ "เข้าไทย")
- บัญชี: แก้ชื่อ/ยอด · Reassign · ลบ — **บัญชีที่มีประวัติ (deposit/cashout/transfer เข้าหรือออก) ลบ/Reassign ไม่ได้**
- **3 action:** เติมเงิน (Deposit) · **ย้ายเงิน (Transfer — ใหม่ 19 ต.ค.)** · ถอนเงิน (Cash Out)
- ประวัติเงินเข้า-ออก (เติม/ย้าย/ถอน) + Cash Flow History ของ trade/investment

### Cash Flow Logic
```
เปิด trade/investment → หักจาก source account (Import = ไม่หัก)
ปิด → คืน settle_thb (margin + P&L) เข้าบัญชีที่เลือก
Deposit  → +ยอด, ไม่ใช่กำไร
Cash Out → −ยอด, remitted = to_thai AND บัญชีต้นทาง != THB
Transfer → ต้นทาง −เงินออก, ปลายทาง +เงินเข้า · ไม่ใช่ deposit/cashout
           เรต = ยอดเข้า/ยอดออกจริง · ต่างประเทศ→THB = นำเข้าไทยเสมอ
           ต่างประเทศ→ต่างประเทศ = เลือกได้ (default ไม่ติ๊ก กันนับซ้ำ) · ต้นทาง THB = ไม่นับ
```

### Log
- Activity Log (ปี/เดือน/ประเภท + CSV) — รวมเติม/ย้าย/ถอน
- สรุปภาษีรายปี: กำไร/ขาดทุน realize · **นำเงินเข้าไทย** (cashout + transfer) พร้อมรายการ/เรต/CSV · ปีที่มีแต่การนำเข้า (ไม่มีขาย) เลือกได้
- เป็นบันทึกรายการ ไม่ใช่การคำนวณภาษี

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
{"id": 1, "name": "Webull", "currency": "USD", "amount": 1500.0,
 "deposits":  [{"date","amount","amount_thb","fx_rate","note"}],
 "cashouts":  [{"date","amount","amount_thb","fx_rate","to_thai","note"}],
 "transfers": [{"date","to_id","to_name","to_currency","amount","amount_in",
                "amount_thb","fx_rate","to_thai","note"}]}
```
- ทุกอย่างเก็บใน jsonb ของบัญชี (ไม่ต้องแก้ schema) · transfer เก็บที่บัญชี **ต้นทาง**
- บัญชีที่ถือ 2 สกุล (Webull/Dime/Bitkub) → แยกเป็น 2 บัญชี แล้วใช้ Transfer ตอนแลกเงิน

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
| Redesign: Plex fonts ใน static/, theme ผ่าน config.toml | ฟอนต์เดิมไม่มีไทย ทำให้ไทย/อังกฤษคนละตระกูล | 2026-10-15 |
| **ไม่ pin streamlit** ใน requirements | pin 1.45.1 แล้ว Cloud บูตไม่ขึ้น (ค้าง spinner) ต้อง revert + Reboot | 2026-10-15 |
| Holdings = ตาราง + แถบปุ่ม + dialog | ติ๊ก→popup→ปุ่ม→ฟอร์ม 3 ขั้น งง · แถบปุ่มเห็นตลอด | 2026-10-17 |
| Holdings section เป็น st.fragment | rerun ทั้งแอปทุกคลิกช้า/กระพริบ | 2026-10-18 |
| Transfer แยกจาก Deposit/Cash Out | เงินย้ายในพอร์ตไม่ใช่เงินเข้า/ออก · เป็นจุดนำเข้าไทยได้ | 2026-10-19 |
| `parse()` ปฏิเสธ NaN/inf ทั้งแอป | "nan" ผ่านทุกเงื่อนไข → save ล้มหลัง Supabase ลบแถวเก่า = ข้อมูลหาย | 2026-10-19 |

---

## อย่าทำ (ตัดสินใจออก / เคยลองแล้วไม่ work)

- **อย่าแก้ `data.py`** — deprecated ไม่ได้ใช้ใน dashboard.py
- **อย่า push `secrets.toml`** — มี API key อยู่ใน .gitignore แล้ว
- **อย่าใช้ number_input กับ currency selector ใน form เดียวกัน** — step/format ไม่ dynamic ในขณะที่ form ยังไม่ submit → ใช้ text_input แทน
- **อย่าใช้ `Styler.applymap()`** ใน pandas 2.x → ใช้ `.map()` แทน (พร้อม try/except fallback)
- **อย่า pin `streamlit==` ใน requirements.txt** — Cloud ใช้เวอร์ชันล่าสุด เทสด้วย venv เวอร์ชันล่าสุดแทน
- **อย่าเขียน CSS อิง `data-baseweb`** — Streamlit ใหม่เปลี่ยนเป็น react-aria แล้ว ใช้ `data-testid` (เช่น `stTextInputRootElement`, `stRadioOption`)
- **อย่าใส่ `font-family` ให้ `.stApp *`** — ไปทับฟอนต์ไอคอน ลูกศร expander กลายเป็นคำว่า keyboard_arrow_down
- **อย่า DELETE Supabase table ทั้งหมดโดยไม่ filter** — ต้องใช้ `?user_id=eq.{uid}` มิฉะนั้น delete ไม่ทำงาน (PostgREST requirement)

---

## Known Issues / ต้องแก้ทีหลัง

- **Transfer ต่างประเทศ→ต่างประเทศย้อนหลัง** ใช้เรตวันที่กดบันทึก ไม่ใช่เรตวันนั้น (เหมือน Cash Out)
- **Open Trades** ยังเป็น expander แบบเก่า ยังไม่ fragment (คลิกยังช้ากว่า Investment)
- **Theme Light ในแอป** (นอกหน้า Login) ยังไม่มี
- **Portfolio line chart**: ใช้ current positions ย้อนหลัง ไม่ได้ track ว่าซื้อ/ขายระหว่างทาง (approximation)
- **Performance**: yfinance + Supabase calls ทุก page load ทำให้ช้า — ควรทำ session_state caching
- **Password reset**: redirect ไป localhost แทน Streamlit URL — ยังไม่ได้แก้ Site URL ใน Supabase

## Planned Next

1. UI polish — chart sizing, label overlap, layout
2. Import port ที่มีอยู่ทั้งหมดด้วย Import mode
3. Performance caching ถ้า laggy เกินไป
4. Auth: Password reset flow (แก้ Site URL ใน Supabase → ชี้ไป Streamlit Cloud URL)
5. Multi-user: RLS ทำงานแล้ว → share URL ให้แฟน/เพื่อนสมัครได้เลย
6. **Watchlist page (tab ใหม่ 👁)** — ติดตามหุ้นที่สนใจก่อนซื้อจริง แยกออกจาก Investment
   - Pre-req: รัน SQL สร้าง table `watchlist` ใน Supabase (4 บรรทัด)
   - งาน: เพิ่ม navbar tnt5 + st.tabs entry + page_watchlist() ~250 บรรทัด
   - UI spec เก็บไว้ที่: `investing/ideas/watchlist-spec.md`
   - ไม่แก้โค้ดเก่า ยกเว้น navbar string + tabs list 2 จุด (navbar fragile zone — test 4-state ก่อน push)

