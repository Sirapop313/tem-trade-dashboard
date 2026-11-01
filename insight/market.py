"""Market snapshot for the daily insight — every number Claude is allowed to quote.

Pulled from yfinance and computed here so the model interprets data instead of
recalling it. Kept free of Streamlit so the GitHub Action can run it alone.
"""
from __future__ import annotations

import io
import math
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import yfinance as yf

INDEXES = {
    "^GSPC": "S&P 500", "^NDX": "Nasdaq 100", "^SOX": "Semiconductors (SOX)",
    "^RUT": "Russell 2000", "RSP": "S&P 500 Equal Weight ETF", "SPY": "S&P 500 ETF",
}
SECTORS = {
    "XLK": "Information Technology", "XLC": "Communication Services",
    "XLY": "Consumer Discretionary", "XLP": "Consumer Staples", "XLE": "Energy",
    "XLF": "Financials", "XLV": "Health Care", "XLI": "Industrials",
    "XLB": "Materials", "XLRE": "Real Estate", "XLU": "Utilities",
}
MACRO = {
    "^IRX": "US 13W yield %", "^FVX": "US 5Y yield %", "^TNX": "US 10Y yield %",
    "^TYX": "US 30Y yield %", "^VIX": "VIX", "^MOVE": "MOVE (bond vol)",
    "DX-Y.NYB": "Dollar index", "BZ=F": "Brent", "CL=F": "WTI", "GC=F": "Gold",
    "BTC-USD": "Bitcoin", "THB=X": "USD/THB",
}
MEGACAPS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO"]
# yields and vol indexes move in points, not percent — report the change in points
POINT_MOVERS = {"^IRX", "^FVX", "^TNX", "^TYX", "^VIX", "^MOVE"}

SP500_LIST = ("https://raw.githubusercontent.com/datasets/"
              "s-and-p-500-companies/main/data/constituents.csv")

# FRED's chart CSV endpoint needs no API key. (id, name, transform)
# transform: "yoy" = % vs 12 obs earlier (monthly index levels), "diff" = change vs
# previous obs (payrolls in thousands), None = the level itself is the reading
FRED = [
    ("CPIAUCSL", "CPI inflation YoY %", "yoy"),
    ("CPILFESL", "Core CPI inflation YoY % (ex food & energy)", "yoy"),
    ("PCEPILFE", "Core PCE inflation YoY % (Fed's gauge)", "yoy"),
    ("UNRATE", "Unemployment rate %", None),
    ("PAYEMS", "Nonfarm payrolls change (thousands)", "diff"),
    ("ICSA", "Initial jobless claims (weekly)", None),
    ("FEDFUNDS", "Fed funds effective rate %", None),
    ("T10Y2Y", "10Y minus 2Y yield spread (curve)", None),
    ("T10YIE", "10Y breakeven inflation % (market's inflation expectation)", None),
    ("BAMLH0A0HYM2", "US high-yield credit spread % (junk bond stress)", None),
    ("NFCI", "Chicago Fed financial conditions (negative = loose)", None),
]
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}&cosd={}"


def _download(tickers: list[str], period: str = "2y") -> dict[str, pd.DataFrame]:
    raw = yf.download(tickers, period=period, interval="1d", auto_adjust=False,
                      group_by="ticker", progress=False, threads=True)
    out = {}
    for t in tickers:
        try:
            df = raw[t].dropna(subset=["Close"])
        except KeyError:
            continue
        if len(df) > 30:
            out[t] = df
    return out


def _rsi(close: pd.Series, n: int = 14) -> float:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return float(100 - 100 / (1 + up.iloc[-1] / dn.iloc[-1])) if dn.iloc[-1] else 100.0


def _macd(close: pd.Series) -> tuple[float, float]:
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    return float(macd.iloc[-1]), float(macd.ewm(span=9, adjust=False).mean().iloc[-1])


def _pivots(df: pd.DataFrame, col: str, lows: bool, months: int = 6, w: int = 5) -> list:
    """Swing lows (or highs) of the last `months`: a bar that is the extreme of the
    w bars on each side. These are the 'previous low on <date>' levels the TA uses."""
    s = df[col].iloc[-months * 21:]
    roll = s.rolling(2 * w + 1, center=True)
    ext = roll.min() if lows else roll.max()
    hits = s[(s == ext)]
    return [{"date": d.strftime("%Y-%m-%d"), "level": round(float(v), 2)}
            for d, v in hits.items()][-6:]


def _r(v, dp=2):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), dp)


def _chg(close: pd.Series, bars: int, points: bool) -> float | None:
    if len(close) <= bars:
        return None
    a, b = close.iloc[-1 - bars], close.iloc[-1]
    return _r(b - a, 3) if points else _r((b / a - 1) * 100)


def _row(t: str, name: str, df: pd.DataFrame, ta: bool) -> dict:
    c = df["Close"]
    pts = t in POINT_MOVERS
    row = {
        "ticker": t, "name": name, "date": c.index[-1].strftime("%Y-%m-%d"),
        "close": _r(c.iloc[-1], 3),
        "chg_1d": _chg(c, 1, pts), "chg_1w": _chg(c, 5, pts),
        "chg_1m": _chg(c, 21, pts), "chg_3m": _chg(c, 63, pts),
        "change_unit": "points" if pts else "%",
    }
    yr = c.iloc[-252:]
    row["high_1y"], row["high_1y_date"] = _r(yr.max()), yr.idxmax().strftime("%Y-%m-%d")
    row["low_1y"], row["low_1y_date"] = _r(yr.min()), yr.idxmin().strftime("%Y-%m-%d")
    row["avg_1y"] = _r(yr.mean())
    if not pts:
        row["from_1y_high_pct"] = _r((c.iloc[-1] / yr.max() - 1) * 100)
    if ta:
        for n in (50, 100, 200):
            ma = c.rolling(n).mean().iloc[-1]
            row[f"ma{n}"] = _r(ma)
            row[f"vs_ma{n}_pct"] = _r((c.iloc[-1] / ma - 1) * 100)
        row["rsi14"], row["rsi14_prev"] = _r(_rsi(c), 1), _r(_rsi(c.iloc[:-1]), 1)
        m, s = _macd(c)
        row["macd"], row["macd_signal"] = _r(m), _r(s)
        row["swing_lows_6m"] = _pivots(df, "Low", lows=True)
        row["swing_highs_6m"] = _pivots(df, "High", lows=False)
        row["daily_closes_10d"] = [
            {"date": d.strftime("%Y-%m-%d"), "close": _r(v), "chg_pct": _r(p)}
            for d, v, p in zip(c.index[-10:], c.iloc[-10:], (c.pct_change() * 100).iloc[-10:])
        ]
    return row


def _breadth() -> dict | None:
    """% of S&P 500 members above their 50/200-day average, and advancers vs decliners.
    The constituent list is a public CSV; if it or the download fails, the insight
    simply goes without breadth rather than failing the whole run."""
    try:
        csv = requests.get(SP500_LIST, timeout=20).text
        syms = [s.replace(".", "-") for s in pd.read_csv(io.StringIO(csv))["Symbol"]]
        raw = yf.download(syms, period="1y", interval="1d", auto_adjust=False,
                          progress=False, threads=True)["Close"]
    except Exception:
        return None
    raw = raw.dropna(axis=1, how="all")
    last, prev = raw.iloc[-1], raw.iloc[-2]
    ok = last.notna() & prev.notna()
    ma50, ma200 = raw.rolling(50).mean().iloc[-1], raw.rolling(200).mean().iloc[-1]
    pct50 = (raw > raw.rolling(50).mean()).sum(axis=1) / raw.notna().sum(axis=1) * 100
    return {
        "members_counted": int(ok.sum()),
        "advancers": int((last[ok] > prev[ok]).sum()),
        "decliners": int((last[ok] < prev[ok]).sum()),
        "pct_above_ma50": _r((last > ma50).sum() / ma50.notna().sum() * 100, 1),
        "pct_above_ma200": _r((last > ma200).sum() / ma200.notna().sum() * 100, 1),
        "pct_above_ma50_1y_low": _r(pct50.iloc[60:].min(), 1),
        "pct_above_ma50_1y_low_date": pct50.iloc[60:].idxmin().strftime("%Y-%m-%d"),
        "pct_above_ma50_1w_ago": _r(pct50.iloc[-6], 1),
    }


def _fred() -> list[dict]:
    """Latest reading of each macro series plus the 3 before it, so the trend is
    visible. A series that fails to load is skipped, not fatal."""
    start = (pd.Timestamp.today() - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
    out = []
    for sid, name, how in FRED:
        try:
            df = pd.read_csv(io.StringIO(requests.get(FRED_CSV.format(sid, start), timeout=20).text))
            s = pd.to_numeric(df.iloc[:, 1], errors="coerce")
            s.index = pd.to_datetime(df.iloc[:, 0])
            s = s.dropna()
            # match by calendar date, never by position: FRED has holes (no October 2025
            # prints after the shutdown), and shift(12) across a hole compares against
            # the wrong month — it read Sep 2026 CPI as 4.02% instead of 3.72%
            if how == "yoy":
                base = s.reindex(s.index - pd.DateOffset(years=1))
                s = pd.Series((s.values / base.values - 1) * 100, index=s.index)
            elif how == "diff":
                base = s.reindex(s.index - pd.DateOffset(months=1))
                s = pd.Series(s.values - base.values, index=s.index)
            s = s.dropna()
        except Exception:
            continue
        out.append({
            "id": sid, "name": name,
            "readings": [{"date": d.strftime("%Y-%m-%d"), "value": _r(v)}
                         for d, v in s.iloc[-4:].items()],
        })
    return out


def _flags(snap: dict) -> list[str]:
    """Rule-based 'the headline and the insides disagree' checks. Free, deterministic,
    and a starting list of contradictions for the weekly write-up to explain."""
    by = {r["ticker"]: r for k in ("indexes", "sectors", "macro") for r in snap.get(k, [])}
    f = []
    spx, b = by.get("^GSPC"), snap.get("breadth") or {}
    if spx and b and (spx["chg_1d"] or 0) < 0 and b.get("advancers", 0) > b.get("decliners", 0):
        f.append(f"S&P 500 ลง {spx['chg_1d']}% แต่หุ้นขึ้น {b['advancers']} ตัว มากกว่าลง "
                 f"{b['decliners']} ตัว → แรงกดมาจากหุ้นใหญ่ไม่กี่ตัว")
    ew = snap.get("equal_vs_cap_weight") or {}
    if spx and ew.get("ratio_chg_1m_pct") is not None and abs(ew["ratio_chg_1m_pct"]) >= 2:
        side = "หุ้นทั่วไปชนะหุ้นใหญ่" if ew["ratio_chg_1m_pct"] > 0 else "หุ้นใหญ่ไม่กี่ตัวแบกตลาด"
        f.append(f"RSP/SPY เปลี่ยน {ew['ratio_chg_1m_pct']}% ใน 1 เดือน → {side}")
    mv, vx = by.get("^MOVE"), by.get("^VIX")
    if mv and vx and mv["avg_1y"] and vx["avg_1y"]:
        m_rel, v_rel = mv["close"] / mv["avg_1y"], vx["close"] / vx["avg_1y"]
        if m_rel - v_rel >= 0.2:
            f.append(f"MOVE {mv['close']} สูงกว่าค่าเฉลี่ย 1 ปี {m_rel - 1:.0%} แต่ VIX {vx['close']} "
                     f"ห่างค่าเฉลี่ยแค่ {v_rel - 1:.0%} → ตลาดบอนด์เครียดกว่าตลาดหุ้น")
    tnx, brent = by.get("^TNX"), by.get("BZ=F")
    if tnx and brent and (tnx["chg_1w"] or 0) <= -0.1 and (brent["chg_1w"] or 0) > 0:
        f.append(f"ยีลด์ 10 ปีลง {abs(tnx['chg_1w']) * 100:.0f} bps ในสัปดาห์ ทั้งที่ Brent ขึ้น "
                 f"{brent['chg_1w']}% → เงินหนีเข้าพันธบัตร ไม่ใช่เพราะเงินเฟ้อลด")
    sox, aapl = by.get("^SOX"), next((r for r in snap.get("megacaps", []) if r["ticker"] == "AAPL"), None)
    if sox and aapl and (sox["chg_1m"] or 0) * (aapl["chg_1m"] or 0) < 0 \
            and abs((sox["chg_1m"] or 0) - (aapl["chg_1m"] or 0)) >= 10:
        f.append(f"SOX {sox['chg_1m']}% vs Apple {aapl['chg_1m']}% ใน 1 เดือน → เงินใช้ Apple "
                 f"หลบความผันผวนของ AI")
    if snap.get("sector_spread_1d_pct", 0) >= 4:
        f.append(f"ช่องว่าง sector ดีสุด-แย่สุด {snap['sector_spread_1d_pct']} จุด% ในวันเดียว "
                 f"→ rotation แรง ไม่ใช่ทั้งตลาดเคลื่อนไปด้วยกัน")
    for r in snap.get("indexes", []):
        if r.get("rsi14") is not None and r["rsi14"] <= 30:
            f.append(f"{r['name']} RSI {r['rsi14']} ต่ำกว่า 30 (oversold — ขายมากเกินไปในระยะสั้น)")
    return f


def _weekly_closes(close: pd.Series, n: int = 13) -> list[dict]:
    w = close.resample("W-FRI").last().dropna().iloc[-n:]
    return [{"week_end": d.strftime("%Y-%m-%d"), "close": _r(v)} for d, v in w.items()]


def build_snapshot() -> dict:
    """Everything the insight prompt needs, as plain JSON-able data."""
    groups = [(INDEXES, True), (SECTORS, False), (MACRO, False),
              ({t: t for t in MEGACAPS}, False)]
    data = _download([t for g, _ in groups for t in g])
    snap = {"generated_at": datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(timespec="minutes")}
    for key, (names, ta) in zip(["indexes", "sectors", "macro", "megacaps"], groups):
        snap[key] = [_row(t, n, data[t], ta) for t, n in names.items() if t in data]
        snap.setdefault("missing", []).extend(t for t in names if t not in data)

    # equal weight vs cap weight: the "is it a few giants or the whole market" gauge
    if "RSP" in data and "SPY" in data:
        ratio = (data["RSP"]["Close"] / data["SPY"]["Close"]).dropna()
        snap["equal_vs_cap_weight"] = {
            "rsp_spy_ratio": _r(ratio.iloc[-1], 4),
            "ratio_chg_1d_pct": _chg(ratio, 1, False),
            "ratio_chg_1m_pct": _chg(ratio, 21, False),
            "ratio_chg_3m_pct": _chg(ratio, 63, False),
        }
    if snap["sectors"]:
        s = sorted(snap["sectors"], key=lambda r: r["chg_1d"] or 0)
        snap["sector_spread_1d_pct"] = _r((s[-1]["chg_1d"] or 0) - (s[0]["chg_1d"] or 0))
    for r in snap["indexes"]:
        r["weekly_closes_13w"] = _weekly_closes(data[r["ticker"]]["Close"])
    by = {r["ticker"]: r for r in snap["macro"]}
    if "^TNX" in by and "^IRX" in by:
        snap["curve_10y_minus_3m"] = _r(by["^TNX"]["close"] - by["^IRX"]["close"], 3)
    snap["breadth"] = _breadth()
    snap["economy"] = _fred()
    snap["flags"] = _flags(snap)
    return snap


def latest_trading_day(snap: dict) -> str:
    spx = next((r for r in snap["indexes"] if r["ticker"] == "^GSPC"), None)
    return spx["date"] if spx else snap["generated_at"][:10]


if __name__ == "__main__":
    # run weekly by .github/workflows/weekly-data.yml; the scheduled Claude task reads
    # the newest file in insight/data/ and writes insight/weekly/<same date>.md
    import json
    from pathlib import Path
    snap = build_snapshot()
    out = Path(__file__).parent / "data" / f"{latest_trading_day(snap)}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} · flags: {len(snap['flags'])} · economy series: {len(snap['economy'])}")
