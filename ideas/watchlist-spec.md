# Watchlist Page — Spec (ไอเดีย อยู่ระหว่างรอ implement)

> วางแผน 2026-09-21 — ยังไม่ได้ build

---

## จุดประสงค์
Tab ใหม่สำหรับติดตามหุ้นที่สนใจก่อนซื้อจริง — แยกออกจาก Investment tab (ซึ่งเป็น positions ที่ซื้อแล้ว)

---

## Pre-requisites (เทมทำก่อน KODE ลงมือ)

รัน SQL นี้ใน Supabase SQL Editor:
```sql
create table watchlist (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users,
  data jsonb not null
);
alter table watchlist enable row level security;
create policy "Users own watchlist" on watchlist
  for all using (auth.uid() = user_id);
```

---

## งานที่ต้องทำใน dashboard.py

| จุด | สิ่งที่แก้ | Risk |
|---|---|---|
| `_inject_navbar()` → `nav_html` | เพิ่ม `<button class="tfin-nt" id="tnt5">👁 Watchlist</button>` | ⚠️ Navbar fragile zone |
| `st.tabs([...])` | เพิ่ม `"👁 Watchlist"` เป็น element ที่ 6 | ต่ำ |
| `main()` body | เพิ่ม `with _tabs[5]: page_watchlist(watchlist, disp, rate)` | ต่ำ |
| `load_watchlist()` | ฟังก์ชันใหม่ — Supabase fetch + fallback JSON | ต่ำ |
| `save_watchlist()` | DELETE by user_id + re-insert (pattern เดิม) | ต่ำ |
| `page_watchlist()` | ฟังก์ชันหน้าใหม่ ~250 บรรทัด | ต่ำ |
| `watchlist.json` | สร้างไฟล์ว่าง `[]` เป็น local fallback | ต่ำ |

**ต้อง test 4-state หลัง navbar เปลี่ยน:** normal / fullscreen / hover tooltip / reload

---

## Data Structure

```json
{
  "id": 1,
  "ticker": "TSLA",
  "category": "รอ dip",
  "note": "รอ pullback ที่ EMA 200",
  "alert_price": 200.0,
  "currency": "USD",
  "added_date": "2026-09-21"
}
```

---

## UI Layout

```
👁 Watchlist
ติดตามหุ้นที่สนใจก่อนซื้อจริง                    [Filter category ▼]  [+ เพิ่ม Ticker]

[X tickers]  [Y categories]  [Z alert]

📁 รอ dip (3)                                                  [✏️ แก้ชื่อ] [🗑 ลบ]
───────────────────────────────────────────────────────────────────────────────────
  TSLA  Tesla          $215.20  ▼ -1.23%  🔔 Alert: $200                      [⋮]
  NVDA  NVIDIA          $122.50  ▲ +2.15%  Note: รอ pullback                   [⋮]
  RKLB  Rocket Lab       $22.40  ▲ +0.88%  Note: รอ earnings                  [⋮]

📁 ระยะยาว (2)
───────────────────────────────────────────────────────────────────────────────────
  GOOG  Alphabet        $175.80  ▲ +0.44%  —                                  [⋮]
  BDMS  BDMS.BK          ฿28.50  ▼ -0.70%  Note: รอ Q3                        [⋮]
```

**[⋮] actions ต่อ row:**
- แก้ไข (inline edit)
- ย้าย Category
- ➕ ซื้อเลย → redirect ไป Investment tab พร้อม pre-fill ticker
- 🗑 ลบออก

---

## Add Form

```
Ticker*     [          ]   Currency  [USD / THB]
Category*   [รอ dip ▼  ]   หรือ [+ สร้างใหม่]
Note        [                                  ]
Alert Price [เว้นว่างได้]
                                  [ยกเลิก]  [เพิ่ม ✓]
```

Validate ว่า yfinance หา ticker เจอก่อน save

---

## Performance

- ใช้ `@st.cache_data(ttl=300)` สำหรับ price fetch ของ watchlist items ทั้งหมด (batch)
- ชื่อบริษัท cache ใน `st.session_state` ต่อ session — ไม่ fetch ทุก render

---

## Empty State

```
👁  ยังไม่มีหุ้นใน Watchlist
    เพิ่ม ticker ที่กำลังสนใจ ก่อนจะตัดสินใจซื้อจริง

    [+ เพิ่ม Ticker แรก]
```
