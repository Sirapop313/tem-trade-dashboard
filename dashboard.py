"""
Tim.fin Personal OS — Investment & Trade Dashboard
"""
import base64 as _b64
import io
import json
import os
import re
from datetime import date

import pandas as pd
import requests as _req
import streamlit as st
import streamlit.components.v1 as _components
import plotly.graph_objects as go
from PIL import Image as _PILImage


# -- Config --
def _load_favicon():
    _dir = os.path.dirname(os.path.abspath(__file__))
    for _p in [os.path.join(_dir, "Tim.fin Logo.png"),
               os.path.join(os.path.dirname(_dir), "tim.fin", "Tim.fin Logo.png")]:
        if os.path.exists(_p):
            return _PILImage.open(_p)
    return "📊"

st.set_page_config(page_title="Tim.fin OS", page_icon=_load_favicon(), layout="wide",
                   initial_sidebar_state="expanded")

DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE      = os.path.join(DIR, "trades.json")
INVESTMENTS_FILE = os.path.join(DIR, "investments.json")
CASH_FILE        = os.path.join(DIR, "cash.json")
STRATEGY_PRESETS = ["Breakout", "Swing", "Buy on dip", "Others"]

# -- Candlestick decorative BG (computed here so CSS can embed it directly) --
_CDATA = [
    ( 35,  70, 108, 188, 228, True),
    ( 95,  85, 122, 202, 245, False),
    (155,  65, 100, 212, 255, False),
    (215,  80, 125, 235, 272, False),
    (275,  85, 138, 258, 290, False),
    (335,  92, 135, 242, 278, True),
    (395,  75, 102, 205, 250, True),
    (455,  52,  75, 175, 228, True),
    (515,  35,  56, 148, 200, True),
    (575,  25,  44, 115, 172, True),
    (635,  30,  52, 135, 190, False),
    (695,  20,  40, 105, 160, True),
    (755,  10,  28,  85, 130, True),
    (815,  15,  33,  88, 142, True),
    (875,   8,  22,  72, 118, True),
]
_close_pts = " ".join(
    f"{'M' if i == 0 else 'L'} {cx} {bt if bull else bb}"
    for i, (cx, wt, bt, bb, wb, bull) in enumerate(_CDATA)
)
_c_svgs = "".join(
    f'<line x1="{cx}" y1="{wt}" x2="{cx}" y2="{wb}" '
    f'stroke="{"#7C3AED" if bull else "#94A3B8"}" stroke-width="1.5" '
    f'stroke-opacity="{"0.28" if bull else "0.16"}"/>'
    f'<rect x="{cx - 12}" y="{bt}" width="24" height="{bb - bt}" '
    f'fill="{"url(#cb)" if bull else "url(#cr)"}" rx="2"/>'
    for cx, wt, bt, bb, wb, bull in _CDATA
)
_svg_raw = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 910 310" opacity="0.28">'
    '<defs>'
    '<linearGradient id="cb" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0%" stop-color="#7C3AED" stop-opacity="0.9"/>'
    '<stop offset="100%" stop-color="#7C3AED" stop-opacity="0.3"/>'
    '</linearGradient>'
    '<linearGradient id="cr" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0%" stop-color="#94A3B8" stop-opacity="0.7"/>'
    '<stop offset="100%" stop-color="#94A3B8" stop-opacity="0.2"/>'
    '</linearGradient>'
    '</defs>'
    + _c_svgs
    + f'<path d="{_close_pts}" fill="none" stroke="#7C3AED" '
    'stroke-width="2.5" stroke-opacity="0.7" stroke-dasharray="5 3"/>'
    '</svg>'
)
_svg_b64 = _b64.b64encode(_svg_raw.encode()).decode()

# -- CSS --
st.markdown(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Syne:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap">',
    unsafe_allow_html=True,
)
st.markdown("""<style>
/* Tokens */
:root {
  --it-bg:      #080F1C;
  --it-sidebar: #09111F;
  --it-card:    #0C1828;
  --it-border:  #192537;
  --it-text:    #E2E8F0;
  --it-muted:   #64748B;
  --it-accent:  #7C3AED;
  --it-accent2: #1D4ED8;
  --it-green:   #22C55E;
  --it-red:     #EF4444;
}

/* Base */
#MainMenu, footer { visibility: hidden; }
[data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }
/* Sidebar always visible — higher specificity beats any injected display:none */
html body [data-testid="stSidebar"] { display: flex !important; }
html body [data-testid="collapsedControl"] { display: flex !important; }

/* Sidebar collapse button (inside sidebar) */
[data-testid="stSidebarCollapseButton"] button {
    background: rgba(124,58,237,0.18) !important;
    border: 1px solid rgba(124,58,237,0.4) !important;
    border-radius: 8px !important;
    color: #C4B5FD !important;
}
[data-testid="stSidebarCollapseButton"] button:hover {
    background: rgba(124,58,237,0.35) !important;
}
/* Expand button shown when sidebar is collapsed — very visible purple pill */
[data-testid="collapsedControl"] {
    position: fixed !important;
    left: 0 !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    z-index: 9999 !important;
    background: #7C3AED !important;
    border-radius: 0 12px 12px 0 !important;
    box-shadow: 4px 0 16px rgba(124,58,237,0.5) !important;
    padding: 6px 2px !important;
}
[data-testid="collapsedControl"] button {
    background: transparent !important;
    border: none !important;
    color: #fff !important;
    min-width: 32px !important;
    min-height: 48px !important;
    font-size: 1.2rem !important;
}

.stApp {
    background-color: #060C18 !important;
    background-image:
        url('data:image/svg+xml;base64,__CANDLE_SVG__'),
        linear-gradient(rgba(124,58,237,0.042) 1px, transparent 1px),
        linear-gradient(90deg, rgba(29,78,216,0.028) 1px, transparent 1px),
        radial-gradient(ellipse 100% 55% at 55% -10%, rgba(124,58,237,0.13) 0%, transparent 65%) !important;
    background-size: 72% 62%, 44px 44px, 44px 44px, 100% 100% !important;
    background-position: bottom right, 0 0, 0 0, 0 0 !important;
    background-repeat: no-repeat, repeat, repeat, no-repeat !important;
    background-attachment: fixed, fixed, fixed, fixed !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
/* Content area: solid bg so SVG decoration doesn't bleed through content */
[data-testid="stMain"] { background: #060C18 !important; }
.main .block-container { max-width: 1400px; padding-top: 1.5rem; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #09111F !important;
    border-right: 1px solid rgba(124,58,237,0.18) !important;
}
[data-testid="stSidebar"] * { font-family: 'Plus Jakarta Sans', sans-serif !important; }
/* Gradient accent bar at top of sidebar */
[data-testid="stSidebarContent"]::before {
    content: '';
    display: block;
    height: 3px;
    background: linear-gradient(90deg, #7C3AED, #1D4ED8, #0D9488);
    border-radius: 0 0 2px 2px;
    margin-bottom: 1rem;
}
/* Sidebar nav items */
[data-testid="stSidebar"] [data-baseweb="radio"] label {
    border-radius: 8px !important;
    padding: 5px 10px !important;
    margin: 2px 0 !important;
    transition: background .15s !important;
}
[data-testid="stSidebar"] [data-baseweb="radio"] label:hover {
    background: rgba(124,58,237,0.1) !important;
}
[data-testid="stSidebar"] [data-baseweb="radio"] [data-checked="true"] ~ div {
    color: #A78BFA !important;
}
/* Sidebar logout button */
[data-testid="stSidebar"] [data-testid="stButton"] button {
    background: transparent !important;
    border: 1px solid rgba(124,58,237,0.28) !important;
    color: var(--it-muted) !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    transition: all .15s !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
    background: rgba(124,58,237,0.1) !important;
    border-color: var(--it-accent) !important;
    color: var(--it-text) !important;
}

/* Page header */
.page-title {
    font-size: 1.8rem; font-weight: 800; margin: 0; line-height: 1.15;
    font-family: 'Syne', sans-serif !important;
    background: linear-gradient(135deg, #C4B5FD 0%, #93C5FD 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.page-sub { font-size: .82rem; color: var(--it-muted); margin-top: 3px; }

/* Section labels */
.section-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: var(--it-accent);
    padding-bottom: .45rem;
    border-bottom: 1px solid rgba(124,58,237,0.22);
    margin-bottom: .75rem;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(124,58,237,0.08) 0%, var(--it-card) 100%) !important;
    border: 1px solid rgba(124,58,237,0.18) !important;
    border-left: 3px solid rgba(124,58,237,0.7) !important;
    border-radius: 12px !important;
    padding: 18px 20px !important;
    transition: transform .15s, box-shadow .15s !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(124,58,237,0.18) !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: var(--it-text) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-variant-numeric: tabular-nums !important;
    letter-spacing: -0.01em !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.62rem !important;
    color: var(--it-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-weight: 700 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background: var(--it-card) !important;
    border: 1px solid var(--it-border) !important;
    border-left: 3px solid rgba(124,58,237,0.38) !important;
    border-radius: 12px !important;
    margin-bottom: .5rem !important;
    transition: border-left-color .15s !important;
}
[data-testid="stExpander"]:hover {
    border-left-color: var(--it-accent) !important;
}
[data-testid="stExpander"] summary {
    padding: 10px 16px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
}

/* Inputs */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input {
    background: rgba(6,12,24,.65) !important;
    border: 1px solid var(--it-border) !important;
    border-radius: 8px !important;
    color: var(--it-text) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--it-accent) !important;
    box-shadow: 0 0 0 2px rgba(124,58,237,.22) !important;
}

/* Select / Multiselect */
[data-baseweb="select"] > div {
    background: rgba(6,12,24,.65) !important;
    border: 1px solid var(--it-border) !important;
    border-radius: 8px !important;
}

/* Tabs — main nav + inner pages */
[data-baseweb="tab-list"] {
    background: rgba(12,24,40,0.75) !important;
    border-radius: 12px !important;
    padding: 5px !important;
    border: 1px solid rgba(124,58,237,0.15) !important;
    gap: 3px !important;
    margin-bottom: 1rem !important;
}
[data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 8px 18px !important;
    color: var(--it-muted) !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    transition: background .15s !important;
}
[data-baseweb="tab"][aria-selected="true"] {
    background: rgba(124,58,237,0.28) !important;
    color: #C4B5FD !important;
    font-weight: 700 !important;
    box-shadow: 0 0 12px rgba(124,58,237,0.25) !important;
}
[data-baseweb="tab-border"] { display: none !important; }

/* Buttons (form submit) */
[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #5B21B6, #1D4ED8) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    width: 100%;
    transition: transform .15s, box-shadow .15s;
}
[data-testid="stFormSubmitButton"] button:hover {
    background: linear-gradient(135deg, #4C1D95, #1E40AF) !important;
    transform: translateY(-1px);
    box-shadow: 0 6px 24px rgba(124,58,237,0.38) !important;
}

/* Regular buttons (non-sidebar, non-login) */
[data-testid="stMain"] [data-testid="stButton"] button {
    background: rgba(124,58,237,0.12) !important;
    border: 1px solid rgba(124,58,237,0.3) !important;
    color: #C4B5FD !important;
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 500 !important;
    transition: all .15s !important;
}
[data-testid="stMain"] [data-testid="stButton"] button:hover {
    background: rgba(124,58,237,0.22) !important;
    border-color: var(--it-accent) !important;
    color: #E2E8F0 !important;
    transform: translateY(-1px) !important;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border: 1px solid var(--it-border) !important;
    border-radius: 12px !important;
}

/* Alerts */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* Multiselect tags */
[data-baseweb="tag"] {
    background: rgba(124,58,237,0.2) !important;
    border: 1px solid rgba(124,58,237,0.35) !important;
    border-radius: 6px !important;
    color: #C4B5FD !important;
}

/* Dividers */
hr { border-color: var(--it-border) !important; }

/* Hide the native Streamlit tab-list — navbar replaces it */
[data-baseweb="tab-list"] { display: none !important; }
</style>""".replace("__CANDLE_SVG__", _svg_b64), unsafe_allow_html=True)

# -- Logo (Tim.fin) --
_logo_path = os.path.join(DIR, "Tim.fin Logo.png")
if not os.path.exists(_logo_path):
    _logo_path = os.path.join(os.path.dirname(DIR), "tim.fin", "Tim.fin Logo.png")
try:
    with open(_logo_path, "rb") as _f:
        _LOGO_B64 = _b64.b64encode(_f.read()).decode()
except Exception:
    _LOGO_B64 = ""


# -- Navbar & Account helpers --

def sb_update_password(new_pass: str) -> tuple[bool, str]:
    """Update current user's password via Supabase."""
    if not _use_sb():
        return False, "ไม่ได้เชื่อม Supabase"
    try:
        resp = _req.put(
            f"{_sb_url()}/auth/v1/user",
            json={"password": new_pass},
            headers=_sb_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            return True, ""
        return False, resp.json().get("message", resp.text)
    except Exception as e:
        return False, str(e)


def _inject_navbar(logo_src: str, email: str, curr: str, rate: float) -> str:
    """Inject navbar HTML+CSS+JS into the parent page via window.parent (components.html iframe)."""
    thb_cls = "on" if curr == "THB" else ""
    usd_cls = "on" if curr == "USD" else ""
    logo_tag = f'<img src="{logo_src}" class="tfin-brand-img">' if logo_src else '<span style="font-size:1.3rem;line-height:1">📊</span>'
    em_short = (email[:22] + "…") if len(email) > 24 else email
    rate_str = f"{rate:.2f}"

    nav_html = (
        f'<div id="tfin-nav">'
        f'<div class="tfin-brand">{logo_tag}<span class="tfin-brand-name">Investment Tracker</span></div>'
        f'<div class="tfin-nav-tabs">'
        f'<button class="tfin-nt on" id="tnt0">📊 Overview</button>'
        f'<button class="tfin-nt" id="tnt1">💼 Investment</button>'
        f'<button class="tfin-nt" id="tnt2">📈 Trade</button>'
        f'<button class="tfin-nt" id="tnt3">💵 Cash</button>'
        f'<button class="tfin-nt" id="tnt4">📓 Log</button>'
        f'</div>'
        f'<div class="tfin-nav-right">'
        f'<span class="tfin-rate">฿{rate_str}/USD</span>'
        f'<div class="tfin-curr-wrap">'
        f'<button class="tfin-cb {thb_cls}" id="cb-thb">THB</button>'
        f'<button class="tfin-cb {usd_cls}" id="cb-usd">USD</button>'
        f'</div>'
        f'<div class="tfin-aw">'
        f'<button class="tfin-ab" id="tfin-acct-btn" title="{email}">👤</button>'
        f'<div class="tfin-dd" id="tfin-acct-dd">'
        f'<div class="tfin-dd-email">{em_short}</div>'
        f'<hr class="tfin-dd-hr">'
        f'<button class="tfin-ddbtn" id="tfin-cpw-btn">🔑 เปลี่ยนรหัสผ่าน</button>'
        f'<button class="tfin-ddbtn red" id="tfin-logout-btn">🚪 ออกจากระบบ</button>'
        f'</div></div></div></div>'
    )

    nav_css = (
        "#tfin-nav{position:fixed!important;top:0!important;left:0!important;right:0!important;"
        "height:58px!important;background:rgba(6,11,22,0.97)!important;"
        "backdrop-filter:blur(20px)!important;-webkit-backdrop-filter:blur(20px)!important;"
        "border-bottom:1px solid rgba(124,58,237,0.18)!important;"
        "display:flex!important;align-items:center!important;justify-content:space-between!important;"
        "padding:0 20px!important;z-index:2147483647!important;"
        "box-shadow:0 2px 28px rgba(0,0,0,0.5)!important;"
        "font-family:'Plus Jakarta Sans','Syne',sans-serif!important;gap:10px!important;}"
        ".tfin-brand{display:flex;align-items:center;gap:8px;flex-shrink:0;}"
        ".tfin-brand-img{height:30px;width:30px;border-radius:6px;object-fit:cover;}"
        ".tfin-brand-name{font-size:.88rem;font-weight:700;color:#E2E8F0;letter-spacing:-.02em;}"
        ".tfin-nav-tabs{display:flex;align-items:center;gap:2px;flex:1;justify-content:center;}"
        ".tfin-nt{background:transparent;border:none;cursor:pointer;color:rgba(148,163,184,.7);"
        "font-size:.8rem;font-weight:500;padding:6px 13px;border-radius:8px;transition:all .15s;"
        "white-space:nowrap;font-family:'Plus Jakarta Sans',sans-serif;line-height:1;}"
        ".tfin-nt:hover{background:rgba(124,58,237,.12);color:#e2e8f0;}"
        ".tfin-nt.on{background:rgba(124,58,237,.22);color:#C4B5FD;font-weight:700;"
        "box-shadow:0 0 0 1px rgba(124,58,237,.3) inset;}"
        ".tfin-nav-right{display:flex;align-items:center;gap:10px;flex-shrink:0;}"
        ".tfin-rate{font-size:.7rem;color:rgba(148,163,184,.5);}"
        ".tfin-curr-wrap{display:flex;background:rgba(255,255,255,.05);border-radius:7px;padding:3px;}"
        ".tfin-cb{background:transparent;border:none;cursor:pointer;font-size:.75rem;font-weight:600;"
        "padding:4px 10px;border-radius:5px;transition:all .14s;color:rgba(148,163,184,.6);"
        "font-family:'Plus Jakarta Sans',sans-serif;}"
        ".tfin-cb.on{background:rgba(124,58,237,.38);color:#C4B5FD;}"
        ".tfin-aw{position:relative;}"
        ".tfin-ab{background:rgba(124,58,237,.1);border:1px solid rgba(124,58,237,.28);"
        "border-radius:50%;width:33px;height:33px;cursor:pointer;color:#C4B5FD;font-size:.9rem;"
        "display:flex;align-items:center;justify-content:center;transition:all .15s;padding:0;}"
        ".tfin-ab:hover{background:rgba(124,58,237,.24);}"
        ".tfin-dd{display:none;position:fixed;top:58px;right:20px;min-width:192px;"
        "background:#0C1828;border:1px solid rgba(124,58,237,.22);border-radius:12px;"
        "padding:10px;box-shadow:0 10px 40px rgba(0,0,0,.65);z-index:2147483646;}"
        ".tfin-dd-email{font-size:.74rem;color:rgba(148,163,184,.65);padding:4px 8px 6px;word-break:break-all;}"
        ".tfin-dd-hr{border:none;border-top:1px solid rgba(124,58,237,.14);margin:5px 0;}"
        ".tfin-ddbtn{display:block;width:100%;text-align:left;background:transparent;border:none;"
        "color:#E2E8F0;font-size:.79rem;padding:7px 9px;border-radius:7px;"
        "cursor:pointer;font-family:inherit;transition:background .12s;}"
        ".tfin-ddbtn:hover{background:rgba(124,58,237,.14);}"
        ".tfin-ddbtn.red{color:#f87171;}"
        ".tfin-ddbtn.red:hover{background:rgba(239,68,68,.1);}"
        "[data-baseweb='tab-list']{display:none!important;}"
    )

    # Use json.dumps to safely embed strings in JS
    nav_html_js = json.dumps(nav_html)
    nav_css_js = json.dumps(nav_css)
    thb_js = "true" if curr == "THB" else "false"
    usd_js = "true" if curr == "USD" else "false"
    rate_js = json.dumps(f"฿{rate_str}/USD")

    return f"""<script>
(function(){{
  var doc = window.parent.document;

  /* 1 — Inject/update navbar CSS in parent <head> (always overwrite to pick up latest) */
  var s = doc.getElementById('tfin-nav-css');
  if(!s){{ s=doc.createElement('style'); s.id='tfin-nav-css'; doc.head.appendChild(s); }}
  s.textContent = {nav_css_js};

  /* 2 — Inject navbar HTML into parent <body> (once) */
  if(!doc.getElementById('tfin-nav')){{
    var tmp = doc.createElement('div');
    tmp.innerHTML = {nav_html_js};
    doc.body.insertBefore(tmp.firstChild, doc.body.firstChild);
  }}

  /* 3 — Sync dynamic state (currency buttons + rate) on every render */
  var cbT = doc.getElementById('cb-thb'); if(cbT) cbT.classList.toggle('on', {thb_js});
  var cbU = doc.getElementById('cb-usd'); if(cbU) cbU.classList.toggle('on', {usd_js});
  var rEl = doc.querySelector('#tfin-nav .tfin-rate'); if(rEl) rEl.textContent = {rate_js};

  /* 4 — Hide Streamlit helper widgets (inline setProperty beats all CSS rules) */
  function hide(el){{ if(el) el.style.setProperty('display','none','important'); }}
  function hideWidgets(){{
    /* radio */
    doc.querySelectorAll('[data-testid="stRadio"]').forEach(function(el){{
      if((el.textContent||'').includes('THB')) hide(el);
    }});
    /* cpw button — hide button + 2 ancestors */
    doc.querySelectorAll('button').forEach(function(b){{
      if((b.textContent||'').trim()==='__cpw__'){{
        hide(b); hide(b.parentElement);
        if(b.parentElement) hide(b.parentElement.parentElement);
      }}
    }});
    /* Streamlit tab navigation row */
    doc.querySelectorAll('[data-baseweb="tab-list"],[data-baseweb="tab-bar"],[role="tablist"]').forEach(function(el){{
      if(!el.closest('#tfin-nav')) hide(el);
    }});
    /* fallback: first child of stTabs wrapper */
    doc.querySelectorAll('[data-testid="stTabs"]').forEach(function(wrap){{
      var fc=wrap.firstElementChild; if(fc) hide(fc.firstElementChild||fc);
    }});
  }}

  /* 5 — Helper functions */
  function getStTabs(){{
    return Array.from(doc.querySelectorAll('[role="tab"]')).filter(function(t){{return !t.closest('#tfin-nav');}});
  }}

  function goTab(i){{
    var tabs=getStTabs(); if(tabs[i]) tabs[i].click();
    doc.querySelectorAll('.tfin-nt').forEach(function(b,j){{b.classList.toggle('on',j===i);}});
  }}

  function setCurr(val){{
    doc.querySelectorAll('[data-testid="stRadio"] label').forEach(function(l){{
      if((l.textContent||'').trim()===val) l.click();
    }});
    var t=doc.getElementById('cb-thb'); if(t) t.classList.toggle('on',val==='THB');
    var u=doc.getElementById('cb-usd'); if(u) u.classList.toggle('on',val==='USD');
  }}

  function toggleAcct(){{
    var dd=doc.getElementById('tfin-acct-dd');
    if(dd) dd.style.display=dd.style.display==='block'?'none':'block';
  }}

  function doLogout(){{
    var btns=doc.querySelectorAll('button');
    for(var i=0;i<btns.length;i++){{if((btns[i].textContent||'').includes('ออกจากระบบ')){{btns[i].click();return;}}}}
  }}

  function triggerCpw(){{
    var dd=doc.getElementById('tfin-acct-dd'); if(dd) dd.style.display='none';
    doc.querySelectorAll('button').forEach(function(b){{
      if((b.textContent||'').trim()==='__cpw__') b.click();
    }});
  }}

  function syncTabs(){{
    var tabs=getStTabs();
    tabs.forEach(function(t,i){{
      var b=doc.getElementById('tnt'+i);
      if(b) b.classList.toggle('on', t.getAttribute('aria-selected')==='true');
    }});
  }}

  /* 6 — Event delegation on navbar (single listener, capture phase) */
  var nav=doc.getElementById('tfin-nav');
  if(nav && !nav._del){{
    nav.addEventListener('click', function(e){{
      var tgt=e.target;
      var tntBtn=tgt.closest && tgt.closest('[id^="tnt"]');
      if(tntBtn){{ var idx=parseInt(tntBtn.id.substring(3)); if(!isNaN(idx)) goTab(idx); e.stopPropagation(); return; }}
      if(tgt.closest && tgt.closest('#cb-thb')){{ setCurr('THB'); e.stopPropagation(); return; }}
      if(tgt.closest && tgt.closest('#cb-usd')){{ setCurr('USD'); e.stopPropagation(); return; }}
      if(tgt.closest && tgt.closest('#tfin-acct-btn')){{ e.stopPropagation(); toggleAcct(); return; }}
      if(tgt.closest && tgt.closest('#tfin-cpw-btn')){{ triggerCpw(); e.stopPropagation(); return; }}
      if(tgt.closest && tgt.closest('#tfin-logout-btn')){{ doLogout(); e.stopPropagation(); return; }}
    }}, true);
    nav._del = true;
  }}

  /* Close dropdown on outside click */
  if(!doc._tfinOuter){{
    doc.addEventListener('click', function(e){{
      if(!(e.target.closest && e.target.closest('.tfin-aw'))){{
        var dd=doc.getElementById('tfin-acct-dd'); if(dd) dd.style.display='none';
      }}
    }}, false);
    doc._tfinOuter = true;
  }}

  /* 7 — MutationObserver: re-hide widgets + sync tabs on every Streamlit rerender */
  if(!window._tfinObserving){{
    new MutationObserver(function(){{ hideWidgets(); syncTabs(); }})
      .observe(doc.body, {{subtree:true, childList:true, attributes:true, attributeFilter:['aria-selected']}});
    window._tfinObserving = true;
  }}

  hideWidgets(); syncTabs();
}})();
</script>"""


# -- Data Layer --
def _load(path: str) -> list:
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8") as f: return json.load(f)

def _save(path: str, data: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# -- Supabase + Auth --
def _use_sb() -> bool:
    try: return bool(st.secrets.get("SUPABASE_URL"))
    except Exception: return False

def _sb_url() -> str:
    return st.secrets["SUPABASE_URL"].rstrip("/")

def _sb_headers() -> dict:
    key = st.secrets["SUPABASE_KEY"]
    session = st.session_state.get("sb_session")
    token = session["access_token"] if session else key
    return {
        "apikey": key, "Authorization": f"Bearer {token}",
        "Content-Type": "application/json", "Prefer": "return=minimal",
    }

def _sb_base(table: str) -> str:
    return _sb_url() + f"/rest/v1/{table}"

def _sb_load(table: str) -> list:
    r = _req.get(f"{_sb_base(table)}?select=data", headers=_sb_headers())
    r.raise_for_status()
    rows = [row["data"] for row in r.json()]
    seen, deduped = set(), []
    for row in rows:
        rid = row.get("id")
        if rid not in seen:
            seen.add(rid)
            deduped.append(row)
    return deduped

def _sb_save(table: str, items: list) -> None:
    user_id = st.session_state.get("sb_session", {}).get("user", {}).get("id")
    if not user_id:
        return
    base, h = _sb_base(table), _sb_headers()
    _req.delete(f"{base}?user_id=eq.{user_id}", headers=h)
    if items:
        _req.post(base, headers={**h, "Prefer": "return=minimal"},
                  json=[{"data": item, "user_id": user_id} for item in items])

def sb_signin(email: str, password: str) -> dict | None:
    try:
        r = _req.post(f"{_sb_url()}/auth/v1/token?grant_type=password",
                      headers={"apikey": st.secrets["SUPABASE_KEY"], "Content-Type": "application/json"},
                      json={"email": email, "password": password}, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return "connection_error"

def sb_refresh(refresh_token: str) -> dict | None:
    try:
        r = _req.post(
            f"{_sb_url()}/auth/v1/token?grant_type=refresh_token",
            headers={"apikey": st.secrets["SUPABASE_KEY"], "Content-Type": "application/json"},
            json={"refresh_token": refresh_token}, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def sb_signup(email: str, password: str) -> tuple[dict | None, str]:
    try:
        r = _req.post(f"{_sb_url()}/auth/v1/signup",
                      headers={"apikey": st.secrets["SUPABASE_KEY"], "Content-Type": "application/json"},
                      json={"email": email, "password": password}, timeout=10)
    except Exception:
        return None, "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้"
    data = r.json()
    if r.status_code in (200, 201):
        return data, ""
    return None, data.get("msg") or data.get("message") or str(data)

def is_logged_in() -> bool:
    return "sb_session" in st.session_state

# -- Public load/save --
def load_trades() -> list:
    return _sb_load("trades") if _use_sb() else _load(TRADES_FILE)

def save_trades(d: list):
    if _use_sb(): _sb_save("trades", d)
    else: _save(TRADES_FILE, d)
    try:
        from journal import regenerate
        regenerate(d)
    except Exception:
        pass

def load_investments() -> list:
    return _sb_load("investments") if _use_sb() else _load(INVESTMENTS_FILE)

def save_investments(d: list):
    if _use_sb(): _sb_save("investments", d)
    else: _save(INVESTMENTS_FILE, d)

CASH_PRESETS = ["Dime", "Webull", "Binance", "Bitkub", "SCB", "KBank", "Others"]

def load_cash() -> list:
    if _use_sb():
        return _sb_load("cash_accounts")
    if not os.path.exists(CASH_FILE):
        return []
    with open(CASH_FILE, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        accounts = []
        if data.get("usd", 0): accounts.append({"id": 1, "name": "USD Cash", "currency": "USD", "amount": data["usd"]})
        if data.get("thb", 0): accounts.append({"id": 2, "name": "THB Cash", "currency": "THB", "amount": data["thb"]})
        return accounts
    return data

def save_cash(cash: list) -> None:
    if _use_sb(): _sb_save("cash_accounts", cash)
    else:
        with open(CASH_FILE, "w", encoding="utf-8") as f:
            json.dump(cash, f, ensure_ascii=False, indent=2)

def cash_deduct(cash: list, account_id, amount_thb: float, rate: float):
    for acc in cash:
        if acc["id"] == account_id:
            deduct = round(amount_thb / rate if acc["currency"] == "USD" else amount_thb, 2)
            acc["amount"] = round(acc["amount"] - deduct, 2)
            break

def cash_credit(cash: list, account_id, amount_thb: float, rate: float):
    for acc in cash:
        if acc["id"] == account_id:
            credit = round(amount_thb / rate if acc["currency"] == "USD" else amount_thb, 2)
            acc["amount"] = round(acc["amount"] + credit, 2)
            break

def acc_label(acc: dict) -> str:
    sym = "$" if acc["currency"] == "USD" else "฿"
    return f"{acc['name']} ({acc['currency']} {sym}{acc['amount']:,.0f})"

def source_selector(cash: list, form_key: str) -> tuple:
    """Returns (selectbox_index, other_name_input, other_currency_input) inside a form."""
    ids     = [a["id"] for a in cash] + ["other"]
    labels  = [acc_label(a) for a in cash] + ["💼 Other Cash (ระบุเอง)"]
    sc1, sc2, sc3 = st.columns(3)
    idx          = sc1.selectbox("จ่ายจากบัญชีไหน", range(len(ids)),
                                  format_func=lambda i: labels[i], key=f"src_{form_key}")
    other_name   = sc2.text_input("ชื่อบัญชี (ถ้าเลือก Other Cash)",
                                   placeholder="เช่น Dime", key=f"src_name_{form_key}")
    other_curr   = sc3.selectbox("สกุลเงิน Other Cash", ["THB", "USD"],
                                  key=f"src_curr_{form_key}")
    return ids[idx], other_name, other_curr

def resolve_source(cash: list, source_id, other_name: str, other_currency: str) -> int:
    """ถ้าเลือก other → สร้าง account ใหม่ แล้ว return id"""
    if source_id != "other":
        return source_id
    new_id = max((a["id"] for a in cash), default=0) + 1
    cash.append({"id": new_id, "name": other_name.strip() or "Other Cash",
                 "currency": other_currency, "amount": 0.0})
    return new_id


# -- Live Prices --
_DR_PATTERN = re.compile(r'^[A-Z]+\d{2}$')  # Thai DR: NINTENDO23, META24

@st.cache_data(ttl=300)
def _fetch_price(ticker: str) -> float | None:
    try:
        import yfinance as yf
        fi = yf.Ticker(ticker).fast_info
        price = fi.last_price or fi.previous_close
        return float(price) if price and price > 0 else None
    except Exception:
        return None

def get_price(ticker: str) -> float | None:
    price = _fetch_price(ticker)
    if price is None and _DR_PATTERN.match(ticker.upper()):
        price = _fetch_price(ticker.upper() + ".BK")
    return price

@st.cache_data(ttl=300)
def get_usd_thb() -> float:
    # Primary: lightweight exchange rate API (no key needed, fast)
    try:
        r = _req.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        if r.status_code == 200:
            thb = r.json().get("rates", {}).get("THB")
            if thb and thb > 1:
                return float(thb)
    except Exception:
        pass
    # Fallback: yfinance
    try:
        import yfinance as yf
        rate = yf.Ticker("THB=X").fast_info.last_price
        if rate and rate > 1:
            return float(rate)
    except Exception:
        pass
    return 34.0


# -- Math Helpers --
def parse(val) -> float | None:
    try: return float(str(val).replace(",", "").strip())
    except Exception: return None

def get_shares(item: dict) -> str:
    return item.get("shares") or item.get("size") or "1"

def get_currency(item: dict) -> str:
    if item.get("currency"): return item["currency"]
    return "THB" if item.get("ticker","").endswith(".BK") else "USD"

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
    return round(diff * s * (rate if trade_currency == "USD" else 1), 2)

def auto_rr(entry, sl, tp) -> str:
    e, s, t = parse(entry), parse(sl), parse(tp)
    if None in (e, s, t) or abs(e - s) == 0: return "—"
    return f"1:{abs(t-e)/abs(e-s):.1f}"

def fmt_pct(val) -> str:
    if not isinstance(val, (int, float)): return "—"
    return f"{'+' if val>=0 else ''}{val:.2f}%"

def fmt_money(val_thb: float | None, disp: str, rate: float, sign: bool = True) -> str:
    if val_thb is None: return "—"
    if disp == "USD":
        v = val_thb / rate
        prefix = ("+" if v >= 0 else "-") if sign else ("" if v >= 0 else "-")
        return f"{prefix}${abs(v):,.2f}"
    prefix = ("+" if val_thb >= 0 else "-") if sign else ("" if val_thb >= 0 else "-")
    return f"{prefix}฿{abs(val_thb):,.0f}"

def to_display(val_thb: float | None, disp: str, rate: float) -> float | None:
    if val_thb is None: return None
    return val_thb / rate if disp == "USD" else val_thb

def get_inv_price(inv: dict) -> float | None:
    """manual_price ถ้าตั้งไว้ มิเช่นนั้น get_price (auto-.BK สำหรับ DR)"""
    mp = parse(inv.get("manual_price"))
    return mp if mp is not None else get_price(inv.get("ticker", ""))

def days_held_str(entry_date_str: str) -> str:
    try:
        d    = date.fromisoformat(str(entry_date_str))
        days = (date.today() - d).days
        if days < 0:   return "—"
        if days < 30:  return f"{days}d"
        months = days // 30
        if months < 12: return f"{months}m {days % 30}d"
        return f"{months // 12}y {months % 12}m"
    except Exception:
        return "—"


# -- Chart Helpers --
CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e2e8f0", size=13),
    showlegend=False,
    margin=dict(t=32, b=8, l=8, r=8),
    xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#94a3b8")),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
               tickfont=dict(size=11, color="#64748b"), zeroline=True,
               zerolinecolor="rgba(255,255,255,0.15)"),
)

def allocation_pie(labels, vals_thb, disp, rate, title, height=320):
    vals = [to_display(v, disp, rate) for v in vals_thb]
    total = sum(v for v in vals if v)
    colors = ["#5865f2","#22c55e","#f59e0b","#ef4444","#06b6d4",
              "#a855f7","#ec4899","#84cc16","#f97316","#14b8a6"]
    fig = go.Figure(go.Pie(
        labels=labels, values=vals, hole=0.45,
        textinfo="label+percent", textfont=dict(size=12, color="#e2e8f0"),
        marker=dict(colors=colors[:len(labels)],
                    line=dict(color="rgba(0,0,0,0.3)", width=1)),
    ))
    sym = "฿" if disp == "THB" else "$"
    fig.update_layout(**{**CHART_LAYOUT,
        "title": dict(text=title, font=dict(size=14, color="#94a3b8"), x=0),
        "height": height, "showlegend": True,
        "legend": dict(font=dict(color="#94a3b8", size=11), orientation="v"),
        "annotations": [dict(text=f"{sym}{total:,.0f}", x=0.5, y=0.5,
                              font=dict(size=15, color="#e2e8f0"), showarrow=False)],
    })
    return fig

@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker: str, period: str, interval: str):
    try:
        import yfinance as yf
        import pandas as pd
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        return df["Close"] if not df.empty else None
    except Exception:
        return None

def portfolio_line_chart(open_items: list, cash_thb: float, rate: float,
                         disp: str, period_label: str, height=300):
    import pandas as pd
    period_map = {"1D": ("1d","1h"), "1W": ("5d","1d"),
                  "1M": ("1mo","1d"), "1Y": ("1y","1wk")}
    period, interval = period_map.get(period_label, ("1mo","1d"))

    histories = {}
    for item in open_items:
        t = item.get("ticker","")
        if t and t not in histories:
            h = get_history(t, period, interval)
            if h is not None:
                histories[t] = h

    if not histories:
        return None

    combined = pd.DataFrame(histories).ffill().bfill()
    if combined.empty:
        return None

    port_vals = []
    for dt, row in combined.iterrows():
        v = cash_thb
        for item in open_items:
            t = item.get("ticker","")
            if t in row.index and pd.notna(row[t]):
                s = parse(get_shares(item)) or 0
                v += s * row[t] * (rate if get_currency(item) == "USD" else 1)
        port_vals.append(to_display(v, disp, rate))

    dates = list(combined.index)
    pct = (port_vals[-1] - port_vals[0]) / port_vals[0] * 100 if port_vals[0] else 0
    color_pct = "#22c55e" if pct >= 0 else "#ef4444"
    sym = "฿" if disp == "THB" else "$"
    sign = "+" if pct >= 0 else ""

    fig = go.Figure(go.Scatter(
        x=dates, y=port_vals, mode="lines",
        line=dict(color="#5865f2", width=2.5),
        fill="tozeroy", fillcolor="rgba(88,101,242,0.08)",
    ))
    fig.update_layout(**{**CHART_LAYOUT,
        "title": dict(
            text=f"Portfolio Value  "
                 f"<span style='color:{color_pct};font-size:14px'>{sign}{pct:.2f}%</span>",
            font=dict(size=14, color="#94a3b8"), x=0),
        "yaxis_title": f"Value ({sym})", "height": height,
        "yaxis_tickformat": ",.0f",
        "xaxis": dict(showgrid=False, tickfont=dict(size=11, color="#94a3b8")),
    })
    return fig

def portfolio_return_chart(open_items: list, rate: float, disp: str, period_label: str,
                           show_spy=False, show_qqq=False, height=300):
    import pandas as pd
    period_map = {"1D": ("1d","1h"), "1W": ("5d","1d"), "1M": ("1mo","1d"), "1Y": ("1y","1wk")}
    period, interval = period_map.get(period_label, ("1mo","1d"))

    histories = {}
    for item in open_items:
        t = item.get("ticker","")
        if t and t not in histories:
            h = get_history(t, period, interval)
            if h is not None:
                histories[t] = h
    if not histories:
        return None

    combined = pd.DataFrame(histories).ffill().bfill()
    if combined.empty:
        return None

    port_vals = []
    for _, row in combined.iterrows():
        v = 0.0
        for item in open_items:
            t = item.get("ticker","")
            if t in row.index and pd.notna(row[t]):
                s = parse(get_shares(item)) or 0
                v += s * float(row[t]) * (rate if get_currency(item) == "USD" else 1)
        port_vals.append(v)

    if not port_vals or port_vals[0] == 0:
        return None

    base   = port_vals[0]
    ret_pcts = [(v - base) / base * 100 for v in port_vals]
    dates    = list(combined.index)
    final    = ret_pcts[-1]
    col      = "#22c55e" if final >= 0 else "#ef4444"
    sign     = "+" if final >= 0 else ""

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=ret_pcts, mode="lines", name="Portfolio",
        line=dict(color="#5865f2", width=2.5),
        fill="tozeroy", fillcolor="rgba(88,101,242,0.08)",
    ))

    for ticker, label, color in [("SPY", "S&P 500", "#f59e0b"), ("QQQ", "NASDAQ 100", "#a78bfa")]:
        if (ticker == "SPY" and show_spy) or (ticker == "QQQ" and show_qqq):
            h = get_history(ticker, period, interval)
            if h is not None:
                h_al = h.reindex(combined.index, method="ffill").dropna()
                if len(h_al) > 0:
                    b0 = float(h_al.iloc[0])
                    fig.add_trace(go.Scatter(
                        x=list(h_al.index),
                        y=[(float(v) - b0) / b0 * 100 for v in h_al],
                        mode="lines", name=label,
                        line=dict(color=color, width=1.5, dash="dot"),
                    ))

    fig.update_layout(**{**CHART_LAYOUT,
        "title": dict(
            text=(f"Return %  <span style='color:{col};font-size:14px'>{sign}{final:.2f}%</span>"
                  f"<br><span style='font-size:10px;color:#64748b'>ราคา-based · ไม่นับเวลาที่ซื้อจริง</span>"),
            font=dict(size=14, color="#94a3b8"), x=0),
        "yaxis_title": "Return (%)", "height": height,
        "yaxis_tickformat": ".2f", "yaxis_ticksuffix": "%",
        "xaxis": dict(showgrid=False, tickfont=dict(size=11, color="#94a3b8")),
        "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    })
    return fig

def build_activity_log(investments: list, trades: list) -> list:
    events = []
    for inv in investments:
        ticker = inv.get("ticker","—")
        if inv.get("entry_date"):
            events.append({"วันที่": inv.get("entry_date",""), "ประเภท": "💼 Invest",
                "Action": "🟢 ซื้อ", "Ticker": ticker,
                "รายละเอียด": f"เปิด · {get_shares(inv)} shares @ {inv.get('entry_price','—')}"})
        for bh in inv.get("buy_history", []):
            events.append({"วันที่": bh.get("date",""), "ประเภท": "💼 Invest",
                "Action": "➕ ซื้อเพิ่ม", "Ticker": ticker,
                "รายละเอียด": f"+{bh.get('shares','?')} shares @ {bh.get('price','—')}"})
        for sh in inv.get("sell_history", []):
            pnl_s = f"฿{sh.get('pnl_thb',0):,.0f}" if sh.get("pnl_thb") is not None else "—"
            events.append({"วันที่": sh.get("date",""), "ประเภท": "💼 Invest",
                "Action": "🔴 ขายบางส่วน", "Ticker": ticker,
                "รายละเอียด": f"-{sh.get('shares','?')} shares @ {sh.get('price','—')} · P&L {pnl_s}"})
        if inv.get("status") == "closed" and inv.get("exit_date"):
            events.append({"วันที่": inv.get("exit_date",""), "ประเภท": "💼 Invest",
                "Action": "🔴 ปิด", "Ticker": ticker,
                "รายละเอียด": f"ปิด @ {inv.get('exit_price','—')} · P&L {fmt_pct(inv.get('pnl_pct'))}"})
    for t in trades:
        ticker = t.get("ticker","—")
        arr = "↑" if t.get("direction") == "Long" else "↓"
        if t.get("open_date"):
            events.append({"วันที่": t.get("open_date",""), "ประเภท": "📈 Trade",
                "Action": "🟢 เปิด", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"{get_shares(t)} shares @ {t.get('entry_price','—')} · SL {t.get('stop_loss','—')} · TP {t.get('take_profit','—')}"})
        for bh in t.get("buy_history", []):
            events.append({"วันที่": bh.get("date",""), "ประเภท": "📈 Trade",
                "Action": "➕ ซื้อเพิ่ม", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"+{bh.get('shares','?')} shares @ {bh.get('price','—')}"})
        for sh in t.get("sell_history", []):
            pnl_s = f"฿{sh.get('pnl_thb',0):,.0f}" if sh.get("pnl_thb") is not None else "—"
            events.append({"วันที่": sh.get("date",""), "ประเภท": "📈 Trade",
                "Action": "🔴 ขายบางส่วน", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"-{sh.get('shares','?')} shares @ {sh.get('price','—')} · P&L {pnl_s}"})
        if t.get("status") == "closed" and t.get("close_date"):
            events.append({"วันที่": t.get("close_date",""), "ประเภท": "📈 Trade",
                "Action": "🔴 ปิด", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"ปิด @ {t.get('exit_price','—')} · P&L {fmt_pct(t.get('pnl_pct'))} · {t.get('win_loss','')}"})
    events.sort(key=lambda e: e.get("วันที่",""), reverse=True)
    return events

def pnl_bar_chart(labels, vals_thb, disp, rate, title, height=280):
    vals   = [to_display(v, disp, rate) for v in vals_thb]
    texts  = [fmt_money(v, disp, rate) for v in vals_thb]
    colors = ["#22c55e" if (v or 0) >= 0 else "#ef4444" for v in vals_thb]
    fig = go.Figure(go.Bar(
        x=labels, y=vals,
        marker=dict(color=colors, opacity=0.85,
                    line=dict(color="rgba(255,255,255,0.1)", width=1)),
        text=texts, textposition="outside",
        textfont=dict(size=13, color="#e2e8f0"), cliponaxis=False,
    ))
    sym = "฿" if disp == "THB" else "$"
    fig.update_layout(**{**CHART_LAYOUT,
        "title": dict(text=title, font=dict(size=14, color="#94a3b8"), x=0),
        "yaxis_title": f"P&L ({sym})", "height": height, "yaxis_tickformat": ",.0f",
    })
    if vals:
        maxv = max(abs(v) for v in vals if v is not None) or 1
        fig.update_yaxes(range=[-maxv * 1.35, maxv * 1.35])
    return fig


# -- UI Helpers --
def section(title: str):
    st.markdown(f'<div class="section-label">{title}</div>', unsafe_allow_html=True)

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

def page_header(title: str, subtitle: str = "") -> tuple[str, float]:
    """Page title (left) + currency toggle (right). Returns (disp, rate)."""
    rate = get_usd_thb()
    col_t, _, col_c = st.columns([6, 2, 2])
    with col_t:
        st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
        if subtitle:
            st.markdown(f'<div class="page-sub">{subtitle}</div>', unsafe_allow_html=True)
    with col_c:
        disp = st.radio("", ["THB", "USD"], horizontal=True,
                        key="display_currency", label_visibility="collapsed")
        st.caption(f"1 USD = ฿{rate:.2f}")
    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
    return disp, rate


# -- Login Page --
def page_login():
    if "login_theme" not in st.session_state:
        st.session_state["login_theme"] = "dark"
    dark = st.session_state["login_theme"] == "dark"

    if dark:
        page_bg  = "#060C18"
        card_bg  = "rgba(8,15,28,0.88)"
        card_bdr = "rgba(124,58,237,0.32)"
        txt      = "#E2E8F0"
        sub      = "#94A3B8"
        sep      = "rgba(255,255,255,0.08)"
        inp_bg   = "rgba(255,255,255,0.06)"
        inp_clr  = "#E2E8F0"
        inp_bdr  = "#192537"
        blob1    = "rgba(124,58,237,0.22)"
        blob2    = "rgba(37,99,235,0.18)"
        blob3    = "rgba(20,184,166,0.12)"
        dot      = "rgba(255,255,255,0.04)"
        tog_lbl  = "☀️ Light"
    else:
        page_bg  = "#EDF2F8"
        card_bg  = "rgba(255,255,255,0.96)"
        card_bdr = "rgba(124,58,237,0.22)"
        txt      = "#0F172A"
        sub      = "#475569"
        sep      = "rgba(0,0,0,0.08)"
        inp_bg   = "#F1F5F9"
        inp_clr  = "#0F172A"
        inp_bdr  = "#CBD5E1"
        blob1    = "rgba(124,58,237,0.14)"
        blob2    = "rgba(37,99,235,0.12)"
        blob3    = "rgba(20,184,166,0.08)"
        dot      = "rgba(0,0,0,0.04)"
        tog_lbl  = "🌙 Dark"

    st.markdown(f"""<style>
header[data-testid="stHeader"]{{display:none!important}}
[data-testid="stToolbar"]{{display:none!important}}
.stApp{{background:{page_bg}!important}}
/* block-container = the card */
[data-testid="stMain"] .block-container{{
    max-width:440px!important;
    margin:3rem auto 2rem!important;
    padding:2rem 1.75rem 2.25rem!important;
    background:{card_bg}!important;
    border:1px solid {card_bdr}!important;
    border-radius:20px!important;
    backdrop-filter:blur(24px)!important;
    -webkit-backdrop-filter:blur(24px)!important;
    box-shadow:0 0 60px rgba(124,58,237,0.14),0 24px 64px rgba(0,0,0,0.28)!important;
    position:relative;z-index:1;
}}
/* text */
[data-testid="stMain"] .block-container p,
[data-testid="stMain"] .block-container label,
[data-testid="stMain"] .block-container .stMarkdown p{{
    color:{sub}!important;
}}
/* inputs */
[data-testid="stTextInput"] input{{
    background:{inp_bg}!important;
    border:1px solid {inp_bdr}!important;
    color:{inp_clr}!important;
    border-radius:8px!important;
    font-family:'Plus Jakarta Sans',sans-serif!important;
}}
[data-testid="stTextInput"] input:focus{{
    border-color:#7C3AED!important;
    box-shadow:0 0 0 2px rgba(124,58,237,0.25)!important;
}}
[data-testid="stTextInput"] label{{
    color:{sub}!important;font-size:.82rem!important;font-weight:500!important;
}}
/* tabs */
[data-baseweb="tab-list"]{{background:transparent!important;border-bottom:1px solid {sep}!important}}
[data-baseweb="tab"]{{color:{sub}!important}}
[data-baseweb="tab"][aria-selected="true"]{{color:{txt}!important}}
/* theme toggle button */
[data-testid="stMain"] [data-testid="stButton"] button{{
    background:transparent!important;border:1px solid {card_bdr}!important;
    color:{sub}!important;border-radius:20px!important;
    font-size:.75rem!important;padding:.25rem 1rem!important;
    font-family:'Plus Jakarta Sans',sans-serif!important;
    width:auto!important;
}}
/* blobs */
.lp-blobs{{position:fixed;inset:0;pointer-events:none;z-index:0;overflow:hidden}}
.lp-blobs .b1{{position:absolute;top:-12%;left:-18%;width:65%;height:65%;
    background:radial-gradient(circle,{blob1} 0%,transparent 68%);filter:blur(50px)}}
.lp-blobs .b2{{position:absolute;top:25%;right:-12%;width:55%;height:55%;
    background:radial-gradient(circle,{blob2} 0%,transparent 68%);filter:blur(44px)}}
.lp-blobs .b3{{position:absolute;bottom:-8%;left:28%;width:50%;height:50%;
    background:radial-gradient(circle,{blob3} 0%,transparent 68%);filter:blur(38px)}}
.lp-blobs .dots{{position:absolute;inset:0;
    background-image:radial-gradient(circle,{dot} 1px,transparent 1px);
    background-size:22px 22px}}
</style>
<div class="lp-blobs"><div class="b1"></div><div class="b2"></div><div class="b3"></div><div class="dots"></div></div>
""", unsafe_allow_html=True)

    # Logo + title (inline styles to bypass Streamlit theme overrides)
    logo_html = (f'<img src="data:image/png;base64,{_LOGO_B64}" '
                 f'style="height:48px;display:block;margin:0 auto .6rem">'
                 if _LOGO_B64 else "")
    st.markdown(f"""
{logo_html}
<h1 style="text-align:center;font-family:'Syne',sans-serif;font-size:1.55rem;
    font-weight:800;color:{txt};margin:0 0 .25rem;line-height:1.2">Investment Tracker</h1>
<p style="text-align:center;color:{sub};font-size:.8rem;margin:0 0 1.1rem">
    ระบบติดตาม Portfolio ส่วนตัว</p>
<hr style="border:none;border-top:1px solid {sep};margin:0 0 1rem">
""", unsafe_allow_html=True)

    # Theme toggle centered
    _c1, _c2, _c3 = st.columns([3, 2, 3])
    with _c2:
        if st.button(tog_lbl, key="login_theme_toggle"):
            st.session_state["login_theme"] = "light" if dark else "dark"
            st.rerun()

    tab_in, tab_up = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก"])

    with tab_in:
        with st.form("login_form"):
            email    = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("เข้าสู่ระบบ", use_container_width=True):
                if not email or not password:
                    st.error("กรุณากรอก Email และ Password")
                else:
                    result = sb_signin(email.strip(), password)
                    if result == "connection_error":
                        st.error("⚠️ เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณารีเฟรชหน้าแล้วลองใหม่")
                    elif result and "access_token" in result:
                        st.session_state["sb_session"] = result
                        if result.get("refresh_token"):
                            st.query_params["_s"] = result["refresh_token"]
                        st.rerun()
                    else:
                        st.error("Email หรือ Password ไม่ถูกต้อง")

    with tab_up:
        with st.form("signup_form"):
            email    = st.text_input("Email")
            password = st.text_input("Password (อย่างน้อย 6 ตัวอักษร)", type="password")
            if st.form_submit_button("สมัครสมาชิก", use_container_width=True):
                if not email or len(password) < 6:
                    st.error("กรุณากรอก Email และ Password อย่างน้อย 6 ตัว")
                else:
                    result, err = sb_signup(email.strip(), password)
                    if result is not None:
                        st.success("✅ สมัครสมาชิกสำเร็จ! กรุณาตรวจสอบ Email เพื่อยืนยันตัวตน แล้วกลับมา Login")
                    else:
                        st.error(f"สมัครไม่สำเร็จ: {err}")


# -- Sidebar (branding + account only, no nav) --
def render_sidebar(logged_in: bool = True) -> None:
    with st.sidebar:
        if _LOGO_B64:
            st.markdown(
                f'<img src="data:image/png;base64,{_LOGO_B64}" '
                f'style="height:36px;display:block;margin:0.5rem auto 0.25rem">',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<p style="text-align:center;font-family:Syne,sans-serif;'
            'font-weight:700;font-size:0.95rem;color:#E2E8F0;margin:0 0 0.25rem">Investment Tracker</p>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        if logged_in and "sb_session" in st.session_state:
            email = st.session_state["sb_session"]["user"]["email"]
            st.caption(f"👤 {email}")
            if st.button("ออกจากระบบ", use_container_width=True):
                del st.session_state["sb_session"]
                st.query_params.pop("_s", None)
                st.rerun()
        st.caption("Tim.fin Personal OS")


# -- Page 1: Overview --
def page_overview(trades: list, investments: list, cash: list, disp: str, rate: float):
    # -- Account Filter --
    _UNASSIGNED = "— ไม่ระบุ"
    _named_accts = sorted(set(
        i.get("source_account_name","") for i in investments if i.get("source_account_name")
    ) | set(a["name"] for a in cash))
    _all_items   = list(investments) + list(trades)
    _has_unassigned = any(not x.get("source_account_name") for x in _all_items)
    all_acct_names = ([_UNASSIGNED] if _has_unassigned else []) + _named_accts
    ov_filter = st.multiselect("แสดงพอร์ต", all_acct_names,
                               placeholder="Overall — แสดงทั้งหมด", key="ov_acct_filter")

    open_trades   = [t for t in trades      if t.get("status") == "open"]
    closed_trades = [t for t in trades      if t.get("status") == "closed"]
    open_inv      = [i for i in investments if i.get("status") == "open"]
    wins          = [t for t in closed_trades if t.get("win_loss") == "Win"]

    if ov_filter:
        _show_unassigned = _UNASSIGNED in ov_filter
        open_inv    = [i for i in open_inv    if i.get("source_account_name") in ov_filter
                       or (_show_unassigned and not i.get("source_account_name"))]
        cash        = [a for a in cash        if a["name"] in ov_filter]
        open_trades = [t for t in open_trades if t.get("source_account_name") in ov_filter
                       or (_show_unassigned and not t.get("source_account_name"))]

    # Portfolio Value = positions + cash
    cash_thb = sum(a["amount"] * rate if a["currency"] == "USD" else a["amount"] for a in cash)
    port_thb = cash_thb
    for item in open_trades + open_inv:
        price = get_price(item.get("ticker",""))
        ref   = str(price) if price else item.get("entry_price")
        p     = calc_position_thb(ref, get_shares(item), get_currency(item), rate)
        if p: port_thb += p

    # Unrealized P&L
    unreal_thb  = 0.0
    unreal_items = []
    for item in open_trades + open_inv:
        price = get_price(item.get("ticker",""))
        if price is None: continue
        direction = item.get("direction", "Long")
        pnl = calc_pnl_thb(item.get("entry_price"), price, get_shares(item),
                            get_currency(item), rate, direction)
        if pnl is not None:
            unreal_thb += pnl
            label = f"{item['ticker']} ({'Trade' if item.get('type')=='trade' else 'Hold'})"
            unreal_items.append({"label": label, "pnl_thb": pnl})

    realized_thb = sum(t.get("pnl_thb", 0) or 0 for t in closed_trades)
    win_rate     = len(wins) / len(closed_trades) * 100 if closed_trades else None

    cost_basis_thb = 0.0
    for _item in open_trades + open_inv:
        _s = parse(get_shares(_item))
        _e = parse(_item.get("entry_price",""))
        if _s and _e:
            cost_basis_thb += _s * _e * (rate if get_currency(_item) == "USD" else 1)

    # -- KPI Row --
    section("Portfolio Summary")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Wealth (incl. Cash)",
              fmt_money(port_thb, disp, rate, sign=False) if port_thb else "No data yet")
    k2.metric("Deployed (Cost Basis)",
              fmt_money(cost_basis_thb if cost_basis_thb else None, disp, rate, sign=False)
              if cost_basis_thb else "No holdings")
    _unreal_ret_pct = unreal_thb / cost_basis_thb * 100 if cost_basis_thb and unreal_items else None
    k3.metric("Unrealized P&L",
              fmt_money(unreal_thb if unreal_items else None, disp, rate),
              delta=fmt_pct(_unreal_ret_pct))
    k4.metric("Realized P&L",
              fmt_money(realized_thb if closed_trades else None, disp, rate)
              if closed_trades else "No trades closed")

    # -- Asset Allocation --
    open_all = open_trades + open_inv
    if open_all or cash_thb > 0:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        col_pie, col_stats = st.columns([5, 4])

        with col_pie:
            pie_labels, pie_vals = [], []
            for item in open_all:
                price = get_price(item.get("ticker",""))
                ref   = str(price) if price else item.get("entry_price")
                pos   = calc_position_thb(ref, get_shares(item), get_currency(item), rate)
                if pos:
                    pie_labels.append(item.get("ticker","?"))
                    pie_vals.append(pos)
            if cash_thb > 0:
                pie_labels.append("💵 Cash")
                pie_vals.append(cash_thb)
            if pie_labels:
                st.plotly_chart(allocation_pie(pie_labels, pie_vals, disp, rate,
                                               "Asset Allocation", height=300),
                                use_container_width=True)

        with col_stats:
            st.markdown("**Portfolio Stats**")
            stats_data = [
                ("💼 Investments",   len(open_inv)),
                ("📈 Open Trades",   len(open_trades)),
                ("🔒 Closed Trades", len(closed_trades)),
            ]
            if win_rate is not None:
                stats_data.append(("🏆 Win Rate", f"{win_rate:.1f}%"))
            for label, val in stats_data:
                a, b = st.columns([3, 2])
                a.caption(label)
                b.markdown(f"**{val}**")

            if cash:
                st.divider()
                st.caption("💵 Cash Accounts")
                for acc in cash:
                    sym_c = "$" if acc["currency"] == "USD" else "฿"
                    val_c = acc["amount"] * rate if acc["currency"] == "USD" else acc["amount"]
                    line  = f"**{acc['name']}** · {sym_c}{acc['amount']:,.2f}"
                    if acc["currency"] == "USD":
                        line += f" (≈฿{val_c:,.0f})"
                    st.caption(line)

    # -- Portfolio Snapshot --
    if open_inv or open_trades:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        sym_ov  = "฿" if disp == "THB" else "$"
        _pc_col = f"P&L ({sym_ov})"
        pos_rows = []
        for item in open_inv:
            price   = get_inv_price(item)
            pnl_thb = calc_pnl_thb(item.get("entry_price"), price, get_shares(item),
                                    get_currency(item), rate) if price else None
            pnl_pct = calc_pnl_pct(item.get("entry_price"), price) if price else None
            ref     = str(price) if price else item.get("entry_price")
            pos_thb = calc_position_thb(ref, get_shares(item), get_currency(item), rate)
            _sv = parse(get_shares(item)); _ev = parse(item.get("entry_price",""))
            cost_thb = _sv * _ev * (rate if get_currency(item) == "USD" else 1) if _sv and _ev else None
            pos_rows.append({
                "_pnl_raw":       pnl_thb or 0,
                "Type":           "💼 Invest",
                "Ticker":         item.get("ticker","—"),
                "Account":        item.get("source_account_name","—") or "ไม่ระบุ",
                "Market Price":   f"{price:,.4f}" if price else "—",
                "Avg Price":      item.get("entry_price","—"),
                "Shares":         get_shares(item),
                "Cost":           fmt_money(cost_thb, disp, rate, sign=False) if cost_thb else "—",
                "Mkt Value":      fmt_money(pos_thb, disp, rate, sign=False),
                _pc_col:          fmt_money(pnl_thb, disp, rate) if price else "—",
                "P&L %":          fmt_pct(pnl_pct) if price else "—",
            })
        for item in open_trades:
            price     = get_price(item.get("ticker",""))
            direction = item.get("direction","Long")
            pnl_thb   = calc_pnl_thb(item.get("entry_price"), price, get_shares(item),
                                      get_currency(item), rate, direction) if price else None
            pnl_pct   = calc_pnl_pct(item.get("entry_price"), price, direction) if price else None
            ref       = str(price) if price else item.get("entry_price")
            pos_thb   = calc_position_thb(ref, get_shares(item), get_currency(item), rate)
            arr       = "↑" if direction == "Long" else "↓"
            _sv = parse(get_shares(item)); _ev = parse(item.get("entry_price",""))
            cost_thb = _sv * _ev * (rate if get_currency(item) == "USD" else 1) if _sv and _ev else None
            pos_rows.append({
                "_pnl_raw":       pnl_thb or 0,
                "Type":           f"📈 Trade {arr}",
                "Ticker":         item.get("ticker","—"),
                "Account":        item.get("source_account_name","—") or "ไม่ระบุ",
                "Market Price":   f"{price:,.4f}" if price else "—",
                "Avg Price":      item.get("entry_price","—"),
                "Shares":         get_shares(item),
                "Cost":           fmt_money(cost_thb, disp, rate, sign=False) if cost_thb else "—",
                "Mkt Value":      fmt_money(pos_thb, disp, rate, sign=False),
                _pc_col:          fmt_money(pnl_thb, disp, rate) if price else "—",
                "P&L %":          fmt_pct(pnl_pct) if price else "—",
            })
        pos_rows.sort(key=lambda r: -r["_pnl_raw"])

        def _col_pnl_ov(val):
            if isinstance(val, str) and val.startswith("+"): return "color:#22c55e;font-weight:600"
            if isinstance(val, str) and val.startswith("-"): return "color:#ef4444;font-weight:600"
            return ""
        df_ov = pd.DataFrame(pos_rows).drop(columns=["_pnl_raw"])
        _all_cols_ov = list(df_ov.columns)

        with st.expander("📋 Portfolio Snapshot", expanded=True):
            _pnl_sub = [c for c in ["P&L %", _pc_col] if c in _all_cols_ov]
            try:
                styled_ov = df_ov.style.map(_col_pnl_ov, subset=_pnl_sub).hide(axis="index") if _pnl_sub else df_ov.style.hide(axis="index")
            except AttributeError:
                styled_ov = df_ov.style.applymap(_col_pnl_ov, subset=_pnl_sub).hide(axis="index") if _pnl_sub else df_ov.style.hide(axis="index")
            st.dataframe(styled_ov, use_container_width=True, hide_index=True)

        if cash:
            cash_lines = []
            for a in cash:
                sym_c = "$" if a["currency"] == "USD" else "฿"
                val_c = a["amount"] * rate if a["currency"] == "USD" else a["amount"]
                cash_lines.append(
                    f"**{a['name']}** · {sym_c}{a['amount']:,.2f}"
                    + (f" (≈฿{val_c:,.0f})" if a["currency"] == "USD" else "")
                )
            st.caption("💵 Cash: " + "  ·  ".join(cash_lines))

    # -- Charts (collapsible) --
    if open_all:
        with st.expander("📊 Charts", expanded=True):
            rc1, rc2, rc3 = st.columns([3, 4, 3])
            with rc1:
                ret_view = st.radio("", ["Overall","Investment","Trade"], horizontal=True,
                                    key="ret_view", label_visibility="collapsed")
            with rc2:
                ret_period = st.radio("", ["1D","1W","1M","1Y"], horizontal=True,
                                      key="ret_period", index=2, label_visibility="collapsed")
            with rc3:
                cspy = st.checkbox("S&P 500", key="cmp_spy")
                cqqq = st.checkbox("NASDAQ 100", key="cmp_qqq")
            ret_items = (open_inv if ret_view == "Investment"
                         else open_trades if ret_view == "Trade"
                         else open_all)
            fig_ret = portfolio_return_chart(ret_items, rate, disp, ret_period,
                                             show_spy=cspy, show_qqq=cqqq, height=280)
            if fig_ret:
                st.caption("📊 วัดการเปลี่ยนแปลงราคาในช่วงเวลาที่เลือก · ไม่ใช่ return จากราคาต้นทุนจริง")
                st.plotly_chart(fig_ret, use_container_width=True)
            else:
                st.info("ไม่มีข้อมูลราคาย้อนหลัง")

    # -- Recent Activity --
    recent_events = build_activity_log(investments, trades)
    if recent_events:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        section("Recent Activity")
        for ev in recent_events[:5]:
            st.caption(
                f"{ev['วันที่']}  ·  {ev['ประเภท']}  {ev['Action']}  "
                f"**{ev['Ticker']}**  ·  {ev['รายละเอียด']}"
            )


# -- Page 2: Investment --
def page_investment(investments: list, trades: list, cash: list, disp: str, rate: float):
    open_inv   = [i for i in investments if i.get("status") == "open"]
    closed_inv = [i for i in investments if i.get("status") == "closed"]
    sym = "฿" if disp == "THB" else "$"

    # -- Account Filter --
    _UNASSIGNED     = "— ไม่ระบุ"
    inv_acct_names  = sorted({i.get("source_account_name","") for i in open_inv if i.get("source_account_name")})
    cash_acct_names = sorted({a["name"] for a in cash})
    _named_inv_opts = sorted(set(inv_acct_names) | set(cash_acct_names))
    _has_unassigned_inv = any(not i.get("source_account_name") for i in open_inv)
    acct_opts   = ([_UNASSIGNED] if _has_unassigned_inv else []) + _named_inv_opts
    acct_filter = st.multiselect("พอร์ต (เลือกได้หลายอัน)", acct_opts,
                                  placeholder="Overall — แสดงทั้งหมด", key="inv_acct_filter")

    if acct_filter:
        _show_unassigned_inv = _UNASSIGNED in acct_filter
        open_inv      = [i for i in open_inv if i.get("source_account_name") in acct_filter
                         or (_show_unassigned_inv and not i.get("source_account_name"))]
        filtered_cash = [a for a in cash if a["name"] in acct_filter]
    else:
        filtered_cash = cash

    # -- Summary --
    section("Investment Summary")
    total_val_thb, total_pnl_thb, total_cost_thb = 0.0, 0.0, 0.0
    best_ticker, best_pct = "—", None

    cash_usd_total = sum(a["amount"] for a in filtered_cash if a["currency"] == "USD")
    cash_thb_total = sum(a["amount"] for a in filtered_cash if a["currency"] == "THB")
    cash_total_thb = (cash_usd_total * rate) + cash_thb_total

    for inv in open_inv:
        price = get_inv_price(inv)
        ref   = str(price) if price else inv.get("entry_price")
        pos   = calc_position_thb(ref, get_shares(inv), get_currency(inv), rate)
        if pos: total_val_thb += pos
        s_val, e_val = parse(get_shares(inv)), parse(inv.get("entry_price",""))
        if s_val and e_val:
            total_cost_thb += s_val * e_val * (rate if get_currency(inv) == "USD" else 1)
        if price:
            pnl = calc_pnl_thb(inv.get("entry_price"), price, get_shares(inv), get_currency(inv), rate)
            pct = calc_pnl_pct(inv.get("entry_price"), price)
            if pnl: total_pnl_thb += pnl
            if pct is not None and (best_pct is None or pct > best_pct):
                best_pct, best_ticker = pct, inv.get("ticker","—")

    total_pnl_pct = total_pnl_thb / total_cost_thb * 100 if total_cost_thb else None
    _best_s = f"{best_ticker} {fmt_pct(best_pct)}" if best_pct is not None else "—"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cost Basis (Deployed)",
              fmt_money(total_cost_thb or None, disp, rate, sign=False) if total_cost_thb else "No holdings")
    k2.metric("Unrealized Return",
              fmt_money(total_pnl_thb or None, disp, rate) if open_inv else "No holdings",
              delta=fmt_pct(total_pnl_pct))
    k3.metric("Holdings", str(len(open_inv)))
    k4.metric("Best Performer", best_ticker if best_pct is not None else "—",
              delta=fmt_pct(best_pct) if best_pct is not None else None)

    # -- Cash + Account Total --
    cash_parts = []
    if cash_thb_total: cash_parts.append(f"฿{cash_thb_total:,.0f} THB")
    if cash_usd_total: cash_parts.append(f"${cash_usd_total:,.2f} USD")
    cash_inline    = " &nbsp;·&nbsp; ".join(cash_parts) if cash_parts else "฿0"
    acct_total_thb = total_val_thb + cash_total_thb
    acct_total_s   = fmt_money(acct_total_thb, disp, rate, sign=False)
    st.markdown(
        f"<div style='background:rgba(88,101,242,0.08);border:1px solid rgba(88,101,242,0.25);"
        f"border-radius:8px;padding:8px 16px;margin:6px 0 4px 0;line-height:1.5'>"
        f"<span style='font-size:11px;color:#64748b;text-transform:uppercase;"
        f"letter-spacing:0.06em'>💵 Cash</span>"
        f"&nbsp;&nbsp;"
        f"<span style='font-size:15px;font-weight:600;color:#e2e8f0'>{cash_inline}</span>"
        f"&nbsp;&nbsp;<span style='font-size:11px;color:#64748b'>· จัดการที่หน้า 💵 Cash</span>"
        f"&nbsp;&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;"
        f"<span style='font-size:11px;color:#64748b;text-transform:uppercase;"
        f"letter-spacing:0.06em'>Account Total</span>"
        f"&nbsp;&nbsp;"
        f"<span style='font-size:15px;font-weight:700;color:#94a3b8'>{acct_total_s}</span>"
        f"<span style='font-size:10px;color:#475569'>&nbsp;(positions + cash)</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # -- Holdings Table --
    if not open_inv:
        st.info("ยังไม่มี Investment — เพิ่มได้ด้านล่าง")
    else:
        # Build raw data first (for sorting)
        raw = []
        pie_labels_inv, pie_vals_inv = [], []
        for inv in open_inv:
            price   = get_inv_price(inv)
            pnl_thb = calc_pnl_thb(inv.get("entry_price"), price, get_shares(inv),
                                    get_currency(inv), rate) if price else None
            pnl_pct = calc_pnl_pct(inv.get("entry_price"), price) if price else None
            ref     = str(price) if price else inv.get("entry_price")
            pos_thb = calc_position_thb(ref, get_shares(inv), get_currency(inv), rate)
            if pos_thb:
                pie_labels_inv.append(inv.get("ticker","?"))
                pie_vals_inv.append(pos_thb)
            s_v = parse(get_shares(inv))
            e_v = parse(inv.get("entry_price",""))
            cost_thb_row = s_v * e_v * (rate if get_currency(inv) == "USD" else 1) if s_v and e_v else 0
            raw.append({
                "inv": inv, "price": price,
                "pnl_thb": pnl_thb or 0, "pnl_pct": pnl_pct or 0,
                "pos_thb": pos_thb or 0, "cost_thb": cost_thb_row,
            })

        # Pie chart + Return % chart
        col_pie_inv, col_ret_inv = st.columns([4, 6])
        with col_pie_inv:
            if pie_labels_inv:
                st.plotly_chart(allocation_pie(pie_labels_inv, pie_vals_inv, disp, rate,
                                               "Holdings Allocation", height=280),
                                use_container_width=True)
        with col_ret_inv:
            inv_rp1, inv_rp2, inv_rp3 = st.columns([5, 4, 3])
            with inv_rp1:
                inv_period = st.radio("", ["1D","1W","1M","1Y"], horizontal=True,
                                      key="inv_period", index=2, label_visibility="collapsed")
            with inv_rp2:
                inv_spy = st.checkbox("S&P 500", key="inv_spy")
            with inv_rp3:
                inv_qqq = st.checkbox("NASDAQ 100", key="inv_qqq")
            fig_inv_ret = portfolio_return_chart(open_inv, rate, disp, inv_period,
                                                  show_spy=inv_spy, show_qqq=inv_qqq, height=260)
            if fig_inv_ret:
                st.plotly_chart(fig_inv_ret, use_container_width=True)
            else:
                st.info("ไม่มีข้อมูลราคาย้อนหลัง")

        # -- Target Allocation --
        inv_with_target = [r for r in raw if r["inv"].get("target_pct") is not None]
        if inv_with_target and total_val_thb:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            section("🎯 Target Allocation")

            t_tickers  = [r["inv"]["ticker"] for r in inv_with_target]
            curr_pcts  = [r["pos_thb"] / total_val_thb * 100 if total_val_thb else 0
                          for r in inv_with_target]
            tgt_pcts   = [r["inv"].get("target_pct", 0) for r in inv_with_target]
            deltas     = [c - t for c, t in zip(curr_pcts, tgt_pcts)]
            total_tgt  = sum(t for t in tgt_pcts if t)

            def _tgt_color(d):
                if abs(d) <= 3: return "#22c55e"
                if abs(d) <= 8: return "#f59e0b"
                return "#ef4444"
            bar_colors = [_tgt_color(d) for d in deltas]

            fig_tgt = go.Figure()
            fig_tgt.add_trace(go.Bar(
                name="Target %", y=t_tickers, x=tgt_pcts, orientation="h",
                marker_color="rgba(148,163,184,0.25)",
                marker_line=dict(color="#94a3b8", width=1),
                text=[f"{p:.0f}%" for p in tgt_pcts], textposition="inside",
                textfont=dict(size=11, color="#94a3b8"),
            ))
            fig_tgt.add_trace(go.Bar(
                name="Current %", y=t_tickers, x=curr_pcts, orientation="h",
                marker_color=bar_colors, opacity=0.85,
                text=[f"{p:.1f}%" for p in curr_pcts], textposition="outside",
                textfont=dict(size=11, color="#e2e8f0"),
            ))
            fig_tgt.update_layout(
                **{**CHART_LAYOUT,
                   "barmode": "overlay",
                   "height": max(200, len(t_tickers) * 45 + 70),
                   "showlegend": True,
                   "legend": dict(orientation="h", y=1.1, x=0, font=dict(size=11, color="#94a3b8")),
                   "margin": dict(t=50, b=8, l=8, r=80),
                   "xaxis": dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                                 ticksuffix="%", tickfont=dict(size=11, color="#94a3b8")),
                   "yaxis": dict(showgrid=False, tickfont=dict(size=12, color="#e2e8f0")),
                   "title": dict(
                       text=(f"Current vs Target  "
                             f"<span style='font-size:11px;color:#64748b'>"
                             f"Target รวม {total_tgt:.0f}% · Cash {max(0, 100-total_tgt):.0f}%</span>"),
                       font=dict(size=13, color="#94a3b8"), x=0),
                }
            )
            st.plotly_chart(fig_tgt, use_container_width=True)

            sym_r = "฿" if disp == "THB" else "$"
            rebal_rows = []
            for r, curr_p, tgt_p, delta in zip(inv_with_target, curr_pcts, tgt_pcts, deltas):
                action_thb = abs(delta) / 100 * total_val_thb
                action_disp = to_display(action_thb, disp, rate)
                if tgt_p == 0:
                    action = "—"
                elif delta > 3:
                    action = f"🔴 ขายลด {sym_r}{action_disp:,.0f}"
                elif delta < -3:
                    action = f"🟢 ซื้อเพิ่ม {sym_r}{action_disp:,.0f}"
                else:
                    action = "✅ ใกล้เป้า"
                rebal_rows.append({
                    "Ticker":   r["inv"]["ticker"],
                    "Current":  f"{curr_p:.1f}%",
                    "Target":   f"{tgt_p:.0f}%",
                    "Δ":        f"{'+' if delta >= 0 else ''}{delta:.1f}%",
                    "Action":   action,
                })
            st.dataframe(rebal_rows, use_container_width=True, hide_index=True)

            no_target = [r["inv"]["ticker"] for r in raw if r["inv"].get("target_pct") is None]
            if no_target:
                st.caption(f"ยังไม่ตั้ง Target %: {', '.join(no_target)} — กดแก้ไขใน position เพื่อตั้งค่า")

        raw.sort(key=lambda r: -r["pnl_thb"])

        # Build display rows
        section(f"Current Holdings ({len(open_inv)})")
        total_mv, total_pnl_disp, total_cost_disp = 0.0, 0.0, 0.0
        rows = []
        for i, r in enumerate(raw):
            inv, price = r["inv"], r["price"]
            mv     = to_display(r["pos_thb"] or 0, disp, rate)
            pnl_d  = to_display(r["pnl_thb"] or 0, disp, rate)
            cost_d = to_display(r["cost_thb"] or 0, disp, rate)
            if price:
                total_mv   += mv
                total_pnl_disp += pnl_d
            total_cost_disp += cost_d
            rows.append({
                "#":             i + 1,
                "Ticker":        inv.get("ticker","—"),
                "ถือมา":         days_held_str(inv.get("entry_date","")),
                "Shares":        get_shares(inv),
                "Avg Cost":      inv.get("entry_price","—"),
                "Total Cost":    fmt_money(r["cost_thb"] or None, disp, rate, sign=False) if r["cost_thb"] else "—",
                "Current Price": (f"📌 {price:.2f}" if inv.get("manual_price") else f"{price:.2f}") if price else "—",
                "Market Value":  fmt_money(r["pos_thb"] or None, disp, rate, sign=False),
                "P&L %":         fmt_pct(r["pnl_pct"]) if price else "—",
                f"P&L ({sym})":  fmt_money(r["pnl_thb"] or None, disp, rate) if price else "—",
                "Thesis":        inv.get("thesis","—"),
            })

        # Total row
        sym_p = "฿" if disp == "THB" else "$"
        total_pnl_pct_row = total_pnl_disp / (total_mv - total_pnl_disp) * 100 if (total_mv - total_pnl_disp) else 0
        rows.append({
            "#":             "—",
            "Ticker":        "📊 TOTAL",
            "Shares":        "—",
            "Avg Cost":      "—",
            "Total Cost":    f"{sym_p}{total_cost_disp:,.0f}",
            "Current Price": "—",
            "Market Value":  f"{sym_p}{total_mv:,.0f}",
            "ถือมา":         "—",
            "P&L %":         fmt_pct(total_pnl_pct_row),
            f"P&L ({sym})":  fmt_money(sum(r["pnl_thb"] for r in raw if r.get("price")), disp, rate),
            "Thesis":        "—",
        })

        pnl_cols = ["P&L %", f"P&L ({sym})"]

        def _color_pnl(val):
            if isinstance(val, str) and val.startswith("+"):
                return "color: #22c55e; font-weight: 600"
            if isinstance(val, str) and val.startswith("-"):
                return "color: #ef4444; font-weight: 600"
            return ""

        def _style_total(row):
            if row["Ticker"] == "📊 TOTAL":
                return ["background-color: rgba(88,101,242,0.12); font-weight: 700"] * len(row)
            return [""] * len(row)

        df_inv = pd.DataFrame(rows)
        try:
            styled = (df_inv.style
                      .map(_color_pnl, subset=pnl_cols)
                      .apply(_style_total, axis=1)
                      .hide(axis="index"))
        except AttributeError:
            styled = (df_inv.style
                      .applymap(_color_pnl, subset=pnl_cols)
                      .apply(_style_total, axis=1)
                      .hide(axis="index"))
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Position actions (ปิด/ลบ)
        with st.expander(f"⚙️ Position Actions ({len(open_inv)})", expanded=False):
            for inv in open_inv:
                price   = get_price(inv.get("ticker",""))
                pnl_thb = calc_pnl_thb(inv.get("entry_price"), price, get_shares(inv),
                                        get_currency(inv), rate) if price else None
                pnl_pct = calc_pnl_pct(inv.get("entry_price"), price) if price else None
                icon    = "🟢" if (pnl_thb or 0) >= 0 else "🔴"

                _ihc    = "green" if (pnl_thb or 0) >= 0 else "red"
                _isv    = parse(get_shares(inv))
                _icost  = calc_position_thb(inv.get("entry_price"), get_shares(inv), get_currency(inv), rate)
                _imval  = (_isv * price * (rate if get_currency(inv) == "USD" else 1)) if price and _isv else None
                _ics    = fmt_money(_icost, disp, rate, sign=False) if _icost else "—"
                _ivs    = fmt_money(_imval, disp, rate, sign=False) if _imval else "—"
                inv_label = (f"{icon} **{inv['ticker']}**  ·  "
                             f"AVG {inv.get('entry_price','—')} → {f'{price:.2f}' if price else '—'}  ·  "
                             f"{_ics} → {_ivs}"
                             f"  |  :{_ihc}[{fmt_pct(pnl_pct)}  {fmt_money(pnl_thb, disp, rate)}]"
                             ).replace("$", r"\$")
                with st.expander(inv_label, expanded=False):
                    # P&L banner
                    _pc2 = "#22c55e" if (pnl_thb or 0) >= 0 else "#ef4444"
                    _bg2 = "rgba(34,197,94,0.08)" if (pnl_thb or 0) >= 0 else "rgba(239,68,68,0.08)"
                    st.markdown(
                        f"<div style='background:{_bg2};border-left:3px solid {_pc2};"
                        f"border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:10px'>"
                        f"<div style='font-size:10px;color:#94a3b8;text-transform:uppercase;"
                        f"letter-spacing:0.07em;margin-bottom:2px'>Unrealized P&L</div>"
                        f"<span style='font-size:22px;font-weight:700;color:{_pc2}'>"
                        f"{fmt_money(pnl_thb, disp, rate) if pnl_thb is not None else '—'}</span>"
                        f"&nbsp;&nbsp;<span style='font-size:13px;color:{_pc2}'>{fmt_pct(pnl_pct)}</span>"
                        f"</div>",
                        unsafe_allow_html=True)
                    im1, im2, im3, im4 = st.columns(4)
                    im1.metric("Cost Basis",    _ics)
                    im2.metric("Mkt Value",     _ivs)
                    im3.metric("AVG Price",     inv.get("entry_price","—"))
                    im4.metric("Current Price", f"{price:.2f}" if price else "—",
                               delta=fmt_pct(pnl_pct) if pnl_pct else None)
                    st.caption(f"Shares: {get_shares(inv)}  ·  {get_currency(inv)}")
                    ca, cb, cc, _, cd = st.columns([2, 2, 2, 1, 1])
                    if ca.button("🔴 ขาย", key=f"ci_{inv['id']}"):
                        st.session_state[f"sell_inv_{inv['id']}"] = True
                        st.session_state.pop(f"edit_inv_{inv['id']}", None)
                        st.session_state.pop(f"add_inv_{inv['id']}", None)
                    if cb.button("✏️ แก้ไข", key=f"ei_{inv['id']}"):
                        st.session_state[f"edit_inv_{inv['id']}"] = True
                        st.session_state.pop(f"sell_inv_{inv['id']}", None)
                        st.session_state.pop(f"add_inv_{inv['id']}", None)
                    if cc.button("➕ ซื้อเพิ่ม", key=f"ai_{inv['id']}"):
                        st.session_state[f"add_inv_{inv['id']}"] = True
                        st.session_state.pop(f"edit_inv_{inv['id']}", None)
                        st.session_state.pop(f"sell_inv_{inv['id']}", None)
                    if cd.button("🗑️", key=f"di_{inv['id']}"):
                        investments[:] = [x for x in investments if x["id"] != inv["id"]]
                        save_investments(investments)
                        st.rerun()

                    if st.session_state.get(f"add_inv_{inv['id']}"):
                        st.markdown("**➕ ซื้อเพิ่ม**")
                        with st.form(f"form_add_inv_{inv['id']}"):
                            aa1, aa2, aa3 = st.columns(3)
                            add_shares = aa1.text_input("จำนวนหุ้นที่ซื้อเพิ่ม *", placeholder="เช่น 5")
                            add_price  = aa2.text_input("ราคาที่ซื้อ *", placeholder="เช่น 80")
                            add_date   = aa3.date_input("วันที่ซื้อ", value=date.today())
                            src_id, other_name, other_curr = source_selector(cash, f"add_inv_{inv['id']}")
                            if st.form_submit_button("✅ ซื้อเพิ่ม"):
                                s_add = parse(add_shares)
                                p_add = parse(add_price)
                                if s_add and p_add:
                                    s_old = parse(get_shares(inv)) or 0
                                    p_old = parse(inv.get("entry_price", "0")) or 0
                                    s_new = s_old + s_add
                                    p_avg = (s_old * p_old + s_add * p_add) / s_new
                                    add_thb = s_add * p_add * (rate if get_currency(inv) == "USD" else 1)
                                    resolved = resolve_source(cash, src_id, other_name, other_curr)
                                    cash_deduct(cash, resolved, add_thb, rate)
                                    save_cash(cash)
                                    _bh = inv.get("buy_history", [])
                                    _bh.append({"date": str(add_date), "shares": add_shares, "price": add_price, "note": "ซื้อเพิ่ม"})
                                    inv.update({
                                        "shares":       str(round(s_new, 8)),
                                        "entry_price":  str(round(p_avg, 4)),
                                        "position_thb": round((inv.get("position_thb") or 0) + add_thb, 2),
                                        "buy_history":  _bh,
                                    })
                                    save_investments(investments)
                                    st.session_state.pop(f"add_inv_{inv['id']}", None)
                                    st.success(f"ซื้อเพิ่ม {add_shares} หุ้น @ {add_price} · AVG ใหม่ = {round(p_avg,4)}")
                                    st.rerun()
                                else:
                                    st.error("กรุณากรอกจำนวนหุ้นและราคา")

                    if st.session_state.get(f"edit_inv_{inv['id']}"):
                        st.markdown("**แก้ไข Investment**")
                        with st.form(f"form_edit_inv_{inv['id']}"):
                            ei1, ei2, ei3 = st.columns(3)
                            new_ticker = ei1.text_input("Ticker",       value=inv.get("ticker",""))
                            new_shares = ei2.text_input("จำนวนหุ้น",    value=get_shares(inv))
                            new_entry  = ei3.text_input("Entry Price",  value=inv.get("entry_price",""))
                            ee1, ee2 = st.columns(2)
                            new_thesis  = ee1.text_input("Thesis", value=inv.get("thesis",""))
                            new_tgt_raw = ee2.text_input(
                                "Target % (สัดส่วนเป้าหมาย)",
                                value=str(inv["target_pct"]) if inv.get("target_pct") is not None else "",
                                placeholder="เช่น 20  (ว่าง = ไม่ตั้ง)",
                            )
                            new_manual_price = st.text_input(
                                "📌 Manual Price (DR / หุ้นที่ดึงราคาไม่ได้)",
                                value=str(inv["manual_price"]) if inv.get("manual_price") is not None else "",
                                placeholder="ใส่ราคาปัจจุบัน เช่น 85.50  (ว่าง = ดึงจาก yfinance)",
                            )
                            if st.form_submit_button("💾 บันทึก"):
                                upd = {
                                    "ticker":      new_ticker.upper().strip(),
                                    "shares":      new_shares,
                                    "entry_price": new_entry,
                                    "thesis":      new_thesis,
                                }
                                t_pct = parse(new_tgt_raw)
                                if t_pct is not None:
                                    upd["target_pct"] = t_pct
                                elif not new_tgt_raw.strip() and "target_pct" in inv:
                                    upd["target_pct"] = None
                                mp = parse(new_manual_price)
                                if mp is not None:
                                    upd["manual_price"] = mp
                                elif not new_manual_price.strip():
                                    upd["manual_price"] = None
                                inv.update(upd)
                                save_investments(investments)
                                st.session_state.pop(f"edit_inv_{inv['id']}", None)
                                st.success("แก้ไขเรียบร้อย!")
                                st.rerun()

                    if st.session_state.get(f"sell_inv_{inv['id']}"):
                        st.markdown("**🔴 ขาย**")
                        s_current = parse(get_shares(inv)) or 0
                        st.caption(f"ถืออยู่ {s_current} หุ้น · AVG {inv.get('entry_price','—')} · ใส่ครบ = ปิด position")
                        with st.form(f"form_sell_inv_{inv['id']}"):
                            sv1, sv2, sv3 = st.columns(3)
                            sell_shares = sv1.text_input("จำนวนที่ขาย *", placeholder=f"สูงสุด {s_current}")
                            exit_p      = sv2.text_input("ราคาที่ขาย *", placeholder="เช่น 420")
                            exit_d      = sv3.date_input("วันที่ขาย", value=date.today())
                            sv4, sv5 = st.columns(2)
                            thesis_ok = sv4.selectbox("Thesis ถูกไหม (ถ้าปิด position)",
                                                       ["✅ ถูก", "❌ ผิด", "⚠️ บางส่วน"])
                            emotion   = sv5.selectbox("Emotion (ถ้าปิด position)",
                                                       ["ปกติ", "กลัว", "โลภ", "FOMO"])
                            lesson    = st.text_input("Lesson ที่ได้ (optional, ถ้าปิด position)")
                            if st.form_submit_button("✅ ยืนยันขาย"):
                                s_sell = parse(sell_shares)
                                ep     = parse(exit_p)
                                if not s_sell or not ep:
                                    st.error("กรุณากรอกจำนวนหุ้นและราคาที่ขาย")
                                elif s_sell > s_current:
                                    st.error(f"ขายได้สูงสุด {s_current} หุ้น")
                                else:
                                    src_id   = inv.get("source_account_id")
                                    currency = get_currency(inv)
                                    exit_thb = s_sell * ep * (rate if currency == "USD" else 1)
                                    if s_sell >= s_current:
                                        pnl_pct_v = calc_pnl_pct(inv["entry_price"], ep)
                                        pnl_thb_v = calc_pnl_thb(inv["entry_price"], ep, str(s_current), currency, rate)
                                        inv.update({"status": "closed", "exit_price": str(ep),
                                                    "exit_date": str(exit_d),
                                                    "pnl_pct": pnl_pct_v, "pnl_thb": pnl_thb_v,
                                                    "thesis_correct": thesis_ok,
                                                    "emotion": emotion, "lesson": lesson})
                                        if src_id:
                                            cash_credit(cash, src_id, exit_thb, rate)
                                            save_cash(cash)
                                        save_investments(investments)
                                        st.session_state.pop(f"sell_inv_{inv['id']}", None)
                                        st.success(f"ปิด Position ✅  P&L = {fmt_money(pnl_thb_v, disp, rate)}")
                                    else:
                                        s_remain  = round(s_current - s_sell, 8)
                                        pnl_thb_p = calc_pnl_thb(inv["entry_price"], ep, str(s_sell), currency, rate)
                                        sell_hist = inv.get("sell_history", [])
                                        sell_hist.append({
                                            "date": str(exit_d), "shares": str(s_sell),
                                            "price": str(ep), "thb": round(exit_thb, 2),
                                            "pnl_thb": round(pnl_thb_p or 0, 2),
                                        })
                                        new_pos_thb = (inv.get("position_thb") or 0) * (s_remain / s_current)
                                        inv.update({
                                            "shares":       str(s_remain),
                                            "position_thb": round(new_pos_thb, 2),
                                            "sell_history": sell_hist,
                                        })
                                        if src_id:
                                            cash_credit(cash, src_id, exit_thb, rate)
                                            save_cash(cash)
                                        save_investments(investments)
                                        st.session_state.pop(f"sell_inv_{inv['id']}", None)
                                        st.success(f"ขาย {s_sell} หุ้น @ {ep} ✅  เหลือ {s_remain} หุ้น · P&L = {fmt_money(pnl_thb_p, disp, rate)}")
                                    st.rerun()

    # -- Closed --
    if closed_inv:
        section(f"Closed ({len(closed_inv)})")
        st.dataframe([{
            "Ticker": i.get("ticker","—"), "Entry": i.get("entry_price","—"),
            "Exit":   i.get("exit_price","—"), "P&L %": fmt_pct(i.get("pnl_pct")),
            f"P&L ({sym})": fmt_money(i.get("pnl_thb"), disp, rate),
            "ซื้อ": i.get("entry_date","—"), "ขาย": i.get("exit_date","—"),
        } for i in closed_inv], use_container_width=True, hide_index=True)

    # -- Add Investment (collapsed) --
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    with st.expander("➕ เพิ่ม / ซื้อเพิ่ม Investment"):
        existing_tickers = sorted({inv["ticker"] for inv in open_inv})
        ticker_options   = existing_tickers + ["➕ Ticker ใหม่"]
        selected_ticker  = st.selectbox("เลือก Ticker", ticker_options, key="new_inv_select")

        if selected_ticker != "➕ Ticker ใหม่":
            # -- ซื้อเพิ่มใน position ที่มีอยู่ --
            existing = next((inv for inv in investments
                             if inv["ticker"] == selected_ticker and inv["status"] == "open"), None)
            if existing:
                cur = get_currency(existing)
                st.caption(f"ถืออยู่: {get_shares(existing)} หุ้น  ·  AVG {existing.get('entry_price','—')}  ·  {cur}")
                with st.form("add_to_pos"):
                    b1, b2, b3 = st.columns(3)
                    add_shares = b1.text_input("จำนวนที่ซื้อเพิ่ม *", placeholder="เช่น 5")
                    add_price  = b2.text_input(f"ราคาที่ซื้อ ({cur}) *", placeholder="เช่น 420")
                    add_date   = b3.date_input("วันที่ซื้อ", value=date.today())
                    st.markdown("---")
                    src_id, other_name, other_curr = source_selector(cash, "add_pos")
                    is_import = st.checkbox("📥 ไม่หักเงินจาก Cash (Import เก่า)", key="import_add_pos")
                    if st.form_submit_button("✅ ซื้อเพิ่ม"):
                        s_add = parse(add_shares)
                        p_add = parse(add_price)
                        if not s_add or not p_add:
                            st.error("กรุณากรอกจำนวนและราคา")
                        else:
                            s_old = parse(get_shares(existing)) or 0
                            p_old = parse(existing.get("entry_price", "0")) or 0
                            s_new = s_old + s_add
                            p_avg = (s_old * p_old + s_add * p_add) / s_new
                            add_thb = s_add * p_add * (rate if cur == "USD" else 1)
                            resolved = resolve_source(cash, src_id, other_name, other_curr)
                            if not is_import:
                                cash_deduct(cash, resolved, add_thb, rate)
                                save_cash(cash)
                            # append buy log
                            history = existing.get("buy_history", [])
                            history.append({
                                "date": str(add_date), "shares": add_shares,
                                "price": add_price, "thb": round(add_thb, 2),
                                "note": "ซื้อเพิ่ม"
                            })
                            existing.update({
                                "shares":       str(round(s_new, 8)),
                                "entry_price":  str(round(p_avg, 4)),
                                "position_thb": round((existing.get("position_thb") or 0) + add_thb, 2),
                                "buy_history":  history,
                            })
                            save_investments(investments)
                            st.success(
                                f"✅ ซื้อเพิ่ม {add_shares} หุ้น @ {add_price}  ·  "
                                f"AVG ใหม่ = {round(p_avg, 4)} {cur}  ·  "
                                f"รวม {round(s_new, 4)} หุ้น"
                            )
                            st.rerun()
        else:
            # -- Ticker ใหม่ --
            with st.form("new_inv"):
                c1, c2, c3 = st.columns(3)
                ticker     = c1.text_input("Ticker *", placeholder="เช่น AOT.BK, AAPL")
                shares     = c2.text_input("จำนวนหุ้น *", placeholder="เช่น 1000")
                currency   = c3.selectbox("ราคาเป็น", ["THB", "USD"])
                c4, c5     = st.columns(2)
                entry      = c4.text_input("Entry Price *", placeholder="ราคาที่ซื้อ")
                entry_date = c5.date_input("วันที่ซื้อ", value=date.today())
                ni1, ni2 = st.columns(2)
                thesis     = ni1.text_input("เหตุผลที่ลงทุน",
                                             placeholder="เช่น พื้นฐานดี dividend สม่ำเสมอ...")
                target_pct_inp = ni2.text_input("Target % (optional)",
                                                 placeholder="เช่น 20  — สัดส่วนเป้าหมายในพอร์ต")
                st.markdown("---")
                src_id, other_name, other_curr = source_selector(cash, "inv")
                is_import = st.checkbox("📥 Import position เก่า (ไม่หักเงินจาก Cash)", key="import_inv")
                if st.form_submit_button("✅ บันทึก"):
                    e, s = parse(entry), parse(shares)
                    if not ticker or e is None or s is None:
                        st.error("กรุณากรอก Ticker, จำนวนหุ้น และ Entry Price")
                    else:
                        pos_thb  = s * e * (rate if currency == "USD" else 1)
                        t_pct_v  = parse(target_pct_inp)
                        resolved = resolve_source(cash, src_id, other_name, other_curr)
                        if not is_import:
                            cash_deduct(cash, resolved, pos_thb, rate)
                            save_cash(cash)
                        new_inv = {
                            "id": next_id(investments), "type": "investment", "status": "open",
                            "ticker": ticker.upper().strip(), "shares": shares,
                            "currency": currency, "entry_price": entry,
                            "entry_date": str(entry_date), "thesis": thesis,
                            "position_thb": round(pos_thb, 2),
                            "source_account_id": resolved,
                            "source_account_name": next((a["name"] for a in cash if a["id"] == resolved), ""),
                            "buy_history": [{"date": str(entry_date), "shares": shares,
                                             "price": entry, "thb": round(pos_thb, 2), "note": "เปิด position"}],
                        }
                        if t_pct_v is not None:
                            new_inv["target_pct"] = t_pct_v
                        investments.append(new_inv)
                        save_investments(investments)
                        st.success(f"✅ บันทึก {ticker.upper()}")
                        st.rerun()


# -- Page 3: Trade --
def page_trade(trades: list, cash: list, disp: str, rate: float):
    open_trades   = [t for t in trades if t.get("status") == "open"]
    closed_trades = [t for t in trades if t.get("status") == "closed"]
    wins   = [t for t in closed_trades if t.get("win_loss") == "Win"]
    losses = [t for t in closed_trades if t.get("win_loss") == "Loss"]
    sym    = "฿" if disp == "THB" else "$"

    realized_thb   = sum(t.get("pnl_thb", 0) or 0 for t in closed_trades)
    win_rate       = len(wins) / len(closed_trades) * 100 if closed_trades else None
    total_win_thb  = sum(t.get("pnl_thb", 0) or 0 for t in wins)
    total_loss_thb = abs(sum(t.get("pnl_thb", 0) or 0 for t in losses))
    profit_factor  = round(total_win_thb / total_loss_thb, 2) if total_loss_thb > 0 else None

    # -- Performance KPIs --
    section("Performance")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Open Trades",   len(open_trades))
    k2.metric("Win Rate",      f"{win_rate:.1f}%" if win_rate is not None else "—")
    k3.metric("Profit Factor", f"{profit_factor:.2f}" if profit_factor else "—")
    k4.metric("Realized P&L",  fmt_money(realized_thb if closed_trades else None, disp, rate))
    k5.metric("Closed Trades", len(closed_trades))

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # -- Open Trades --
    if not open_trades:
        st.info("ไม่มี Open Trade ในขณะนี้")
    else:
        section(f"Open Trades ({len(open_trades)})")

        # -- Overview table --
        _tr_rows = []
        _tr_total_cost, _tr_total_mv, _tr_total_pnl = 0.0, 0.0, 0.0
        for _ti, _t in enumerate(open_trades):
            _tp    = get_price(_t.get("ticker",""))
            _tpnl  = calc_pnl_thb(_t.get("entry_price"), _tp, get_shares(_t),
                                   get_currency(_t), rate, _t.get("direction","Long")) if _tp else None
            _tpct  = calc_pnl_pct(_t.get("entry_price"), _tp, _t.get("direction","Long")) if _tp else None
            _tcost = calc_position_thb(_t.get("entry_price"), get_shares(_t), get_currency(_t), rate)
            _tsv2  = parse(get_shares(_t))
            _tmv   = (_tsv2 * _tp * (rate if get_currency(_t) == "USD" else 1)) if _tp and _tsv2 else None
            if _tp:
                _tr_total_mv  += to_display(_tmv or 0, disp, rate)
                _tr_total_pnl += to_display(_tpnl or 0, disp, rate)
            _tr_total_cost += to_display(_tcost or 0, disp, rate)
            _tr_rows.append({
                "#":             _ti + 1,
                "Dir":           "↑ Long" if _t.get("direction","Long") == "Long" else "↓ Short",
                "Ticker":        _t.get("ticker","—"),
                "Shares":        get_shares(_t),
                "AVG Price":     _t.get("entry_price","—"),
                "Current Price": f"{_tp:.2f}" if _tp else "—",
                "Cost":          fmt_money(_tcost, disp, rate, sign=False) if _tcost else "—",
                "Mkt Value":     fmt_money(_tmv, disp, rate, sign=False) if _tmv else "—",
                "P&L %":         fmt_pct(_tpct) if _tpct is not None else "—",
                f"P&L ({sym})":  fmt_money(_tpnl, disp, rate) if _tpnl is not None else "—",
                "TP":            _t.get("take_profit","—"),
                "SL":            _t.get("stop_loss","—"),
            })
        _sym_p = "฿" if disp == "THB" else "$"
        _tr_pnl_pct_tot = _tr_total_pnl / (_tr_total_mv - _tr_total_pnl) * 100 if (_tr_total_mv - _tr_total_pnl) else 0
        _tr_rows.append({
            "#": "—", "Dir": "—", "Ticker": "📊 TOTAL", "Shares": "—",
            "AVG Price": "—", "Current Price": "—",
            "Cost":          f"{_sym_p}{_tr_total_cost:,.0f}",
            "Mkt Value":     f"{_sym_p}{_tr_total_mv:,.0f}",
            "P&L %":         fmt_pct(_tr_pnl_pct_tot),
            f"P&L ({sym})":  f"{_sym_p}{_tr_total_pnl:,.0f}",
            "TP": "—", "SL": "—",
        })
        _pnl_cols_t = ["P&L %", f"P&L ({sym})"]
        def _color_pnl_t(val):
            if isinstance(val, str) and val.startswith("+"):
                return "color: #22c55e; font-weight: 600"
            if isinstance(val, str) and val.startswith("-"):
                return "color: #ef4444; font-weight: 600"
            return ""
        def _style_total_t(row):
            if row["Ticker"] == "📊 TOTAL":
                return ["background-color: rgba(88,101,242,0.12); font-weight: 700"] * len(row)
            return [""] * len(row)
        _df_tr = pd.DataFrame(_tr_rows)
        try:
            _styled_tr = (_df_tr.style
                          .map(_color_pnl_t, subset=_pnl_cols_t)
                          .apply(_style_total_t, axis=1)
                          .hide(axis="index"))
        except AttributeError:
            _styled_tr = (_df_tr.style
                          .applymap(_color_pnl_t, subset=_pnl_cols_t)
                          .apply(_style_total_t, axis=1)
                          .hide(axis="index"))
        st.dataframe(_styled_tr, use_container_width=True, hide_index=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # -- Per-trade action menus --
        for t in open_trades:
            price   = get_price(t.get("ticker",""))
            pnl_thb = calc_pnl_thb(t.get("entry_price"), price, get_shares(t),
                                    get_currency(t), rate, t.get("direction","Long")) if price else None
            pnl_pct = calc_pnl_pct(t.get("entry_price"), price, t.get("direction","Long")) if price else None
            pos_thb = calc_position_thb(t.get("entry_price"), get_shares(t), get_currency(t), rate)
            _tsv    = parse(get_shares(t))
            mkt_val_thb = (_tsv * price * (rate if get_currency(t) == "USD" else 1)) if price and _tsv else None
            tp_val  = parse(t.get("take_profit",""))
            sl_val  = parse(t.get("stop_loss",""))
            tp_thb  = calc_pnl_thb(t.get("entry_price"), tp_val, get_shares(t),
                                    get_currency(t), rate, t.get("direction","Long")) if tp_val else None
            sl_thb  = calc_pnl_thb(t.get("entry_price"), sl_val, get_shares(t),
                                    get_currency(t), rate, t.get("direction","Long")) if sl_val else None
            icon  = "🟢" if (pnl_thb or 0) >= 0 else "🔴"
            arrow = "↑" if t.get("direction") == "Long" else "↓"
            _hc   = "green" if (pnl_thb or 0) >= 0 else "red"
            _cs   = fmt_money(pos_thb, disp, rate, sign=False) if pos_thb else "—"
            _vs   = fmt_money(mkt_val_thb, disp, rate, sign=False) if mkt_val_thb else "—"
            header = (f"{icon} **{t['ticker']}** {arrow}  ·  "
                      f"AVG {t.get('entry_price','—')} → {f'{price:.2f}' if price else '—'}  ·  "
                      f"{_cs} → {_vs}"
                      f"  |  :{_hc}[{fmt_pct(pnl_pct)}  {fmt_money(pnl_thb, disp, rate)}]"
                      ).replace("$", r"\$")

            with st.expander(header):
                # P&L banner
                _pc = "#22c55e" if (pnl_thb or 0) >= 0 else "#ef4444"
                _bg = "rgba(34,197,94,0.08)" if (pnl_thb or 0) >= 0 else "rgba(239,68,68,0.08)"
                st.markdown(
                    f"<div style='background:{_bg};border-left:3px solid {_pc};"
                    f"border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:10px'>"
                    f"<div style='font-size:10px;color:#94a3b8;text-transform:uppercase;"
                    f"letter-spacing:0.07em;margin-bottom:2px'>Unrealized P&L</div>"
                    f"<span style='font-size:22px;font-weight:700;color:{_pc}'>"
                    f"{fmt_money(pnl_thb, disp, rate) if pnl_thb is not None else '—'}</span>"
                    f"&nbsp;&nbsp;<span style='font-size:13px;color:{_pc}'>{fmt_pct(pnl_pct)}</span>"
                    f"</div>",
                    unsafe_allow_html=True)

                r1c1, r1c2, r1c3, r1c4 = st.columns(4)
                r1c1.metric("Cost Basis",    fmt_money(pos_thb, disp, rate, sign=False) if pos_thb else "—")
                r1c2.metric("Mkt Value",     fmt_money(mkt_val_thb, disp, rate, sign=False) if mkt_val_thb else "—")
                r1c3.metric("AVG Price",     t.get("entry_price","—"))
                r1c4.metric("Current Price", f"{price:.2f}" if price else "—",
                            delta=fmt_pct(pnl_pct) if pnl_pct else None)
                st.caption(f"Shares: {get_shares(t)}  ·  {get_currency(t)}  ·  เปิด {t.get('open_date','—')}")

                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

                r2c1, r2c2, r2c3 = st.columns(3)
                with r2c1:
                    st.markdown(
                        f"<div style='font-size:12px;color:#64748b;margin-bottom:2px'>TP</div>"
                        f"<div style='font-size:18px;font-weight:600'>{t.get('take_profit','—')}</div>"
                        f"<div style='font-size:12px;color:#22c55e'>"
                        f"Profit {fmt_money(tp_thb, disp, rate) if tp_thb is not None else '—'}</div>",
                        unsafe_allow_html=True)
                with r2c2:
                    st.markdown(
                        f"<div style='font-size:12px;color:#64748b;margin-bottom:2px'>SL</div>"
                        f"<div style='font-size:18px;font-weight:600'>{t.get('stop_loss','—')}</div>"
                        f"<div style='font-size:12px;color:#ef4444'>"
                        f"Loss {fmt_money(sl_thb, disp, rate) if sl_thb is not None else '—'}</div>",
                        unsafe_allow_html=True)
                with r2c3:
                    st.markdown(
                        f"<div style='font-size:12px;color:#64748b;margin-bottom:2px'>R:R &amp; Info</div>"
                        f"<div style='font-size:15px;font-weight:600'>{t.get('rr','—')}</div>"
                        f"<div style='font-size:11px;color:#64748b'>{get_currency(t)} · เปิด {t.get('open_date','—')}</div>",
                        unsafe_allow_html=True)

                st.caption(f"Thesis: {t.get('thesis','—')}")
                st.divider()

                ca, cb, cc, _, cd = st.columns([2, 2, 2, 1, 1])
                if ca.button("🔴 ขาย", key=f"btn_close_{t['id']}"):
                    st.session_state[f"show_close_{t['id']}"] = True
                    st.session_state.pop(f"show_edit_{t['id']}", None)
                    st.session_state.pop(f"show_add_{t['id']}", None)
                if cb.button("✏️ แก้ไข", key=f"btn_edit_{t['id']}"):
                    st.session_state[f"show_edit_{t['id']}"] = True
                    st.session_state.pop(f"show_close_{t['id']}", None)
                    st.session_state.pop(f"show_add_{t['id']}", None)
                if cc.button("➕ ซื้อเพิ่ม", key=f"btn_add_{t['id']}"):
                    st.session_state[f"show_add_{t['id']}"] = True
                    st.session_state.pop(f"show_close_{t['id']}", None)
                    st.session_state.pop(f"show_edit_{t['id']}", None)
                if cd.button("🗑️", key=f"btn_del_{t['id']}"):
                    trades[:] = [x for x in trades if x["id"] != t["id"]]
                    save_trades(trades)
                    st.rerun()

                if st.session_state.get(f"show_add_{t['id']}"):
                    st.markdown("**➕ ซื้อเพิ่ม**")
                    with st.form(f"form_add_{t['id']}"):
                        ta1, ta2, ta3 = st.columns(3)
                        add_shares = ta1.text_input("จำนวน Shares ที่ซื้อเพิ่ม *", placeholder="เช่น 2")
                        add_price  = ta2.text_input("ราคาที่ซื้อ *", placeholder="เช่น 420")
                        add_date   = ta3.date_input("วันที่ซื้อ", value=date.today())
                        src_id, other_name, other_curr = source_selector(cash, f"add_trade_{t['id']}")
                        if st.form_submit_button("✅ ซื้อเพิ่ม"):
                            s_add = parse(add_shares)
                            p_add = parse(add_price)
                            if s_add and p_add:
                                s_old = parse(get_shares(t)) or 0
                                p_old = parse(t.get("entry_price", "0")) or 0
                                s_new = s_old + s_add
                                p_avg = (s_old * p_old + s_add * p_add) / s_new
                                add_thb = s_add * p_add * (rate if get_currency(t) == "USD" else 1)
                                resolved = resolve_source(cash, src_id, other_name, other_curr)
                                cash_deduct(cash, resolved, add_thb, rate)
                                save_cash(cash)
                                _tbh = t.get("buy_history", [])
                                _tbh.append({"date": str(add_date), "shares": add_shares, "price": add_price, "note": "ซื้อเพิ่ม"})
                                t.update({
                                    "shares":      str(round(s_new, 8)),
                                    "entry_price": str(round(p_avg, 4)),
                                    "position_thb": round((t.get("position_thb") or 0) + add_thb, 2),
                                    "rr": auto_rr(str(round(p_avg, 4)), t.get("stop_loss",""), t.get("take_profit","")),
                                    "buy_history": _tbh,
                                })
                                save_trades(trades)
                                st.session_state.pop(f"show_add_{t['id']}", None)
                                st.success(f"ซื้อเพิ่ม {add_shares} shares @ {add_price} · AVG ใหม่ = {round(p_avg,4)}")
                                st.rerun()
                            else:
                                st.error("กรุณากรอกจำนวน shares และราคา")

                if st.session_state.get(f"show_edit_{t['id']}"):
                    st.markdown("**แก้ไข Trade**")
                    with st.form(f"form_edit_{t['id']}"):
                        ec1, ec2, ec3 = st.columns(3)
                        new_ticker = ec1.text_input("Ticker",      value=t.get("ticker",""))
                        new_shares = ec2.text_input("Shares",      value=get_shares(t))
                        new_entry  = ec3.text_input("AVG Price",   value=t.get("entry_price",""))
                        ec4, ec5, ec6 = st.columns(3)
                        new_sl     = ec4.text_input("Stop Loss",   value=t.get("stop_loss",""))
                        new_tp     = ec5.text_input("Take Profit", value=t.get("take_profit",""))
                        new_thesis = ec6.text_input("Thesis",      value=t.get("thesis",""))
                        ec7, ec8   = st.columns([3, 1])
                        _acct_opts = ["— ไม่ระบุ"] + [a["name"] for a in cash]
                        _curr_acct = t.get("source_account_name", "")
                        _acct_idx  = _acct_opts.index(_curr_acct) if _curr_acct in _acct_opts else 0
                        new_acct   = ec7.selectbox("พอร์ต / บัญชี", _acct_opts, index=_acct_idx)
                        new_dir    = ec8.selectbox("Direction", ["Long", "Short"],
                                                   index=0 if t.get("direction","Long") == "Long" else 1)
                        if st.form_submit_button("💾 บันทึก"):
                            _matched = next((a for a in cash if a["name"] == new_acct), None)
                            t.update({
                                "ticker": new_ticker.upper().strip(),
                                "shares": new_shares, "stop_loss": new_sl,
                                "take_profit": new_tp, "entry_price": new_entry,
                                "thesis": new_thesis,
                                "rr": auto_rr(new_entry, new_sl, new_tp),
                                "direction": new_dir,
                                "source_account_name": _matched["name"] if _matched else "",
                                "source_account_id":   _matched["id"]   if _matched else None,
                            })
                            save_trades(trades)
                            st.session_state.pop(f"show_edit_{t['id']}", None)
                            st.success("แก้ไขเรียบร้อย!")
                            st.rerun()

                if st.session_state.get(f"show_close_{t['id']}"):
                    st.markdown("**🔴 ขาย**")
                    s_current = parse(get_shares(t)) or 0
                    st.caption(f"ถืออยู่ {s_current} shares · AVG {t.get('entry_price','—')} · ใส่ครบ = ปิด trade")
                    with st.form(f"form_close_{t['id']}"):
                        tc1, tc2, tc3 = st.columns(3)
                        sell_shares = tc1.text_input("จำนวน Shares ที่ขาย *", placeholder=f"สูงสุด {s_current}")
                        exit_p      = tc2.text_input("Exit Price *")
                        exit_d      = tc3.date_input("วันที่ปิด", value=date.today())
                        tc4, tc5    = st.columns(2)
                        thesis_ok   = tc4.selectbox("Thesis ถูกไหม (ถ้าขายหมด)",
                                                     ["✅ ถูก", "❌ ผิด", "⚠️ บางส่วน"])
                        emotion     = tc5.selectbox("Emotion (ถ้าขายหมด)",
                                                     ["ปกติ", "กลัว", "โลภ", "FOMO"])
                        lesson      = st.text_input("Lesson ที่ได้ (ถ้าขายหมด)")
                        if st.form_submit_button("✅ ยืนยันขาย"):
                            s_sell = parse(sell_shares)
                            ep     = parse(exit_p)
                            if not s_sell or not ep:
                                st.error("กรุณากรอกจำนวน shares และ Exit Price")
                            elif s_sell > s_current:
                                st.error(f"ขายได้สูงสุด {s_current} shares")
                            else:
                                src_id    = t.get("source_account_id")
                                currency  = get_currency(t)
                                direction = t.get("direction", "Long")
                                if s_sell >= s_current:
                                    pnl_pct_v = calc_pnl_pct(t["entry_price"], ep, direction)
                                    pnl_thb_v = calc_pnl_thb(t["entry_price"], ep, str(s_current), currency, rate, direction)
                                    t.update({
                                        "status": "closed", "exit_price": str(ep),
                                        "close_date": str(exit_d), "thesis_correct": thesis_ok,
                                        "emotion": emotion, "lesson": lesson,
                                        "pnl_pct": pnl_pct_v, "pnl_thb": pnl_thb_v,
                                        "win_loss": "Win" if (pnl_thb_v or 0) > 0 else "Loss",
                                    })
                                    if src_id:
                                        exit_thb = s_current * ep * (rate if currency == "USD" else 1)
                                        if direction == "Short":
                                            entry_thb = s_current * (parse(t["entry_price"]) or 0) * (rate if currency == "USD" else 1)
                                            exit_thb  = 2 * entry_thb - exit_thb
                                        cash_credit(cash, src_id, exit_thb, rate)
                                        save_cash(cash)
                                    save_trades(trades)
                                    st.session_state.pop(f"show_close_{t['id']}", None)
                                    st.success(f"ปิด Trade ✅  P&L = {fmt_money(pnl_thb_v, disp, rate)}")
                                else:
                                    s_remain   = round(s_current - s_sell, 8)
                                    pnl_thb_p  = calc_pnl_thb(t["entry_price"], ep, str(s_sell), currency, rate, direction)
                                    exit_thb_p = s_sell * ep * (rate if currency == "USD" else 1)
                                    if direction == "Short":
                                        entry_thb_p = s_sell * (parse(t["entry_price"]) or 0) * (rate if currency == "USD" else 1)
                                        exit_thb_p  = 2 * entry_thb_p - exit_thb_p
                                    sell_hist = t.get("sell_history", [])
                                    sell_hist.append({
                                        "date": str(exit_d), "shares": str(s_sell),
                                        "price": str(ep), "pnl_thb": round(pnl_thb_p or 0, 2),
                                    })
                                    new_pos_thb = (t.get("position_thb") or 0) * (s_remain / s_current)
                                    t.update({
                                        "shares":       str(s_remain),
                                        "position_thb": round(new_pos_thb, 2),
                                        "sell_history": sell_hist,
                                        "rr": auto_rr(t["entry_price"], t.get("stop_loss",""), t.get("take_profit","")),
                                    })
                                    if src_id:
                                        cash_credit(cash, src_id, exit_thb_p, rate)
                                        save_cash(cash)
                                    save_trades(trades)
                                    st.session_state.pop(f"show_close_{t['id']}", None)
                                    st.success(f"ขาย {s_sell} shares @ {ep} ✅  เหลือ {s_remain} shares · P&L = {fmt_money(pnl_thb_p, disp, rate)}")
                                st.rerun()

    # -- Analytics --
    closed_with_pnl = [t for t in closed_trades if t.get("pnl_thb") is not None]
    if not closed_with_pnl and open_trades:
        st.info("📊 กราฟ Analytics จะขึ้นหลังจากปิด Trade แรก")
    if closed_with_pnl:
        section("Analytics")
        col_wl, col_strat = st.columns(2)

        with col_wl:
            win_count, loss_count = len(wins), len(losses)
            if win_count + loss_count > 0:
                fig_pie = go.Figure(go.Pie(
                    labels=["Win", "Loss"], values=[win_count, loss_count],
                    marker=dict(colors=["#22c55e", "#ef4444"]),
                    hole=0.5, textinfo="percent+value",
                    textfont=dict(size=13, color="#e2e8f0"),
                ))
                fig_pie.update_layout(**{**CHART_LAYOUT, "height": 240,
                    "title": dict(text="Win / Loss Distribution",
                                  font=dict(size=14, color="#94a3b8"), x=0),
                    "showlegend": True, "legend": dict(font=dict(color="#94a3b8")),
                })
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_strat:
            strat_pnl: dict[str, float] = {}
            for t in closed_with_pnl:
                s = t.get("strategy", "—")
                strat_pnl[s] = strat_pnl.get(s, 0) + (t.get("pnl_thb") or 0)
            if strat_pnl:
                st.plotly_chart(
                    pnl_bar_chart(list(strat_pnl.keys()), list(strat_pnl.values()),
                                  disp, rate, "P&L by Strategy", height=240),
                    use_container_width=True)

    # -- Closed Trades Table --
    if closed_trades:
        section(f"Closed Trades ({len(closed_trades)})")
        _ct_rows = [{
            "Ticker":       t.get("ticker","—"),
            "Strategy":     t.get("strategy","—"),
            "เปิด":         t.get("open_date","—"),
            "ปิด":          t.get("close_date","—"),
            "Entry":        t.get("entry_price","—"),
            "Exit":         t.get("exit_price","—"),
            "P&L %":        fmt_pct(t.get("pnl_pct")),
            f"P&L ({sym})": fmt_money(t.get("pnl_thb"), disp, rate),
            "W/L":          t.get("win_loss","—"),
            "Lesson":       t.get("lesson","—"),
        } for t in sorted(closed_trades, key=lambda x: x.get("close_date",""), reverse=True)]
        st.dataframe(pd.DataFrame(_ct_rows), use_container_width=True, hide_index=True)

    # -- New Trade Form (collapsed) --
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    with st.expander("➕ เปิด Trade ใหม่"):
        strategy = strategy_input("nt")
        with st.form("new_trade"):
            c1, c2, c3, c4 = st.columns(4)
            ticker    = c1.text_input("Ticker *", placeholder="เช่น AAPL, BTC-USD")
            direction = c2.selectbox("Direction", ["Long", "Short"])
            currency  = c3.selectbox("ราคาเป็น", ["THB", "USD"])
            shares    = c4.text_input("จำนวนหุ้น *", placeholder="เช่น 100")
            c5, c6, c7 = st.columns(3)
            entry     = c5.text_input("Entry Price *")
            sl        = c6.text_input("Stop Loss")
            tp        = c7.text_input("Take Profit")
            thesis    = st.text_area("Thesis *", height=80,
                                     placeholder="เหตุผลสั้นๆ ที่ชัดเจน")
            open_date = st.date_input("วันที่เปิด", value=date.today())
            st.markdown("---")
            src_id, other_name, other_curr = source_selector(cash, "trade")
            is_import = st.checkbox("📥 Import position เก่า (ไม่หักเงินจาก Cash)", key="import_trade")
            if st.form_submit_button("✅ บันทึก Trade"):
                e, s = parse(entry), parse(shares)
                if not ticker or e is None:
                    st.error("กรุณากรอก Ticker และ Entry Price")
                elif not strategy:
                    st.error("กรุณาเลือก Strategy")
                else:
                    rr       = auto_rr(entry, sl, tp)
                    pos_thb  = (s or 0) * e * (rate if currency == "USD" else 1)
                    resolved = resolve_source(cash, src_id, other_name, other_curr)
                    if not is_import:
                        cash_deduct(cash, resolved, pos_thb, rate)
                        save_cash(cash)
                    trades.append({
                        "id": next_id(trades), "type": "trade", "status": "open",
                        "ticker": ticker.upper().strip(), "direction": direction,
                        "strategy": strategy, "currency": currency,
                        "entry_price": entry, "shares": shares,
                        "stop_loss": sl, "take_profit": tp, "rr": rr,
                        "thesis": thesis, "open_date": str(open_date),
                        "position_thb": round(pos_thb, 2),
                        "source_account_id": resolved,
                        "source_account_name": next((a["name"] for a in cash if a["id"] == resolved), ""),
                    })
                    save_trades(trades)
                    st.success(f"✅ บันทึก! R:R = {rr} · Position: {fmt_money(pos_thb, disp, rate, sign=False)}")
                    st.rerun()


# -- Page 4: Cash --
def page_cash(trades: list, investments: list, cash: list, disp: str, rate: float):

    # -- Summary metrics --
    section("Summary")
    cash_usd = sum(a["amount"] for a in cash if a["currency"] == "USD")
    cash_thb = sum(a["amount"] for a in cash if a["currency"] == "THB")
    cash_total_thb = (cash_usd * rate) + cash_thb

    m1, m2, m3 = st.columns(3)
    m1.metric("Cash THB รวม", f"฿{cash_thb:,.0f}")
    m2.metric("Cash USD รวม", f"${cash_usd:,.2f}")
    m3.metric(f"Net Cash ({disp})", fmt_money(cash_total_thb, disp, rate, sign=False) if cash else "฿0")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # -- Pie + Account cards with inline management --
    if not cash:
        st.info("ยังไม่มีบัญชี Cash — เพิ่มได้ด้านล่าง")
    else:
        col_pie, col_cards = st.columns([4, 5])

        with col_pie:
            pie_labels, pie_vals = [], []
            for acc in cash:
                val_thb = acc["amount"] * rate if acc["currency"] == "USD" else acc["amount"]
                if val_thb > 0:
                    pie_labels.append(acc["name"])
                    pie_vals.append(val_thb)
            if pie_labels:
                st.plotly_chart(
                    allocation_pie(pie_labels, pie_vals, "THB", rate, "Cash Allocation", height=320),
                    use_container_width=True
                )

        with col_cards:
            for acc in cash:
                clr     = "#22c55e" if acc["amount"] >= 0 else "#ef4444"
                sym     = "$" if acc["currency"] == "USD" else "฿"
                fmt     = f"{sym}{acc['amount']:,.2f}" if acc["currency"] == "USD" else f"{sym}{acc['amount']:,.0f}"
                val_thb = acc["amount"] * rate if acc["currency"] == "USD" else acc["amount"]
                sub     = f"≈฿{val_thb:,.0f}" if acc["currency"] == "USD" else acc["currency"]

                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.04);"
                    f"border:1px solid rgba(255,255,255,0.07);border-radius:12px 12px 0 0;"
                    f"padding:14px 20px;display:flex;justify-content:space-between;"
                    f"align-items:center;margin-bottom:0'>"
                    f"<span style='font-size:0.7rem;color:#94a3b8;text-transform:uppercase;"
                    f"letter-spacing:0.09em;min-width:80px'>{acc['name']}</span>"
                    f"<span style='font-size:1.55rem;font-weight:700;color:{clr}'>{fmt}</span>"
                    f"<span style='font-size:0.72rem;color:#64748b;text-align:right'>{sub}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                with st.expander("✏️ จัดการ", expanded=False):
                    other_accs = [a for a in cash if a["id"] != acc["id"]]
                    _ec1, _ec2, _ec3 = st.columns([3, 3, 2])

                    with _ec1:
                        st.caption("แก้ชื่อ / ยอด")
                        with st.form(f"edit_acc_{acc['id']}"):
                            new_name   = st.text_input("ชื่อ", value=acc["name"],
                                                       label_visibility="collapsed",
                                                       placeholder="ชื่อบัญชี")
                            new_amount = st.text_input("ยอด", value=str(acc["amount"]),
                                                       label_visibility="collapsed",
                                                       placeholder="ยอดเงิน")
                            if st.form_submit_button("💾 บันทึก", use_container_width=True):
                                acc["name"]   = new_name.strip() or acc["name"]
                                acc["amount"] = round(parse(new_amount) or 0, 2)
                                save_cash(cash)
                                st.rerun()

                    if other_accs:
                        with _ec2:
                            st.caption("🔀 Reassign")
                            with st.form(f"reassign_{acc['id']}"):
                                t_idx = st.selectbox("ย้ายเข้า", range(len(other_accs)),
                                                      format_func=lambda i: acc_label(other_accs[i]),
                                                      label_visibility="collapsed")
                                if st.form_submit_button("ยืนยัน", use_container_width=True):
                                    target  = other_accs[t_idx]
                                    amt_thb = acc["amount"] * rate if acc["currency"] == "USD" else acc["amount"]
                                    target["amount"] = round(target["amount"] + (amt_thb / rate if target["currency"] == "USD" else amt_thb), 2)
                                    for item in trades + investments:
                                        if item.get("source_account_id") == acc["id"]:
                                            item["source_account_id"]   = target["id"]
                                            item["source_account_name"] = target["name"]
                                    cash[:] = [a for a in cash if a["id"] != acc["id"]]
                                    save_cash(cash)
                                    save_trades(trades)
                                    save_investments(investments)
                                    st.success(f"ย้าย → '{target['name']}' ✅")
                                    st.rerun()

                    with _ec3:
                        st.caption("ลบ")
                        st.markdown("<div style='height:1.55rem'></div>", unsafe_allow_html=True)
                        if st.button("🗑️ ลบ", key=f"del_acc_{acc['id']}",
                                     use_container_width=True):
                            cash[:] = [a for a in cash if a["id"] != acc["id"]]
                            save_cash(cash)
                            st.rerun()
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # -- Add account --
    with st.expander("➕ เพิ่มบัญชี Cash"):
        with st.form("add_cash_page"):
            fc1, fc2, fc3 = st.columns(3)
            preset      = fc1.selectbox("แหล่ง Cash", CASH_PRESETS)
            custom_name = fc2.text_input("หรือพิมพ์ชื่อเอง", placeholder="เช่น Binance Thai")
            currency    = fc3.selectbox("สกุลเงิน", ["THB", "USD"])
            amount_str  = st.text_input("ยอดเริ่มต้น", placeholder="เช่น 50000 หรือ 1500.50")
            if st.form_submit_button("💾 บันทึก"):
                name   = custom_name.strip() if custom_name.strip() else preset
                new_id = max((a["id"] for a in cash), default=0) + 1
                cash.append({"id": new_id, "name": name, "currency": currency,
                             "amount": round(parse(amount_str) or 0, 2)})
                save_cash(cash)
                st.success(f"เพิ่ม {name} ({currency}) เรียบร้อย!")
                st.rerun()

    # -- Cash Flow History --
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    section("Cash Flow History")

    flows = []
    for t in trades:
        src = t.get("source_account_name") or t.get("source_account_id") or "—"
        pos = calc_position_thb(t.get("entry_price"), get_shares(t), get_currency(t), rate)
        flows.append({
            "วันที่":   t.get("open_date","—"),
            "ประเภท":  "เปิด Trade",
            "Ticker":  t.get("ticker","—"),
            "บัญชี":   src,
            "Flow":    fmt_money(-(pos or 0), disp, rate),
        })
        if t.get("status") == "closed" and t.get("exit_price"):
            ep = parse(t.get("exit_price",""))
            exit_thb = parse(get_shares(t)) * (ep or 0) * (rate if get_currency(t) == "USD" else 1)
            flows.append({
                "วันที่":   t.get("close_date","—"),
                "ประเภท":  "ปิด Trade",
                "Ticker":  t.get("ticker","—"),
                "บัญชี":   src,
                "Flow":    fmt_money(exit_thb, disp, rate),
            })
    for inv in investments:
        src = inv.get("source_account_name") or inv.get("source_account_id") or "—"
        pos = calc_position_thb(inv.get("entry_price"), get_shares(inv), get_currency(inv), rate)
        flows.append({
            "วันที่":   inv.get("entry_date","—"),
            "ประเภท":  "ซื้อ Investment",
            "Ticker":  inv.get("ticker","—"),
            "บัญชี":   src,
            "Flow":    fmt_money(-(pos or 0), disp, rate),
        })
        if inv.get("status") == "closed" and inv.get("exit_price"):
            ep = parse(inv.get("exit_price",""))
            exit_thb = parse(get_shares(inv)) * (ep or 0) * (rate if get_currency(inv) == "USD" else 1)
            flows.append({
                "วันที่":   inv.get("exit_date","—"),
                "ประเภท":  "ขาย Investment",
                "Ticker":  inv.get("ticker","—"),
                "บัญชี":   src,
                "Flow":    fmt_money(exit_thb, disp, rate),
            })

    if flows:
        flows.sort(key=lambda x: x["วันที่"], reverse=True)
        st.dataframe(flows, use_container_width=True, hide_index=True)
    else:
        st.caption("ยังไม่มีรายการ — จะแสดงเมื่อมี trade/investment ที่เลือก source account")


# -- Page 5: Log --
def page_log(trades: list, investments: list, disp: str, rate: float):
    sym = "฿" if disp == "THB" else "$"

    # -- Activity Log --
    section("Activity Log")
    activity = build_activity_log(investments, trades)
    if activity:
        st.dataframe(activity, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มี activity")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    rows = []
    for t in trades:
        rows.append({
            "Type": "Trade", "Ticker": t.get("ticker","—"),
            "Dir": t.get("direction","—"), "Strategy": t.get("strategy","—"),
            "Entry": t.get("entry_price","—"), "Exit": t.get("exit_price","—"),
            "P&L %": fmt_pct(t.get("pnl_pct")),
            f"P&L ({sym})": fmt_money(t.get("pnl_thb"), disp, rate),
            "W/L": t.get("win_loss", "open" if t.get("status")=="open" else "—"),
            "วันที่": t.get("open_date","—"), "Status": t.get("status","—"),
            "Lesson": t.get("lesson","—"),
        })
    for inv in investments:
        rows.append({
            "Type": "Investment", "Ticker": inv.get("ticker","—"),
            "Dir": "Long", "Strategy": "—",
            "Entry": inv.get("entry_price","—"), "Exit": inv.get("exit_price","—"),
            "P&L %": fmt_pct(inv.get("pnl_pct")),
            f"P&L ({sym})": fmt_money(inv.get("pnl_thb"), disp, rate),
            "W/L": "open" if inv.get("status")=="open" else fmt_pct(inv.get("pnl_pct")),
            "วันที่": inv.get("entry_date","—"), "Status": inv.get("status","—"),
            "Lesson": "—",
        })

    if not rows:
        st.info("ยังไม่มีข้อมูล")
        return

    # -- Filters --
    section("Filters")
    f1, f2, f3 = st.columns(3)
    tf = f1.selectbox("ประเภท", ["ทั้งหมด", "Trade", "Investment"])
    sf = f2.selectbox("Status",  ["ทั้งหมด", "open", "closed"])
    wf = f3.selectbox("W/L",     ["ทั้งหมด", "Win", "Loss", "open"])

    filtered = rows
    if tf != "ทั้งหมด": filtered = [r for r in filtered if r["Type"]   == tf]
    if sf != "ทั้งหมด": filtered = [r for r in filtered if r["Status"] == sf]
    if wf != "ทั้งหมด": filtered = [r for r in filtered if r["W/L"]    == wf]

    # -- Table --
    section(f"History ({len(filtered)} entries)")
    st.dataframe(filtered, use_container_width=True, hide_index=True)

    # -- Export CSV --
    if filtered:
        csv = pd.DataFrame(filtered).to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Export CSV", data=csv,
            file_name=f"timfin_log_{date.today()}.csv",
            mime="text/csv",
        )


# -- Main --
def main():
    # Restore session from URL param (survives page refresh)
    if _use_sb() and "sb_session" not in st.session_state:
        rt = st.query_params.get("_s")
        if rt:
            s = sb_refresh(rt)
            if s and "access_token" in s:
                st.session_state["sb_session"] = s
                if s.get("refresh_token"):
                    st.query_params["_s"] = s["refresh_token"]

    _logged_in = not _use_sb() or is_logged_in()
    render_sidebar(logged_in=_logged_in)

    if not _logged_in:
        page_login()
        return

    try:
        trades      = load_trades()
        investments = load_investments()
        cash        = load_cash()
    except Exception as _e:
        if "401" in str(_e) or "403" in str(_e):
            st.session_state.pop("sb_session", None)
            st.query_params.pop("_s", None)
            st.rerun()
        st.error(f"⚠️ โหลดข้อมูลไม่ได้: {_e}")
        st.stop()

    rate = get_usd_thb()
    _email = (st.session_state.get("sb_session") or {}).get("user", {}).get("email", "")

    # -- Hidden currency radio (JS finds it by label text and clicks it) --
    disp = st.radio("", ["THB", "USD"], horizontal=True,
                    key="display_currency", label_visibility="collapsed")

    # -- Hidden change-password trigger (JS finds button by text and clicks it) --
    _cpw_clicked = st.button("__cpw__", key="_cpw_btn")
    if _cpw_clicked:
        st.session_state["_show_cpw"] = not st.session_state.get("_show_cpw", False)
        st.rerun()

    # -- Inject navbar (HTML + CSS + JS) into parent document via window.parent --
    _components.html(
        _inject_navbar(
            f'data:image/png;base64,{_LOGO_B64}' if _LOGO_B64 else "",
            _email, st.session_state.get("display_currency", "THB"), rate,
        ),
        height=0, scrolling=False,
    )

    # Spacer so content starts below fixed navbar
    st.markdown('<div style="height:58px;margin:0;padding:0;line-height:0;font-size:0"></div>',
                unsafe_allow_html=True)

    # -- Change-password panel --
    if st.session_state.get("_show_cpw"):
        with st.container(border=True):
            st.subheader("🔑 เปลี่ยนรหัสผ่าน")
            with st.form("form_change_pw"):
                _np1 = st.text_input("รหัสผ่านใหม่", type="password", placeholder="อย่างน้อย 8 ตัวอักษร")
                _np2 = st.text_input("ยืนยันรหัสผ่านใหม่", type="password")
                _cpw_submit = st.form_submit_button("✅ เปลี่ยนรหัสผ่าน")
                if _cpw_submit:
                    if len(_np1) < 8:
                        st.error("รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")
                    elif _np1 != _np2:
                        st.error("รหัสผ่านทั้งสองไม่ตรงกัน")
                    else:
                        _ok, _err = sb_update_password(_np1)
                        if _ok:
                            st.success("✅ เปลี่ยนรหัสผ่านสำเร็จ!")
                            st.session_state["_show_cpw"] = False
                            st.rerun()
                        else:
                            st.error(f"เปลี่ยนไม่สำเร็จ: {_err}")
            if st.button("ยกเลิก", key="_cpw_cancel"):
                st.session_state["_show_cpw"] = False
                st.rerun()

    # -- Tabs --
    _tabs = st.tabs(["📊 Overview", "💼 Investment", "📈 Trade", "💵 Cash", "📓 Log"])
    with _tabs[0]: page_overview(trades, investments, cash, disp, rate)
    with _tabs[1]: page_investment(investments, trades, cash, disp, rate)
    with _tabs[2]: page_trade(trades, cash, disp, rate)
    with _tabs[3]: page_cash(trades, investments, cash, disp, rate)
    with _tabs[4]: page_log(trades, investments, disp, rate)


main()
