"""
Tim.fin Personal OS — Investment & Trade Dashboard
"""
import base64 as _b64
import html
import io
import json
import math
import os
import re
from datetime import date

import pandas as pd
import requests as _req
import streamlit as st
import streamlit.components.v1 as _components
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

# -- CSS --
# Fonts come from .streamlit/config.toml ([[theme.fontFaces]], files in static/fonts),
# so Streamlit applies them everywhere including the canvas-drawn dataframes. Forcing
# a font-family on every element here would also hit Streamlit's icon font and turn
# the expander arrows into the literal word "keyboard_arrow_down".
st.markdown("""<style>
/* Tokens — keep in sync with .streamlit/config.toml */
:root {
  --it-bg:      #0D1012;
  --it-card:    #14181B;
  --it-raise:   #1A1F23;
  --it-border:  #262C31;
  --it-text:    #E9E6DF;
  --it-muted:   #8B9196;
  --it-faint:   #5B6268;
  --it-accent:  #D9A441;
  --it-accent-ink: #1A1408;
  --it-green:   #3DBE7F;
  --it-red:     #EF5F55;
  --it-mono:    'IBM Plex Mono', ui-monospace, monospace;
}

/* Base */
#MainMenu, footer { visibility: hidden; }
[data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }
/* No sidebar. It only repeated what the navbar already shows — logo, app name,
   email, logout — and once collapsed it could not be reopened, because the
   reopen control lives in stHeader and this app hides that. */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] { display: none !important; }

.stApp, [data-testid="stMain"] { background: var(--it-bg) !important; }
.main .block-container { max-width: 1280px; padding-top: 1.5rem; }

/* Section labels */
.section-label {
    font-size: 12px; font-weight: 600; letter-spacing: 0.05em;
    text-transform: uppercase; color: var(--it-muted);
    margin: .35rem 0 .6rem;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: var(--it-card) !important;
    border: 1px solid var(--it-border) !important;
    border-radius: 8px !important;
    padding: 14px 16px !important;
}
[data-testid="stMetricValue"] {
    font-family: var(--it-mono) !important;
    font-size: 1.45rem !important;
    font-weight: 600 !important;
    color: var(--it-text) !important;
    font-variant-numeric: tabular-nums !important;
    letter-spacing: -0.01em !important;
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {
    font-size: 12px !important;
    color: var(--it-muted) !important;
    font-weight: 500 !important;
}
[data-testid="stMetricDelta"] { font-family: var(--it-mono) !important; }
[data-testid="stMetricValue"] * { font-family: var(--it-mono) !important; }

/* Radios as a segmented control: same widget and value, drawn like the THB/USD toggle.
   Two selector sets because Streamlit changed the radio markup between versions:
   role=radiogroup + label[data-baseweb=radio] (<=1.45) and stRadioGroup/stRadioOption (newer). */
[data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"],
[data-testid="stMain"] [data-testid="stRadioGroup"] {
    display: inline-flex !important; flex-wrap: wrap; gap: 2px !important;
    border: 1px solid var(--it-border); border-radius: 6px; padding: 2px;
}
[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"],
[data-testid="stMain"] [data-testid="stRadioOption"] {
    margin: 0 !important; padding: 4px 12px !important; border-radius: 4px; cursor: pointer;
    transition: background .15s;
}
[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child,
[data-testid="stMain"] [data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) { display: none !important; }
[data-testid="stMain"] [data-testid="stRadio"] label p { color: var(--it-muted) !important; font-size: 13px !important; }
[data-testid="stMain"] [data-testid="stRadio"] label:has(input:checked) { background: var(--it-raise); }
[data-testid="stMain"] [data-testid="stRadio"] label:has(input:checked) p,
[data-testid="stMain"] [data-testid="stRadio"] label:hover p { color: var(--it-text) !important; }

/* Expanders */
[data-testid="stExpander"] details,
[data-testid="stExpander"] {
    background: var(--it-card) !important;
    border-color: var(--it-border) !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] { margin-bottom: .5rem !important; }
[data-testid="stExpander"] summary { padding: 10px 16px !important; font-weight: 500 !important; }
[data-testid="stExpander"] summary:hover { color: var(--it-text) !important; }

/* Inputs: the visible box is BaseWeb's outer wrapper (data-baseweb=input/textarea),
   which takes the theme's secondary colour; the inner base-input and the password
   reveal button sit on top of it, so they go transparent and the wrapper is styled */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"],
[data-testid="stSelectbox"] .react-aria-ComboBox [role="group"],
[data-testid="stMultiSelect"] .react-aria-ComboBox [role="group"] {
    background: var(--it-bg) !important;
    border-color: var(--it-border) !important;
    border-radius: 6px !important;
}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within,
[data-baseweb="select"] > div:focus-within,
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stTextAreaRootElement"]:focus-within,
.react-aria-ComboBox [role="group"]:focus-within { border-color: var(--it-accent) !important; }
[data-baseweb="base-input"], [data-baseweb="base-input"] input, [data-baseweb="base-input"] textarea,
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea, [data-baseweb="input"] button {
    background: transparent !important;
    color: var(--it-text) !important;
}
[data-testid="stWidgetLabel"] p { color: var(--it-muted) !important; font-size: 13px !important; }

/* Buttons: one filled primary (form submit), everything else outlined */
[data-testid="stFormSubmitButton"] button {
    background: var(--it-accent) !important;
    color: var(--it-accent-ink) !important;
    border: 1px solid var(--it-accent) !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    width: 100%;
}
[data-testid="stFormSubmitButton"] button p { color: var(--it-accent-ink) !important; }
[data-testid="stFormSubmitButton"] button:hover { filter: brightness(1.07); }
[data-testid="stMain"] [data-testid="stButton"] button,
[data-testid="stMain"] [data-testid="stDownloadButton"] button,
[role="dialog"] [data-testid="stButton"] button {
    background: var(--it-card) !important;
    border: 1px solid var(--it-border) !important;
    color: var(--it-text) !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    transition: background .15s, border-color .15s !important;
}
[data-testid="stMain"] [data-testid="stButton"] button:hover,
[data-testid="stMain"] [data-testid="stDownloadButton"] button:hover,
[role="dialog"] [data-testid="stButton"] button:hover {
    background: var(--it-raise) !important;
    border-color: var(--it-faint) !important;
}
[data-testid="stMain"] [data-testid="stButton"] button:disabled { opacity: .45; }

/* Dataframes, alerts, captions, dividers */
[data-testid="stDataFrame"] { border: 1px solid var(--it-border) !important; border-radius: 8px !important; overflow: hidden; }
[data-testid="stAlert"] { border-radius: 8px !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--it-muted) !important; }
[data-baseweb="tag"] {
    background: rgba(217,164,65,0.14) !important;
    border: 1px solid rgba(217,164,65,0.3) !important;
    border-radius: 4px !important;
    color: var(--it-accent) !important;
}
hr { border-color: var(--it-border) !important; }
:focus-visible { outline: 2px solid var(--it-accent) !important; outline-offset: 2px; }

/* Allocation legend list (beside the donut) */
.al-list { display: grid; grid-template-columns: 1fr; gap: 2px; max-height: 236px; max-width: 480px; overflow-y: auto; padding-right: 4px; }
.al-it { display: grid; grid-template-columns: 10px 1fr auto 64px; gap: 10px; align-items: center;
         padding: 5px 0; border-bottom: 1px solid var(--it-border); font-size: 14px; }
.al-it:last-child { border-bottom: 0; }
.al-sw { width: 10px; height: 10px; border-radius: 2px; }
.al-tk { font-weight: 600; color: var(--it-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.al-w, .al-p { font-family: var(--it-mono); font-size: 13px; text-align: right; font-variant-numeric: tabular-nums; }
.al-w { color: var(--it-muted); }

/* Position drawer (opens under the holdings table for the selected row) */
.pd-head { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.pd-tk { font-size: 20px; font-weight: 700; color: var(--it-text); }
.pd-sub { font-family: var(--it-mono); font-size: 13px; color: var(--it-muted); }
.pd-pill { font-family: var(--it-mono); font-size: 13px; padding: 2px 8px; border-radius: 4px; }
.pd-facts { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--it-border);
            border: 1px solid var(--it-border); border-radius: 6px; overflow: hidden; margin-bottom: 14px; }
.pd-facts > div { background: var(--it-card); padding: 10px 12px; min-width: 0; }
.pd-facts .l { font-size: 12px; color: var(--it-muted); }
.pd-facts .v { font-family: var(--it-mono); font-size: 15px; color: var(--it-text); margin-top: 2px;
               white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 640px) { .pd-facts { grid-template-columns: 1fr 1fr; } }
.st-key-pos_drawer { background: var(--it-raise) !important; }
.st-key-pos_drawer [data-testid="stButton"] button { min-height: 0 !important; }
[data-testid="stMain"] [class*="st-key-sellbtn_"] button,
[role="dialog"] [class*="st-key-sellbtn_"] button {
    color: var(--it-red) !important; border-color: rgba(239,95,85,.35) !important; background: rgba(239,95,85,.10) !important; }
[data-testid="stMain"] [class*="st-key-sellbtn_"] button p,
[role="dialog"] [class*="st-key-sellbtn_"] button p { color: var(--it-red) !important; }
/* position popup */
[role="dialog"] { background: var(--it-card) !important; border: 1px solid var(--it-border) !important; }
[role="dialog"] .pd-facts > div { background: var(--it-raise); }

/* Hide the native Streamlit tab-list — navbar replaces it */
[data-baseweb="tab-list"] { display: none !important; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
</style>""", unsafe_allow_html=True)

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


# 16px line icons for the navbar (stroke follows the button's text colour)
_ICON_EYE = ('<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4">'
             '<path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5Z"/><circle cx="8" cy="8" r="2"/></svg>')
_ICON_EYE_OFF = ('<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4">'
                 '<path d="M2 2l12 12M6.6 3.2A7 7 0 0 1 8 3c4.5 0 7 5 7 5a12 12 0 0 1-2 2.6'
                 'M10 12.6A6 6 0 0 1 8 13c-4.5 0-7-5-7-5a12 12 0 0 1 2.6-3"/></svg>')
_ICON_USER = ('<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4">'
              '<circle cx="8" cy="5.5" r="2.8"/><path d="M2.5 14c.8-2.8 3-4.2 5.5-4.2s4.7 1.4 5.5 4.2"/></svg>')


def _inject_navbar(logo_src: str, email: str, curr: str, rate: float,
                   hide_amt: bool = False) -> str:
    """Inject navbar HTML+CSS+JS into the parent page via window.parent (components.html iframe)."""
    thb_cls = "on" if curr == "THB" else ""
    usd_cls = "on" if curr == "USD" else ""
    logo_tag = f'<img src="{logo_src}" class="tfin-brand-img" alt="">' if logo_src else ""
    em_short = (email[:22] + "…") if len(email) > 24 else email
    rate_str = f"{rate:.2f}"

    nav_html = (
        f'<div id="tfin-nav">'
        f'<div class="tfin-brand">{logo_tag}<span class="tfin-brand-name">Tim.fin OS</span></div>'
        f'<div class="tfin-nav-tabs">'
        f'<button class="tfin-nt on" id="tnt0">Overview</button>'
        f'<button class="tfin-nt" id="tnt1">Investment</button>'
        f'<button class="tfin-nt" id="tnt2">Trade</button>'
        f'<button class="tfin-nt" id="tnt3">Cash</button>'
        f'<button class="tfin-nt" id="tnt4">Log</button>'
        f'</div>'
        f'<div class="tfin-nav-right">'
        f'<span class="tfin-rate">฿{rate_str}/USD</span>'
        f'<div class="tfin-curr-wrap">'
        f'<button class="tfin-cb {thb_cls}" id="cb-thb">THB</button>'
        f'<button class="tfin-cb {usd_cls}" id="cb-usd">USD</button>'
        f'</div>'
        f'<button class="tfin-eye{" off" if hide_amt else ""}" id="tfin-eye" '
        f'title="{"แสดงยอดเงิน" if hide_amt else "ซ่อนยอดเงิน"}">'
        f'{_ICON_EYE_OFF if hide_amt else _ICON_EYE}</button>'
        f'<div class="tfin-aw">'
        f'<button class="tfin-ab" id="tfin-acct-btn" title="{email}">{_ICON_USER}</button>'
        f'<div class="tfin-dd" id="tfin-acct-dd">'
        f'<div class="tfin-dd-email">{em_short}</div>'
        f'<hr class="tfin-dd-hr">'
        f'<button class="tfin-ddbtn red" id="tfin-logout-btn">ออกจากระบบ</button>'
        f'</div></div></div></div>'
    )

    nav_css = (
        "#tfin-nav{position:fixed!important;top:0!important;left:0!important;right:0!important;"
        "height:56px!important;background:#0D1012!important;"
        "border-bottom:1px solid #262C31!important;"
        "display:flex!important;align-items:center!important;justify-content:space-between!important;"
        "padding:0 20px!important;z-index:2147483647!important;"
        "font-family:'IBM Plex Sans Thai',sans-serif!important;gap:16px!important;}"
        ".tfin-brand{display:flex;align-items:center;gap:9px;flex-shrink:0;}"
        ".tfin-brand-img{height:28px;width:28px;border-radius:6px;object-fit:cover;}"
        ".tfin-brand-name{font-size:15px;font-weight:700;color:#E9E6DF;}"
        ".tfin-nav-tabs{display:flex;align-items:center;gap:2px;flex:1;justify-content:flex-start;}"
        ".tfin-nt{background:transparent;border:none;cursor:pointer;color:#8B9196;"
        "font-size:14px;font-weight:500;padding:7px 12px;border-radius:6px;"
        "transition:color .15s,background .15s;white-space:nowrap;font-family:inherit;line-height:1.2;}"
        ".tfin-nt:hover{color:#E9E6DF;}"
        ".tfin-nt.on{background:#1A1F23;color:#E9E6DF;}"
        ".tfin-nav-right{display:flex;align-items:center;gap:8px;flex-shrink:0;}"
        ".tfin-rate{font-size:12px;color:#5B6268;font-family:'IBM Plex Mono',monospace;margin-right:4px;}"
        ".tfin-curr-wrap{display:flex;border:1px solid #262C31;border-radius:6px;padding:2px;gap:2px;}"
        ".tfin-cb{background:transparent;border:none;cursor:pointer;font-size:12px;font-weight:500;"
        "padding:4px 10px;border-radius:4px;transition:color .15s,background .15s;color:#8B9196;"
        "font-family:'IBM Plex Mono',monospace;}"
        ".tfin-cb:hover{color:#E9E6DF;}"
        ".tfin-cb.on{background:#1A1F23;color:#E9E6DF;}"
        ".tfin-eye,.tfin-ab{background:transparent;border:1px solid #262C31;border-radius:6px;cursor:pointer;"
        "width:32px;height:32px;padding:0;color:#8B9196;display:flex;align-items:center;justify-content:center;"
        "transition:color .15s,border-color .15s;flex-shrink:0;}"
        ".tfin-eye svg,.tfin-ab svg{width:16px;height:16px;display:block;}"
        ".tfin-eye:hover,.tfin-ab:hover{color:#E9E6DF;border-color:#5B6268;}"
        ".tfin-eye.off{color:#D9A441;border-color:rgba(217,164,65,.45);}"
        ".tfin-aw{position:relative;}"
        ".tfin-dd{display:none;position:fixed;top:56px;right:20px;min-width:200px;"
        "background:#14181B;border:1px solid #262C31;border-radius:8px;"
        "padding:8px;box-shadow:0 12px 32px rgba(0,0,0,.5);z-index:2147483646;}"
        ".tfin-dd-email{font-size:12px;color:#8B9196;padding:4px 8px 6px;word-break:break-all;}"
        ".tfin-dd-hr{border:none;border-top:1px solid #262C31;margin:4px 0;}"
        ".tfin-ddbtn{display:block;width:100%;text-align:left;background:transparent;border:none;"
        "color:#E9E6DF;font-size:13px;padding:8px 9px;border-radius:6px;"
        "cursor:pointer;font-family:inherit;transition:background .12s;}"
        ".tfin-ddbtn:hover{background:#1A1F23;}"
        ".tfin-ddbtn.red{color:#EF5F55;}"
        "[data-baseweb='tab-list']{display:none!important;}"
        # ---- Narrow screens. Streamlit already stacks st.columns on its own at 640px,
        # so the navbar is the only thing that breaks: below its minimum width the
        # currency toggle, privacy toggle and account button end up past the right edge
        # and cannot be tapped. That minimum grows every time a control is added to the
        # bar, so this sits well clear of the measured edge rather than on it. ANY new
        # control in tfin-nav-right means re-measuring this number. Up to here the 5 tabs
        # move to a bottom bar and the top row keeps identity + currency + privacy +
        # account. Pure CSS, DOM order untouched, so the navbar's click delegation
        # behaves as it does on desktop.
        "@media(max-width:960px){"
        # no backdrop-filter anywhere in the bar: it would make #tfin-nav a containing
        # block for fixed-position descendants and pin the tab bar to the navbar
        "#tfin-nav{height:52px!important;padding:0 12px!important;gap:8px!important;}"
        ".tfin-brand-name{display:none!important;}"
        ".tfin-brand-img{height:26px!important;width:26px!important;}"
        ".tfin-rate{font-size:11px!important;white-space:nowrap;}"
        ".tfin-cb{padding:7px 11px!important;}"
        ".tfin-eye,.tfin-ab{width:38px!important;height:38px!important;}"
        ".tfin-dd{top:54px!important;right:8px!important;}"
        ".tfin-nav-tabs{position:fixed!important;left:0!important;right:0!important;"
        "bottom:0!important;top:auto!important;height:56px!important;"
        "background:#0D1012!important;border-top:1px solid #262C31!important;"
        "justify-content:space-around!important;gap:2px!important;"
        "padding:0 4px env(safe-area-inset-bottom,0px)!important;z-index:2147483647!important;}"
        ".tfin-nt{flex:1 1 0!important;min-width:0!important;min-height:44px!important;"
        "font-size:12px!important;padding:4px 2px!important;"
        "display:flex!important;align-items:center!important;justify-content:center!important;"
        "overflow:hidden!important;text-overflow:ellipsis!important;}"
        # keep the last rows clear of the bottom bar
        "[data-testid='stMain']{padding-bottom:68px!important;}"
        "}"
        # iOS Safari zooms the whole page in whenever a focused field is under 16px,
        # and never zooms back out. Touch widths only.
        "@media(max-width:640px){"
        "input,textarea,select{font-size:16px!important;}"
        "[data-testid='stMain'] button{min-height:44px!important;}"
        "}"
    )

    # Use json.dumps to safely embed strings in JS
    nav_html_js = json.dumps(nav_html)
    nav_css_js = json.dumps(nav_css)
    thb_js = "true" if curr == "THB" else "false"
    usd_js = "true" if curr == "USD" else "false"
    hide_js = "true" if hide_amt else "false"
    rate_js = json.dumps(f"฿{rate_str}/USD")
    eye_on_js, eye_off_js = json.dumps(_ICON_EYE), json.dumps(_ICON_EYE_OFF)

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
  var eye = doc.getElementById('tfin-eye');
  if(eye){{
    eye.classList.toggle('off', {hide_js});
    eye.innerHTML = {hide_js} ? {eye_off_js} : {eye_on_js};
    eye.title = {hide_js} ? 'แสดงยอดเงิน' : 'ซ่อนยอดเงิน';
  }}

  /* 4 — Hide Streamlit helper widgets (inline setProperty beats all CSS rules) */
  function hide(el){{ if(el) el.style.setProperty('display','none','important'); }}
  function hideWidgets(){{
    /* radio — the two that only exist to be driven by the navbar buttons */
    doc.querySelectorAll('[data-testid="stRadio"]').forEach(function(el){{
      var t = el.textContent||'';
      if(t.includes('THB') || t.includes('ซ่อนยอด')) hide(el);
    }});
    /* hide any stRadio that appears before the tabs wrapper */
    var stTabsEl=doc.querySelector('[data-testid="stTabs"]');
    if(stTabsEl){{
      doc.querySelectorAll('[data-testid="stRadio"]').forEach(function(w){{
        if(stTabsEl.compareDocumentPosition(w)&Node.DOCUMENT_POSITION_PRECEDING) hide(w);
      }});
    }}
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

  /* Privacy toggle — drives the hidden "แสดงยอด/ซ่อนยอด" radio, same trick as setCurr */
  function toggleEye(){{
    var b = doc.getElementById('tfin-eye');
    var want = (b && b.classList.contains('off')) ? 'แสดงยอด' : 'ซ่อนยอด';
    var hit = false;
    doc.querySelectorAll('[data-testid="stRadio"] label').forEach(function(l){{
      if((l.textContent||'').trim()===want){{ l.click(); hit = true; }}
    }});
    /* optimistic flip so the icon responds before Streamlit finishes the rerun */
    if(hit && b){{
      var off = want === 'ซ่อนยอด';
      b.classList.toggle('off', off);
      b.innerHTML = off ? {eye_off_js} : {eye_on_js};
      b.title = off ? 'แสดงยอดเงิน' : 'ซ่อนยอดเงิน';
    }}
  }}

  function toggleAcct(){{
    var dd=doc.getElementById('tfin-acct-dd');
    if(dd) dd.style.display=dd.style.display==='block'?'none':'block';
  }}

  function doLogout(){{
    /* skip our own navbar button — it sits first in the DOM and would self-click */
    var btns=doc.querySelectorAll('button');
    for(var i=0;i<btns.length;i++){{
      if(btns[i].closest && btns[i].closest('#tfin-nav')) continue;
      if((btns[i].textContent||'').includes('ออกจากระบบ')){{ btns[i].click(); return; }}
    }}
  }}

  function syncTabs(){{
    var tabs=getStTabs();
    tabs.forEach(function(t,i){{
      var b=doc.getElementById('tnt'+i);
      if(b) b.classList.toggle('on', t.getAttribute('aria-selected')==='true');
    }});
  }}

  /* 6 — Event delegation on navbar (single listener, capture phase).
     Re-attach on every load: the navbar element lives in the parent document and
     survives reruns, but this iframe's JS context does not — a listener from a
     torn-down iframe stays bound yet dead, so a once-only guard kills the navbar
     after the first rerun that changes its HTML. Swap the old handler for a live one. */
  var nav=doc.getElementById('tfin-nav');
  if(nav){{
    if(nav._tfinH){{ try{{ nav.removeEventListener('click', nav._tfinH, true); }}catch(e){{}} }}
    nav._tfinH = function(e){{
      var tgt=e.target;
      var tntBtn=tgt.closest && tgt.closest('[id^="tnt"]');
      if(tntBtn){{ var idx=parseInt(tntBtn.id.substring(3)); if(!isNaN(idx)) goTab(idx); e.stopPropagation(); return; }}
      if(tgt.closest && tgt.closest('#cb-thb')){{ setCurr('THB'); e.stopPropagation(); return; }}
      if(tgt.closest && tgt.closest('#cb-usd')){{ setCurr('USD'); e.stopPropagation(); return; }}
      if(tgt.closest && tgt.closest('#tfin-eye')){{ toggleEye(); e.stopPropagation(); return; }}
      if(tgt.closest && tgt.closest('#tfin-acct-btn')){{ e.stopPropagation(); toggleAcct(); return; }}
      if(tgt.closest && tgt.closest('#tfin-logout-btn')){{ doLogout(); e.stopPropagation(); return; }}
    }};
    nav.addEventListener('click', nav._tfinH, true);
  }}

  /* Close dropdown on outside click — same re-attach pattern */
  if(doc._tfinOuterH){{ try{{ doc.removeEventListener('click', doc._tfinOuterH, false); }}catch(e){{}} }}
  doc._tfinOuterH = function(e){{
    if(!(e.target.closest && e.target.closest('.tfin-aw'))){{
      var dd=doc.getElementById('tfin-acct-dd'); if(dd) dd.style.display='none';
    }}
  }};
  doc.addEventListener('click', doc._tfinOuterH, false);

  /* 7 — Fullscreen detection: hide navbar when any stFullScreenFrame covers viewport */
  function syncNavVisibility(){{
    var nav = doc.getElementById('tfin-nav');
    if(!nav) return;
    var vw = window.parent.innerWidth || 900;
    var vh = window.parent.innerHeight || 700;
    var frames = doc.querySelectorAll('[data-testid="stFullScreenFrame"]');
    var isFS = false;
    for(var i=0; i<frames.length; i++){{
      try{{
        var r = frames[i].getBoundingClientRect();
        if(r.width > vw * 0.9 && r.height > vh * 0.9){{ isFS = true; break; }}
      }}catch(e){{}}
    }}
    nav.style.setProperty('display', isFS ? 'none' : 'flex', 'important');
  }}

  /* 8 — MutationObserver: re-hide widgets + sync tabs + check fullscreen on every rerender */
  if(!window._tfinObserving){{
    new MutationObserver(function(){{ hideWidgets(); syncTabs(); syncNavVisibility(); }})
      .observe(doc.body, {{subtree:true, childList:true, attributes:true, attributeFilter:['aria-selected','style','class']}});
    window._tfinObserving = true;
  }}

  hideWidgets(); syncTabs(); syncNavVisibility();
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
    return f"{acc['name']} ({acc['currency']} {money(acc['amount'], sym)})"

def source_selector(cash: list, form_key: str) -> tuple:
    """Returns (selectbox_index, other_name_input, other_currency_input) inside a form."""
    ids     = [a["id"] for a in cash] + ["other"]
    labels  = [acc_label(a) for a in cash] + ["Other Cash (ระบุเอง)"]
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

def trade_leverage(item: dict) -> float:
    """1 for anything recorded before leverage existed, or entered below 1."""
    lev = parse(str(item.get("leverage", 1)))
    return lev if lev and math.isfinite(lev) and lev >= 1 else 1.0


def settle_thb(item: dict, shares_closed: float, pnl_thb, rate: float) -> float:
    """Cash that goes back to an account when `shares_closed` of a trade is closed:
    the margin that slice tied up, plus its P&L.

    At 1x the margin is the full cost, so this reproduces the old proceeds formula
    in both directions — Long: exit value; Short: 2 x cost - exit value — to the baht.
    Above 1x it returns margin + P&L only. Crediting the notional instead is what
    dropped ฿154,897 into an account on a leveraged Binance future whose real margin
    was a fraction of that.
    """
    cost = shares_closed * (parse(item.get("entry_price")) or 0) \
        * (rate if get_currency(item) == "USD" else 1)
    return cost / trade_leverage(item) + (pnl_thb or 0)


def _trim_pct(sh: dict):
    """Price return of one partial sell, from what was stored at the time.

    The "thb" field is cost + P&L for both directions (a Short stores
    2 x cost - exit), so cost = thb - pnl. Reading the trade's current entry
    price instead would be wrong once a later buy-more has moved the average.
    """
    thb, pnl = sh.get("thb"), sh.get("pnl_thb")
    if thb is None or pnl is None or thb - pnl <= 0:
        return None
    return round(pnl / (thb - pnl) * 100, 2)


def position_value_thb(item: dict, price, rate: float) -> float:
    """What an open position is worth to its owner at `price`: the capital it tied
    up plus its unrealised P&L — the same thing settle_thb() would return if it
    were closed now.

    For an unleveraged Long that is just market value, so investments read as
    before. It differs where market value was wrong to begin with: a 10x trade
    counts its margin, not the notional (cash only fell by the margin, so counting
    the notional overstated net worth by the borrowed 90%); and a Short now falls
    in value as price rises, where it used to rise with it.
    Falls back to entry price, i.e. zero P&L, when no live price is available.
    """
    s = parse(get_shares(item)) or 0
    p = price if price is not None else parse(item.get("entry_price"))
    if p is None or not s:
        return 0.0
    pnl = calc_pnl_thb(item.get("entry_price"), p, str(s), get_currency(item),
                       rate, item.get("direction", "Long")) or 0
    return settle_thb(item, s, pnl, rate)


def auto_rr(entry, sl, tp) -> str:
    e, s, t = parse(entry), parse(sl), parse(tp)
    if None in (e, s, t) or abs(e - s) == 0: return "—"
    return f"1:{abs(t-e)/abs(e-s):.1f}"

def fmt_pct(val) -> str:
    if not isinstance(val, (int, float)): return "—"
    return f"{'+' if val>=0 else ''}{val:.2f}%"

MASK = "•••••"


def hidden_amounts() -> bool:
    """Privacy toggle: blank out anything that reveals portfolio size.

    Masks absolute money only. Percentages, prices, tickers and share counts stay
    readable so the app is still demonstrable with the amounts switched off.
    """
    return st.session_state.get("amount_visibility") == "ซ่อนยอด"


def money(val: float | None, sym: str = "฿", dp: int = 0) -> str:
    """Pre-converted amount with its own symbol — for the spots that do not go
    through fmt_money(). Never use it for the FX rate: that is public, not wealth."""
    if val is None: return "—"
    if hidden_amounts(): return MASK
    return f"{sym}{val:,.{dp}f}"


def fmt_money(val_thb: float | None, disp: str, rate: float, sign: bool = True) -> str:
    if val_thb is None: return "—"
    if hidden_amounts(): return MASK
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
# categorical slices — kept clear of the green/red that mean profit/loss elsewhere
ALLOC_COLORS = ["#D9A441", "#6E8FB5", "#8F7AB8", "#5AA39A", "#C0855A", "#9AA3AD", "#B5677A",
                "#A3A15A", "#6FB0C8", "#C9B48A", "#7E9C6B", "#B08FA6", "#8AA7A0", "#C7866B"]

CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#E9E6DF", size=13, family="IBM Plex Sans Thai, sans-serif"),
    hoverlabel=dict(font=dict(family="IBM Plex Sans Thai, sans-serif")),
    showlegend=False,
    margin=dict(t=32, b=8, l=8, r=8),
    xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#8B9196")),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
               tickfont=dict(size=11, color="#6B7176"), zeroline=True,
               zerolinecolor="rgba(255,255,255,0.15)"),
)

def _pnl_tint(pct) -> str:
    """Tile colour for a P&L %: surface grey pulled toward green or red with the size
    of the move (saturates around ±20%). None (cash) stays neutral."""
    base = (0x1A, 0x1F, 0x23)
    if pct is None or not math.isfinite(pct):
        return "#2A3035"
    tgt = (0x3D, 0xBE, 0x7F) if pct >= 0 else (0xEF, 0x5F, 0x55)
    k = (min(abs(pct) * 3.2, 62) + 12) / 100
    return "#" + "".join(f"{round(b + (t - b) * k):02X}" for b, t in zip(base, tgt))


def allocation_treemap(labels, vals_thb, pcts, disp, rate, height=360):
    """Holdings as boxes: area = share of money, colour = P&L %. Reads both at once,
    which a pie cannot do once there are more than a handful of slices."""
    vals = [to_display(v, disp, rate) for v in vals_thb]
    total = sum(vals) or 1
    hide = hidden_amounts()
    pct_txt = ["" if p is None else fmt_pct(p) for p in pcts]
    hover = [f"{l}<br>{v / total * 100:.1f}% ของพอร์ต"
             + ("" if hide else f"<br>{fmt_money(vt, disp, rate, sign=False)}")
             + (f"<br>P&L {t}" if t else "")
             for l, v, vt, t in zip(labels, vals, vals_thb, pct_txt)]
    fig = go.Figure(go.Treemap(
        labels=labels, parents=[""] * len(labels), values=vals, sort=True,
        customdata=pct_txt, hovertext=hover, hoverinfo="text",
        texttemplate="<b>%{label}</b><br>%{percentRoot:.1%}<br>%{customdata}",
        textfont=dict(family="IBM Plex Sans Thai, sans-serif", size=14, color="#E9E6DF"),
        textposition="top left",
        marker=dict(colors=[_pnl_tint(p) for p in pcts],
                    line=dict(color="#0D1012", width=3), pad=dict(t=8, l=8, r=8, b=8)),
        tiling=dict(pad=0), pathbar=dict(visible=False),
    ))
    fig.update_layout(**{**CHART_LAYOUT, "height": height,
                         "margin": dict(t=4, b=4, l=0, r=0)})
    return fig


def allocation_panel(labels, vals_thb, pcts, disp, rate, key: str) -> None:
    """Donut with the total in the middle and a legend list beside it: ticker, share of
    the portfolio and P&L %. Slice labels around the ring collide once there are more
    than a few holdings, so the reading happens in the list instead."""
    view = st.radio("มุมมอง", ["Pie", "Treemap"], horizontal=True,
                    key=f"alloc_view_{key}", label_visibility="collapsed")
    if view == "Treemap":
        st.plotly_chart(allocation_treemap(labels, vals_thb, pcts, disp, rate, height=320),
                        use_container_width=True, key=f"alloc_tm_{key}")
        return
    total = sum(vals_thb) or 1
    order = sorted(range(len(labels)), key=lambda i: -vals_thb[i])
    cols = [ALLOC_COLORS[n % len(ALLOC_COLORS)] for n in range(len(order))]
    # a name on every slice collides once there are a dozen holdings; label the ones
    # at 3%+ and leave the slivers to the list beside the chart
    shares = [vals_thb[i] / total * 100 for i in order]
    names = [f"{labels[i]}<br>{sh:.0f}%" if sh >= 3 else "" for i, sh in zip(order, shares)]
    fig = go.Figure(go.Pie(
        labels=[labels[i] for i in order], values=[to_display(vals_thb[i], disp, rate) for i in order],
        hole=0.6, sort=False, direction="clockwise",
        text=names, textinfo="text", textposition="outside",
        textfont=dict(size=11, color="#C9C6BF", family="IBM Plex Sans Thai, sans-serif"),
        marker=dict(colors=cols, line=dict(color="#0D1012", width=2)),
        hovertemplate="%{label}<br>%{percent}<extra></extra>", automargin=True,
    ))
    fig.update_layout(**{**CHART_LAYOUT, "height": 300, "margin": dict(t=30, b=30, l=50, r=50),
        "annotations": [dict(text=("รวม<br><b>" + fmt_money(total, disp, rate, sign=False) + "</b>"),
                             x=0.5, y=0.5, showarrow=False,
                             font=dict(size=13, color="#E9E6DF", family="IBM Plex Mono, monospace"))]})
    rows = []
    for n, i in enumerate(order):
        p = pcts[i]
        pc = "#8B9196" if p is None else ("#3DBE7F" if p >= 0 else "#EF5F55")
        rows.append(
            f"<div class='al-it'><span class='al-sw' style='background:{cols[n]}'></span>"
            f"<span class='al-tk'>{html.escape(str(labels[i]))}</span>"
            f"<span class='al-w'>{vals_thb[i] / total * 100:.1f}%</span>"
            f"<span class='al-p' style='color:{pc}'>{'' if p is None else fmt_pct(p)}</span></div>")
    c1, c2 = st.columns([1, 1], vertical_alignment="center")
    with c1:
        st.plotly_chart(fig, use_container_width=True, key=f"alloc_{key}")
    with c2:
        st.markdown("<div class='al-list'>" + "".join(rows) + "</div>", unsafe_allow_html=True)


def allocation_pie(labels, vals_thb, disp, rate, title, height=320):
    vals = [to_display(v, disp, rate) for v in vals_thb]
    total = sum(v for v in vals if v)
    colors = ALLOC_COLORS
    fig = go.Figure(go.Pie(
        labels=labels, values=vals, hole=0.45,
        textinfo="label+percent", textfont=dict(size=12, color="#E9E6DF"),
        marker=dict(colors=colors[:len(labels)],
                    line=dict(color="#0D1012", width=2)),
    ))
    sym = "฿" if disp == "THB" else "$"
    fig.update_layout(**{**CHART_LAYOUT,
        "title": dict(text=title, font=dict(size=14, color="#8B9196"), x=0),
        "height": height, "showlegend": True,
        "legend": dict(font=dict(color="#8B9196", size=11), orientation="v"),
        "annotations": [dict(text=money(total, sym), x=0.5, y=0.5,
                              font=dict(size=15, color="#E9E6DF"), showarrow=False)],
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
                v += position_value_thb(item, float(row[t]), rate)
        port_vals.append(to_display(v, disp, rate))

    dates = list(combined.index)
    pct = (port_vals[-1] - port_vals[0]) / port_vals[0] * 100 if port_vals[0] else 0
    color_pct = "#3DBE7F" if pct >= 0 else "#EF5F55"
    sym = "฿" if disp == "THB" else "$"
    sign = "+" if pct >= 0 else ""

    fig = go.Figure(go.Scatter(
        x=dates, y=port_vals, mode="lines",
        line=dict(color="#D9A441", width=2.5),
        fill="tozeroy", fillcolor="rgba(217,164,65,0.08)",
    ))
    fig.update_layout(**{**CHART_LAYOUT,
        "title": dict(
            text=f"Portfolio Value  "
                 f"<span style='color:{color_pct};font-size:14px'>{sign}{pct:.2f}%</span>",
            font=dict(size=14, color="#8B9196"), x=0),
        "yaxis_title": f"Value ({sym})", "height": height,
        "yaxis_tickformat": ",.0f",
        "xaxis": dict(showgrid=False, tickfont=dict(size=11, color="#8B9196")),
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
    col      = "#3DBE7F" if final >= 0 else "#EF5F55"
    sign     = "+" if final >= 0 else ""

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=ret_pcts, mode="lines", name="Portfolio",
        line=dict(color="#D9A441", width=2.5),
        fill="tozeroy", fillcolor="rgba(217,164,65,0.08)",
    ))

    for ticker, label, color in [("SPY", "S&P 500", "#6E8FB5"), ("QQQ", "NASDAQ 100", "#8F7AB8")]:
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
                  f"<br><span style='font-size:10px;color:#6B7176'>ราคา-based · ไม่นับเวลาที่ซื้อจริง</span>"),
            font=dict(size=14, color="#8B9196"), x=0),
        "yaxis_title": "Return (%)", "height": height,
        "yaxis_tickformat": ".2f", "yaxis_ticksuffix": "%",
        "xaxis": dict(showgrid=False, tickfont=dict(size=11, color="#8B9196")),
        "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    })
    return fig

def build_realized_events(investments: list, trades: list) -> list:
    """Every sale that locked in a gain or loss, from both investments and trades.

    Three things produce one: a fully closed position, a partial sell recorded in
    sell_history, and the same two on the trade side. The Overview KPI and the tax
    summary both read this, so the two can never drift apart.

    fx_rate / proceeds_thb are only present on records closed after they started
    being saved; older rows leave them blank rather than guessing a rate.
    """
    out = []

    def add(kind, item, date_s, shares, price, pnl_thb, proceeds_thb, fx, partial):
        if not date_s:
            return
        out.append({
            "kind":         kind,                       # "Invest" | "Trade"
            "ticker":       item.get("ticker", "—"),
            "currency":     get_currency(item),
            "entry_date":   item.get("entry_date") or item.get("open_date") or "",
            "entry_price":  item.get("entry_price"),
            "sell_date":    date_s,
            "sell_price":   price,
            "shares":       shares,
            "pnl_thb":      pnl_thb,
            "proceeds_thb": proceeds_thb,
            "fx_rate":      fx,
            "partial":      partial,
            "account":      item.get("source_account_name") or "—",
        })

    for inv in investments:
        for sh in inv.get("sell_history", []):
            add("Invest", inv, sh.get("date"), sh.get("shares"), sh.get("price"),
                sh.get("pnl_thb"), sh.get("thb"), sh.get("fx_rate"), True)
        if inv.get("status") == "closed":
            add("Invest", inv, inv.get("exit_date"), get_shares(inv), inv.get("exit_price"),
                inv.get("pnl_thb"), inv.get("proceeds_thb"),
                inv.get("fx_rate_at_close"), False)

    for t in trades:
        # "received" is the cash that came back: on a leveraged trade that is margin +
        # P&L, not the notional sale value (identical at 1x)
        for sh in t.get("sell_history", []):
            add("Trade", t, sh.get("date"), sh.get("shares"), sh.get("price"),
                sh.get("pnl_thb"), sh.get("settled_thb", sh.get("thb")), sh.get("fx_rate"), True)
        if t.get("status") == "closed":
            add("Trade", t, t.get("close_date"), get_shares(t), t.get("exit_price"),
                t.get("pnl_thb"), t.get("settled_thb", t.get("proceeds_thb")),
                t.get("fx_rate_at_close"), False)

    out.sort(key=lambda e: e["sell_date"], reverse=True)
    return out


def build_cashouts(cash: list) -> list:
    """Money taken out of the portfolio to spend, newest first.

    Kept deliberately apart from realized P&L: realized measures how the picks
    did, a cashout is cash leaving the system. Netting a withdrawal against
    realized would read as a loss when it is just spending a gain.

    Stored per account under "cashouts" — cash_accounts is a jsonb blob that
    save_cash() writes whole, so this needs no schema change.
    """
    out = []
    for acc in cash:
        for c in acc.get("cashouts", []):
            out.append({
                "date":       c.get("date", ""),
                "account":    acc.get("name", "—"),
                "currency":   acc.get("currency", "THB"),
                "amount":     c.get("amount"),          # in the account's own currency
                "amount_thb": c.get("amount_thb"),
                "fx_rate":    c.get("fx_rate"),
                "to_thai":    bool(c.get("to_thai")),
                "note":       c.get("note", ""),
                # Only a withdrawal out of a foreign-currency account and into
                # Thailand is a remittance. Pulling THB out of a Thai account moves
                # money that was already onshore, so nothing is being brought in.
                "remitted":   bool(c.get("to_thai")) and acc.get("currency") != "THB",
            })
    out.sort(key=lambda c: c["date"], reverse=True)
    return out


def build_deposits(cash: list) -> list:
    """Money put into the portfolio from outside, newest first.

    The counterpart to build_cashouts(). Before this, the only way to add money
    was overwriting an account's balance, which left no record — a deposit was
    indistinguishable from a typo fix or a realised gain, so actual return
    (value − deposits + withdrawals) could not be computed. Stored per account
    under "deposits", same jsonb blob, no schema change.
    """
    out = []
    for acc in cash:
        for d in acc.get("deposits", []):
            out.append({
                "date":       d.get("date", ""),
                "account":    acc.get("name", "—"),
                "currency":   acc.get("currency", "THB"),
                "amount":     d.get("amount"),          # in the account's own currency
                "amount_thb": d.get("amount_thb"),
                "fx_rate":    d.get("fx_rate"),
                "note":       d.get("note", ""),
            })
    out.sort(key=lambda d: d["date"], reverse=True)
    return out


def build_activity_log(investments: list, trades: list, cash: list | None = None) -> list:
    events = []
    for inv in investments:
        ticker = inv.get("ticker","—")
        if inv.get("entry_date"):
            events.append({"วันที่": inv.get("entry_date",""), "ประเภท": "Invest",
                "Action": "ซื้อ", "Ticker": ticker,
                "รายละเอียด": f"เปิด · {get_shares(inv)} shares @ {inv.get('entry_price','—')}"})
        for bh in inv.get("buy_history", []):
            events.append({"วันที่": bh.get("date",""), "ประเภท": "Invest",
                "Action": "ซื้อเพิ่ม", "Ticker": ticker,
                "รายละเอียด": f"+{bh.get('shares','?')} shares @ {bh.get('price','—')}"})
        for sh in inv.get("sell_history", []):
            pnl_s = money(sh.get('pnl_thb'))
            events.append({"วันที่": sh.get("date",""), "ประเภท": "Invest",
                "Action": "ขายบางส่วน", "Ticker": ticker,
                "รายละเอียด": f"-{sh.get('shares','?')} shares @ {sh.get('price','—')} · P&L {pnl_s}"})
        if inv.get("status") == "closed" and inv.get("exit_date"):
            events.append({"วันที่": inv.get("exit_date",""), "ประเภท": "Invest",
                "Action": "ปิด", "Ticker": ticker,
                "รายละเอียด": f"ปิด @ {inv.get('exit_price','—')} · P&L {fmt_pct(inv.get('pnl_pct'))}"})
    for t in trades:
        ticker = t.get("ticker","—")
        arr = "↑" if t.get("direction") == "Long" else "↓"
        if t.get("open_date"):
            events.append({"วันที่": t.get("open_date",""), "ประเภท": "Trade",
                "Action": "เปิด", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"{get_shares(t)} shares @ {t.get('entry_price','—')} · SL {t.get('stop_loss','—')} · TP {t.get('take_profit','—')}"})
        for bh in t.get("buy_history", []):
            events.append({"วันที่": bh.get("date",""), "ประเภท": "Trade",
                "Action": "ซื้อเพิ่ม", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"+{bh.get('shares','?')} shares @ {bh.get('price','—')}"})
        for sh in t.get("sell_history", []):
            pnl_s = money(sh.get('pnl_thb'))
            events.append({"วันที่": sh.get("date",""), "ประเภท": "Trade",
                "Action": "ขายบางส่วน", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"-{sh.get('shares','?')} shares @ {sh.get('price','—')} · P&L {pnl_s}"})
        if t.get("status") == "closed" and t.get("close_date"):
            events.append({"วันที่": t.get("close_date",""), "ประเภท": "Trade",
                "Action": "ปิด", "Ticker": f"{ticker} {arr}",
                "รายละเอียด": f"ปิด @ {t.get('exit_price','—')} · P&L {fmt_pct(t.get('pnl_pct'))} · {t.get('win_loss','')}"})
    # money moving in and out of the portfolio, so the log shows the whole story
    for d in build_deposits(cash or []):
        sym = "$" if d["currency"] == "USD" else "฿"
        events.append({"วันที่": d["date"], "ประเภท": "Cash",
            "Action": "เติมเงิน", "Ticker": d["account"],
            "รายละเอียด": f"+{money(d['amount'], sym, 2)}"
                          + (f" (≈{money(d['amount_thb'])})" if d["currency"] != "THB" else "")
                          + (f" · {d['note']}" if d["note"] else "")})
    for c in build_cashouts(cash or []):
        sym = "$" if c["currency"] == "USD" else "฿"
        events.append({"วันที่": c["date"], "ประเภท": "Cash",
            "Action": "ถอนเงิน", "Ticker": c["account"],
            "รายละเอียด": f"−{money(c['amount'], sym, 2)}"
                          + (f" (≈{money(c['amount_thb'])})" if c["currency"] != "THB" else "")
                          + (" · โอนเข้าไทย" if c["remitted"] else "")
                          + (f" · {c['note']}" if c["note"] else "")})
    events.sort(key=lambda e: e.get("วันที่",""), reverse=True)
    return events

def pnl_bar_chart(labels, vals_thb, disp, rate, title, height=280):
    vals   = [to_display(v, disp, rate) for v in vals_thb]
    texts  = [fmt_money(v, disp, rate) for v in vals_thb]
    colors = ["#3DBE7F" if (v or 0) >= 0 else "#EF5F55" for v in vals_thb]
    fig = go.Figure(go.Bar(
        x=labels, y=vals,
        marker=dict(color=colors, opacity=0.85,
                    line=dict(color="rgba(255,255,255,0.1)", width=1)),
        text=texts, textposition="outside",
        textfont=dict(size=13, color="#E9E6DF"), cliponaxis=False,
    ))
    sym = "฿" if disp == "THB" else "$"
    fig.update_layout(**{**CHART_LAYOUT,
        "title": dict(text=title, font=dict(size=14, color="#8B9196"), x=0),
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
    # a custom strategy must reopen as "Others" with its text, not as the first preset —
    # otherwise editing a trade tagged "Gap Fill" shows Breakout and saving overwrites it
    if default in STRATEGY_PRESETS:
        preset = default
    elif default:
        preset = "Others"
    else:
        preset = STRATEGY_PRESETS[0]
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

    # same tokens as the app (dark) and the mockup's light set
    if dark:
        bg, card, line, txt, sub, acc, acc_ink = ("#0D1012", "#14181B", "#262C31", "#E9E6DF",
                                                  "#8B9196", "#D9A441", "#1A1408")
        tog_lbl = "Light"
    else:
        bg, card, line, txt, sub, acc, acc_ink = ("#F4F3EF", "#FFFFFF", "#E2DFD8", "#17191B",
                                                  "#63686D", "#9C7218", "#FFFFFF")
        tog_lbl = "Dark"

    st.markdown(f"""<style>
header[data-testid="stHeader"]{{display:none!important}}
[data-testid="stToolbar"]{{display:none!important}}
.stApp,[data-testid="stMain"]{{background:{bg}!important}}
[data-testid="stMain"] .block-container{{max-width:1040px!important;padding-top:9vh!important}}
[data-testid="stMain"] p,[data-testid="stMain"] label,[data-testid="stWidgetLabel"] p{{color:{sub}!important}}
/* the app hides Streamlit's tab-list because the navbar replaces it; the login
   tabs (sign in / sign up) are real tabs and must stay visible */
[data-testid="stMain"] [data-baseweb="tab-list"]{{display:flex!important;background:transparent!important;
    border-bottom:1px solid {line}!important;gap:4px!important}}
[data-baseweb="tab"]{{color:{sub}!important;padding:8px 4px!important;margin-right:14px!important}}
[data-baseweb="tab"] p{{color:inherit!important;font-weight:500!important}}
[data-baseweb="tab"][aria-selected="true"]{{color:{txt}!important}}
[data-baseweb="tab-highlight"]{{background:{acc}!important}}
[data-baseweb="tab-border"]{{display:none!important}}
/* form card */
[data-testid="stForm"]{{background:{card}!important;border:1px solid {line}!important;border-radius:10px!important;
    padding:22px 22px 18px!important}}
[data-baseweb="input"],[data-testid="stTextInputRootElement"]{{background:{bg}!important;border:1px solid {line}!important;border-radius:6px!important}}
[data-baseweb="input"]:focus-within,[data-testid="stTextInputRootElement"]:focus-within{{border-color:{acc}!important}}
[data-testid="stTextInputField"]{{color:{txt}!important;background:transparent!important}}
[data-testid="stTextInputRootElement"] button{{background:transparent!important}}
[data-testid="stTextInputRootElement"] button span{{color:{sub}!important}}
[data-baseweb="base-input"],[data-baseweb="input"] input,[data-baseweb="input"] button{{background:transparent!important;color:{txt}!important}}
[data-baseweb="input"] button svg{{fill:{sub}!important;color:{sub}!important}}
[data-testid="stFormSubmitButton"] button{{background:{acc}!important;border-color:{acc}!important}}
[data-testid="stFormSubmitButton"] button p{{color:{acc_ink}!important;font-weight:600!important}}
[data-testid="stMain"] [data-testid="stButton"] button{{background:transparent!important;border:1px solid {line}!important;
    border-radius:6px!important;padding:.2rem .9rem!important;min-height:0!important}}
[data-testid="stMain"] [data-testid="stButton"] button p{{color:{sub}!important;font-size:13px!important}}
.lp-h{{font-size:40px;line-height:1.15;font-weight:700;color:{txt};margin:18px 0 14px;letter-spacing:-.01em}}
.lp-p{{color:{sub};font-size:16px;margin:0 0 26px;max-width:40ch}}
.lp-brand{{display:flex;align-items:center;gap:10px;font-weight:700;font-size:16px;color:{txt}}}
.lp-brand img{{width:30px;height:30px;border-radius:7px}}
.lp-line{{width:100%;max-width:440px;height:auto;display:block}}
.lp-line path.l{{stroke-dasharray:900;stroke-dashoffset:900;animation:lpdraw 1.6s cubic-bezier(.3,.6,.2,1) .2s forwards}}
.lp-line circle{{opacity:0;animation:lpfade .4s ease 1.6s forwards}}
@keyframes lpdraw{{to{{stroke-dashoffset:0}}}}
@keyframes lpfade{{to{{opacity:1}}}}
@media (prefers-reduced-motion:reduce){{.lp-line path.l{{animation:none;stroke-dashoffset:0}}.lp-line circle{{animation:none;opacity:1}}}}
@media (max-width:640px){{
  [data-testid="stMain"] .block-container{{padding-top:4vh!important}}
  .lp-h{{font-size:30px;margin:14px 0 8px}} .lp-p{{margin-bottom:8px}} .lp-line{{display:none}}
}}
</style>""", unsafe_allow_html=True)

    logo_html = (f'<img src="data:image/png;base64,{_LOGO_B64}" alt="">' if _LOGO_B64 else "")
    # a fixed, illustrative curve; it draws itself once on load (not account data)
    _pts = [62, 58, 60, 51, 54, 47, 49, 40, 44, 36, 38, 30, 33, 24, 27, 18, 20, 12]
    _d = "M" + " L".join(f"{i * 440 / (len(_pts) - 1):.1f},{y * 1.6:.1f}" for i, y in enumerate(_pts))
    pitch, form_col = st.columns([1.15, 1], gap="large")
    with pitch:
        st.markdown(f"""<div class="lp-brand">{logo_html}<span>Tim.fin OS</span></div>
<div class="lp-h">พอร์ตทั้งหมด<br>ในสมุดเล่มเดียว</div>
<p class="lp-p">หุ้น เทรด เงินสด และบันทึกภาษี รวมไว้ที่เดียว ดูได้ทั้งบาทและดอลลาร์</p>
<svg class="lp-line" viewBox="0 0 440 110" aria-hidden="true">
<line x1="0" y1="109" x2="440" y2="109" stroke="{line}"/>
<path class="l" d="{_d}" fill="none" stroke="{acc}" stroke-width="2.2" stroke-linejoin="round"/>
<circle cx="440" cy="{_pts[-1] * 1.6:.1f}" r="4.5" fill="{acc}"/></svg>""", unsafe_allow_html=True)
        if st.button(tog_lbl, key="login_theme_toggle"):
            st.session_state["login_theme"] = "light" if dark else "dark"
            st.rerun()

    with form_col:
        _render_login_forms()


def _render_login_forms():
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
                        st.error("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณารีเฟรชหน้าแล้วลองใหม่")
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
                        st.success("สมัครสมาชิกสำเร็จ กรุณาตรวจสอบ Email เพื่อยืนยันตัวตน แล้วกลับมา Login")
                    else:
                        st.error(f"สมัครไม่สำเร็จ: {err}")


# -- Sidebar (branding + account only, no nav) --
def render_logout_target(logged_in: bool) -> None:
    """The real logout button, kept off-screen.

    The navbar's account menu is HTML injected into the parent document, so it
    cannot touch session state itself — doLogout() finds a Streamlit button by
    its label text and clicks it. That button used to sit in the sidebar; with
    the sidebar gone it lives here, moved out of view rather than hidden with
    display:none so the synthetic click still reaches React.
    """
    if not (logged_in and "sb_session" in st.session_state):
        return
    # Streamlit stamps a keyed widget's container with .st-key-<key>
    # (convertKeyToClassName in its bundle) — the only stable hook onto one widget.
    st.markdown(
        '<style>.st-key-tfin_real_logout{position:absolute!important;'
        'left:-9999px!important;top:0!important;height:1px!important;'
        'overflow:hidden!important;}</style>',
        unsafe_allow_html=True,
    )
    if st.button("ออกจากระบบ", key="tfin_real_logout"):
        del st.session_state["sb_session"]
        st.query_params.pop("_s", None)
        st.rerun()


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
        port_thb += position_value_thb(item, get_price(item.get("ticker","")), rate)

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

    # Realized covers every locked-in sale: closed trades, closed investments, and
    # partial sells of either. It used to read closed_trades alone, so selling an
    # investment or trimming a position produced a gain that showed up nowhere.
    realized_events = build_realized_events(investments, trades)
    realized_thb    = sum(e["pnl_thb"] or 0 for e in realized_events)
    realized_trade  = sum(e["pnl_thb"] or 0 for e in realized_events if e["kind"] == "Trade")
    realized_inv    = sum(e["pnl_thb"] or 0 for e in realized_events if e["kind"] == "Invest")
    # Win rate stays a trading metric — long-term holds are not won or lost per sale.
    win_rate     = len(wins) / len(closed_trades) * 100 if closed_trades else None

    cost_basis_thb = 0.0
    for _item in open_trades + open_inv:
        _s = parse(get_shares(_item))
        _e = parse(_item.get("entry_price",""))
        if _s and _e:
            # capital actually deployed: the margin on a leveraged trade, not the notional
            cost_basis_thb += (_s * _e * (rate if get_currency(_item) == "USD" else 1)
                               / trade_leverage(_item))

    # -- KPI Row --
    section("Portfolio Summary")
    cashouts_ov = build_cashouts(cash)
    cashout_thb = sum(c["amount_thb"] or 0 for c in cashouts_ov)

    # labels kept short: at five columns the long ones truncate mid-word
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Wealth",
              fmt_money(port_thb, disp, rate, sign=False) if port_thb else "No data yet",
              help="มูลค่าพอร์ตทั้งหมด รวมเงินสดในทุกบัญชี")
    k2.metric("Deployed",
              fmt_money(cost_basis_thb if cost_basis_thb else None, disp, rate, sign=False)
              if cost_basis_thb else "No holdings",
              help="ต้นทุนรวมของ position ที่ยังถืออยู่ (cost basis)")
    _unreal_ret_pct = unreal_thb / cost_basis_thb * 100 if cost_basis_thb and unreal_items else None
    k3.metric("Unrealized P&L",
              fmt_money(unreal_thb if unreal_items else None, disp, rate),
              delta=fmt_pct(_unreal_ret_pct))
    k4.metric("Realized P&L",
              fmt_money(realized_thb, disp, rate) if realized_events else "ยังไม่มีการขาย")
    if realized_events:
        # a delta string gets clipped by the card width, a caption wraps instead
        k4.caption(f"Trade {fmt_money(realized_trade, disp, rate)}  ·  "
                   f"Invest {fmt_money(realized_inv, disp, rate)}")
    # kept as its own card, never netted against Realized — spending a gain is
    # not a loss, and merging the two makes the performance figure meaningless
    k5.metric("Cash Out",
              fmt_money(cashout_thb, disp, rate, sign=False) if cashouts_ov else "—",
              help="เงินที่ถอนออกจากพอร์ตไปใช้จ่ายแล้ว — แยกจาก Realized เพราะ "
                   "การถอนกำไรไปใช้ไม่ใช่การขาดทุน")
    if cashouts_ov:
        k5.caption(f"{len(cashouts_ov)} ครั้ง · ล่าสุด {cashouts_ov[0]['date']}")

    # -- Asset Allocation (pie) + Return Chart side by side --
    open_all = open_trades + open_inv
    if open_all or cash_thb > 0:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        pie_labels, pie_vals, pie_pcts = [], [], []
        for item in open_all:
            # same valuation as Total Wealth so the slices add up to the headline;
            # a position underwater past its capital has no positive share to draw
            _px = get_price(item.get("ticker",""))
            pos = position_value_thb(item, _px, rate)
            if pos > 0:
                pie_labels.append(item.get("ticker","?"))
                pie_vals.append(pos)
                _pp = calc_pnl_pct(item.get("entry_price"), _px,
                                   item.get("direction", "Long")) if _px else None
                pie_pcts.append(_pp * trade_leverage(item) if _pp is not None else None)
        if cash_thb > 0:
            pie_labels.append("Cash")
            pie_vals.append(cash_thb)
            pie_pcts.append(None)

        col_chart = st.container()
        with col_chart:
            if open_all:
                cc1, cc2, cc3 = st.columns([3, 4, 4])
                with cc1:
                    ret_view = st.radio("", ["Overall","Investment","Trade"], horizontal=True,
                                        key="ret_view", label_visibility="collapsed")
                with cc2:
                    ret_period = st.radio("", ["1D","1W","1M","1Y"], horizontal=True,
                                          key="ret_period", index=2, label_visibility="collapsed")
                with cc3:
                    cspy = st.checkbox("S&P 500", key="cmp_spy")
                    cqqq = st.checkbox("NASDAQ 100", key="cmp_qqq")
                ret_items = (open_inv if ret_view == "Investment"
                             else open_trades if ret_view == "Trade"
                             else open_all)
                fig_ret = portfolio_return_chart(ret_items, rate, disp, ret_period,
                                                 show_spy=cspy, show_qqq=cqqq, height=270)
                if fig_ret:
                    st.plotly_chart(fig_ret, use_container_width=True)
                else:
                    st.info("ไม่มีข้อมูลราคาย้อนหลัง")

        if pie_labels:
            section("ถืออะไรอยู่")
            allocation_panel(pie_labels, pie_vals, pie_pcts, disp, rate, key="ov")

    # -- Stats + Cash compact row --
    if open_all or cash:
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Investments",   len(open_inv))
        s2.metric("Open Trades",   len(open_trades))
        s3.metric("Closed Trades", len(closed_trades))
        s4.metric("Win Rate",      f"{win_rate:.1f}%" if win_rate is not None else "—")
        if cash:
            cash_parts = []
            for a in cash:
                sym_c = "$" if a["currency"] == "USD" else "฿"
                val_c = a["amount"] * rate if a["currency"] == "USD" else a["amount"]
                part  = f"**{a['name']}** · {money(a['amount'], sym_c, 2)}"
                if a["currency"] == "USD":
                    part += f" (≈{money(val_c)})"
                cash_parts.append(part)
            st.markdown("<small>Cash · " + "  ·  ".join(cash_parts) + "</small>", unsafe_allow_html=True)

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
                "Type":           "Invest",
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
                "Type":           f"Trade {arr}",
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
            if isinstance(val, str) and val.startswith("+"): return "color:#3DBE7F;font-weight:600"
            if isinstance(val, str) and val.startswith("-"): return "color:#EF5F55;font-weight:600"
            return ""
        df_ov = pd.DataFrame(pos_rows).drop(columns=["_pnl_raw"])
        _all_cols_ov = list(df_ov.columns)

        with st.expander("Portfolio Snapshot", expanded=True):
            _pnl_sub = [c for c in ["P&L %", _pc_col] if c in _all_cols_ov]
            try:
                styled_ov = df_ov.style.map(_col_pnl_ov, subset=_pnl_sub).hide(axis="index") if _pnl_sub else df_ov.style.hide(axis="index")
            except AttributeError:
                styled_ov = df_ov.style.applymap(_col_pnl_ov, subset=_pnl_sub).hide(axis="index") if _pnl_sub else df_ov.style.hide(axis="index")
            st.dataframe(styled_ov, use_container_width=True, hide_index=True)

    # -- Recent Activity --
    recent_events = build_activity_log(investments, trades, cash)
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
    if cash_thb_total: cash_parts.append(f"{money(cash_thb_total)} THB")
    if cash_usd_total: cash_parts.append(f"{money(cash_usd_total, '$', 2)} USD")
    cash_inline    = " &nbsp;·&nbsp; ".join(cash_parts) if cash_parts else "฿0"
    acct_total_thb = total_val_thb + cash_total_thb
    acct_total_s   = fmt_money(acct_total_thb, disp, rate, sign=False)
    st.markdown(
        f"<div style='background:rgba(217,164,65,0.08);border:1px solid rgba(217,164,65,0.25);"
        f"border-radius:8px;padding:8px 16px;margin:6px 0 4px 0;line-height:1.5'>"
        f"<span style='font-size:11px;color:#6B7176;text-transform:uppercase;"
        f"letter-spacing:0.06em'>Cash</span>"
        f"&nbsp;&nbsp;"
        f"<span style='font-size:15px;font-weight:600;color:#E9E6DF'>{cash_inline}</span>"
        f"&nbsp;&nbsp;<span style='font-size:11px;color:#6B7176'>· จัดการที่หน้า Cash</span>"
        f"&nbsp;&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;"
        f"<span style='font-size:11px;color:#6B7176;text-transform:uppercase;"
        f"letter-spacing:0.06em'>Account Total</span>"
        f"&nbsp;&nbsp;"
        f"<span style='font-size:15px;font-weight:700;color:#8B9196'>{acct_total_s}</span>"
        f"<span style='font-size:10px;color:#5B6268'>&nbsp;(positions + cash)</span>"
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
        # stacked, not side by side: with a dozen holdings the pie needs the width
        # for its labels, and the return chart reads better full width anyway
        col_pie_inv, col_ret_inv = st.container(), st.container()
        with col_pie_inv:
            if pie_labels_inv:
                section("ถืออะไรอยู่")
                _ip = [calc_pnl_pct(r["inv"].get("entry_price"), r["price"]) if r["price"] else None
                       for r in raw if r["pos_thb"]]
                allocation_panel(pie_labels_inv, pie_vals_inv, _ip, disp, rate, key="inv")
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
            section("Target Allocation")

            t_tickers  = [r["inv"]["ticker"] for r in inv_with_target]
            curr_pcts  = [r["pos_thb"] / total_val_thb * 100 if total_val_thb else 0
                          for r in inv_with_target]
            tgt_pcts   = [r["inv"].get("target_pct", 0) for r in inv_with_target]
            deltas     = [c - t for c, t in zip(curr_pcts, tgt_pcts)]
            total_tgt  = sum(t for t in tgt_pcts if t)

            def _tgt_color(d):
                if abs(d) <= 3: return "#3DBE7F"
                if abs(d) <= 8: return "#f59e0b"
                return "#EF5F55"
            bar_colors = [_tgt_color(d) for d in deltas]

            fig_tgt = go.Figure()
            fig_tgt.add_trace(go.Bar(
                name="Target %", y=t_tickers, x=tgt_pcts, orientation="h",
                marker_color="rgba(148,163,184,0.25)",
                marker_line=dict(color="#8B9196", width=1),
                text=[f"{p:.0f}%" for p in tgt_pcts], textposition="inside",
                textfont=dict(size=11, color="#8B9196"),
            ))
            fig_tgt.add_trace(go.Bar(
                name="Current %", y=t_tickers, x=curr_pcts, orientation="h",
                marker_color=bar_colors, opacity=0.85,
                text=[f"{p:.1f}%" for p in curr_pcts], textposition="outside",
                textfont=dict(size=11, color="#E9E6DF"),
            ))
            fig_tgt.update_layout(
                **{**CHART_LAYOUT,
                   "barmode": "overlay",
                   "height": max(200, len(t_tickers) * 45 + 70),
                   "showlegend": True,
                   "legend": dict(orientation="h", y=1.1, x=0, font=dict(size=11, color="#8B9196")),
                   "margin": dict(t=50, b=8, l=8, r=80),
                   "xaxis": dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                                 ticksuffix="%", tickfont=dict(size=11, color="#8B9196")),
                   "yaxis": dict(showgrid=False, tickfont=dict(size=12, color="#E9E6DF")),
                   "title": dict(
                       text=(f"Current vs Target  "
                             f"<span style='font-size:11px;color:#6B7176'>"
                             f"Target รวม {total_tgt:.0f}% · Cash {max(0, 100-total_tgt):.0f}%</span>"),
                       font=dict(size=13, color="#8B9196"), x=0),
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
                    action = f"ขายลด {money(action_disp, sym_r)}"
                elif delta < -3:
                    action = f"ซื้อเพิ่ม {money(action_disp, sym_r)}"
                else:
                    action = "ใกล้เป้า"
                rebal_rows.append({
                    "Ticker":   r["inv"]["ticker"],
                    "Current":  f"{curr_p:.1f}%",
                    "Target":   f"{tgt_p:.0f}%",
                    "Δ":        f"{'+' if delta >= 0 else ''}{delta:.1f}%",
                    "Action":   action,
                })
            st.dataframe(rebal_rows, use_container_width=True, hide_index=True)

            no_target = [r["inv"]["ticker"] for r in raw if r["inv"].get("target_pct") is None]

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
                "Current Price": (f"{price:.2f} (manual)" if inv.get("manual_price") else f"{price:.2f}") if price else "—",
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
            "Ticker":        "TOTAL",
            "Shares":        "—",
            "Avg Cost":      "—",
            "Total Cost":    money(total_cost_disp, sym_p),
            "Current Price": "—",
            "Market Value":  money(total_mv, sym_p),
            "ถือมา":         "—",
            "P&L %":         fmt_pct(total_pnl_pct_row),
            f"P&L ({sym})":  fmt_money(sum(r["pnl_thb"] for r in raw if r.get("price")), disp, rate),
            "Thesis":        "—",
        })

        pnl_cols = ["P&L %", f"P&L ({sym})"]

        def _color_pnl(val):
            if isinstance(val, str) and val.startswith("+"):
                return "color: #3DBE7F; font-weight: 600"
            if isinstance(val, str) and val.startswith("-"):
                return "color: #EF5F55; font-weight: 600"
            return ""

        def _style_total(row):
            if row["Ticker"] == "TOTAL":
                return ["background-color: rgba(217,164,65,0.12); font-weight: 700"] * len(row)
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
        # Clicking a row opens that position's drawer under the table, the way the
        # mockup does it — one table instead of the table plus a second list of
        # expanders repeating the same rows.
        _ev = st.dataframe(styled, use_container_width=True, hide_index=True,
                           on_select="rerun", selection_mode="single-row", key="inv_hold_tbl",
                           height=(len(rows) + 1) * 35 + 3)

        # The selected row opens as a popup over the page, where the eye already is,
        # rather than a panel below a long table. It opens once per new selection:
        # closing it with X and then changing currency must not pop it back up.
        @st.dialog("จัดการ Position", width="large")
        def _inv_dialog(inv):
            price   = get_price(inv.get("ticker",""))
            pnl_thb = calc_pnl_thb(inv.get("entry_price"), price, get_shares(inv),
                                    get_currency(inv), rate) if price else None
            pnl_pct = calc_pnl_pct(inv.get("entry_price"), price) if price else None
            _isv    = parse(get_shares(inv))
            _icost  = calc_position_thb(inv.get("entry_price"), get_shares(inv), get_currency(inv), rate)
            _imval  = (_isv * price * (rate if get_currency(inv) == "USD" else 1)) if price and _isv else None
            _ics    = fmt_money(_icost, disp, rate, sign=False) if _icost else "—"
            _ivs    = fmt_money(_imval, disp, rate, sign=False) if _imval else "—"
            _pc2 = "#3DBE7F" if (pnl_thb or 0) >= 0 else "#EF5F55"
            _bg2 = "rgba(61,190,127,0.12)" if (pnl_thb or 0) >= 0 else "rgba(239,95,85,0.12)"
            _acct = inv.get("source_account_name") or "—"
            st.markdown(
                f"<div class='pd-head'><span class='pd-tk'>{html.escape(inv['ticker'])}</span>"
                f"<span class='pd-sub'>{html.escape(get_shares(inv))} หุ้น · AVG {html.escape(str(inv.get('entry_price','—')))}"
                f" → {f'{price:,.2f}' if price else '—'}</span>"
                f"<span class='pd-pill' style='color:{_pc2};background:{_bg2}'>"
                f"{fmt_money(pnl_thb, disp, rate) if pnl_thb is not None else '—'} · {fmt_pct(pnl_pct)}</span></div>"
                f"<div class='pd-facts'>"
                f"<div><div class='l'>ต้นทุน</div><div class='v'>{_ics}</div></div>"
                f"<div><div class='l'>มูลค่า</div><div class='v'>{_ivs}</div></div>"
                f"<div><div class='l'>ถือตั้งแต่</div><div class='v'>{html.escape(inv.get('entry_date') or '—')}</div></div>"
                f"<div><div class='l'>บัญชี</div><div class='v' style='font-family:inherit'>{html.escape(_acct)}</div></div>"
                f"</div>".replace("$", "&#36;"),
                unsafe_allow_html=True)
            ca, cb, cc, _, cd = st.columns([1, 1, 1, 4, 1])
            if cc.button("ขาย", key=f"sellbtn_{inv['id']}", use_container_width=True):
                st.session_state[f"sell_inv_{inv['id']}"] = True
                st.session_state.pop(f"edit_inv_{inv['id']}", None)
                st.session_state.pop(f"add_inv_{inv['id']}", None)
            if cb.button("แก้ไข", key=f"ei_{inv['id']}", use_container_width=True):
                st.session_state[f"edit_inv_{inv['id']}"] = True
                st.session_state.pop(f"sell_inv_{inv['id']}", None)
                st.session_state.pop(f"add_inv_{inv['id']}", None)
            if ca.button("ซื้อเพิ่ม", key=f"ai_{inv['id']}", use_container_width=True):
                st.session_state[f"add_inv_{inv['id']}"] = True
                st.session_state.pop(f"edit_inv_{inv['id']}", None)
                st.session_state.pop(f"sell_inv_{inv['id']}", None)
            if cd.button("ลบ", key=f"di_{inv['id']}", use_container_width=True):
                investments[:] = [x for x in investments if x["id"] != inv["id"]]
                save_investments(investments)
                st.session_state.pop("inv_hold_tbl", None)
                st.rerun()

            if st.session_state.get(f"add_inv_{inv['id']}"):
                st.markdown("**ซื้อเพิ่ม**")
                with st.form(f"form_add_inv_{inv['id']}"):
                    aa1, aa2, aa3 = st.columns(3)
                    add_shares = aa1.text_input("จำนวนหุ้นที่ซื้อเพิ่ม *", placeholder="เช่น 5")
                    add_price  = aa2.text_input("ราคาที่ซื้อ *", placeholder="เช่น 80")
                    add_date   = aa3.date_input("วันที่ซื้อ", value=date.today())
                    src_id, other_name, other_curr = source_selector(cash, f"add_inv_{inv['id']}")
                    if st.form_submit_button("ยืนยันซื้อเพิ่ม"):
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
                            st.session_state.pop("inv_hold_tbl", None)
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
                        "Manual Price (DR / หุ้นที่ดึงราคาไม่ได้)",
                        value=str(inv["manual_price"]) if inv.get("manual_price") is not None else "",
                        placeholder="ใส่ราคาปัจจุบัน เช่น 85.50  (ว่าง = ดึงจาก yfinance)",
                    )
                    if st.form_submit_button("บันทึก"):
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
                        st.session_state.pop("inv_hold_tbl", None)
                        st.rerun()

            if st.session_state.get(f"sell_inv_{inv['id']}"):
                st.markdown("**ขาย**")
                s_current = parse(get_shares(inv)) or 0
                st.caption(f"ถืออยู่ {s_current:,.10g} หุ้น · AVG {inv.get('entry_price','—')}")
                with st.form(f"form_sell_inv_{inv['id']}"):
                    # a button can't fill a field inside a form, so Max is a tick
                    # read on submit — it sells exactly what is held, no typing
                    sv1, svm, sv2, sv3 = st.columns([3, 1, 3, 3])
                    sell_shares = sv1.text_input("จำนวนที่ขาย *", placeholder=f"สูงสุด {s_current:,.10g}")
                    with svm:
                        st.markdown("<div style='height:35px'></div>", unsafe_allow_html=True)
                        sell_max = st.checkbox("Max", key=f"sell_inv_max_{inv['id']}", help="ขายหมดทั้ง position ไม่ต้องพิมพ์จำนวน")
                    exit_p      = sv2.text_input("ราคาที่ขาย *", placeholder="เช่น 420")
                    exit_d      = sv3.date_input("วันที่ขาย", value=date.today())
                    sv4, sv5 = st.columns(2)
                    thesis_ok = sv4.selectbox("Thesis ถูกไหม (ถ้าปิด position)",
                                               ["✅ ถูก", "❌ ผิด", "⚠️ บางส่วน"])
                    emotion   = sv5.selectbox("Emotion (ถ้าปิด position)",
                                               ["ปกติ", "กลัว", "โลภ", "FOMO"])
                    lesson    = st.text_input("Lesson ที่ได้ (optional, ถ้าปิด position)")
                    if st.form_submit_button("ยืนยันขาย"):
                        s_sell = s_current if sell_max else parse(sell_shares)
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
                                            # pnl_thb is converted at today's rate; keep the
                                            # rate and the THB proceeds or the filed figure
                                            # can never be reproduced later
                                            "fx_rate_at_close": round(rate, 4),
                                            "proceeds_thb": round(exit_thb, 2),
                                            "thesis_correct": thesis_ok,
                                            "emotion": emotion, "lesson": lesson})
                                if src_id:
                                    cash_credit(cash, src_id, exit_thb, rate)
                                    save_cash(cash)
                                save_investments(investments)
                                st.session_state.pop(f"sell_inv_{inv['id']}", None)
                                st.success(f"ปิด Position · P&L = {fmt_money(pnl_thb_v, disp, rate)}")
                            else:
                                s_remain  = round(s_current - s_sell, 8)
                                pnl_thb_p = calc_pnl_thb(inv["entry_price"], ep, str(s_sell), currency, rate)
                                sell_hist = inv.get("sell_history", [])
                                sell_hist.append({
                                    "date": str(exit_d), "shares": str(s_sell),
                                    "price": str(ep), "thb": round(exit_thb, 2),
                                    "pnl_thb": round(pnl_thb_p or 0, 2),
                                    "fx_rate": round(rate, 4),
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
                                st.success(f"ขาย {s_sell} หุ้น @ {ep} · เหลือ {s_remain} หุ้น · P&L = {fmt_money(pnl_thb_p, disp, rate)}")
                            st.session_state.pop("inv_hold_tbl", None)
                            st.rerun()

        try:
            _sel_rows = list(_ev.selection.rows)
        except Exception:
            _sel_rows = []
        _sel_inv = raw[_sel_rows[0]]["inv"] if _sel_rows and _sel_rows[0] < len(raw) else None
        if _sel_inv is None:
            st.session_state.pop("inv_dlg_last", None)
            st.caption("คลิกแถวในตารางเพื่อซื้อเพิ่ม / แก้ไข / ขาย")
        elif st.session_state.get("inv_dlg_last") != _sel_inv["id"]:
            st.session_state["inv_dlg_last"] = _sel_inv["id"]
            for _f in ("add_inv_", "edit_inv_", "sell_inv_"):
                st.session_state.pop(f"{_f}{_sel_inv['id']}", None)
            _inv_dialog(_sel_inv)

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
    with st.expander("เพิ่ม / ซื้อเพิ่ม Investment"):
        existing_tickers = sorted({inv["ticker"] for inv in open_inv})
        ticker_options   = existing_tickers + ["+ Ticker ใหม่"]
        selected_ticker  = st.selectbox("เลือก Ticker", ticker_options, key="new_inv_select")

        if selected_ticker != "+ Ticker ใหม่":
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
                    is_import = st.checkbox("ไม่หักเงินจาก Cash (Import เก่า)", key="import_add_pos")
                    if st.form_submit_button("ยืนยันซื้อเพิ่ม"):
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
                                f"ซื้อเพิ่ม {add_shares} หุ้น @ {add_price}  ·  "
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
                is_import = st.checkbox("Import position เก่า (ไม่หักเงินจาก Cash)", key="import_inv")
                if st.form_submit_button("บันทึก"):
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
                        st.success(f"บันทึก {ticker.upper()}")
                        st.rerun()


# -- Page 3: Trade --
def page_trade(trades: list, cash: list, disp: str, rate: float):
    open_trades   = [t for t in trades if t.get("status") == "open"]
    closed_trades = [t for t in trades if t.get("status") == "closed"]
    sym    = "฿" if disp == "THB" else "$"

    # trade side only, but via the shared builder so partial sells count here too
    _tr_realized   = [e for e in build_realized_events([], trades)]
    realized_thb   = sum(e["pnl_thb"] or 0 for e in _tr_realized)

    # Win rate and the analytics count every sale, trims included, the same unit as
    # Realized above. Counting only fully closed trades left a trimmed position's
    # locked-in profit in Realized but out of the win/loss numbers next to it.
    _sales = []
    for t in trades:
        _st = t.get("strategy") or "—"
        for x in t.get("sell_history", []):
            if x.get("pnl_thb") is not None:
                _sales.append({"strategy": _st, "pnl": x["pnl_thb"], "date": x.get("date") or "",
                               "ticker": t.get("ticker", "—")})
        if t.get("status") == "closed" and t.get("pnl_thb") is not None:
            _sales.append({"strategy": _st, "pnl": t["pnl_thb"], "date": t.get("close_date") or "",
                           "ticker": t.get("ticker", "—")})
    wins   = [x for x in _sales if x["pnl"] > 0]
    losses = [x for x in _sales if x["pnl"] <= 0]
    win_rate       = len(wins) / len(_sales) * 100 if _sales else None
    total_win_thb  = sum(x["pnl"] for x in wins)
    total_loss_thb = abs(sum(x["pnl"] for x in losses))
    profit_factor  = round(total_win_thb / total_loss_thb, 2) if total_loss_thb > 0 else None

    # -- Performance KPIs --
    section("Performance")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Open Trades",   len(open_trades))
    k2.metric("Win Rate",      f"{win_rate:.1f}%" if win_rate is not None else "—",
              help="สัดส่วนครั้งที่ขายแล้วได้กำไร นับทุกครั้งที่ขาย รวมขายบางส่วน")
    k3.metric("Profit Factor", f"{profit_factor:.2f}" if profit_factor else "—",
              help="กำไรรวม ÷ ขาดทุนรวม — มากกว่า 1 แปลว่าได้มากกว่าเสีย")
    k4.metric("Realized P&L",  fmt_money(realized_thb, disp, rate) if _tr_realized else "—")
    k5.metric("ขายไปแล้ว", f"{len(_sales)} ครั้ง",
              help=f"ปิดหมด {len(closed_trades)} trade · ที่เหลือคือขายบางส่วน")

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
            "#": "—", "Dir": "—", "Ticker": "TOTAL", "Shares": "—",
            "AVG Price": "—", "Current Price": "—",
            "Cost":          money(_tr_total_cost, _sym_p),
            "Mkt Value":     money(_tr_total_mv, _sym_p),
            "P&L %":         fmt_pct(_tr_pnl_pct_tot),
            f"P&L ({sym})":  money(_tr_total_pnl, _sym_p),
            "TP": "—", "SL": "—",
        })
        _pnl_cols_t = ["P&L %", f"P&L ({sym})"]
        def _color_pnl_t(val):
            if isinstance(val, str) and val.startswith("+"):
                return "color: #3DBE7F; font-weight: 600"
            if isinstance(val, str) and val.startswith("-"):
                return "color: #EF5F55; font-weight: 600"
            return ""
        def _style_total_t(row):
            if row["Ticker"] == "TOTAL":
                return ["background-color: rgba(217,164,65,0.12); font-weight: 700"] * len(row)
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
            arrow = "↑" if t.get("direction") == "Long" else "↓"
            _hc   = "green" if (pnl_thb or 0) >= 0 else "red"
            _cs   = fmt_money(pos_thb, disp, rate, sign=False) if pos_thb else "—"
            _vs   = fmt_money(mkt_val_thb, disp, rate, sign=False) if mkt_val_thb else "—"
            _lev   = trade_leverage(t)
            # on a leveraged trade the price move understates the result on the
            # money actually at risk — show ROE (on margin), the figure Binance shows
            _pct_s = (f"{fmt_pct(pnl_pct * _lev)} ROE" if _lev > 1 and pnl_pct is not None
                      else fmt_pct(pnl_pct))
            header = (f"**{t['ticker']}** {arrow}"
                      + (f" `{_lev:g}x`" if _lev > 1 else "") + "  ·  "
                      f"AVG {t.get('entry_price','—')} → {f'{price:.2f}' if price else '—'}  ·  "
                      f"{_cs} → {_vs}"
                      f"  |  :{_hc}[{_pct_s}  {fmt_money(pnl_thb, disp, rate)}]"
                      ).replace("$", r"\$")

            with st.expander(header):
                # P&L banner
                _pc = "#3DBE7F" if (pnl_thb or 0) >= 0 else "#EF5F55"
                _bg = "rgba(61,190,127,0.08)" if (pnl_thb or 0) >= 0 else "rgba(239,95,85,0.08)"
                st.markdown(
                    f"<div style='background:{_bg};border-left:3px solid {_pc};"
                    f"border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:10px'>"
                    f"<div style='font-size:10px;color:#8B9196;text-transform:uppercase;"
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
                        f"<div style='font-size:12px;color:#6B7176;margin-bottom:2px'>TP</div>"
                        f"<div style='font-size:18px;font-weight:600'>{t.get('take_profit','—')}</div>"
                        f"<div style='font-size:12px;color:#3DBE7F'>"
                        f"Profit {fmt_money(tp_thb, disp, rate) if tp_thb is not None else '—'}</div>",
                        unsafe_allow_html=True)
                with r2c2:
                    st.markdown(
                        f"<div style='font-size:12px;color:#6B7176;margin-bottom:2px'>SL</div>"
                        f"<div style='font-size:18px;font-weight:600'>{t.get('stop_loss','—')}</div>"
                        f"<div style='font-size:12px;color:#EF5F55'>"
                        f"Loss {fmt_money(sl_thb, disp, rate) if sl_thb is not None else '—'}</div>",
                        unsafe_allow_html=True)
                with r2c3:
                    st.markdown(
                        f"<div style='font-size:12px;color:#6B7176;margin-bottom:2px'>R:R &amp; Info</div>"
                        f"<div style='font-size:15px;font-weight:600'>{t.get('rr','—')}</div>"
                        f"<div style='font-size:11px;color:#6B7176'>{get_currency(t)} · เปิด {t.get('open_date','—')}</div>",
                        unsafe_allow_html=True)

                st.caption(f"Thesis: {t.get('thesis','—')}")

                # trims already taken out of this position — they used to be visible
                # only in the Log, so the trade page showed the remaining size with no
                # sign that part of it had been sold and its profit already locked in
                _trims = t.get("sell_history", [])
                if _trims:
                    _sold = sum(parse(x.get("shares")) or 0 for x in _trims)
                    _rpnl = sum(x.get("pnl_thb") or 0 for x in _trims)
                    st.markdown(f"**ขายไปแล้วบางส่วน** · {_sold:,.10g} shares · "
                                f"กำไรที่ realize แล้ว {fmt_money(_rpnl, disp, rate)}")
                    st.dataframe([{
                        "วันที่":       x.get("date", "—"),
                        "จำนวน":       f"{parse(x.get('shares')) or 0:,.10g}",
                        "ราคาขาย":     x.get("price", "—"),
                        "P&L %":       fmt_pct(_trim_pct(x)),
                        f"P&L ({sym})": fmt_money(x.get("pnl_thb"), disp, rate),
                        "คืนเงินเข้า":  x.get("settled_to") or "—",
                        "Lesson":      x.get("lesson") or "—",
                    } for x in sorted(_trims, key=lambda x: x.get("date", ""), reverse=True)],
                        use_container_width=True, hide_index=True)
                st.divider()

                ca, cb, cc, _, cd = st.columns([2, 2, 2, 1, 1])
                if ca.button("ขาย", key=f"btn_close_{t['id']}"):
                    st.session_state[f"show_close_{t['id']}"] = True
                    st.session_state.pop(f"show_edit_{t['id']}", None)
                    st.session_state.pop(f"show_add_{t['id']}", None)
                if cb.button("แก้ไข", key=f"btn_edit_{t['id']}"):
                    st.session_state[f"show_edit_{t['id']}"] = True
                    st.session_state.pop(f"show_close_{t['id']}", None)
                    st.session_state.pop(f"show_add_{t['id']}", None)
                if cc.button("ซื้อเพิ่ม", key=f"btn_add_{t['id']}"):
                    st.session_state[f"show_add_{t['id']}"] = True
                    st.session_state.pop(f"show_close_{t['id']}", None)
                    st.session_state.pop(f"show_edit_{t['id']}", None)
                if cd.button("ลบ", key=f"btn_del_{t['id']}"):
                    trades[:] = [x for x in trades if x["id"] != t["id"]]
                    save_trades(trades)
                    st.rerun()

                if st.session_state.get(f"show_add_{t['id']}"):
                    st.markdown("**ซื้อเพิ่ม**")
                    with st.form(f"form_add_{t['id']}"):
                        ta1, ta2, ta3 = st.columns(3)
                        add_shares = ta1.text_input("จำนวน Shares ที่ซื้อเพิ่ม *", placeholder="เช่น 2")
                        add_price  = ta2.text_input("ราคาที่ซื้อ *", placeholder="เช่น 420")
                        add_date   = ta3.date_input("วันที่ซื้อ", value=date.today())
                        src_id, other_name, other_curr = source_selector(cash, f"add_trade_{t['id']}")
                        if st.form_submit_button("ยืนยันซื้อเพิ่ม"):
                            s_add = parse(add_shares)
                            p_add = parse(add_price)
                            if s_add and p_add:
                                s_old = parse(get_shares(t)) or 0
                                p_old = parse(t.get("entry_price", "0")) or 0
                                s_new = s_old + s_add
                                p_avg = (s_old * p_old + s_add * p_add) / s_new
                                add_thb = s_add * p_add * (rate if get_currency(t) == "USD" else 1)
                                # a leveraged position adds margin, not notional — the
                                # close settles cost / leverage, so both sides must agree
                                add_margin = add_thb / trade_leverage(t)
                                resolved = resolve_source(cash, src_id, other_name, other_curr)
                                cash_deduct(cash, resolved, add_margin, rate)
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
                        # inside a form a free-text "Others" box can't appear on demand, so
                        # offer the presets plus whatever custom value the trade already has
                        _cur_strat  = t.get("strategy", "")
                        _strat_opts = [s for s in STRATEGY_PRESETS if s != "Others"]
                        if _cur_strat and _cur_strat not in _strat_opts:
                            _strat_opts.append(_cur_strat)
                        new_strat  = st.selectbox(
                            "Strategy", _strat_opts,
                            index=_strat_opts.index(_cur_strat) if _cur_strat in _strat_opts else 0)
                        if st.form_submit_button("บันทึก"):
                            _matched = next((a for a in cash if a["name"] == new_acct), None)
                            t.update({
                                "ticker": new_ticker.upper().strip(),
                                "shares": new_shares, "stop_loss": new_sl,
                                "take_profit": new_tp, "entry_price": new_entry,
                                "thesis": new_thesis,
                                "rr": auto_rr(new_entry, new_sl, new_tp),
                                "direction": new_dir,
                                "strategy": new_strat,
                                "source_account_name": _matched["name"] if _matched else "",
                                "source_account_id":   _matched["id"]   if _matched else None,
                            })
                            save_trades(trades)
                            st.session_state.pop(f"show_edit_{t['id']}", None)
                            st.success("แก้ไขเรียบร้อย!")
                            st.rerun()

                if st.session_state.get(f"show_close_{t['id']}"):
                    st.markdown("**ขาย**")
                    s_current = parse(get_shares(t)) or 0
                    st.caption(f"ถืออยู่ {s_current:,.10g} shares · AVG {t.get('entry_price','—')}")
                    with st.form(f"form_close_{t['id']}"):
                        # a button can't fill a field inside a form, so Max is a tick
                        # read on submit — it sells exactly what is held, no typing
                        tc1, tcm, tc2, tc3 = st.columns([3, 1, 3, 3])
                        sell_shares = tc1.text_input("จำนวน Shares ที่ขาย *", placeholder=f"สูงสุด {s_current:,.10g}")
                        with tcm:
                            st.markdown("<div style='height:35px'></div>", unsafe_allow_html=True)
                            sell_max = st.checkbox("Max", key=f"close_max_{t['id']}",
                                                   help="ขายหมดทั้ง position ไม่ต้องพิมพ์จำนวน")
                        exit_p      = tc2.text_input("Exit Price *")
                        exit_d      = tc3.date_input("วันที่ปิด", value=date.today())
                        tc4, tc5    = st.columns(2)
                        thesis_ok   = tc4.selectbox("Thesis ถูกไหม (ถ้าขายหมด)",
                                                     ["✅ ถูก", "❌ ผิด", "⚠️ บางส่วน"])
                        emotion     = tc5.selectbox("Emotion (ถ้าขายหมด)",
                                                     ["ปกติ", "กลัว", "โลภ", "FOMO"])
                        lesson      = st.text_input("Lesson ที่ได้", placeholder="ขายบางส่วนก็ใส่ได้ เช่น ขายก่อนเพราะชะล่าใจ")
                        # Choose where the money lands instead of always crediting the
                        # opening account in silence. Keyed by account id, not name:
                        # names change on rename and can repeat across currencies, and
                        # a name lookup would quietly credit nothing or the wrong one.
                        _dest_ids  = [a["id"] for a in cash] + [None]
                        _dest_lbl  = {a["id"]: acc_label(a) for a in cash}
                        _src_id    = t.get("source_account_id")
                        # An imported position never had its cost deducted, so crediting
                        # it back by default puts money in that never left — the exact
                        # way a Binance future landed ฿154,897 in Streaming. Default to no
                        # cash move and let the person pick the account deliberately.
                        if t.get("is_import") or _src_id not in _dest_ids:
                            _dest_idx = len(_dest_ids) - 1
                        else:
                            _dest_idx = _dest_ids.index(_src_id)
                        dest_id = st.selectbox(
                            "คืนเงินเข้าบัญชี", _dest_ids, index=_dest_idx,
                            format_func=lambda i: "— ไม่คืนเงินเข้า Cash" if i is None else _dest_lbl[i],
                            key=f"close_dest_{t['id']}")
                        if t.get("is_import"):
                            st.caption("Position Import — ตั้งไว้ไม่คืนเงิน ถ้าเงินเข้าบัญชีจริงให้เลือกบัญชี")
                        allow_neg = st.checkbox("ยืนยันว่าขาดทุนเกินเงินที่วางจริง (cross margin)",
                                                key=f"close_neg_{t['id']}",
                                                help="ติ๊กเฉพาะเมื่อขาดทุนเกินเงินที่วางไว้จริง "
                                                     "เช่น futures แบบ cross margin")
                        if st.form_submit_button("ยืนยันขาย"):
                            s_sell = s_current if sell_max else parse(sell_shares)
                            ep     = parse(exit_p)
                            if not s_sell or not ep:
                                st.error("กรุณากรอกจำนวน shares และ Exit Price")
                            elif s_sell > s_current:
                                st.error(f"ขายได้สูงสุด {s_current} shares")
                            # A close that returns less than nothing debits the account. Real
                            # under cross margin, so not clamped — but far more often a typo
                            # (exit 8.5 for 85 on a 10x long would take ~8x the margin), so it
                            # must be confirmed. Shown here, before any rerun, so it is seen.
                            elif (settle_thb(t, s_sell,
                                             calc_pnl_thb(t["entry_price"], ep, str(s_sell),
                                                          get_currency(t), rate,
                                                          t.get("direction", "Long")),
                                             rate) < 0 and not allow_neg):
                                st.error("ราคาปิดนี้ทำให้ขาดทุนเกินเงินที่วางไว้ — บัญชีจะถูกหักเพิ่ม "
                                         "ตรวจ Exit Price อีกครั้ง ถ้าถูกต้องจริง (cross margin) "
                                         "ให้ติ๊กช่องยืนยันแล้วกดใหม่")
                            else:
                                _dest     = next((a for a in cash if a["id"] == dest_id), None)
                                currency  = get_currency(t)
                                direction = t.get("direction", "Long")
                                if s_sell >= s_current:
                                    pnl_pct_v = calc_pnl_pct(t["entry_price"], ep, direction)
                                    pnl_thb_v = calc_pnl_thb(t["entry_price"], ep, str(s_current), currency, rate, direction)
                                    # computed before the update so the filed THB figure and the
                                    # rate behind it are stored, not just recomputed on display
                                    exit_thb = s_current * ep * (rate if currency == "USD" else 1)
                                    if direction == "Short":
                                        entry_thb = s_current * (parse(t["entry_price"]) or 0) * (rate if currency == "USD" else 1)
                                        exit_thb  = 2 * entry_thb - exit_thb
                                    t.update({
                                        "status": "closed", "exit_price": str(ep),
                                        "close_date": str(exit_d), "thesis_correct": thesis_ok,
                                        "emotion": emotion, "lesson": lesson,
                                        "pnl_pct": pnl_pct_v, "pnl_thb": pnl_thb_v,
                                        "fx_rate_at_close": round(rate, 4),
                                        "proceeds_thb": round(exit_thb, 2),
                                        "win_loss": "Win" if (pnl_thb_v or 0) > 0 else "Loss",
                                    })
                                    _settle = settle_thb(t, s_current, pnl_thb_v, rate)
                                    t.update({"settled_thb": round(_settle, 2),
                                              "settled_to": _dest["name"] if _dest else ""})
                                    if _dest:
                                        cash_credit(cash, _dest["id"], _settle, rate)
                                        save_cash(cash)
                                    save_trades(trades)
                                    st.session_state.pop(f"show_close_{t['id']}", None)
                                    _where = (f" · คืน {fmt_money(_settle, disp, rate, sign=False)} เข้า {_dest['name']}"
                                              if _dest else " · ไม่ได้คืนเงินเข้า Cash")
                                    st.success(f"ปิด Trade · P&L = {fmt_money(pnl_thb_v, disp, rate)}{_where}")
                                else:
                                    s_remain   = round(s_current - s_sell, 8)
                                    pnl_thb_p  = calc_pnl_thb(t["entry_price"], ep, str(s_sell), currency, rate, direction)
                                    exit_thb_p = s_sell * ep * (rate if currency == "USD" else 1)
                                    if direction == "Short":
                                        entry_thb_p = s_sell * (parse(t["entry_price"]) or 0) * (rate if currency == "USD" else 1)
                                        exit_thb_p  = 2 * entry_thb_p - exit_thb_p
                                    _settle_p = settle_thb(t, s_sell, pnl_thb_p, rate)
                                    sell_hist = t.get("sell_history", [])
                                    sell_hist.append({
                                        "date": str(exit_d), "shares": str(s_sell),
                                        "price": str(ep), "pnl_thb": round(pnl_thb_p or 0, 2),
                                        "thb": round(exit_thb_p, 2),
                                        "fx_rate": round(rate, 4),
                                        "settled_thb": round(_settle_p, 2),
                                        "settled_to": _dest["name"] if _dest else "",
                                        "lesson": lesson.strip(),
                                    })
                                    new_pos_thb = (t.get("position_thb") or 0) * (s_remain / s_current)
                                    t.update({
                                        "shares":       str(s_remain),
                                        "position_thb": round(new_pos_thb, 2),
                                        "sell_history": sell_hist,
                                        "rr": auto_rr(t["entry_price"], t.get("stop_loss",""), t.get("take_profit","")),
                                    })
                                    if _dest:
                                        cash_credit(cash, _dest["id"], _settle_p, rate)
                                        save_cash(cash)
                                    save_trades(trades)
                                    st.session_state.pop(f"show_close_{t['id']}", None)
                                    st.success(f"ขาย {s_sell} shares @ {ep} · เหลือ {s_remain} shares · P&L = {fmt_money(pnl_thb_p, disp, rate)}")
                                st.rerun()

    # -- Analytics --
    # Plain-language scorecard instead of a win/loss donut and an axis chart: it has
    # to answer "how much did I win, how many times, with which strategy" at a glance.
    if not _sales and open_trades:
        st.info("ยังไม่มีการขาย")
    if _sales:
        section("สรุปผลงาน")
        G, R, MUTED, TXT = "#3DBE7F", "#EF5F55", "#8B9196", "#E9E6DF"

        def _m(v):  # money for HTML; a bare $ pair would be read as LaTeX
            return fmt_money(v, disp, rate).replace("$", "&#36;")

        def _tile(label, big, sub, color):
            return (f"<div style='flex:1;min-width:150px;background:rgba(255,255,255,0.03);"
                    f"border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px 14px'>"
                    f"<div style='font-size:12px;color:{MUTED}'>{label}</div>"
                    f"<div style='font-size:24px;font-weight:700;color:{color};margin:2px 0'>{big}</div>"
                    f"<div style='font-size:12px;color:{MUTED}'>{sub}</div></div>")

        net = total_win_thb - total_loss_thb
        _avg_w = total_win_thb / len(wins) if wins else None
        _avg_l = -total_loss_thb / len(losses) if losses else None
        tiles = "".join([
            _tile(f"ชนะ {len(wins)} ครั้ง", _m(total_win_thb),
                  f"เฉลี่ย {_m(_avg_w)} / ครั้ง" if wins else "ยังไม่มี", G),
            _tile(f"แพ้ {len(losses)} ครั้ง", _m(-total_loss_thb),
                  f"เฉลี่ย {_m(_avg_l)} / ครั้ง" if losses else "ยังไม่มี", R),
            _tile("สุทธิ", _m(net), f"จากการขาย {len(_sales)} ครั้ง", G if net >= 0 else R),
        ])
        _wp = win_rate or 0
        bar = (f"<div style='display:flex;justify-content:space-between;font-size:12px;"
               f"color:{MUTED};margin:12px 0 4px'><span>ชนะ {_wp:.0f}%</span>"
               f"<span>แพ้ {100 - _wp:.0f}%</span></div>"
               f"<div style='display:flex;height:8px;border-radius:4px;overflow:hidden;"
               f"background:{R}'><div style='width:{_wp:.1f}%;background:{G}'></div></div>")
        st.markdown(f"<div style='display:flex;gap:10px;flex-wrap:wrap'>{tiles}</div>{bar}",
                    unsafe_allow_html=True)

        # by strategy, best first; bar length = share of the biggest absolute result
        by: dict[str, dict] = {}
        for x in _sales:
            d = by.setdefault(x["strategy"], {"n": 0, "w": 0, "net": 0.0})
            d["n"] += 1; d["w"] += x["pnl"] > 0; d["net"] += x["pnl"]
        _mx = max(abs(d["net"]) for d in by.values()) or 1
        rows = []
        for name, d in sorted(by.items(), key=lambda kv: kv[1]["net"], reverse=True):
            c = G if d["net"] >= 0 else R
            rows.append(
                f"<div style='padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06)'>"
                f"<div style='display:flex;justify-content:space-between;gap:8px;align-items:baseline'>"
                f"<span style='color:{TXT};font-weight:600'>{html.escape(name)}</span>"
                f"<span style='color:{c};font-weight:700'>{_m(d['net'])}</span></div>"
                f"<div style='display:flex;justify-content:space-between;gap:8px;font-size:12px;"
                f"color:{MUTED};margin:2px 0 5px'><span>ชนะ {d['w']}/{d['n']} ครั้ง · "
                f"{d['w'] / d['n'] * 100:.0f}%</span><span>เฉลี่ย {_m(d['net'] / d['n'])} / ครั้ง</span></div>"
                f"<div style='height:5px;border-radius:3px;background:rgba(255,255,255,0.05)'>"
                f"<div style='height:5px;border-radius:3px;width:{abs(d['net']) / _mx * 100:.1f}%;"
                f"background:{c}'></div></div></div>")
        st.markdown(f"<div style='font-size:13px;color:{MUTED};margin:20px 0 2px'>"
                    f"แยกตาม Strategy — เรียงจากทำเงินได้มากสุด</div>{''.join(rows)}",
                    unsafe_allow_html=True)

    # -- Closed Trades Table --
    # Every sale, not only full closes: a trim on a still-open trade locks in profit
    # too, and used to be visible only in the Log. A trade trimmed then closed shows
    # one row per trim plus the final close, which only covers the remaining shares,
    # so nothing is counted twice.
    def _pct_txt(t, pct):
        lev = trade_leverage(t)
        if lev > 1 and isinstance(pct, (int, float)):
            return f"{fmt_pct(pct * lev)} ROE ({lev:g}x)"
        return fmt_pct(pct)

    def _qty(v):
        n = parse(v)
        return "—" if n is None else f"{n:,.10g}"

    _sale_rows = []
    for t in closed_trades:
        _sale_rows.append({
            "Ticker":       t.get("ticker","—"),
            "การขาย":       "ปิดหมด",
            "Strategy":     t.get("strategy","—"),
            "เปิด":         t.get("open_date","—"),
            "ปิด":          t.get("close_date","—"),
            "จำนวน":        _qty(get_shares(t)),
            "Entry":        str(t.get("entry_price","—")),
            "Exit":         str(t.get("exit_price","—")),
            "P&L %":        _pct_txt(t, t.get("pnl_pct")),
            f"P&L ({sym})": fmt_money(t.get("pnl_thb"), disp, rate),
            "W/L":          t.get("win_loss","—"),
            "Lesson":       t.get("lesson","—"),
        })
    for t in trades:
        for x in t.get("sell_history", []):
            _p = x.get("pnl_thb")
            _sale_rows.append({
                "Ticker":       t.get("ticker","—"),
                "การขาย":       "ขายบางส่วน" + (" · ยังถืออยู่" if t.get("status") == "open" else ""),
                "Strategy":     t.get("strategy","—"),
                "เปิด":         t.get("open_date","—"),
                "ปิด":          x.get("date","—"),
                "จำนวน":        _qty(x.get("shares")),
                "Entry":        str(t.get("entry_price","—")),
                "Exit":         str(x.get("price","—")),
                "P&L %":        _pct_txt(t, _trim_pct(x)),
                f"P&L ({sym})": fmt_money(_p, disp, rate),
                "W/L":          "—" if _p is None else ("Win" if _p > 0 else "Loss"),
                "Lesson":       x.get("lesson") or "—",
            })
    # -- Past Performance --
    # One row per trade, every sale folded together: the reader wants "what did this
    # trade make", not the trim-by-trim mechanics, which stay in Closed Trades below.
    _perf = []
    for t in trades:
        legs = []  # (date, shares, price, pnl, cost)
        # cost from what was stored at sale time; rebuilt from entry x shares only for
        # old rows that predate it, at the rate saved with the sale when there is one
        def _cost_fb(shares, fx):
            return calc_position_thb(t.get("entry_price"), shares, get_currency(t), fx or rate)
        for x in t.get("sell_history", []):
            if x.get("pnl_thb") is None: continue
            _c = (x["thb"] - x["pnl_thb"]) if x.get("thb") is not None \
                 else _cost_fb(x.get("shares"), x.get("fx_rate"))
            legs.append((x.get("date") or "", parse(x.get("shares")), parse(x.get("price")),
                         x["pnl_thb"], _c))
        if t.get("status") == "closed" and t.get("pnl_thb") is not None:
            _c = (t["proceeds_thb"] - t["pnl_thb"]) if t.get("proceeds_thb") is not None \
                 else (t.get("position_thb") or _cost_fb(get_shares(t), t.get("fx_rate_at_close")))
            legs.append((t.get("close_date") or "", parse(get_shares(t)),
                         parse(t.get("exit_price")), t["pnl_thb"], _c))
        if not legs: continue
        pnl  = sum(l[3] for l in legs)
        cost = sum(l[4] for l in legs if l[4] is not None)
        _sw  = [(l[1], l[2]) for l in legs if l[1] and l[2] is not None]
        avg_exit = (sum(a * b for a, b in _sw) / sum(a for a, _ in _sw)) if _sw else None
        last = max(l[0] for l in legs)
        try:
            days = (date.fromisoformat(last[:10]) - date.fromisoformat(str(t.get("open_date"))[:10])).days
        except Exception:
            days = None
        lev = trade_leverage(t)
        pct = pnl / cost * 100 * lev if cost > 0 else None
        _perf.append({"t": t, "date": last, "pnl": pnl, "cost": cost, "avg_exit": avg_exit,
                      "days": days, "lev": lev, "pct": pct,
                      "open": t.get("status") == "open"})

    if _perf:
        _perf.sort(key=lambda r: r["date"], reverse=True)
        _hide = hidden_amounts()
        _G, _R = "#3DBE7F", "#EF5F55"

        # ① Equity curve: cumulative realized after each sale, with the drop from the
        # running peak underneath. Answers "is this getting better or worse".
        _seq = sorted(_sales, key=lambda x: x["date"])
        _cum, _peak, eq, dd = 0.0, 0.0, [], []
        for x in _seq:
            _cum += x["pnl"]; _peak = max(_peak, _cum)
            eq.append(to_display(_cum, disp, rate)); dd.append(to_display(_cum - _peak, disp, rate))
        _dts = [x["date"] for x in _seq]
        _hv = [f"{x['date']} · {x['ticker']}<br>{fmt_money(x['pnl'], disp, rate)}" for x in _seq]
        fig_eq = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28],
                               vertical_spacing=0.04)
        fig_eq.add_trace(go.Scatter(
            x=_dts, y=eq, mode="lines+markers", line=dict(color="#8B9196", width=2, shape="hv"),
            marker=dict(size=8, color=[_G if x["pnl"] > 0 else _R for x in _seq],
                        line=dict(color="#14181B", width=1.5)),
            text=_hv, hovertemplate="%{text}<extra></extra>"), row=1, col=1)
        fig_eq.add_trace(go.Scatter(
            x=_dts, y=dd, mode="lines", line=dict(color=_R, width=1, shape="hv"),
            fill="tozeroy", fillcolor="rgba(239,95,85,0.18)", hoverinfo="skip"), row=2, col=1)
        fig_eq.update_layout(**{**CHART_LAYOUT, "height": 340,
            "title": dict(text="Realized สะสม · Drawdown", font=dict(size=14, color="#8B9196"), x=0)})
        fig_eq.update_yaxes(automargin=True, showgrid=True, gridcolor="rgba(255,255,255,0.06)", tickformat=",.0f",
                            tickfont=dict(size=11, color="#6B7176"), showticklabels=not _hide,
                            zeroline=True, zerolinecolor="rgba(255,255,255,0.15)")
        fig_eq.update_xaxes(automargin=True, showgrid=False, tickfont=dict(size=11, color="#8B9196"))
        if _hide:
            fig_eq.update_traces(hoverinfo="skip", hovertemplate=None)

        # ② P&L per trade in time order: shows whether losses are small next to wins
        _bt = sorted(_perf, key=lambda r: r["date"])
        fig_bt = go.Figure(go.Bar(
            x=list(range(len(_bt))), y=[to_display(r["pnl"], disp, rate) for r in _bt],
            marker=dict(color=[_G if r["pnl"] > 0 else _R for r in _bt], opacity=0.9),
            text=[f"{r['date']} · {r['t'].get('ticker','—')}<br>{fmt_money(r['pnl'], disp, rate)}"
                  for r in _bt],
            textposition="none", hovertemplate="%{text}<extra></extra>"))
        fig_bt.update_layout(**{**CHART_LAYOUT, "height": 300, "bargap": 0.25,
            "title": dict(text="P&L รายเทรด", font=dict(size=14, color="#8B9196"), x=0)})
        fig_bt.update_xaxes(automargin=True, tickvals=list(range(len(_bt))),
                            ticktext=[r["t"].get("ticker", "—").replace(".BK", "") for r in _bt],
                            tickangle=-45 if len(_bt) > 8 else 0)
        fig_bt.update_yaxes(automargin=True, tickformat=",.0f", showticklabels=not _hide)
        if _hide:
            fig_bt.update_traces(hoverinfo="skip", hovertemplate=None)

        _c1, _c2 = st.columns(2)
        _c1.plotly_chart(fig_eq, use_container_width=True)
        _c2.plotly_chart(fig_bt, use_container_width=True)

        PER = 15
        n_pages = (len(_perf) - 1) // PER + 1
        pg = min(max(st.session_state.get("pp_page", 1), 1), n_pages)
        section(f"Past Performance ({len(_perf)} trades)")
        G, R, MUTED, TXT, LINE = "#3DBE7F", "#EF5F55", "#8B9196", "#E9E6DF", "rgba(255,255,255,0.07)"

        def _h(v):  # escape for HTML; a bare $ pair would be read as LaTeX
            return html.escape(str(v)).replace("$", "&#36;")

        th = (f"padding:8px 10px;font-size:11px;font-weight:600;color:{MUTED};text-transform:uppercase;"
              f"letter-spacing:0.05em;border-bottom:1px solid {LINE};white-space:nowrap")
        td = f"padding:9px 10px;border-bottom:1px solid {LINE};white-space:nowrap"
        heads = [("วันที่ขาย", "left"), ("Ticker", "left"), ("Strategy", "left"), ("ถือ", "right"),
                 ("Size", "right"), ("Return", "right"), ("P&L", "right")]
        out = ["<div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse;"
               f"font-size:14px;color:{TXT};font-variant-numeric:tabular-nums'><thead><tr>"
               + "".join(f"<th style='{th};text-align:{al}'>{h}</th>" for h, al in heads)
               + "</tr></thead><tbody>"]
        for r in _perf[(pg - 1) * PER: pg * PER]:
            t = r["t"]; c = G if r["pnl"] > 0 else (R if r["pnl"] < 0 else MUTED)
            badge = (f" <span style='font-size:11px;color:{MUTED};border:1px solid {LINE};"
                     f"border-radius:4px;padding:1px 5px'>ยังถืออยู่</span>" if r["open"] else "")
            lev_b = (f" <span style='font-size:11px;color:{MUTED}'>{r['lev']:g}x</span>"
                     if r["lev"] > 1 else "")
            held = "—" if r["days"] is None else f"{r['days']} วัน"
            pct = (fmt_pct(r["pct"]) + (" ROE" if r["lev"] > 1 else "")) if r["pct"] is not None else "—"
            out.append(
                "<tr>"
                f"<td style='{td};color:{MUTED}'>{_h(r['date'])}</td>"
                f"<td style='{td};font-weight:700'>{_h(t.get('ticker','—'))}{badge}</td>"
                f"<td style='{td}'>{_h(t.get('strategy') or '—')}</td>"
                f"<td style='{td};text-align:right;color:{MUTED}'>"
                f"{held}</td>"
                f"<td style='{td};text-align:right'>{_h(fmt_money(r['cost'], disp, rate, sign=False) if r['cost'] else '—')}{lev_b}</td>"
                f"<td style='{td};text-align:right;color:{c}'>{_h(pct)}</td>"
                f"<td style='{td};text-align:right;color:{c};font-weight:700'>{_h(fmt_money(r['pnl'], disp, rate))}</td>"
                "</tr>")
        out.append("</tbody></table></div>")
        st.markdown("".join(out), unsafe_allow_html=True)
        if n_pages > 1:
            p1, p2, p3 = st.columns([1, 2, 1])
            if p1.button("← ก่อนหน้า", key="pp_prev", disabled=pg <= 1, use_container_width=True):
                st.session_state["pp_page"] = pg - 1; st.rerun()
            p2.markdown(f"<div style='text-align:center;color:{MUTED};padding-top:8px'>"
                        f"หน้า {pg} / {n_pages}</div>", unsafe_allow_html=True)
            if p3.button("ถัดไป →", key="pp_next", disabled=pg >= n_pages, use_container_width=True):
                st.session_state["pp_page"] = pg + 1; st.rerun()

    if _sale_rows:
        _sale_rows.sort(key=lambda r: r["ปิด"] or "", reverse=True)
        _n_trim = len(_sale_rows) - len(closed_trades)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        with st.expander(f"Closed Trades — ทุกครั้งที่ขาย ({len(_sale_rows)})"
                         + (f" · ขายบางส่วน {_n_trim}" if _n_trim else "")):
            st.dataframe(pd.DataFrame(_sale_rows), use_container_width=True, hide_index=True)

    _journal = [t for t in trades if t.get("status") == "closed" or t.get("sell_history")]
    if _journal:

        # Journal fields only. Price, size and dates stay locked: the cash has already
        # settled against them, and changing them here would desync every balance.
        with st.expander("แก้ไขบันทึก Trade (Strategy / Lesson)"):
            _ct_sorted = sorted(_journal, key=lambda x: x.get("close_date") or max(
                (h.get("date", "") for h in x.get("sell_history", [])), default=""), reverse=True)
            _ct_lbl = {t["id"]: f"{t.get('ticker','—')} · "
                                + (f"ปิด {t.get('close_date','—')}" if t.get("status") == "closed"
                                   else "ยังถืออยู่ · ขายบางส่วนแล้ว")
                                + f" · {t.get('strategy','—')}" for t in _ct_sorted}
            ct_id = st.selectbox("เลือก Trade", list(_ct_lbl), format_func=lambda i: _ct_lbl[i],
                                 key="ct_edit_pick")
            ct = next(t for t in _journal if t["id"] == ct_id)
            _ct_closed = ct.get("status") == "closed"
            # outside a form so picking "Others" reveals its text box immediately
            ct_strategy = strategy_input(f"ct_{ct_id}", ct.get("strategy", ""))
            if _ct_closed:
                _emo_opts = ["ปกติ", "กลัว", "โลภ", "FOMO"]
                _th_opts  = ["✅ ถูก", "❌ ผิด", "⚠️ บางส่วน"]
                ce1, ce2 = st.columns(2)
                ct_emotion = ce1.selectbox(
                    "Emotion", _emo_opts, key=f"ct_emo_{ct_id}",
                    index=_emo_opts.index(ct["emotion"]) if ct.get("emotion") in _emo_opts else 0)
                ct_thesis = ce2.selectbox(
                    "Thesis ถูกไหม", _th_opts, key=f"ct_th_{ct_id}",
                    index=_th_opts.index(ct["thesis_correct"]) if ct.get("thesis_correct") in _th_opts else 0)
                ct_lesson = st.text_area("Lesson (ตอนปิดหมด)", value=ct.get("lesson", ""), height=80,
                                         key=f"ct_les_{ct_id}")
            # a trim's lesson often only becomes clear later, e.g. sold half early out
            # of complacency and the rest went much higher, so each one stays editable
            _trim_les = []
            for _i, _h in enumerate(ct.get("sell_history", [])):
                _trim_les.append(st.text_input(
                    f"Lesson ขายบางส่วน {_h.get('date','—')} · {_h.get('shares','—')} @ {_h.get('price','—')}",
                    value=_h.get("lesson", ""), key=f"ct_tles_{ct_id}_{_i}"))
            if st.button("บันทึกการแก้ไข", key=f"ct_save_{ct_id}"):
                if not (ct_strategy or "").strip():
                    st.error("กรุณาระบุ Strategy")
                else:
                    ct["strategy"] = ct_strategy.strip()
                    if _ct_closed:
                        ct.update({"emotion": ct_emotion, "thesis_correct": ct_thesis,
                                   "lesson": ct_lesson.strip()})
                    for _h, _v in zip(ct.get("sell_history", []), _trim_les):
                        _h["lesson"] = _v.strip()
                    save_trades(trades)
                    st.rerun()

    # -- New Trade Form (collapsed) --
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    with st.expander("เปิด Trade ใหม่"):
        strategy = strategy_input("nt")
        with st.form("new_trade"):
            c1, c2, c3, c4 = st.columns(4)
            ticker    = c1.text_input("Ticker *", placeholder="เช่น AAPL, BTC-USD")
            direction = c2.selectbox("Direction", ["Long", "Short"])
            currency  = c3.selectbox("ราคาเป็น", ["THB", "USD"])
            shares    = c4.text_input("จำนวนหุ้น *", placeholder="เช่น 100")
            c5, c6, c7, c8 = st.columns(4)
            entry     = c5.text_input("Entry Price *")
            sl        = c6.text_input("Stop Loss")
            tp        = c7.text_input("Take Profit")
            lev_in    = c8.text_input("Leverage (x)", value="1",
                                      help="หุ้นปกติ = 1 · Futures ใส่ตามที่เปิดใน Binance เช่น 10 · "
                                           "ใส่จำนวนตามขนาด position จริง (notional) "
                                           "ระบบจะหักเงินแค่ margin = ขนาด ÷ leverage")
            thesis    = st.text_area("Thesis *", height=80,
                                     placeholder="เหตุผลสั้นๆ ที่ชัดเจน")
            open_date = st.date_input("วันที่เปิด", value=date.today())
            st.markdown("---")
            src_id, other_name, other_curr = source_selector(cash, "trade")
            is_import = st.checkbox("Import position เก่า (ไม่หักเงินจาก Cash)", key="import_trade")
            if st.form_submit_button("บันทึก Trade"):
                e, s = parse(entry), parse(shares)
                # accept "10x" — the field is labelled (x), and treating it as unparseable
                # used to fall back to 1x and deduct the full notional, the very bug this
                # field exists to prevent. Reject anything non-finite: NaN slips past a
                # plain range check because every comparison with it is False.
                _lev_s = (lev_in or "").strip().lower().rstrip("x").strip()
                lev    = parse(_lev_s) if _lev_s else 1.0
                if not ticker or e is None:
                    st.error("กรุณากรอก Ticker และ Entry Price")
                elif not strategy:
                    st.error("กรุณาเลือก Strategy")
                elif lev is None or not math.isfinite(lev) or lev < 1 or lev > 125:
                    st.error("Leverage ต้องเป็นตัวเลข 1 ถึง 125 (เช่น 10 หรือ 10x)")
                else:
                    rr       = auto_rr(entry, sl, tp)
                    pos_thb  = (s or 0) * e * (rate if currency == "USD" else 1)
                    # notional stays in position_thb (exposure, used for sizing and P&L);
                    # only the margin actually leaves the account
                    margin_thb = pos_thb / lev
                    resolved = resolve_source(cash, src_id, other_name, other_curr)
                    if not is_import:
                        cash_deduct(cash, resolved, margin_thb, rate)
                        save_cash(cash)
                    trades.append({
                        "id": next_id(trades), "type": "trade", "status": "open",
                        "ticker": ticker.upper().strip(), "direction": direction,
                        "strategy": strategy, "currency": currency,
                        "entry_price": entry, "shares": shares,
                        "stop_loss": sl, "take_profit": tp, "rr": rr,
                        "thesis": thesis, "open_date": str(open_date),
                        "position_thb": round(pos_thb, 2),
                        "leverage": lev,
                        # remembered so a later close can tell the cost never left an account
                        "is_import": bool(is_import),
                        "source_account_id": resolved,
                        "source_account_name": next((a["name"] for a in cash if a["id"] == resolved), ""),
                    })
                    save_trades(trades)
                    _lev_txt = (f" · {lev:g}x · Margin {fmt_money(margin_thb, disp, rate, sign=False)}"
                                if lev > 1 else "")
                    st.success(f"บันทึกแล้ว · R:R = {rr} · Position: "
                               f"{fmt_money(pos_thb, disp, rate, sign=False)}{_lev_txt}")
                    st.rerun()


# -- Page 4: Cash --
def page_cash(trades: list, investments: list, cash: list, disp: str, rate: float):

    # -- Summary metrics --
    section("Summary")
    cash_usd = sum(a["amount"] for a in cash if a["currency"] == "USD")
    cash_thb = sum(a["amount"] for a in cash if a["currency"] == "THB")
    cash_total_thb = (cash_usd * rate) + cash_thb

    cashouts     = build_cashouts(cash)
    cashout_thb  = sum(c["amount_thb"] or 0 for c in cashouts)
    deposits     = build_deposits(cash)
    deposit_thb  = sum(d["amount_thb"] or 0 for d in deposits)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Cash THB รวม", money(cash_thb))
    m2.metric("Cash USD รวม", money(cash_usd, "$", 2))
    m3.metric(f"Net Cash ({disp})", fmt_money(cash_total_thb, disp, rate, sign=False) if cash else "฿0")
    m4.metric("Deposit",
              fmt_money(deposit_thb, disp, rate, sign=False) if deposits else "—",
              help="เงินที่เติมเข้าพอร์ตจากข้างนอก — นับตั้งแต่เริ่มบันทึกผ่านปุ่มเติมเงิน")
    if deposits:
        m4.caption(f"{len(deposits)} ครั้ง · ล่าสุด {deposits[0]['date']}")
    m5.metric("Cash Out",
              fmt_money(cashout_thb, disp, rate, sign=False) if cashouts else "—")
    if cashouts:
        _rem = sum(c["amount_thb"] or 0 for c in cashouts if c["remitted"])
        m5.caption(f"{len(cashouts)} ครั้ง · เข้าไทย {fmt_money(_rem, disp, rate, sign=False)}")

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
                clr     = "#3DBE7F" if acc["amount"] >= 0 else "#EF5F55"
                sym     = "$" if acc["currency"] == "USD" else "฿"
                fmt     = money(acc['amount'], sym, 2 if acc["currency"] == "USD" else 0)
                val_thb = acc["amount"] * rate if acc["currency"] == "USD" else acc["amount"]
                sub     = f"≈{money(val_thb)}" if acc["currency"] == "USD" else acc["currency"]

                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.04);"
                    f"border:1px solid rgba(255,255,255,0.07);border-radius:12px 12px 0 0;"
                    f"padding:14px 20px;display:flex;justify-content:space-between;"
                    f"align-items:center;margin-bottom:0'>"
                    f"<span style='font-size:0.7rem;color:#8B9196;text-transform:uppercase;"
                    f"letter-spacing:0.09em;min-width:80px'>{acc['name']}</span>"
                    f"<span style='font-size:1.55rem;font-weight:700;color:{clr}'>{fmt}</span>"
                    f"<span style='font-size:0.72rem;color:#6B7176;text-align:right'>{sub}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                with st.expander("จัดการ", expanded=False):
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
                            if st.form_submit_button("บันทึก", use_container_width=True):
                                acc["name"]   = new_name.strip() or acc["name"]
                                acc["amount"] = round(parse(new_amount) or 0, 2)
                                save_cash(cash)
                                st.rerun()

                    if other_accs:
                        with _ec2:
                            st.caption("Reassign")
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
                                    st.success(f"ย้ายเข้า '{target['name']}' แล้ว")
                                    st.rerun()

                    with _ec3:
                        st.caption("ลบ")
                        st.markdown("<div style='height:1.55rem'></div>", unsafe_allow_html=True)
                        if st.button("ลบ", key=f"del_acc_{acc['id']}",
                                     use_container_width=True):
                            cash[:] = [a for a in cash if a["id"] != acc["id"]]
                            save_cash(cash)
                            st.rerun()
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # -- Deposit (money coming into the portfolio from outside) --
    if cash:
        with st.expander("Deposit — เติมเงินเข้าพอร์ต"):
            # picker outside the form so the currency in the amount label follows
            # the chosen account immediately (inside a form it only updates on submit)
            _dopts = [acc_label(a) for a in cash]
            d_idx = st.selectbox("เข้าบัญชี", range(len(_dopts)),
                                 format_func=lambda i: _dopts[i], key="dep_acc")
            _dacc = cash[d_idx]
            with st.form("deposit_form", clear_on_submit=True):
                dc1, dc2, dc3 = st.columns([3, 3, 4])
                d_amt  = dc1.text_input(f"ยอดเติม ({_dacc['currency']})", "")
                d_dt   = dc2.date_input("วันที่เติม", value=date.today())
                d_note = dc3.text_input("บันทึก (ไม่บังคับ)", "",
                                        placeholder="เช่น เงินเดือน / โอนจาก SCB / DCA")
                if st.form_submit_button("เติมเงิน", use_container_width=True):
                    amt = parse(d_amt)
                    if not amt or amt <= 0:
                        st.error("ใส่ยอดเติมให้ถูกต้อง")
                    else:
                        amt_thb = amt * rate if _dacc["currency"] == "USD" else amt
                        _dacc.setdefault("deposits", []).append({
                            "date": str(d_dt), "amount": round(amt, 2),
                            "amount_thb": round(amt_thb, 2),
                            "fx_rate": round(rate, 4), "note": d_note.strip(),
                        })
                        _dacc["amount"] = round(_dacc["amount"] + amt, 2)
                        save_cash(cash)
                        _s = "$" if _dacc["currency"] == "USD" else "฿"
                        st.success(f"เติม {money(amt, _s, 2)} เข้า {_dacc['name']} แล้ว")
                        st.rerun()

    # -- Cash out (money leaving the portfolio to be spent) --
    if cash:
        with st.expander("Cash Out — ถอนเงินออกไปใช้"):
            with st.form("cashout_form", clear_on_submit=True):
                oc1, oc2, oc3 = st.columns([4, 3, 3])
                _opts = [acc_label(a) for a in cash]
                o_idx = oc1.selectbox("จากบัญชี", range(len(_opts)),
                                      format_func=lambda i: _opts[i])
                _acc  = cash[o_idx]
                _foreign = _acc["currency"] != "THB"
                o_amt = oc2.text_input(f"ยอดถอน ({_acc['currency']})", "")
                o_dt  = oc3.date_input("วันที่ถอน", value=date.today())
                oc4, oc5 = st.columns([3, 7])
                # The question only exists for a foreign-currency account; THB sitting
                # in a Thai account is already onshore and cannot be "brought in".
                if _foreign:
                    o_thai = oc4.checkbox("โอนเข้าไทย", value=True,
                                          help=f"เงินก้อนนี้ออกจากบัญชี {_acc['currency']} "
                                               "เข้าบัญชีในไทยไหม — จังหวะนี้คือตัวที่ "
                                               "เกี่ยวกับภาษี ถ้าเก็บไว้ต่างประเทศให้ติ๊กออก")
                else:
                    o_thai = False
                o_note = oc5.text_input("บันทึก (ไม่บังคับ)", "",
                                        placeholder="เช่น ค่าเทอม / ซื้อของ / โอนเข้า SCB")

                if st.form_submit_button("ถอนเงิน", use_container_width=True):
                    amt = parse(o_amt)
                    if not amt or amt <= 0:
                        st.error("ใส่ยอดถอนให้ถูกต้อง")
                    elif amt > _acc["amount"]:
                        _s = "$" if _acc["currency"] == "USD" else "฿"
                        st.error("ยอดในบัญชีมีแค่ " + money(_acc["amount"], _s, 2))
                    else:
                        amt_thb = amt * rate if _acc["currency"] == "USD" else amt
                        _acc.setdefault("cashouts", []).append({
                            "date": str(o_dt), "amount": round(amt, 2),
                            "amount_thb": round(amt_thb, 2),
                            # same reason as closing a position: without the rate the
                            # THB figure cannot be reproduced once the rate moves
                            "fx_rate": round(rate, 4),
                            "to_thai": bool(o_thai), "note": o_note.strip(),
                        })
                        _acc["amount"] = round(_acc["amount"] - amt, 2)
                        save_cash(cash)
                        _s = "$" if _acc["currency"] == "USD" else "฿"
                        st.success(f"ถอนออก {money(amt, _s, 2)} จาก {_acc['name']} แล้ว")
                        st.rerun()

        # one table for both directions — reading in/out side by side is the point
        flows_io = (
            [{**d, "_kind": "in"} for d in deposits]
            + [{**c, "_kind": "out"} for c in cashouts]
        )
        flows_io.sort(key=lambda f: f["date"], reverse=True)
        if flows_io:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            section(f"ประวัติเงินเข้า-ออก ({len(flows_io)})")
            st.dataframe([{
                "วันที่":     f["date"],
                "ประเภท":     "เติม" if f["_kind"] == "in" else "ถอน",
                "บัญชี":      f["account"],
                "ยอด":        (("+" if f["_kind"] == "in" else "−")
                               + money(f["amount"], "$" if f["currency"] == "USD" else "฿", 2)
                               if f["amount"] is not None else "—"),
                "เป็นบาท":    money(f["amount_thb"], dp=2),
                "เรต":        f"{f['fx_rate']:.4f}" if f["fx_rate"] else "—",
                "นำเข้าไทย":  ("—" if f["_kind"] == "in" or f["currency"] == "THB"
                               else ("ใช่" if f["remitted"] else "ไม่")),
                "บันทึก":     f["note"] or "—",
            } for f in flows_io], use_container_width=True, hide_index=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # -- Add account --
    with st.expander("เพิ่มบัญชี Cash"):
        with st.form("add_cash_page"):
            fc1, fc2, fc3 = st.columns(3)
            preset      = fc1.selectbox("แหล่ง Cash", CASH_PRESETS)
            custom_name = fc2.text_input("หรือพิมพ์ชื่อเอง", placeholder="เช่น Binance Thai")
            currency    = fc3.selectbox("สกุลเงิน", ["THB", "USD"])
            amount_str  = st.text_input("ยอดเริ่มต้น", placeholder="เช่น 50000 หรือ 1500.50")
            if st.form_submit_button("บันทึก"):
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
        # show what actually left the account: the margin, and nothing for an import
        if not t.get("is_import"):
            flows.append({
                "วันที่":   t.get("open_date","—"),
                "ประเภท":  "เปิด Trade",
                "Ticker":  t.get("ticker","—"),
                "บัญชี":   src,
                "Flow":    fmt_money(-((pos or 0) / trade_leverage(t)), disp, rate),
            })
        if t.get("status") == "closed" and t.get("exit_price"):
            if "settled_thb" in t:
                # closed after settlement was recorded: show the cash that really came
                # back and where it went (nothing, if the close moved no cash)
                if t.get("settled_to"):
                    flows.append({
                        "วันที่":   t.get("close_date","—"),
                        "ประเภท":  "ปิด Trade",
                        "Ticker":  t.get("ticker","—"),
                        "บัญชี":   t["settled_to"],
                        "Flow":    fmt_money(t["settled_thb"], disp, rate),
                    })
            else:
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
        st.caption("ยังไม่มีรายการ")


# -- Page 5: Log --
def page_log(trades: list, investments: list, cash: list, disp: str, rate: float):
    sym = "฿" if disp == "THB" else "$"

    # ============ Activity Log ============
    section("Activity Log")
    activity = build_activity_log(investments, trades, cash)

    if not activity:
        st.info("ยังไม่มี activity")
    else:
        _yrs  = [int(e["วันที่"][:4]) for e in activity
                 if len(e.get("วันที่", "")) >= 4 and e["วันที่"][:4].isdigit()]
        _lo   = min(_yrs, default=2026)
        years = list(range(2030, min(_lo, 2030) - 1, -1))

        a1, a2, a3 = st.columns([2, 2, 3])
        yr_pick = a1.selectbox("ปี", ["ทั้งหมด"] + years, key="log_year")
        mo_pick = a2.selectbox("เดือน", ["ทั้งหมด"] + list(range(1, 13)), key="log_month")
        ty_pick = a3.selectbox("ประเภท", ["ทั้งหมด", "Invest", "Trade", "Cash"], key="log_type")

        shown = activity
        if yr_pick != "ทั้งหมด":
            shown = [e for e in shown if e.get("วันที่", "").startswith(f"{yr_pick}-")]
        if mo_pick != "ทั้งหมด":
            shown = [e for e in shown if e.get("วันที่", "")[5:7] == f"{mo_pick:02d}"]
        if ty_pick != "ทั้งหมด":
            shown = [e for e in shown if e.get("ประเภท") == ty_pick]

        st.caption(f"{len(shown)} รายการ")
        if shown:
            st.dataframe(shown, use_container_width=True, hide_index=True)
            st.download_button(
                "Export CSV", key="dl_activity",
                data=pd.DataFrame(shown).to_csv(index=False).encode("utf-8-sig"),
                file_name=f"timfin_activity_{date.today()}.csv", mime="text/csv",
            )
        else:
            st.info("ไม่มีรายการในช่วงที่เลือก")

    # ============ Tax summary (replaces the old History dump) ============
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    section("สรุปภาษี")

    realized = build_realized_events(investments, trades)
    if not realized:
        st.info("ยังไม่มีการขาย")
        return

    tax_years = sorted({e["sell_date"][:4] for e in realized if len(e["sell_date"]) >= 4},
                       reverse=True)
    pick = st.selectbox("ปี", tax_years, key="tax_year")
    yr_rows = [e for e in realized if e["sell_date"].startswith(pick)]

    gain = sum(e["pnl_thb"] or 0 for e in yr_rows if (e["pnl_thb"] or 0) > 0)
    loss = sum(e["pnl_thb"] or 0 for e in yr_rows if (e["pnl_thb"] or 0) < 0)
    yr_out  = [c for c in build_cashouts(cash) if c["date"].startswith(pick)]
    remit   = sum(c["amount_thb"] or 0 for c in yr_out if c["remitted"])

    t1, t2, t3, t4 = st.columns(4)
    t1.metric("กำไรที่ realize", fmt_money(gain, disp, rate))
    t2.metric("ขาดทุนที่ realize", fmt_money(loss, disp, rate))
    t3.metric("สุทธิ", fmt_money(gain + loss, disp, rate))
    t4.metric("นำเงินเข้าไทย",
              fmt_money(remit, disp, rate, sign=False) if yr_out else "—",
              help="เฉพาะที่ถอนจากบัญชีต่างสกุลแล้วโอนเข้าไทย — "
                   "ถอนจากบัญชี THB ไม่นับ เพราะเงินอยู่ในไทยแล้ว")
    if yr_out:
        t4.caption(f"Cash Out ทั้งปี "
                   f"{fmt_money(sum(c['amount_thb'] or 0 for c in yr_out), disp, rate, sign=False)}")

    tax_tbl = [{
        "ขายเมื่อ":      e["sell_date"],
        "ประเภท":        e["kind"] + (" (บางส่วน)" if e["partial"] else ""),
        "Ticker":        e["ticker"],
        "ซื้อเมื่อ":     e["entry_date"] or "—",
        "ราคาซื้อ":      e["entry_price"] or "—",
        "ราคาขาย":       e["sell_price"] or "—",
        "จำนวน":         e["shares"] or "—",
        "สกุล":          e["currency"],
        "เรต ณ วันขาย":  f"{e['fx_rate']:.4f}" if e["fx_rate"] else "—",
        "ได้รับ (฿)":    money(e["proceeds_thb"], "", 2),
        "กำไร/ขาดทุน (฿)": money(e["pnl_thb"], "", 2),
        "บัญชี":         e["account"],
    } for e in yr_rows]

    st.dataframe(tax_tbl, use_container_width=True, hide_index=True)
    st.download_button(
        "Export CSV สำหรับยื่นภาษี", key="dl_tax",
        data=pd.DataFrame(tax_tbl).to_csv(index=False).encode("utf-8-sig"),
        file_name=f"timfin_tax_{pick}.csv", mime="text/csv",
    )
    if any(e["fx_rate"] is None for e in yr_rows):
        st.caption("⚠️ เรต “—” = ใช้เรตปัจจุบัน ไม่ใช่เรตวันขาย")
    st.caption("บันทึกรายการ ไม่ใช่การคำนวณภาษี — ยืนยันกับนักบัญชีก่อนยื่น")


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
        st.error(f"โหลดข้อมูลไม่ได้: {_e}")
        st.stop()

    rate = get_usd_thb()
    _email = (st.session_state.get("sb_session") or {}).get("user", {}).get("email", "")

    # -- CSS injected directly — hides helpers before page paint (no flash) --
    st.markdown(
        '<style>'
        # Currency radio (key=display_currency) is hidden by JS text-match; remove the
        # blanket stRadio hide that was also killing the 1D/1W/1M/1Y period selectors.
        # Only hide tab-list (replaced by custom navbar) and strip top padding.
        '[data-baseweb="tab-list"]{display:none!important;}'
        # Clear the 58px fixed navbar here rather than with a spacer element, so the
        # clearance does not also cost a flex gap slot. 30px measured, not guessed: the
        # navbar iframe's container still occupies 26px and the tab panel adds 16px of
        # its own padding, which lands the first row ~14px under the bar.
        # Written as a child selector on purpose: stMainBlockContainer IS a direct child
        # of stMain, so the zeroing rule below outranks a lone attribute selector.
        '[data-testid="stMain"]>div{padding-top:0!important;}'
        '[data-testid="stMain"]>[data-testid="stMainBlockContainer"]'
        '{padding-top:30px!important;}'
        # Everything at the top level of this block except the tabs is an invisible
        # helper (two style blocks, the two navbar-driven radios, the navbar iframe),
        # and each was still charged the block's 16px gap — 112px of dead space above
        # the first real content. Scoped to the OUTERMOST block only: the page has ~135
        # vertical blocks and zeroing the gap on all of them would flatten every section.
        '[data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlockBorderWrapper"]'
        '>[data-testid="stVerticalBlock"]{gap:0!important;}'
        '</style>',
        unsafe_allow_html=True,
    )

    # -- Hidden radios: the navbar buttons click these by label text --
    disp = st.radio("", ["THB", "USD"], horizontal=True,
                    key="display_currency", label_visibility="collapsed")
    st.radio("", ["แสดงยอด", "ซ่อนยอด"], horizontal=True,
             key="amount_visibility", label_visibility="collapsed")

    render_logout_target(_logged_in)

    # -- Inject navbar (HTML + CSS + JS) into parent document via window.parent --
    _components.html(
        _inject_navbar(
            f'data:image/png;base64,{_LOGO_B64}' if _LOGO_B64 else "",
            _email, st.session_state.get("display_currency", "THB"), rate,
            hidden_amounts(),
        ),
        height=0, scrolling=False,
    )

    # -- Tabs --
    _tabs = st.tabs(["Overview", "Investment", "Trade", "Cash", "Log"])
    with _tabs[0]: page_overview(trades, investments, cash, disp, rate)
    with _tabs[1]: page_investment(investments, trades, cash, disp, rate)
    with _tabs[2]: page_trade(trades, cash, disp, rate)
    with _tabs[3]: page_cash(trades, investments, cash, disp, rate)
    with _tabs[4]: page_log(trades, investments, cash, disp, rate)


main()
