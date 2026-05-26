"""
Data layer — รองรับ 2 backend:
  LOCAL  : trades.json (default, ใช้บน localhost)
  CLOUD  : Supabase (เปิดใช้ตอน deploy โดย set secrets)

วิธีเปิด Supabase: ใส่ SUPABASE_URL และ SUPABASE_KEY ใน .streamlit/secrets.toml
"""
import json
import os

import streamlit as st

DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE = os.path.join(DIR, "trades.json")


# ── helpers ───────────────────────────────────────────────────────────────────

def _use_supabase() -> bool:
    try:
        return bool(st.secrets.get("SUPABASE_URL"))
    except Exception:
        return False


def calc_pnl(entry: str, exit_: str, direction: str) -> float | None:
    try:
        e = float(str(entry).replace(",", ""))
        x = float(str(exit_).replace(",", ""))
        pct = (x - e) / e * 100
        return round(-pct if direction == "Short" else pct, 2)
    except Exception:
        return None


# ── JSON backend ──────────────────────────────────────────────────────────────

def _json_load() -> list:
    if not os.path.exists(TRADES_FILE):
        return []
    with open(TRADES_FILE, encoding="utf-8") as f:
        return json.load(f)


def _json_save(trades: list) -> None:
    with open(TRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)


# ── Supabase backend ──────────────────────────────────────────────────────────
# Table schema (รันใน Supabase SQL editor ครั้งแรก):
#
#   create table trades (
#     row_id  serial primary key,
#     data    jsonb  not null
#   );

@st.cache_resource
def _get_supabase():
    from supabase import create_client  # type: ignore
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def _sb_load() -> list:
    sb = _get_supabase()
    rows = sb.table("trades").select("data").order("row_id").execute().data
    return [r["data"] for r in rows]


def _sb_save(trades: list) -> None:
    sb = _get_supabase()
    sb.table("trades").delete().neq("row_id", 0).execute()
    for t in trades:
        sb.table("trades").insert({"data": t}).execute()


# ── Public API ────────────────────────────────────────────────────────────────

def load_trades() -> list:
    return _sb_load() if _use_supabase() else _json_load()


def save_trades(trades: list) -> None:
    """บันทึก trades และ regenerate journal อัตโนมัติ"""
    if _use_supabase():
        _sb_save(trades)
    else:
        _json_save(trades)
    from journal import regenerate  # noqa: import here to avoid circular at module level
    regenerate(trades)
