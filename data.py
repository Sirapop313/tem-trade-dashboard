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


# ── Supabase backend (REST API โดยตรง ไม่ขึ้นกับ library version) ────────────
# Table schema (รันใน Supabase SQL editor ครั้งแรก):
#
#   create table trades (
#     row_id  serial primary key,
#     data    jsonb  not null
#   );

import requests as _requests

def _sb_base() -> str:
    return st.secrets["SUPABASE_URL"].rstrip("/") + "/rest/v1"

def _sb_headers() -> dict:
    key = st.secrets["SUPABASE_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

def _sb_load() -> list:
    r = _requests.get(f"{_sb_base()}/trades?select=data", headers=_sb_headers())
    r.raise_for_status()
    return [row["data"] for row in r.json()]

def _sb_save(trades: list) -> None:
    base, h = _sb_base(), _sb_headers()
    _requests.delete(f"{base}/trades", headers=h)
    if trades:
        _requests.post(f"{base}/trades",
                       headers={**h, "Prefer": "return=minimal"},
                       json=[{"data": t} for t in trades])


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
