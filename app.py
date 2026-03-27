import streamlit as st
import streamlit.components.v1 as components
import api_client
from api_client import APIError
from datetime import datetime, timezone
import time

TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h"]
PROVIDERS = ["IBKR", "BYBIT"]
ALERT_STATUSES = ["OPEN", "TP_HIT", "SL_HIT", "CANCELED"]
ALERT_DIRECTIONS = ["LONG", "SHORT"]
ALERT_TYPES = ["PREALERT", "TRIGGER_ALERT", "TREND_STRENGTH_ALERT"]
STATUS_COLORS = {
    "ACTIVE": "🟢",
    "PAUSED": "🟡",
    "COMPLETED": "🔴",
}
TIMEFRAME_REFRESH_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
}

st.set_page_config(page_title="TradingKK", page_icon="📈", layout="wide")

# ── Custom CSS ────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    .session-card {
        background: #1e1e2f;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        border-left: 4px solid #4f8ff7;
    }
    .session-card-paused {
        border-left-color: #f0ad4e;
    }
    .session-card-completed {
        border-left-color: #6c757d;
    }
    div[data-testid="stSidebar"] {
        background: #0e1117;
    }
    .system-clock-widget {
        position: fixed;
        right: 16px;
        bottom: 16px;
        z-index: 9999;
        background: rgba(14, 17, 23, 0.92);
        border: 1px solid rgba(151, 166, 195, 0.35);
        border-radius: 10px;
        padding: 8px 10px;
        min-width: 132px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
    }
    .system-clock-label {
        font-size: 11px;
        line-height: 1.1;
        color: #9aa0a6;
        margin-bottom: 2px;
    }
    .system-clock-time {
        font-size: 18px;
        line-height: 1.15;
        font-weight: 700;
        color: #e8eaed;
        font-variant-numeric: tabular-nums;
    }
    /* Make Streamlit dialog close button clearly visible */
    div[data-testid="stDialog"] button[aria-label="Close"] {
        position: absolute !important;
        top: 10px !important;
        right: 10px !important;
        z-index: 20 !important;
        width: 30px !important;
        height: 30px !important;
        min-height: 30px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(160, 170, 190, 0.55) !important;
        background: rgba(25, 30, 40, 0.88) !important;
        box-shadow: 0 0 8px rgba(0, 0, 0, 0.35) !important;
        color: #e8eaed !important;
        opacity: 1 !important;
    }
    div[data-testid="stDialog"] > div {
        position: relative !important;
    }
    div[data-testid="stDialog"] button[aria-label="Close"] svg {
        display: none !important;
    }
    div[data-testid="stDialog"] button[aria-label="Close"]::after {
        content: "×";
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #e8eaed;
        font-size: 18px;
        font-weight: 800;
        line-height: 1;
    }
    div[data-testid="stDialog"] button[aria-label="Close"]:hover {
        border-color: rgba(220, 230, 245, 0.7) !important;
        background: rgba(35, 42, 56, 0.95) !important;
        box-shadow: 0 0 10px rgba(120, 145, 200, 0.28) !important;
    }
    .info-rich-text {
        font-size: 1.03rem;
        line-height: 1.65;
        color: #8bdc65;
        background: #131722;
        border: 1px solid rgba(151, 166, 195, 0.35);
        border-radius: 10px;
        padding: 0.9rem 1rem;
        white-space: pre-wrap;
    }
    .tcp-top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(180deg, #2a2d35 0%, #1a1d24 100%);
        border: 1px solid rgba(80, 85, 95, 0.8);
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 12px rgba(0,0,0,0.4);
    }
    .tcp-title {
        font-family: 'Segoe UI', 'Roboto', 'Oswald', 'Arial Black', sans-serif;
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        color: #f0c048;
        text-shadow: 0 0 12px rgba(240, 192, 72, 0.5);
    }
    .tcp-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .tcp-led {
        width: 12px;
        height: 12px;
        border-radius: 50%;
    }
    .tcp-led-online {
        background: #22c55e;
        box-shadow: 0 0 8px #22c55e, 0 0 16px rgba(34, 197, 94, 0.6);
    }
    .tcp-led-offline {
        background: #ef4444;
        box-shadow: 0 0 8px #ef4444, 0 0 16px rgba(239, 68, 68, 0.6);
    }
    .tcp-status-text {
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
    }
    .tcp-status-online {
        color: #22c55e;
    }
    .tcp-status-offline {
        color: #ef4444;
    }
    .tcp-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        grid-template-rows: repeat(2, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    .tcp-panel {
        background: linear-gradient(180deg, #252830 0%, #1a1d24 100%);
        border: 1px solid rgba(70, 75, 85, 0.8);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 2px 8px rgba(0,0,0,0.3);
        min-height: 190px;
        height: 190px;
        display: flex;
        flex-direction: column;
    }
    .tcp-panel-label {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: #888;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .tcp-bias-gauge-wrap {
        width: 100%;
        height: 90px;
        position: relative;
    }
    .tcp-bias-gauge {
        width: 100%;
        height: 65px;
        position: relative;
        background: linear-gradient(90deg, #ef4444 0%, #9aa0a6 50%, #22c55e 100%);
        border-radius: 32px 32px 0 0;
    }
    .tcp-bias-gauge-inner {
        position: absolute;
        bottom: 5px;
        left: 50%;
        transform: translateX(-50%);
        width: 72%;
        height: 52px;
        background: linear-gradient(180deg, #252830 0%, #1a1d24 100%);
        border-radius: 26px 26px 0 0;
    }
    .tcp-bias-arrow {
        position: absolute;
        bottom: 2px;
        left: 50%;
        transform-origin: 50% 90%;
        font-size: 1.4rem;
        line-height: 1;
        color: #22c55e;
        text-shadow: 0 0 8px rgba(34, 197, 94, 0.8);
    }
    .tcp-bias-arrow-bearish { transform: translateX(-50%) rotate(-55deg); color: #ef4444; text-shadow: 0 0 8px rgba(239, 68, 68, 0.8); }
    .tcp-bias-arrow-neutral { transform: translateX(-50%) rotate(0deg); color: #9aa0a6; text-shadow: 0 0 8px rgba(154, 160, 166, 0.6); }
    .tcp-bias-arrow-bullish { transform: translateX(-50%) rotate(55deg); color: #22c55e; text-shadow: 0 0 8px rgba(34, 197, 94, 0.8); }
    .tcp-bias-label {
        text-align: center;
        font-size: 0.9rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }
    .tcp-bias-bullish { color: #22c55e; }
    .tcp-bias-bearish { color: #ef4444; }
    .tcp-bias-neutral { color: #9aa0a6; }
    .tcp-pb-gauge-wrap {
        width: 100%;
        height: 90px;
        position: relative;
    }
    .tcp-pb-gauge {
        width: 100%;
        height: 65px;
        position: relative;
        background: linear-gradient(90deg, #ef4444 0%, #ef4444 33%, #f0ad4e 33%, #f0ad4e 66%, #3b82f6 66%, #3b82f6 100%);
        border-radius: 32px 32px 0 0;
    }
    .tcp-pb-gauge-inner {
        position: absolute;
        bottom: 5px;
        left: 50%;
        transform: translateX(-50%);
        width: 72%;
        height: 52px;
        background: linear-gradient(180deg, #252830 0%, #1a1d24 100%);
        border-radius: 26px 26px 0 0;
    }
    .tcp-pb-gauge-labels {
        position: absolute;
        bottom: 12px;
        left: 0;
        right: 0;
        display: flex;
        justify-content: space-between;
        padding: 0 8%;
        font-size: 0.58rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: rgba(255,255,255,0.9);
        pointer-events: none;
    }
    .tcp-pb-arrow {
        position: absolute;
        bottom: 2px;
        left: 50%;
        transform-origin: 50% 90%;
        font-size: 1.4rem;
        line-height: 1;
        color: #f0ad4e;
        text-shadow: 0 0 8px rgba(240, 173, 78, 0.8);
    }
    .tcp-pb-arrow-invalid { transform: translateX(-50%) rotate(-55deg); color: #ef4444; text-shadow: 0 0 8px rgba(239, 68, 68, 0.8); }
    .tcp-pb-arrow-ready { transform: translateX(-50%) rotate(0deg); color: #f0ad4e; text-shadow: 0 0 8px rgba(240, 173, 78, 0.8); }
    .tcp-pb-arrow-forming { transform: translateX(-50%) rotate(55deg); color: #3b82f6; text-shadow: 0 0 8px rgba(59, 130, 246, 0.8); }
    .tcp-pb-label {
        text-align: center;
        font-size: 0.85rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }
    .tcp-pb-label-invalid { color: #ef4444; }
    .tcp-pb-label-ready { color: #f0ad4e; }
    .tcp-pb-label-forming { color: #3b82f6; }
    .tcp-pb-label-none { color: #9aa0a6; }
    .tcp-vol-lights {
        display: flex;
        justify-content: center;
        gap: 0.6rem;
        margin: 0.5rem 0;
    }
    .tcp-vol-light {
        width: 16px;
        height: 16px;
        border-radius: 50%;
    }
    .tcp-vol-light-low { background: #3b82f6; }
    .tcp-vol-light-normal { background: #22c55e; }
    .tcp-vol-light-high { background: #ef4444; }
    .tcp-vol-light-active { box-shadow: 0 0 10px currentColor, 0 0 20px currentColor; }
    .tcp-vol-light-low.tcp-vol-light-active { color: #3b82f6; }
    .tcp-vol-light-normal.tcp-vol-light-active { color: #22c55e; }
    .tcp-vol-light-high.tcp-vol-light-active { color: #ef4444; }
    .tcp-vol-data {
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: #f0c048;
        text-align: center;
    }
    .tcp-trend-wrap {
        height: 90px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.35rem;
    }
    .tcp-trend-direction {
        font-size: 0.9rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
    .tcp-trend-direction-bullish { color: #22c55e; text-shadow: 0 0 10px rgba(34,197,94,0.45); }
    .tcp-trend-direction-bearish { color: #ef4444; text-shadow: 0 0 10px rgba(239,68,68,0.45); }
    .tcp-trend-direction-neutral { color: #9aa0a6; }
    .tcp-trend-level-badge {
        font-size: 0.66rem;
        font-weight: 800;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: #d5d9e0;
        background: rgba(0,0,0,0.35);
        border: 1px solid rgba(100,110,130,0.7);
        border-radius: 999px;
        padding: 0.2rem 0.55rem;
    }
    .tcp-trend-bars {
        display: flex;
        gap: 0.2rem;
    }
    .tcp-trend-bar {
        width: 16px;
        height: 6px;
        border-radius: 2px;
        background: #3a3f4a;
        border: 1px solid rgba(130,140,160,0.35);
    }
    .tcp-trend-bar-active-bullish { background: #22c55e; box-shadow: 0 0 8px rgba(34,197,94,0.55); }
    .tcp-trend-bar-active-bearish { background: #ef4444; box-shadow: 0 0 8px rgba(239,68,68,0.55); }
    .tcp-trend-bar-active-neutral { background: #9aa0a6; box-shadow: 0 0 6px rgba(154,160,166,0.45); }
    .tcp-control-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
    }
    .tcp-control-label-wrap {
        display: flex;
        align-items: center;
        min-height: 38px;
    }
    .tcp-control-label {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #888;
        min-width: 72px;
    }
    .tcp-session-status {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-top: 0.9rem;
        padding: 0.55rem 0.85rem;
        background: rgba(0,0,0,0.35);
        border-radius: 8px;
        border: 1px solid rgba(70,75,85,0.6);
    }
    .tcp-session-led {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }
    .tcp-session-led-active { background: #22c55e; box-shadow: 0 0 8px #22c55e; }
    .tcp-session-led-paused { background: #f0ad4e; box-shadow: 0 0 8px #f0ad4e; }
    .tcp-session-led-completed { background: #6c757d; box-shadow: 0 0 6px #6c757d; }
    .tcp-session-led-none { background: #555; }
    .tcp-freeze-light {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        display: inline-block;
    }
    .tcp-freeze-light-on {
        background: #3ab8ff;
        box-shadow: 0 0 10px #3ab8ff, 0 0 18px rgba(58, 184, 255, 0.65);
    }
    .tcp-freeze-light-off {
        background: #666;
        box-shadow: 0 0 4px rgba(130, 130, 130, 0.35);
    }
    .tcp-session-status-text {
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    .tcp-session-status-active { color: #22c55e; }
    .tcp-session-status-paused { color: #f0ad4e; }
    .tcp-session-status-completed { color: #9aa0a6; }
    .tcp-session-status-none { color: #666; }
    .tcp-alert-status-body {
        min-height: 90px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.45rem;
        padding: 0 0.25rem;
    }
    .tcp-alert-main-line {
        font-size: 1.2rem;
        font-weight: 800;
        line-height: 1.2;
        text-align: center;
    }
    .tcp-alert-risk-row {
        min-height: 22px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .tcp-alert-risk-row:empty { display: none; min-height: 0; }
    .tcp-risk-pill {
        display: inline-block;
        font-size: 0.62rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        padding: 0.22rem 0.6rem;
        border-radius: 999px;
        border: 1px solid rgba(120,130,150,0.45);
    }
    .tcp-risk-pill-risky {
        color: #fff7ed;
        background: linear-gradient(180deg, #c2410c 0%, #9a3412 100%);
        border-color: rgba(251, 146, 60, 0.55);
        box-shadow: 0 0 10px rgba(194, 65, 12, 0.45);
    }
    .tcp-risk-pill-safe {
        color: #bbf7d0;
        background: rgba(34, 197, 94, 0.14);
        border-color: rgba(34, 197, 94, 0.5);
    }
    .tcp-risk-pill-unknown {
        color: #9aa0a6;
        background: rgba(0,0,0,0.25);
        border-color: rgba(100,110,130,0.4);
    }
    .tcp-controls-inner {
        padding-top: 0.25rem;
    }
    .tcp-panel-controls .stRadio > div {
        flex-direction: row !important;
        gap: 0 !important;
        background: #0d0f12 !important;
        border-radius: 22px !important;
        padding: 4px !important;
        border: 1px solid rgba(70,75,85,0.6) !important;
        width: fit-content !important;
    }
    .tcp-panel-controls .stRadio label {
        background: transparent !important;
        color: #666 !important;
        padding: 5px 16px !important;
        border-radius: 18px !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
        margin: 0 2px !important;
        transition: all 0.2s ease !important;
    }
    .tcp-panel-controls .stRadio label:hover { color: #9aa0a6 !important; }
    .tcp-panel-controls .stRadio label:has(input:checked) {
        background: linear-gradient(180deg, #22c55e 0%, #16a34a 100%) !important;
        color: #fff !important;
        box-shadow: 0 0 10px rgba(34, 197, 94, 0.4) !important;
    }
    .tcp-panel-controls .stRadio label:first-of-type:has(input:checked) {
        background: linear-gradient(180deg, #3b3f47 0%, #2a2d33 100%) !important;
        color: #9aa0a6 !important;
        box-shadow: none !important;
    }
    .tcp-control-row-refresh {
        margin-bottom: 0.5rem;
    }
    .tcp-control-row-refresh .tcp-control-label { margin-bottom: 0; min-width: auto; }
    .tcp-quick-retro-switch .stRadio > div {
        flex-direction: row !important;
        gap: 0 !important;
        background: linear-gradient(180deg, #3a414d 0%, #1c212a 100%) !important;
        border-radius: 8px !important;
        padding: 4px !important;
        border: 1px solid rgba(145, 155, 170, 0.55) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 2px 8px rgba(0,0,0,0.45) !important;
        width: fit-content !important;
    }
    .tcp-quick-retro-switch .stRadio label {
        background: transparent !important;
        color: #9aa3b4 !important;
        padding: 6px 18px !important;
        border-radius: 6px !important;
        border: 1px solid transparent !important;
        font-size: 0.72rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.08em !important;
        margin: 0 2px !important;
        text-transform: uppercase !important;
        transition: all 0.16s ease !important;
    }
    .tcp-quick-retro-switch .stRadio label:has(input:checked) {
        color: #ecf9ff !important;
        border-color: rgba(69, 255, 204, 0.7) !important;
        background: linear-gradient(180deg, #0f6b62 0%, #0a4a44 100%) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 0 12px rgba(69, 255, 204, 0.35) !important;
    }
    .tcp-quick-retro-switch .stRadio label:first-of-type:has(input:checked) {
        color: #ffe6db !important;
        border-color: rgba(255, 129, 102, 0.7) !important;
        background: linear-gradient(180deg, #7a2c1f 0%, #4f1d14 100%) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.15), 0 0 10px rgba(255, 129, 102, 0.3) !important;
    }
    .tcp-master-panel {
        background: rgba(20, 22, 28, 0.6);
        border: 1px solid rgba(70, 75, 85, 0.6);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    .tcp-quick-subpanel-label {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: #888;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    div:has(#tcp-rules-btn-marker) + div button {
        background: linear-gradient(180deg, #2a3f4d 0%, #1a2835 100%) !important;
        color: #7eb8d4 !important;
        border: 1px solid rgba(58, 144, 184, 0.5) !important;
        box-shadow: 0 0 6px rgba(58, 144, 184, 0.25) !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
    }
    div:has(#tcp-rules-btn-marker) + div button:hover {
        color: #9ecde8 !important;
        box-shadow: 0 0 10px rgba(58, 144, 184, 0.35) !important;
    }
    div:has(#tcp-guardian-btn-marker) + div button {
        background: linear-gradient(180deg, #6f1d62 0%, #4d1246 100%) !important;
        color: #ffd5f5 !important;
        border: 1px solid rgba(255, 120, 220, 0.55) !important;
        box-shadow: 0 0 8px rgba(255, 77, 208, 0.28), 0 0 16px rgba(255, 77, 208, 0.14) !important;
        font-weight: 800 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        min-height: 34px !important;
        padding: 0.35rem 0.9rem !important;
        font-size: 0.76rem !important;
        border-radius: 8px !important;
    }
    div:has(#tcp-guardian-btn-marker) + div button:hover {
        color: #ffe8fb !important;
        box-shadow: 0 0 12px rgba(255, 77, 208, 0.38), 0 0 20px rgba(255, 77, 208, 0.2) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.tcp-quick-subpanel-label) {
        min-height: 128px;
    }
    .tcp-knob-panel {
        background: linear-gradient(180deg, #252830 0%, #1a1d24 100%);
        border: 1px solid rgba(70, 75, 85, 0.8);
        border-radius: 10px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 2rem;
        flex-wrap: wrap;
    }
    .tcp-knob-panel-label {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: #888;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .tcp-knob-wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
    }
    .tcp-knob-dial {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(145deg, #2a2d35 0%, #1a1d24 50%, #252830 100%);
        border: 3px solid #3b3f47;
        box-shadow: inset 0 2px 6px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3);
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .tcp-knob-pointer {
        width: 4px;
        height: 28px;
        background: linear-gradient(180deg, #f0ad4e 0%, #d4892a 100%);
        border-radius: 2px;
        position: absolute;
        top: 8px;
        left: 50%;
        transform-origin: 50% 32px;
        transform: translateX(-50%) rotate(-135deg);
        box-shadow: 0 0 6px rgba(240, 173, 78, 0.5);
    }
    .tcp-knob-value {
        font-size: 1.1rem;
        font-weight: 800;
        color: #f0c048;
        letter-spacing: 0.05em;
    }
    .tcp-knob-slider-wrap {
        width: 120px;
        margin-top: 0.25rem;
    }
    .tcp-knob-slider-wrap input[type="range"] {
        width: 100%;
        height: 6px;
        -webkit-appearance: none;
        background: #1a1d24;
        border-radius: 3px;
        outline: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _fmt_dt(val) -> str:
    if not val:
        return "—"
    try:
        # Keep backend timestamp representation unchanged in UI.
        return str(val)
    except Exception:
        return str(val)


def _tcp_alert_risky_bool(alert: dict | None) -> bool | None:
    if not isinstance(alert, dict):
        return None
    r = alert.get("risky")
    if r is None:
        return None
    if isinstance(r, bool):
        return r
    if isinstance(r, (int, float)):
        return bool(r)
    if isinstance(r, str):
        return r.strip().lower() in ("true", "1", "yes", "on")
    return None


def _bias_colored_html(value: str | None) -> str:
    bias = (value or "NEUTRAL").upper()
    color_map = {
        "BULLISH": "#2ca02c",
        "BEARISH": "#d62728",
        "NEUTRAL": "#9aa0a6",
    }
    color = color_map.get(bias, "#9aa0a6")
    return f"<span style='color: {color}; font-weight: 700;'>{bias}</span>"


def _volatility_status_colored_html(value: str | None) -> str:
    status = (value or "—").upper()
    color_map = {
        "LOW": "#9aa0a6",
        "NORMAL": "#2ca02c",
        "HIGH": "#d62728",
    }
    color = color_map.get(status, "#9aa0a6")
    return f"<span style='color: {color}; font-weight: 700;'>{status}</span>"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _elapsed_seconds_from_started(started_at: str | None) -> int | None:
    start_dt = _parse_dt(started_at)
    if not start_dt:
        return None
    return max(0, int((datetime.now(start_dt.tzinfo) - start_dt).total_seconds()))


def _format_hms(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _refresh_seconds_for_timeframe(timeframe: str | None) -> int:
    return int(TIMEFRAME_REFRESH_SECONDS.get((timeframe or "").strip(), 60))


@st.fragment(run_every="1s")
def _system_clock_widget() -> None:
    now_utc = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    st.markdown(
        f"""
        <div style="height:0;">
            <div class="system-clock-widget">
                <div class="system-clock-label">System Clock</div>
                <div class="system-clock-time">{now_utc}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.fragment(run_every="1s")
def _tcp_auto_refresh_fragment() -> None:
    auto_enabled = bool(st.session_state.get("tcp_auto_refresh_enabled", False))

    cfg = st.session_state.get("tcp_auto_refresh_cfg")
    if isinstance(cfg, dict):
        session_id = cfg.get("session_id", st.session_state.get("tcp_session_knob", 1))
        timeframe = cfg.get("timeframe", "1m")
        interval_seconds = int(cfg.get("interval_seconds", _refresh_seconds_for_timeframe(timeframe)))
    else:
        session_id = st.session_state.get("tcp_session_knob", 1)
        timeframe = "1m"
        interval_seconds = _refresh_seconds_for_timeframe(timeframe)

    last_fetch_ts = float(st.session_state.get("tcp_last_fetch_ts", 0.0))
    elapsed = max(0.0, time.time() - last_fetch_ts)
    remaining = max(0, int(interval_seconds - elapsed))

    if not auto_enabled:
        st.caption(f"Auto-refresh OFF | Session #{session_id} | TF: {timeframe}")
        return

    st.caption(
        f"Auto-refresh ON | Session #{session_id} | TF: {timeframe} | "
        f"Every {interval_seconds}s | Next in {remaining}s"
    )

    if elapsed < interval_seconds:
        return

    try:
        session_detail = api_client.get_session(int(session_id))
        st.session_state["tcp_session_detail"] = session_detail if isinstance(session_detail, dict) else {}
        panel_result = api_client.get_trading_control_panel(int(session_id))
        st.session_state["tcp_panel_result"] = panel_result
        st.session_state["tcp_last_fetch_ts"] = time.time()
        st.session_state.pop("tcp_error", None)
        st.rerun()
    except Exception:
        st.session_state["tcp_last_fetch_ts"] = time.time()


@st.fragment(run_every="1s")
def _visualize_auto_refresh_fragment(show_caption: bool = False) -> None:
    if not st.session_state.get("viz_auto_refresh_enabled", False):
        return

    cfg = st.session_state.get("visualize_auto_refresh_cfg")
    if not isinstance(cfg, dict):
        if show_caption:
            st.caption("Auto-refresh is enabled. Run Visualize once to start polling.")
        return

    session_id = cfg.get("session_id")
    num_bars = cfg.get("num_bars", 200)
    timeframe = cfg.get("timeframe", "1m")
    interval_seconds = int(cfg.get("interval_seconds", _refresh_seconds_for_timeframe(timeframe)))
    last_fetch_ts = float(st.session_state.get("visualize_last_fetch_ts", 0.0))

    elapsed = max(0.0, time.time() - last_fetch_ts)
    remaining = max(0, int(interval_seconds - elapsed))
    if show_caption:
        st.caption(
            f"Auto-refresh ON | Session #{session_id} | TF: {timeframe} | "
            f"Every {interval_seconds}s | Next in {remaining}s"
        )

    if elapsed < interval_seconds:
        return

    try:
        viz_result = api_client.visualize_session(int(session_id), int(num_bars))
        st.session_state["session_visualization_result"] = viz_result
        tf = viz_result.get("session", {}).get("timeframe", timeframe)
        st.session_state["visualize_auto_refresh_cfg"] = {
            "session_id": int(session_id),
            "num_bars": int(num_bars),
            "timeframe": tf,
            "interval_seconds": _refresh_seconds_for_timeframe(tf),
        }
        st.session_state["visualize_last_fetch_ts"] = time.time()
        st.session_state.pop("visualize_auto_refresh_error", None)
        # Fragment refresh alone does not redraw the outer visualize panel;
        # rerun app so chart/bias/pullback sections render the new payload.
        st.rerun()
    except APIError:
        st.session_state["visualize_auto_refresh_error"] = f"No such session exists with id {session_id}"
        st.session_state["visualize_last_fetch_ts"] = time.time()
    except Exception:
        st.session_state["visualize_auto_refresh_error"] = f"No such session exists with id {session_id}"
        st.session_state["visualize_last_fetch_ts"] = time.time()


# ── Sidebar ───────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📈 TradingKK")
    st.caption("Trading session manager")
    st.divider()

    backend_ok = False
    try:
        api_client.health_check()
        backend_ok = True
        st.success("Backend connected")
    except Exception:
        st.error("Backend unreachable (localhost:8000)")

    st.divider()
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Trading Control Panel"

    nav_pages = ["Trading Control Panel", "Session", "Provider", "Information"]
    for p in nav_pages:
        is_selected = st.session_state["nav_page"] == p
        if st.button(
            p,
            key=f"nav_{p}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state["nav_page"] = p
            st.rerun()

    page = st.session_state["nav_page"]


# ── Sessions page ─────────────────────────────────────────────────────

def sessions_page():
    st.header("Session")
    sessions_tab, bias_tab, pullback_tab, volatility_tab, visualize_tab, alerts_tab = st.tabs(
        ["Session", "Bias Calculations", "Pullback Calculations", "Volatility Calculations", "Visualize", "Alerts"]
    )

    with sessions_tab:
        left_col, right_col = st.columns([3, 1])
        with left_col:
            st.caption("Session controls are shown below.")
        with right_col:
            with st.container(border=True):
                st.markdown("##### 🕒 Session Clock")
                try:
                    clock_sessions = api_client.list_sessions(limit=200, offset=0)
                except Exception:
                    clock_sessions = []

                clock_candidates = [s for s in clock_sessions if s.get("status") in ("ACTIVE", "PAUSED")]
                if not clock_candidates:
                    st.info("No active/paused session.")
                else:
                    session_labels = {
                        int(s["id"]): f"#{s['id']} {s['symbol']} ({s['status']})"
                        for s in clock_candidates
                    }
                    selected_sid = st.selectbox(
                        "Session",
                        options=list(session_labels.keys()),
                        format_func=lambda sid: session_labels.get(int(sid), f"#{sid}"),
                        key="session_clock_select",
                    )

                    selected = next((s for s in clock_candidates if int(s.get("id", -1)) == int(selected_sid)), None)
                    if st.button("↻ Refresh", key="session_clock_refresh", type="secondary", use_container_width=True):
                        try:
                            selected = api_client.get_session(int(selected_sid))
                        except Exception:
                            pass

                    if not selected:
                        selected = clock_candidates[0]

                    sid = int(selected["id"])
                    status = selected.get("status", "PAUSED")

                    if status == "PAUSED" and f"paused_elapsed_{sid}" in st.session_state:
                        elapsed = int(st.session_state[f"paused_elapsed_{sid}"])
                    else:
                        elapsed = _elapsed_seconds_from_started(selected.get("started_at")) or 0

                    st.metric("Elapsed", _format_hms(elapsed))
                    if status == "PAUSED":
                        st.caption("Paused clock (frozen at pause)")
                    elif status == "ACTIVE":
                        st.caption("Running from latest start/restart")

    with bias_tab:
        st.subheader("Bias Calculations")
        list_cols = st.columns(4)
        with list_cols[0]:
            bc_session_id = st.number_input("Session ID", min_value=1, value=1, step=1, key="bc_session_id")
        with list_cols[1]:
            bc_limit = st.number_input("Limit", min_value=1, max_value=1000, value=100, step=10, key="bc_limit")
        with list_cols[2]:
            bc_offset = st.number_input("Offset", min_value=0, value=0, step=10, key="bc_offset")
        with list_cols[3]:
            st.write("")
            if st.button("Get By Session", use_container_width=True, key="bc_get_all"):
                try:
                    session_bias = api_client.list_bias_calculations(
                        session_id=int(bc_session_id),
                        limit=int(bc_limit),
                        offset=int(bc_offset),
                    )
                    st.session_state["bias_calculations_list"] = session_bias
                    st.success(f"Loaded {len(session_bias)} bias calculation(s) for session #{int(bc_session_id)}.")
                except APIError as e:
                    st.error(f"Failed to list bias calculations: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

        detail_id = st.number_input(
            "Bias Calculation ID (Get One)", min_value=1, value=1, step=1, key="bc_detail_id"
        )
        if st.button("Get One", use_container_width=True, key="bc_get_one"):
            try:
                st.session_state["bias_calculation_detail"] = api_client.get_bias_calculation(int(detail_id))
            except APIError as e:
                st.error(f"Failed to get bias calculation: {e.detail}")
            except Exception as e:
                st.error(f"Connection error: {e}")

        if "bias_calculations_list" in st.session_state:
            with st.container(border=True):
                st.markdown("**Session Bias Calculations**")
                import pandas as pd

                df = pd.DataFrame(st.session_state["bias_calculations_list"])
                if "calculated_at" in df.columns:
                    df["calculated_at"] = df["calculated_at"].apply(_fmt_dt)

                bias_columns = [
                    col
                    for col in ["ma_bar_bias", "ma_persistent_bias", "structure_bias", "strenght", "candidate_bias", "state_bias"]
                    if col in df.columns
                ]

                def _bias_style(value):
                    bias = str(value).upper()
                    if bias == "BULLISH":
                        return "color: #2ca02c; font-weight: 700;"
                    if bias == "BEARISH":
                        return "color: #d62728; font-weight: 700;"
                    if bias == "NEUTRAL":
                        return "color: #9aa0a6; font-weight: 700;"
                    return ""

                styled_df = df.style
                if bias_columns:
                    styled_df = styled_df.map(_bias_style, subset=bias_columns)

                st.dataframe(styled_df, use_container_width=True, hide_index=True)

        if "bias_calculation_detail" in st.session_state:
            detail = st.session_state["bias_calculation_detail"]
            st.markdown("**Bias Calculation Detail**")
            bias_cols = st.columns(5)
            with bias_cols[0]:
                st.markdown(
                    f"**MA Bar Bias**<br>{_bias_colored_html(detail.get('ma_bar_bias', 'NEUTRAL'))}",
                    unsafe_allow_html=True,
                )
            with bias_cols[1]:
                st.markdown(
                    f"**MA Persistent Bias**<br>{_bias_colored_html(detail.get('ma_persistent_bias', 'NEUTRAL'))}",
                    unsafe_allow_html=True,
                )
            with bias_cols[2]:
                st.markdown(
                    f"**Structure Bias**<br>{_bias_colored_html(detail.get('structure_bias', 'NEUTRAL'))}",
                    unsafe_allow_html=True,
                )
            with bias_cols[3]:
                st.markdown(
                    f"**Strength**<br>{_bias_colored_html(detail.get('strenght', 'NEUTRAL'))}",
                    unsafe_allow_html=True,
                )
            with bias_cols[4]:
                st.markdown(
                    f"**Candidate Bias**<br>{_bias_colored_html(detail.get('candidate_bias', 'NEUTRAL'))}",
                    unsafe_allow_html=True,
                )
            st.json(detail)

    with pullback_tab:
        st.subheader("Pullback Calculations")
        list_cols = st.columns(4)
        with list_cols[0]:
            pc_session_id = st.number_input("Session ID", min_value=1, value=1, step=1, key="pc_session_id")
        with list_cols[1]:
            pc_limit = st.number_input("Limit", min_value=1, max_value=1000, value=100, step=10, key="pc_limit")
        with list_cols[2]:
            pc_offset = st.number_input("Offset", min_value=0, value=0, step=10, key="pc_offset")
        with list_cols[3]:
            st.write("")
            if st.button("Get By Session", use_container_width=True, key="pc_get_all"):
                try:
                    session_pullbacks = api_client.list_pullback_calculations(
                        session_id=int(pc_session_id),
                        limit=int(pc_limit),
                        offset=int(pc_offset),
                    )
                    st.session_state["pullback_calculations_list"] = session_pullbacks
                    st.success(
                        f"Loaded {len(session_pullbacks)} pullback calculation(s) for session #{int(pc_session_id)}."
                    )
                except APIError as e:
                    st.error(f"Failed to list pullback calculations: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

        detail_id = st.number_input(
            "Pullback Calculation ID (Get One)", min_value=1, value=1, step=1, key="pc_detail_id"
        )
        if st.button("Get One", use_container_width=True, key="pc_get_one"):
            try:
                st.session_state["pullback_calculation_detail"] = api_client.get_pullback_calculation(int(detail_id))
            except APIError as e:
                st.error(f"Failed to get pullback calculation: {e.detail}")
            except Exception as e:
                st.error(f"Connection error: {e}")

        if "pullback_calculations_list" in st.session_state:
            with st.container(border=True):
                st.markdown("**Session Pullback Calculations**")
                import pandas as pd

                df = pd.DataFrame(st.session_state["pullback_calculations_list"])
                if "calculated_at" in df.columns:
                    df["calculated_at"] = df["calculated_at"].apply(_fmt_dt)
                if "pb_start_at" in df.columns:
                    df["pb_start_at"] = df["pb_start_at"].apply(_fmt_dt)

                bias_columns = [col for col in ["state_bias"] if col in df.columns]

                def _bias_style(value):
                    bias = str(value).upper()
                    if bias == "BULLISH":
                        return "color: #2ca02c; font-weight: 700;"
                    if bias == "BEARISH":
                        return "color: #d62728; font-weight: 700;"
                    if bias == "NEUTRAL":
                        return "color: #9aa0a6; font-weight: 700;"
                    return ""

                styled_df = df.style
                if bias_columns:
                    styled_df = styled_df.map(_bias_style, subset=bias_columns)

                st.dataframe(styled_df, use_container_width=True, hide_index=True)

        if "pullback_calculation_detail" in st.session_state:
            detail = st.session_state["pullback_calculation_detail"]
            with st.container(border=True):
                st.markdown("**Pullback Calculation Detail**")
                top_cols = st.columns(4)
                with top_cols[0]:
                    st.markdown(
                        f"**State Bias**<br>{_bias_colored_html(detail.get('state_bias', 'NEUTRAL'))}",
                        unsafe_allow_html=True,
                    )
                with top_cols[1]:
                    st.metric("Pullback State", detail.get("pullback_state", "NONE"))
                with top_cols[2]:
                    st.metric("Pullback Direction", detail.get("pullback_direction", "NONE"))
                with top_cols[3]:
                    st.metric("Trigger Alert", "Yes" if detail.get("trigger_alert") else "No")
                st.caption(f"Reset Reason: **{detail.get('reset_reason', '—')}**")
                st.json(detail)

    with volatility_tab:
        st.subheader("Volatility Calculations")
        list_cols = st.columns(4)
        with list_cols[0]:
            vc_session_id = st.number_input("Session ID", min_value=1, value=1, step=1, key="vc_session_id")
        with list_cols[1]:
            vc_limit = st.number_input("Limit", min_value=1, max_value=1000, value=100, step=10, key="vc_limit")
        with list_cols[2]:
            vc_offset = st.number_input("Offset", min_value=0, value=0, step=10, key="vc_offset")
        with list_cols[3]:
            st.write("")
            if st.button("Get By Session", use_container_width=True, key="vc_get_all"):
                try:
                    session_volatility = api_client.list_volatility_calculations(
                        session_id=int(vc_session_id),
                        limit=int(vc_limit),
                        offset=int(vc_offset),
                    )
                    st.session_state["volatility_calculations_list"] = session_volatility
                    st.success(
                        f"Loaded {len(session_volatility)} volatility calculation(s) for session #{int(vc_session_id)}."
                    )
                except APIError as e:
                    st.error(f"Failed to list volatility calculations: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

        vc_detail_id = st.number_input(
            "Volatility Calculation ID (Get One)", min_value=1, value=1, step=1, key="vc_detail_id"
        )
        if st.button("Get One", use_container_width=True, key="vc_get_one"):
            try:
                st.session_state["volatility_calculation_detail"] = api_client.get_volatility_calculation(
                    int(vc_detail_id)
                )
            except APIError as e:
                st.error(f"Failed to get volatility calculation: {e.detail}")
            except Exception as e:
                st.error(f"Connection error: {e}")

        if "volatility_calculations_list" in st.session_state:
            with st.container(border=True):
                st.markdown("**Session Volatility Calculations**")
                import pandas as pd

                df = pd.DataFrame(st.session_state["volatility_calculations_list"])
                for dt_col in ["calculated_at", "created_at", "updated_at"]:
                    if dt_col in df.columns:
                        df[dt_col] = df[dt_col].apply(_fmt_dt)

                # Keep bias-style coloring if these fields exist in volatility payload.
                bias_columns = [col for col in ["state_bias", "candidate_bias"] if col in df.columns]
                vol_status_cols = [col for col in ["volatility_status"] if col in df.columns]

                def _bias_style(value):
                    bias = str(value).upper()
                    if bias == "BULLISH":
                        return "color: #2ca02c; font-weight: 700;"
                    if bias == "BEARISH":
                        return "color: #d62728; font-weight: 700;"
                    if bias == "NEUTRAL":
                        return "color: #9aa0a6; font-weight: 700;"
                    return ""

                def _volatility_status_style(value):
                    s = str(value).upper()
                    if s == "LOW":
                        return "color: #9aa0a6; font-weight: 700;"
                    if s == "NORMAL":
                        return "color: #2ca02c; font-weight: 700;"
                    if s == "HIGH":
                        return "color: #d62728; font-weight: 700;"
                    return ""

                styled_df = df.style
                if bias_columns:
                    styled_df = styled_df.map(_bias_style, subset=bias_columns)
                if vol_status_cols:
                    styled_df = styled_df.map(_volatility_status_style, subset=vol_status_cols)

                st.dataframe(styled_df, use_container_width=True, hide_index=True)

        if "volatility_calculation_detail" in st.session_state:
            detail = st.session_state["volatility_calculation_detail"]
            with st.container(border=True):
                st.markdown("**Volatility Calculation Detail**")
                top_cols = st.columns(5)
                with top_cols[0]:
                    st.metric("ID", detail.get("id", "—"))
                with top_cols[1]:
                    st.metric("Session ID", detail.get("session_id", "—"))
                with top_cols[2]:
                    st.markdown(
                        f"**Volatility Status**<br>{_volatility_status_colored_html(detail.get('volatility_status'))}",
                        unsafe_allow_html=True,
                    )
                with top_cols[3]:
                    st.metric("Timeframe", detail.get("timeframe", "—"))
                with top_cols[4]:
                    calc_at = _fmt_dt(detail.get("calculated_at")) if detail.get("calculated_at") else "—"
                    st.metric("Calculated At", calc_at)
                st.json(detail)

    with visualize_tab:
        st.subheader("Visualize Session")
        ctrl_cols = st.columns([1, 1, 3])
        with ctrl_cols[0]:
            st.toggle("Auto Refresh", key="viz_auto_refresh_enabled")
            _visualize_auto_refresh_fragment(show_caption=True)
        with ctrl_cols[1]:
            if st.button("Refresh now", key="viz_refresh_now", use_container_width=True):
                cfg = st.session_state.get("visualize_auto_refresh_cfg")
                if isinstance(cfg, dict):
                    cfg_session_id = int(cfg.get("session_id", 0))
                    try:
                        viz_result = api_client.visualize_session(cfg_session_id, int(cfg.get("num_bars", 200)))
                        st.session_state["session_visualization_result"] = viz_result
                        tf = viz_result.get("session", {}).get("timeframe", cfg.get("timeframe", "1m"))
                        st.session_state["visualize_auto_refresh_cfg"] = {
                            "session_id": cfg_session_id,
                            "num_bars": int(cfg.get("num_bars", 200)),
                            "timeframe": tf,
                            "interval_seconds": _refresh_seconds_for_timeframe(tf),
                        }
                        st.session_state["visualize_last_fetch_ts"] = time.time()
                        st.session_state.pop("visualize_auto_refresh_error", None)
                    except APIError:
                        st.error(f"No such session exists with id {cfg_session_id}")
                    except Exception:
                        st.error(f"No such session exists with id {cfg_session_id}")
                else:
                    st.info("Run Visualize first to initialize refresh config.")
        with ctrl_cols[2]:
            if st.session_state.get("visualize_auto_refresh_error"):
                st.warning(st.session_state["visualize_auto_refresh_error"])

        with st.container(border=True):
            with st.form("visualize_session_form"):
                viz_cols = st.columns(2)
                with viz_cols[0]:
                    viz_session_id = st.number_input("Session ID", min_value=1, value=1, step=1, key="viz_session_id")
                with viz_cols[1]:
                    viz_num_bars = st.number_input("Num Bars", min_value=20, max_value=1000, value=70, step=20, key="viz_num_bars")

                if st.form_submit_button("Run Visualize", use_container_width=True):
                    try:
                        viz_result = api_client.visualize_session(int(viz_session_id), int(viz_num_bars))
                        st.session_state["session_visualization_result"] = viz_result
                        tf = viz_result.get("session", {}).get("timeframe", "1m")
                        st.session_state["visualize_auto_refresh_cfg"] = {
                            "session_id": int(viz_session_id),
                            "num_bars": int(viz_num_bars),
                            "timeframe": tf,
                            "interval_seconds": _refresh_seconds_for_timeframe(tf),
                        }
                        st.session_state["visualize_last_fetch_ts"] = time.time()
                        st.session_state.pop("visualize_auto_refresh_error", None)
                    except APIError:
                        st.error(f"No such session exists with id {int(viz_session_id)}")
                    except Exception:
                        st.error(f"No such session exists with id {int(viz_session_id)}")

        if "session_visualization_result" in st.session_state:
            data = st.session_state["session_visualization_result"]
            session = data.get("session", {})
            bars = data.get("bars", [])
            session_alerts = []
            if session.get("id") is not None:
                try:
                    session_alerts = api_client.list_alerts(
                        session_id=int(session.get("id")),
                        limit=1000,
                        offset=0,
                    )
                except Exception:
                    session_alerts = []

            with st.container(border=True):
                st.markdown(
                    f"**Session #{session.get('id', '—')}** | Symbol: `{session.get('symbol', '—')}` | "
                    f"Provider: `{session.get('provider', '—')}` | TF: `{session.get('timeframe', '—')}` | "
                    f"Bars: `{data.get('bars_count', len(bars))}` | Market Connected: `{data.get('market_data_connected', False)}`"
                )

                import pandas as pd
                import altair as alt

                if bars:
                    bars_df = pd.DataFrame([{"bar_index": idx, **bar} for idx, bar in enumerate(bars)])
                    for col in ["open", "high", "low", "close", "sma9", "sma20", "atr14"]:
                        if col in bars_df.columns:
                            bars_df[col] = pd.to_numeric(bars_df[col], errors="coerce")
                    # Backend timestamps are UTC; parse as UTC to keep chart times unchanged.
                    bars_df["date"] = pd.to_datetime(bars_df.get("date"), errors="coerce", utc=True)
                    chart_df = bars_df.dropna(subset=["date", "open", "high", "low", "close"]).copy()

                    if not chart_df.empty:
                        last_bar = chart_df.iloc[-1]
                        last_close = pd.to_numeric(last_bar.get("close"), errors="coerce")
                        last_close_display = (
                            f"{float(last_close):,.2f}" if pd.notna(last_close) else "—"
                        )
                        last_bar_time_raw = None
                        if isinstance(bars, list) and bars:
                            last_raw = bars[-1]
                            if isinstance(last_raw, dict):
                                last_bar_time_raw = last_raw.get("date")
                        chart_header_cols = st.columns([1, 2])
                        with chart_header_cols[0]:
                            st.metric("Last Closed Price", last_close_display)
                        with chart_header_cols[1]:
                            st.caption(f"Last bar time: {_fmt_dt(last_bar_time_raw)}")

                        chart_df["candle_low"] = chart_df[["open", "close"]].min(axis=1)
                        chart_df["candle_high"] = chart_df[["open", "close"]].max(axis=1)
                        bull_indices = {
                            int(i)
                            for i in data.get("bull_bar_indices", [])
                            if isinstance(i, (int, float)) or (isinstance(i, str) and i.isdigit())
                        }
                        bear_indices = {
                            int(i)
                            for i in data.get("bear_bar_indices", [])
                            if isinstance(i, (int, float)) or (isinstance(i, str) and i.isdigit())
                        }
                        persistence_window = session.get("persistence_window")
                        try:
                            persistence_window = int(persistence_window)
                        except (TypeError, ValueError):
                            persistence_window = 0
                        max_bar_index = int(chart_df["bar_index"].max())
                        marker_min_index = (
                            max_bar_index - persistence_window + 1
                            if persistence_window and persistence_window > 0
                            else max_bar_index + 1
                        )

                        def _resolve_candle_color(row):
                            idx = int(row["bar_index"])
                            is_bull = row["close"] >= row["open"]
                            if idx >= marker_min_index:
                                return "#39ff14" if is_bull else "#ff073a"
                            return "#2ca02c" if is_bull else "#d62728"

                        chart_df["candle_color"] = chart_df.apply(_resolve_candle_color, axis=1)

                        price_scale = alt.Scale(zero=False)
                        x_scale_utc = alt.Scale(type="utc")
                        wick = alt.Chart(chart_df).mark_rule().encode(
                            x=alt.X("date:T", title="Time (UTC)", scale=x_scale_utc),
                            y=alt.Y("low:Q", title="Price", scale=price_scale),
                            y2="high:Q",
                            color=alt.value("#9aa0a6"),
                        )
                        candle = alt.Chart(chart_df).mark_bar(size=8).encode(
                            x=alt.X("date:T", scale=x_scale_utc),
                            y=alt.Y("candle_low:Q", scale=price_scale),
                            y2="candle_high:Q",
                            color=alt.Color("candle_color:N", scale=None, legend=None),
                        )
                        chart = wick + candle

                        highlight_rows = []
                        if bull_indices or bear_indices:
                            for _, row in chart_df.iterrows():
                                idx = int(row["bar_index"])
                                if idx < marker_min_index:
                                    continue
                                if idx in bull_indices:
                                    highlight_rows.append(
                                        {
                                            "date": row["date"],
                                            "price": row["low"],
                                            "label": "Bull Index",
                                        }
                                    )
                                if idx in bear_indices:
                                    highlight_rows.append(
                                        {
                                            "date": row["date"],
                                            "price": row["high"],
                                            "label": "Bear Index",
                                        }
                                    )
                        if highlight_rows:
                            highlights_df = pd.DataFrame(highlight_rows)
                            highlight_markers = alt.Chart(highlights_df).mark_point(
                                filled=True, size=70, shape="circle", stroke="black", strokeWidth=0.8, opacity=0.9
                            ).encode(
                                x=alt.X("date:T", scale=x_scale_utc),
                                y=alt.Y("price:Q", scale=price_scale),
                                color=alt.Color(
                                    "label:N",
                                    scale=alt.Scale(domain=["Bull Index", "Bear Index"], range=["#00ff00", "#ff0033"]),
                                    legend=alt.Legend(title="Bar Highlights"),
                                ),
                            )
                            chart = chart + highlight_markers

                        if "sma9" in chart_df.columns and chart_df["sma9"].notna().any():
                            chart = chart + alt.Chart(chart_df).mark_line(color="#1f77b4", strokeWidth=2).encode(
                                x=alt.X("date:T", scale=x_scale_utc),
                                y=alt.Y("sma9:Q", scale=price_scale),
                            )
                        if "sma20" in chart_df.columns and chart_df["sma20"].notna().any():
                            chart = chart + alt.Chart(chart_df).mark_line(color="#ff7f0e", strokeWidth=2).encode(
                                x=alt.X("date:T", scale=x_scale_utc),
                                y=alt.Y("sma20:Q", scale=price_scale),
                            )

                        # ATR hint band around close ± ATR14.
                        if "atr14" in chart_df.columns and chart_df["atr14"].notna().any():
                            atr_hint_df = chart_df.dropna(subset=["atr14"]).copy()
                            atr_hint_df["atr_upper"] = atr_hint_df["close"] + atr_hint_df["atr14"]
                            atr_hint_df["atr_lower"] = atr_hint_df["close"] - atr_hint_df["atr14"]
                            atr_band = alt.Chart(atr_hint_df).mark_area(opacity=0.12, color="#9c27b0").encode(
                                x=alt.X("date:T", scale=x_scale_utc),
                                y=alt.Y("atr_lower:Q", scale=price_scale),
                                y2="atr_upper:Q",
                            )
                            chart = chart + atr_band

                        # Swing markers and horizontal levels.
                        swings = []
                        for key in ["latest_high_swing", "previous_high_swing", "latest_low_swing", "previous_low_swing"]:
                            if data.get(key):
                                swings.append(data[key])
                        if swings:
                            swings_df = pd.DataFrame(swings)
                            if {"bar_index", "type", "price"}.issubset(swings_df.columns):
                                swings_df["bar_index"] = pd.to_numeric(swings_df["bar_index"], errors="coerce").astype("Int64")
                                swings_df["price"] = pd.to_numeric(swings_df["price"], errors="coerce")
                                swings_df = swings_df.dropna(subset=["bar_index", "price"])
                                marker_df = swings_df.merge(chart_df[["bar_index", "date"]], on="bar_index", how="left")
                                marker_df = marker_df.dropna(subset=["date", "price"])
                                if not marker_df.empty:
                                    markers = alt.Chart(marker_df).mark_point(
                                        filled=True, size=280, stroke="black", strokeWidth=1.5, opacity=0.95
                                    ).encode(
                                        x=alt.X("date:T", scale=x_scale_utc),
                                        y=alt.Y("price:Q", scale=price_scale),
                                        color=alt.Color(
                                            "type:N",
                                            scale=alt.Scale(domain=["HIGH", "LOW"], range=["#ff0033", "#00b4ff"]),
                                            legend=alt.Legend(title="Swing"),
                                        ),
                                        shape=alt.Shape(
                                            "type:N",
                                            scale=alt.Scale(domain=["HIGH", "LOW"], range=["triangle-up", "triangle-down"]),
                                            legend=None,
                                        ),
                                    )
                                    chart = chart + markers

                        # Latest alert entry/stop/target lines.
                        latest_alert = data.get("latest_alert")
                        if isinstance(latest_alert, dict):
                            alert_is_open = latest_alert.get("outcome_status") == "OPEN"
                            if alert_is_open:
                                for field, color in [
                                    ("entry_signal_price", "#00c853"),
                                    ("stop_price", "#d50000"),
                                    ("target_price", "#2962ff"),
                                ]:
                                    val = latest_alert.get(field)
                                    if val is not None:
                                        line_df = pd.DataFrame([{"y": float(val)}])
                                        line = alt.Chart(line_df).mark_rule(color=color, strokeDash=[6, 3]).encode(
                                            y=alt.Y("y:Q", scale=price_scale)
                                        )
                                        chart = chart + line

                        # Vertical dotted lines for all session alerts (PREALERT + TRIGGER_ALERT).
                        if session_alerts:
                            alerts_df = pd.DataFrame(session_alerts)
                            if {"created_at", "direction"}.issubset(alerts_df.columns):
                                alerts_df["alert_time"] = pd.to_datetime(alerts_df["created_at"], errors="coerce")
                                alerts_df = alerts_df.dropna(subset=["alert_time"])
                                if not chart_df.empty and "date" in chart_df.columns:
                                    # Keep endpoint UTC values unchanged; localize naive datetimes to UTC.
                                    if alerts_df["alert_time"].dt.tz is None:
                                        alerts_df["alert_time"] = alerts_df["alert_time"].dt.tz_localize("UTC")
                                    else:
                                        alerts_df["alert_time"] = alerts_df["alert_time"].dt.tz_convert("UTC")
                                    chart_times = pd.to_datetime(chart_df["date"], errors="coerce")
                                    if chart_times.dt.tz is None:
                                        chart_times = chart_times.dt.tz_localize("UTC")
                                    else:
                                        chart_times = chart_times.dt.tz_convert("UTC")
                                    min_chart_time = chart_times.min()
                                    max_chart_time = chart_times.max()
                                    alerts_df = alerts_df[
                                        (alerts_df["alert_time"] >= min_chart_time)
                                        & (alerts_df["alert_time"] <= max_chart_time)
                                    ]
                                if not alerts_df.empty:
                                    alert_vlines = alt.Chart(alerts_df).mark_rule(
                                        strokeDash=[4, 4], strokeWidth=1.6, opacity=0.95
                                    ).encode(
                                        x=alt.X("alert_time:T", scale=x_scale_utc),
                                        color=alt.Color(
                                            "direction:N",
                                            scale=alt.Scale(domain=["LONG", "SHORT"], range=["#39ff14", "#ff073a"]),
                                            legend=alt.Legend(title="Alert Direction"),
                                        ),
                                        tooltip=[
                                            alt.Tooltip("id:Q", title="Alert ID"),
                                            alt.Tooltip("type:N", title="Type"),
                                            alt.Tooltip("direction:N", title="Direction"),
                                            alt.Tooltip("outcome_status:N", title="Outcome"),
                                            alt.Tooltip("alert_time:T", title="Time"),
                                        ],
                                    )
                                    chart = chart + alert_vlines

                        st.caption(
                            "Legend: Candles + SMA9/SMA20 | Neon candles: actual open/close direction | "
                            "Small circle markers: Bull/Bear index points | Purple band: ATR14 hint | "
                            "Swing markers: High/Low | Alert lines: Entry/Stop/Target | "
                            "Dotted vertical lines: Alerts (LONG green / SHORT red)"
                        )
                        st.altair_chart(chart.properties(height=420), use_container_width=True)
                    else:
                        st.info("Visualization bars are not chartable.")
                else:
                    st.info("No bars returned in visualization response.")

                # Bias status panel.
                st.markdown("### Bias Status")
                bias_cols = st.columns(4)
                with bias_cols[0]:
                    st.markdown(
                        f"**Session State Bias**<br>{_bias_colored_html(session.get('state_bias', 'NEUTRAL'))}",
                        unsafe_allow_html=True,
                    )
                with bias_cols[1]:
                    st.markdown(
                        f"**Session Candidate Bias**<br>{_bias_colored_html(session.get('candidate_bias', 'NEUTRAL'))}",
                        unsafe_allow_html=True,
                    )
                with bias_cols[2]:
                    st.metric("Consecutive Count", session.get("consecutive_count", 0))
                with bias_cols[3]:
                    st.metric("Can Calculate Bias", data.get("latest_bias_calculation", {}).get("can_calculate_bias", "—"))

                latest_bias = data.get("latest_bias_calculation")
                if latest_bias:
                    lb_cols = st.columns(5)
                    with lb_cols[0]:
                        st.markdown(
                            f"**MA Bar Bias**<br>{_bias_colored_html(latest_bias.get('ma_bar_bias', 'NEUTRAL'))}",
                            unsafe_allow_html=True,
                        )
                    with lb_cols[1]:
                        st.markdown(
                            f"**MA Persistent Bias**<br>{_bias_colored_html(latest_bias.get('ma_persistent_bias', 'NEUTRAL'))}",
                            unsafe_allow_html=True,
                        )
                    with lb_cols[2]:
                        st.markdown(
                            f"**Structure Bias**<br>{_bias_colored_html(latest_bias.get('structure_bias', 'NEUTRAL'))}",
                            unsafe_allow_html=True,
                        )
                    with lb_cols[3]:
                        st.markdown(
                            f"**Strength**<br>{_bias_colored_html(latest_bias.get('strenght', 'NEUTRAL'))}",
                            unsafe_allow_html=True,
                        )
                    with lb_cols[4]:
                        st.metric("Bull / Bear Count", f"{latest_bias.get('bull_count', 0)} / {latest_bias.get('bear_count', 0)}")

                # Pullback status panel.
                st.markdown("### Pullback Status")
                pb_cols = st.columns(5)
                with pb_cols[0]:
                    st.metric("Pullback State", session.get("pullback_state", "NONE"))
                with pb_cols[1]:
                    st.metric("Direction", session.get("pullback_direction", "NONE"))
                with pb_cols[2]:
                    st.metric("PB Anchor High", session.get("pb_anchor_high", "—"))
                with pb_cols[3]:
                    st.metric("PB Anchor Low", session.get("pb_anchor_low", "—"))
                with pb_cols[4]:
                    st.metric("Touched SMA20", "Yes" if session.get("touched_sma20") else "No")

                latest_pullback = data.get("latest_pullback_calculation")
                if latest_pullback:
                    st.markdown("**Latest Pullback Calculation**")
                    lp_cols = st.columns(4)
                    with lp_cols[0]:
                        st.metric("State", latest_pullback.get("pullback_state", "NONE"))
                    with lp_cols[1]:
                        st.metric("Direction", latest_pullback.get("pullback_direction", "NONE"))
                    with lp_cols[2]:
                        st.metric("Trigger Alert", "Yes" if latest_pullback.get("trigger_alert") else "No")
                    with lp_cols[3]:
                        st.metric("Touched SMA20", "Yes" if latest_pullback.get("touched_sma20") else "No")
                    st.caption(f"Reset Reason: **{latest_pullback.get('reset_reason', '—')}**")
                    st.json(latest_pullback)

                # Volatility panel.
                st.markdown("### Volatility")
                latest_volatility = data.get("latest_volatility_calculation")
                if latest_volatility:
                    lv_cols = st.columns(5)
                    with lv_cols[0]:
                        st.markdown(
                            f"**Status**<br>{_volatility_status_colored_html(latest_volatility.get('volatility_status'))}",
                            unsafe_allow_html=True,
                        )
                    with lv_cols[1]:
                        st.metric("ATR14", latest_volatility.get("atr14", "—"))
                    with lv_cols[2]:
                        st.metric("ATR14 SMA20", latest_volatility.get("atr14_sma20", "—"))
                    with lv_cols[3]:
                        st.metric("Vol Ratio", latest_volatility.get("vol_ratio", "—"))
                    with lv_cols[4]:
                        st.metric("Can Calculate", "Yes" if latest_volatility.get("can_calculate") else "No")
                    st.caption(f"Reason: {latest_volatility.get('reason', '—')}")
                    st.json(latest_volatility)
                else:
                    st.info("No latest volatility calculation available.")

                # Alert panel.
                st.markdown("### Alert")
                latest_alert = data.get("latest_alert")
                if latest_alert:
                    alert_cols = st.columns(5)
                    with alert_cols[0]:
                        st.metric("Direction", latest_alert.get("direction", "—"))
                    with alert_cols[1]:
                        st.metric("Type", latest_alert.get("type", "—"))
                    with alert_cols[2]:
                        st.metric("Entry", latest_alert.get("entry_signal_price", "—"))
                    with alert_cols[3]:
                        st.metric("Stop", latest_alert.get("stop_price", "—"))
                    with alert_cols[4]:
                        st.metric("Target", latest_alert.get("target_price", "—"))
                    st.caption(f"Outcome Status: {latest_alert.get('outcome_status', '—')}")
                else:
                    st.info("No latest alert available.")

    with alerts_tab:
        st.subheader("Alerts")

        with st.container(border=True):
            st.markdown("**List Alerts**")
            list_cols = st.columns(7)
            with list_cols[0]:
                al_session_id_filter = st.number_input(
                    "Session ID (0 = all)",
                    min_value=0,
                    value=0,
                    step=1,
                    key="al_list_session_id",
                )
            with list_cols[1]:
                al_status_filter = st.selectbox("Status", ["All"] + ALERT_STATUSES, index=0, key="al_list_status")
            with list_cols[2]:
                al_direction_filter = st.selectbox(
                    "Direction", ["All"] + ALERT_DIRECTIONS, index=0, key="al_list_direction"
                )
            with list_cols[3]:
                al_type_filter = st.selectbox("Type", ["All"] + ALERT_TYPES, index=0, key="al_list_type")
            with list_cols[4]:
                al_risky_filter = st.selectbox("Risky", ["All", "Yes", "No"], index=0, key="al_list_risky")
            with list_cols[5]:
                al_limit = st.number_input("Limit", min_value=1, max_value=1000, value=100, step=10, key="al_list_limit")
            with list_cols[6]:
                al_offset = st.number_input("Offset", min_value=0, value=0, step=10, key="al_list_offset")

            if st.button("Get Alerts", use_container_width=True, key="al_get_list"):
                try:
                    session_id_filter = int(al_session_id_filter) if int(al_session_id_filter) > 0 else None
                    risky_filter_val = (
                        True if al_risky_filter == "Yes" else False if al_risky_filter == "No" else None
                    )
                    alerts = api_client.list_alerts(
                        session_id=session_id_filter,
                        outcome_status=al_status_filter if al_status_filter != "All" else None,
                        direction=al_direction_filter if al_direction_filter != "All" else None,
                        type=al_type_filter if al_type_filter != "All" else None,
                        risky=risky_filter_val,
                        limit=int(al_limit),
                        offset=int(al_offset),
                    )

                    # Keep a UI-side fallback filter for backends that ignore unknown query params.
                    if risky_filter_val is not None:
                        alerts = [a for a in alerts if bool(a.get("risky", False)) == risky_filter_val]
                    st.session_state["alerts_list"] = alerts
                    st.success(f"Loaded {len(alerts)} alert(s).")
                except APIError as e:
                    st.error(f"Failed to list alerts: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

            if "alerts_list" in st.session_state:
                import pandas as pd

                alerts_df = pd.DataFrame(st.session_state["alerts_list"])
                if "created_at" in alerts_df.columns:
                    alerts_df["created_at"] = alerts_df["created_at"].apply(_fmt_dt)
                preferred_cols = [
                    "id",
                    "session_id",
                    "created_at",
                    "direction",
                    "type",
                    "outcome_status",
                    "risky",
                    "entry_signal_price",
                    "stop_price",
                    "target_price",
                    "reason",
                ]
                display_cols = [c for c in preferred_cols if c in alerts_df.columns] + [
                    c for c in alerts_df.columns if c not in preferred_cols
                ]
                st.dataframe(alerts_df[display_cols], use_container_width=True, hide_index=True)

        with st.container(border=True):
            st.markdown("**Get One / Delete One**")
            action_cols = st.columns(2)
            with action_cols[0]:
                al_detail_id = st.number_input("Alert ID (Get One)", min_value=1, value=1, step=1, key="al_detail_id")
                if st.button("Get One Alert", use_container_width=True, key="al_get_one"):
                    try:
                        st.session_state["alert_detail"] = api_client.get_alert(int(al_detail_id))
                    except APIError as e:
                        st.error(f"Failed to get alert: {e.detail}")
                    except Exception as e:
                        st.error(f"Connection error: {e}")
            with action_cols[1]:
                al_delete_id = st.number_input(
                    "Alert ID (Delete One)", min_value=1, value=1, step=1, key="al_delete_id"
                )
                if st.button("Delete One Alert", use_container_width=True, key="al_delete_one", type="primary"):
                    try:
                        api_client.delete_alert(int(al_delete_id))
                        st.success(f"Deleted alert #{int(al_delete_id)}")
                        if "alerts_list" in st.session_state:
                            st.session_state["alerts_list"] = [
                                row
                                for row in st.session_state["alerts_list"]
                                if int(row.get("id", -1)) != int(al_delete_id)
                            ]
                        if "alert_detail" in st.session_state and int(st.session_state["alert_detail"].get("id", -1)) == int(
                            al_delete_id
                        ):
                            st.session_state.pop("alert_detail", None)
                    except APIError as e:
                        st.error(f"Failed to delete alert: {e.detail}")
                    except Exception as e:
                        st.error(f"Connection error: {e}")

            if "alert_detail" in st.session_state:
                st.markdown("**Alert Detail**")
                ad = st.session_state["alert_detail"]
                detail_cols = st.columns(6)
                with detail_cols[0]:
                    st.metric("Direction", ad.get("direction", "—"))
                with detail_cols[1]:
                    st.metric("Type", ad.get("type", "—"))
                with detail_cols[2]:
                    st.metric("Outcome Status", ad.get("outcome_status", "—"))
                with detail_cols[3]:
                    st.metric("Entry", ad.get("entry_signal_price", "—"))
                with detail_cols[4]:
                    st.metric("Stop", ad.get("stop_price", "—"))
                with detail_cols[5]:
                    st.metric("Risky", "Yes" if bool(ad.get("risky", False)) else "No")
                st.json(ad)

        with st.container(border=True):
            st.markdown("**Cancel Alerts For Session**")
            cancel_cols = st.columns([3, 2])
            with cancel_cols[0]:
                cancel_session_id = st.number_input(
                    "Session ID (Cancel Alerts)",
                    min_value=1,
                    value=1,
                    step=1,
                    key="alerts_cancel_session_id",
                )
            with cancel_cols[1]:
                st.write("")
                if st.button(
                    "Cancel Session Alerts",
                    use_container_width=True,
                    key="alerts_cancel_session_btn",
                    type="primary",
                ):
                    try:
                        api_client.cancel_session_alerts(int(cancel_session_id))
                        st.success(f"Canceled alerts for session #{int(cancel_session_id)}.")
                    except APIError as e:
                        st.error(f"Failed to cancel alerts for session: {e.detail}")
                    except Exception as e:
                        st.error(f"Connection error: {e}")

        with st.container(border=True):
            st.markdown("**Alert Performance By Session**")
            perf_cols = st.columns([3, 2])
            with perf_cols[0]:
                perf_session_id = st.number_input(
                    "Session ID (Alert Performance)",
                    min_value=1,
                    value=1,
                    step=1,
                    key="alerts_perf_session_id",
                )
            with perf_cols[1]:
                st.write("")
                if st.button(
                    "Get Alert Performance",
                    use_container_width=True,
                    key="alerts_get_performance_btn",
                ):
                    try:
                        st.session_state["alerts_performance"] = api_client.get_alert_performance(int(perf_session_id))
                    except APIError as e:
                        st.error(f"Failed to get alert performance: {e.detail}")
                    except Exception as e:
                        st.error(f"Connection error: {e}")

            if "alerts_performance" in st.session_state:
                perf = st.session_state["alerts_performance"]
                perf_metrics_1 = st.columns(5)
                with perf_metrics_1[0]:
                    st.metric("Total Alerts", perf.get("total_alerts", 0))
                with perf_metrics_1[1]:
                    st.metric("PREALERTs", perf.get("no_pre_alerts", 0))
                with perf_metrics_1[2]:
                    st.metric("Trigger Alerts", perf.get("no_trigger_alerts", 0))
                with perf_metrics_1[3]:
                    st.metric("TP Hits", perf.get("tp_hits", 0))
                with perf_metrics_1[4]:
                    st.metric("SL Hits", perf.get("sl_hits", 0))

                perf_metrics_2 = st.columns(4)
                with perf_metrics_2[0]:
                    st.metric("Canceled", perf.get("canceled", 0))
                with perf_metrics_2[1]:
                    st.metric("Open", perf.get("open", 0))
                with perf_metrics_2[2]:
                    st.metric("Win Rate", f"{float(perf.get('win_rate', 0)):.2f}%")
                with perf_metrics_2[3]:
                    st.metric("Session ID", perf.get("session_id", "—"))
                st.json(perf)

    with sessions_tab:
        with st.container(border=True):
            st.markdown("**Session Metadata**")
            md_top_cols = st.columns([3, 2])
            with md_top_cols[0]:
                md_session_id = st.number_input(
                    "Session ID (Metadata)",
                    min_value=1,
                    value=1,
                    step=1,
                    key="session_metadata_session_id",
                )
            with md_top_cols[1]:
                st.write("")
                get_metadata_clicked = st.button("Get Metadata", use_container_width=True, key="session_get_metadata_btn")

            if get_metadata_clicked:
                try:
                    st.session_state["session_metadata"] = api_client.get_session_metadata(int(md_session_id))
                except APIError as e:
                    st.error(f"Failed to get metadata: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

            if "session_metadata" in st.session_state:
                metadata = st.session_state["session_metadata"]
                md_cols = st.columns(4)
                with md_cols[0]:
                    st.metric("max_pullback_depth_atr", metadata.get("max_pullback_depth_atr", "—"))
                with md_cols[1]:
                    st.metric("max_pullback_duration_bars", metadata.get("max_pullback_duration_bars", "—"))
                with md_cols[2]:
                    st.metric("min_pullback_depth_atr", metadata.get("min_pullback_depth_atr", "—"))
                with md_cols[3]:
                    st.metric("sma20_touch_band_atr", metadata.get("sma20_touch_band_atr", "—"))

                md_cols_2 = st.columns(4)
                with md_cols_2[0]:
                    st.metric("strong_close_max_wick_ratio", metadata.get("strong_close_max_wick_ratio", "—"))
                with md_cols_2[1]:
                    st.metric(
                        "risky_alert_range_threshold_pct",
                        metadata.get("risky_alert_range_threshold_pct", "—"),
                    )
                with md_cols_2[2]:
                    st.metric("persistence_threshold", metadata.get("persistence_threshold", "—"))
                with md_cols_2[3]:
                    st.metric("strength_threshold", metadata.get("strength_threshold", "—"))

                md_cols_3 = st.columns(4)
                with md_cols_3[0]:
                    st.metric("cooldown_until", metadata.get("cooldown_until", "—"))
                st.json(metadata)

        # ── Create session form ───────────────────────────────────────
        with st.expander("➕ Create new session", expanded=False):
            with st.form("create_session_form"):
                col1, col2 = st.columns(2)
                with col1:
                    symbol = st.text_input("Symbol", value="BTCUSDT", placeholder="e.g. AAPL, EURUSD")
                    provider = st.selectbox(
                        "Provider",
                        PROVIDERS,
                        index=PROVIDERS.index("BYBIT") if "BYBIT" in PROVIDERS else 0,
                    )
                    timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=0)
                with col2:
                    sec_type = st.selectbox(
                        "Sec Type",
                        SEC_TYPES,
                        index=SEC_TYPES.index("SPOT") if "SPOT" in SEC_TYPES else 0,
                    )
                    hysteresis_k = st.number_input("Hysteresis K", min_value=1, value=2, step=1)
                    persistence_window = st.number_input("Persistence Window", min_value=5, value=20, step=1)
                bottom_col1, bottom_col2 = st.columns(2)
                with bottom_col1:
                    persistence_threshold = st.number_input("Persistence Threshold", min_value=1, value=10, step=1)
                with bottom_col2:
                    swing_lookback = st.number_input("Swing Lookback", min_value=1, value=2, step=1)
                cooldown_until = st.number_input("Cooldown Until", min_value=0, value=5, step=1)

                submitted = st.form_submit_button("Create Session", use_container_width=True)
                if submitted:
                    if not symbol or not symbol.strip():
                        st.error("Symbol is required.")
                    else:
                        try:
                            new_session = api_client.create_session(
                                symbol=symbol,
                                provider=provider,
                                timeframe=timeframe,
                                sec_type=sec_type,
                                hysteresis_k=int(hysteresis_k),
                                persistence_window=int(persistence_window),
                                persistence_threshold=int(persistence_threshold),
                                swing_lookback=int(swing_lookback),
                                cooldown_until=int(cooldown_until),
                            )
                            st.success(f"Session **#{new_session['id']}** created for **{new_session['symbol']}**")
                            st.rerun()
                        except APIError as e:
                            st.error(f"Failed to create session: {e.detail}")
                        except Exception as e:
                            st.error(f"Connection error: {e}")

    with sessions_tab:
        st.divider()

        # ── Filters ───────────────────────────────────────────────────────
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            status_filter = st.selectbox(
                "Filter by status",
                ["All", "ACTIVE", "PAUSED", "COMPLETED"],
                index=0,
            )
        with filter_col2:
            symbol_filter = st.text_input("Filter by symbol", placeholder="Leave blank for all")
        with filter_col3:
            provider_filter = st.selectbox("Filter by provider", ["All"] + PROVIDERS, index=0)

        # ── Fetch sessions ────────────────────────────────────────────────
        try:
            sessions = api_client.list_sessions(
                status=status_filter if status_filter != "All" else None,
                symbol=symbol_filter.strip().upper() if symbol_filter.strip() else None,
                provider=provider_filter if provider_filter != "All" else None,
            )
        except APIError as e:
            st.error(f"Failed to load sessions: {e.detail}")
            return
        except Exception as e:
            st.error(f"Cannot reach backend: {e}")
            return

        if not sessions:
            st.info("No sessions found. Create one above to get started.")
            return

        st.subheader(f"{len(sessions)} session(s)")

        for sess in sessions:
            sid = sess["id"]
            status = sess["status"]
            icon = STATUS_COLORS.get(status, "⚪")
            card_class = "session-card"
            if status == "PAUSED":
                card_class += " session-card-paused"
            elif status == "COMPLETED":
                card_class += " session-card-completed"

            with st.container(border=True):
                top_left, top_right = st.columns([3, 1])
                with top_left:
                    st.markdown(f"### {icon} {sess['symbol']}  `#{sid}`")
                with top_right:
                    st.markdown(f"**Status:** {status}")

                detail_cols = st.columns(5)
                with detail_cols[0]:
                    st.metric("Provider / TF", f"{sess.get('provider', 'IBKR')} / {sess['timeframe']}")
                with detail_cols[1]:
                    state_bias = sess.get("state_bias", sess.get("current_bias", "NEUTRAL"))
                    st.markdown(f"**State Bias**<br>{_bias_colored_html(state_bias)}", unsafe_allow_html=True)
                with detail_cols[2]:
                    st.markdown(
                        f"**Candidate Bias**<br>{_bias_colored_html(sess.get('candidate_bias', 'NEUTRAL'))}",
                        unsafe_allow_html=True,
                    )
                with detail_cols[3]:
                    st.metric("Sec Type", sess.get("sec_type", "STK"))
                with detail_cols[4]:
                    st.metric("Consec. Count", sess["consecutive_count"])

                param_cols = st.columns(5)
                with param_cols[0]:
                    st.caption(f"Persist. Window: **{sess['persistence_window']}**")
                with param_cols[1]:
                    st.caption(f"Persist. Threshold: **{sess['persistence_threshold']}**")
                with param_cols[2]:
                    st.caption(f"Cooldown Until: **{sess.get('cooldown_until', '—')}**")
                with param_cols[3]:
                    st.caption(f"Started: **{_fmt_dt(sess.get('started_at'))}**")
                with param_cols[4]:
                    st.caption(f"Ended: **{_fmt_dt(sess.get('ended_at'))}**")

                pullback_cols = st.columns(5)
                with pullback_cols[0]:
                    st.caption(f"Swing Lookback: **{sess.get('swing_lookback', '—')}**")
                with pullback_cols[1]:
                    st.caption(f"Pullback State: **{sess.get('pullback_state', 'NONE')}**")
                with pullback_cols[2]:
                    st.caption(f"Pullback Direction: **{sess.get('pullback_direction', 'NONE')}**")
                with pullback_cols[3]:
                    touched = "Yes" if sess.get("touched_sma20") else "No"
                    st.caption(f"Touched SMA20: **{touched}**")
                with pullback_cols[4]:
                    st.caption(f"Alert Freeze: **{'Yes' if sess.get('alert_freeze') else 'No'}**")

                level_cols = st.columns(5)
                with level_cols[0]:
                    st.caption(f"PB Anchor High: **{sess.get('pb_anchor_high', '—')}**")
                with level_cols[1]:
                    st.caption(f"PB Low: **{sess.get('pb_low', '—')}**")
                with level_cols[2]:
                    st.caption(f"PB Anchor Low: **{sess.get('pb_anchor_low', '—')}**")
                with level_cols[3]:
                    st.caption(f"PB High: **{sess.get('pb_high', '—')}**")
                with level_cols[4]:
                    st.caption(f"PB Start At: **{_fmt_dt(sess.get('pb_start_at'))}**")

                st.caption(f"Last Alert At: **{_fmt_dt(sess.get('last_alert_at'))}**")

                # ── Action buttons ────────────────────────────────────────
                btn_cols = st.columns(5)

                with btn_cols[0]:
                    if status != "ACTIVE":
                        if st.button("▶ Start", key=f"start_{sid}", use_container_width=True):
                            try:
                                api_client.start_session(sid, sec_type=sess.get("sec_type"))
                                st.session_state.pop(f"paused_elapsed_{sid}", None)
                                st.rerun()
                            except APIError as e:
                                st.error(e.detail)

                with btn_cols[1]:
                    if status == "ACTIVE":
                        if st.button("⏸ Pause", key=f"pause_{sid}", use_container_width=True):
                            try:
                                paused_session = api_client.pause_session(sid)
                                elapsed = _elapsed_seconds_from_started(paused_session.get("started_at", sess.get("started_at")))
                                if elapsed is not None:
                                    st.session_state[f"paused_elapsed_{sid}"] = elapsed
                                st.rerun()
                            except APIError as e:
                                st.error(e.detail)

                with btn_cols[2]:
                    if status in ("ACTIVE", "PAUSED"):
                        if st.button("⏹ End", key=f"end_{sid}", use_container_width=True):
                            try:
                                api_client.end_session(sid)
                                st.session_state.pop(f"paused_elapsed_{sid}", None)
                                st.rerun()
                            except APIError as e:
                                st.error(e.detail)

                with btn_cols[3]:
                    if status != "ACTIVE":
                        if st.button("✏️ Edit", key=f"edit_{sid}", use_container_width=True):
                            st.session_state[f"editing_{sid}"] = True

                with btn_cols[4]:
                    if st.button("🗑 Delete", key=f"del_{sid}", use_container_width=True, type="primary"):
                        st.session_state[f"confirm_del_{sid}"] = True

                # ── Delete confirmation ───────────────────────────────────
                if st.session_state.get(f"confirm_del_{sid}"):
                    st.warning(f"Are you sure you want to delete session **#{sid}**?")
                    confirm_cols = st.columns(2)
                    with confirm_cols[0]:
                        if st.button("Yes, delete", key=f"yes_del_{sid}", type="primary", use_container_width=True):
                            try:
                                api_client.delete_session(sid)
                                st.session_state.pop(f"confirm_del_{sid}", None)
                                st.rerun()
                            except APIError as e:
                                st.error(e.detail)
                    with confirm_cols[1]:
                        if st.button("Cancel", key=f"no_del_{sid}", use_container_width=True):
                            st.session_state.pop(f"confirm_del_{sid}", None)
                            st.rerun()

                # ── Edit form ─────────────────────────────────────────────
                if st.session_state.get(f"editing_{sid}"):
                    with st.form(f"edit_form_{sid}"):
                        st.subheader(f"Edit Session #{sid}")
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            new_provider = st.selectbox(
                                "Provider",
                                PROVIDERS,
                                index=PROVIDERS.index(sess.get("provider", "IBKR"))
                                if sess.get("provider", "IBKR") in PROVIDERS
                                else 0,
                                key=f"provider_{sid}",
                            )
                            new_sec_type = st.selectbox(
                                "Sec Type",
                                SEC_TYPES,
                                index=SEC_TYPES.index(sess.get("sec_type", "STK"))
                                if sess.get("sec_type", "STK") in SEC_TYPES
                                else 0,
                                key=f"sec_type_{sid}",
                            )
                            new_tf = st.selectbox(
                                "Timeframe",
                                TIMEFRAMES,
                                index=TIMEFRAMES.index(sess["timeframe"]),
                                key=f"tf_{sid}",
                            )
                            new_hk = st.number_input(
                                "Hysteresis K", min_value=1, value=sess["hysteresis_k"], key=f"hk_{sid}"
                            )
                            new_sl = st.number_input(
                                "Swing Lookback", min_value=1, value=sess.get("swing_lookback", 2), key=f"sl_{sid}"
                            )
                        with ec2:
                            new_pw = st.number_input(
                                "Persistence Window", min_value=5, value=sess["persistence_window"], key=f"pw_{sid}"
                            )
                            new_pt = st.number_input(
                                "Persistence Threshold", min_value=1, value=sess["persistence_threshold"], key=f"pt_{sid}"
                            )
                            new_cooldown = st.number_input(
                                "Cooldown Until", min_value=0, value=sess.get("cooldown_until", 5), key=f"cooldown_{sid}"
                            )
                        save_cols = st.columns(2)
                        with save_cols[0]:
                            if st.form_submit_button("Save", use_container_width=True):
                                try:
                                    api_client.update_session(
                                        sid,
                                        provider=new_provider,
                                        sec_type=new_sec_type,
                                        timeframe=new_tf,
                                        hysteresis_k=int(new_hk),
                                        persistence_window=int(new_pw),
                                        persistence_threshold=int(new_pt),
                                        swing_lookback=int(new_sl),
                                        cooldown_until=int(new_cooldown),
                                    )
                                    st.session_state.pop(f"editing_{sid}", None)
                                    st.rerun()
                                except APIError as e:
                                    st.error(e.detail)
                        with save_cols[1]:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                st.session_state.pop(f"editing_{sid}", None)
                                st.rerun()


# ── Provider page ─────────────────────────────────────────────────────

SEC_TYPES = ["STK", "FOREX", "SPOT"]

def provider_page():
    st.header("Provider Gateway")
    selected_provider = st.selectbox("Provider", PROVIDERS, index=0, key="provider_gateway_select")

    # ── Connection controls ───────────────────────────────────────────
    st.subheader("Connection")
    conn_cols = st.columns(3)

    with conn_cols[0]:
        if st.button("Connect", use_container_width=True):
            try:
                result = api_client.provider_connect(provider=selected_provider)
                st.success(f"Connected: {result}")
            except APIError as e:
                st.error(f"Connect failed: {e.detail}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    with conn_cols[1]:
        if st.button("Disconnect", use_container_width=True):
            try:
                result = api_client.provider_disconnect(provider=selected_provider)
                st.success(f"Disconnected: {result}")
            except APIError as e:
                st.error(f"Disconnect failed: {e.detail}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    with conn_cols[2]:
        if st.button("Check Status", use_container_width=True):
            try:
                status = api_client.provider_status(provider=selected_provider)
                st.session_state["provider_status"] = status
            except APIError as e:
                st.error(f"Status check failed: {e.detail}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    if "provider_status" in st.session_state:
        with st.container(border=True):
            st.markdown("**Gateway Status**")
            st.json(st.session_state["provider_status"])

    st.divider()

    # ── Test Bar ──────────────────────────────────────────────────────
    st.subheader("Test Bars")

    with st.form("test_bar_form"):
        tb_cols = st.columns(5)
        with tb_cols[0]:
            tb_symbol = st.text_input("Symbol", placeholder="e.g. AAPL or EURUSD")
        with tb_cols[1]:
            tb_provider = st.selectbox(
                "Provider",
                PROVIDERS,
                index=PROVIDERS.index(selected_provider) if selected_provider in PROVIDERS else 0,
                key="tb_provider",
            )
        with tb_cols[2]:
            tb_timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=0)
        with tb_cols[3]:
            tb_sec_type = st.selectbox("Security Type", SEC_TYPES, index=0)
        with tb_cols[4]:
            tb_num_bars = st.number_input("Num Bars", min_value=5, max_value=200, value=20, step=5)

        tb_submitted = st.form_submit_button("Fetch Test Bar", use_container_width=True)
        if tb_submitted:
            if not tb_symbol or not tb_symbol.strip():
                st.error("Symbol is required.")
            else:
                try:
                    bar_data = api_client.get_test_bars(
                        symbol=tb_symbol,
                        provider=tb_provider,
                        timeframe=tb_timeframe,
                        sec_type=tb_sec_type,
                        num_bars=int(tb_num_bars),
                    )
                    st.session_state["test_bar_result"] = bar_data
                except APIError as e:
                    st.error(f"Test bar failed: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    if "test_bar_result" in st.session_state:
        result = st.session_state["test_bar_result"]

        meta_symbol = ""
        meta_timeframe = ""
        meta_count = None

        if isinstance(result, dict) and "bars" in result:
            bars = result.get("bars", [])
            meta_symbol = result.get("symbol", "")
            meta_timeframe = result.get("timeframe", "")
            meta_count = result.get("count")
        elif isinstance(result, list):
            bars = result
        elif isinstance(result, dict):
            bars = [result]
        else:
            bars = []

        if meta_symbol or meta_timeframe or meta_count is not None:
            st.caption(
                f"Symbol: {meta_symbol or '-'} | Timeframe: {meta_timeframe or '-'} | Count: {meta_count if meta_count is not None else len(bars)}"
            )

        if not bars:
            st.info("No bars returned.")
        else:
            import pandas as pd
            import altair as alt

            indexed_bars = []
            for idx, bar in enumerate(bars):
                row = dict(bar)
                indicators = row.get("indicators")
                if isinstance(indicators, dict):
                    for key, value in indicators.items():
                        row.setdefault(key, value)

                if "atr14" not in row:
                    for key, value in row.items():
                        normalized = "".join(ch for ch in str(key).lower() if ch.isalnum())
                        if normalized in {"atr14", "atr"}:
                            row["atr14"] = value
                            break

                indexed_bars.append({"bar_index": idx, **row})

            df = pd.DataFrame(indexed_bars)
            if "atr14" not in df.columns:
                atr_like_cols = [col for col in df.columns if "atr" in str(col).lower()]
                if atr_like_cols:
                    df["atr14"] = df[atr_like_cols[0]]
            if "atr14" not in df.columns:
                df["atr14"] = None

            desired_cols = [
                "bar_index",
                "date",
                "open",
                "high",
                "low",
                "close",
                "atr14",
                "sma9",
                "sma20",
                "volume",
                "vwap",
            ]
            display_cols = [c for c in desired_cols if c in df.columns]
            display_df = df[display_cols].copy()
            if "atr14" in display_df.columns:
                display_df["atr14"] = pd.to_numeric(display_df["atr14"], errors="coerce")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Basic candlestick chart with optional SMA overlays.
            if {"date", "open", "high", "low", "close"}.issubset(df.columns):
                for col in ["open", "high", "low", "close", "sma9", "sma20", "atr14"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                chart_df = df.dropna(subset=["date", "open", "high", "low", "close"]).copy()

                if not chart_df.empty:
                    st.caption(
                        "Legend: Green = Up candle | Red = Down candle | Blue = SMA9 | Orange = SMA20 | Purple = ATR14"
                    )

                    chart_df["candle_low"] = chart_df[["open", "close"]].min(axis=1)
                    chart_df["candle_high"] = chart_df[["open", "close"]].max(axis=1)
                    chart_df["candle_color"] = chart_df.apply(
                        lambda row: "#2ca02c" if row["close"] >= row["open"] else "#d62728", axis=1
                    )

                    price_scale = alt.Scale(zero=False)
                    x_scale_utc = alt.Scale(type="utc")

                    wick = alt.Chart(chart_df).mark_rule().encode(
                        x=alt.X("date:T", title="Time (UTC)", scale=x_scale_utc),
                        y=alt.Y("low:Q", title="Price", scale=price_scale),
                        y2="high:Q",
                        color=alt.value("#9aa0a6"),
                    )

                    candle = alt.Chart(chart_df).mark_bar(size=8).encode(
                        x=alt.X("date:T", scale=x_scale_utc),
                        y=alt.Y("candle_low:Q", scale=price_scale),
                        y2="candle_high:Q",
                        color=alt.Color("candle_color:N", scale=None, legend=None),
                    )

                    chart = wick + candle

                    if "sma9" in chart_df.columns and chart_df["sma9"].notna().any():
                        sma9_line = alt.Chart(chart_df).mark_line(color="#1f77b4", strokeWidth=2).encode(
                            x=alt.X("date:T", scale=x_scale_utc),
                            y=alt.Y("sma9:Q", scale=price_scale),
                        )
                        chart = chart + sma9_line

                    if "sma20" in chart_df.columns and chart_df["sma20"].notna().any():
                        sma20_line = alt.Chart(chart_df).mark_line(color="#ff7f0e", strokeWidth=2).encode(
                            x=alt.X("date:T", scale=x_scale_utc),
                            y=alt.Y("sma20:Q", scale=price_scale),
                        )
                        chart = chart + sma20_line

                    if "atr14" in chart_df.columns and chart_df["atr14"].notna().any():
                        atr_df = chart_df.dropna(subset=["atr14"]).copy()
                        atr_chart = alt.Chart(atr_df).mark_line(color="#9c27b0", strokeWidth=2).encode(
                            x=alt.X("date:T", title="Time (UTC)", scale=x_scale_utc),
                            y=alt.Y("atr14:Q", title="ATR14", scale=alt.Scale(zero=False)),
                        )
                        st.altair_chart(
                            alt.vconcat(
                                chart.properties(height=300),
                                atr_chart.properties(height=120),
                            ).resolve_scale(x="shared"),
                            use_container_width=True,
                        )
                    else:
                        st.altair_chart(chart.properties(height=380), use_container_width=True)
                else:
                    st.info("Bars returned, but date/price values are not chartable.")

    st.divider()

    # ── Detect Swings ─────────────────────────────────────────────────
    st.subheader("Detect Swings")

    with st.form("detect_swings_form"):
        sw_cols = st.columns(5)
        with sw_cols[0]:
            sw_symbol = st.text_input("Symbol", placeholder="e.g. AAPL or EURUSD", key="sw_symbol")
        with sw_cols[1]:
            sw_provider = st.selectbox(
                "Provider",
                PROVIDERS,
                index=PROVIDERS.index(selected_provider) if selected_provider in PROVIDERS else 0,
                key="sw_provider",
            )
        with sw_cols[2]:
            sw_timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=0, key="sw_tf")
        with sw_cols[3]:
            sw_sec_type = st.selectbox("Security Type", SEC_TYPES, index=0, key="sw_sec")
        with sw_cols[4]:
            sw_lookback = st.number_input("Lookback", min_value=1, max_value=10, value=2, step=1, key="sw_lb")

        sw_submitted = st.form_submit_button("Detect Swings", use_container_width=True)
        if sw_submitted:
            if not sw_symbol or not sw_symbol.strip():
                st.error("Symbol is required.")
            else:
                try:
                    swing_data = api_client.detect_swings(
                        symbol=sw_symbol,
                        provider=sw_provider,
                        timeframe=sw_timeframe,
                        sec_type=sw_sec_type,
                        lookback=int(sw_lookback),
                    )
                    st.session_state["swing_result"] = swing_data
                    try:
                        chart_bars = int(swing_data.get("total_bars", 20))
                        chart_bars = max(1, min(200, chart_bars))
                        swing_bars_data = api_client.get_test_bars(
                            symbol=sw_symbol,
                            provider=sw_provider,
                            timeframe=sw_timeframe,
                            sec_type=sw_sec_type,
                            num_bars=chart_bars,
                        )
                        st.session_state["swing_bars_result"] = swing_bars_data
                    except APIError as e:
                        st.warning(f"Swings detected, but bars could not be fetched for chart: {e.detail}")
                except APIError as e:
                    st.error(f"Detect swings failed: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    if "swing_result" in st.session_state:
        data = st.session_state["swing_result"]
        with st.container(border=True):
            st.markdown(
                f"**{data.get('symbol', '')}** — {data.get('timeframe', '')} "
                f"— Lookback: {data.get('lookback', '')} — Total bars: {data.get('total_bars', '')}"
            )
            st.caption(f"Enough swings: {data.get('enough_swings', False)} | Message: {data.get('message', '')}")

            swings = [
                s
                for s in [
                    data.get("previous_last_high_swing"),
                    data.get("last_high_swing"),
                    data.get("previous_last_low_swing"),
                    data.get("last_low_swing"),
                ]
                if s is not None
            ]
            if not swings:
                st.info("No swing points detected.")
            else:
                high_swings = [s for s in swings if s["type"] == "HIGH"]
                low_swings = [s for s in swings if s["type"] == "LOW"]

                summary_cols = st.columns(2)
                with summary_cols[0]:
                    st.metric("Swing Highs", len(high_swings))
                with summary_cols[1]:
                    st.metric("Swing Lows", len(low_swings))

                for swing in swings:
                    swing_icon = "🔺" if swing["type"] == "HIGH" else "🔻"
                    st.markdown(
                        f"{swing_icon} **{swing['type']}** at bar `{swing['bar_index']}` — "
                        f"Price: **{swing['price']}**"
                    )

            bars_result = st.session_state.get("swing_bars_result")
            bars = bars_result.get("bars", []) if isinstance(bars_result, dict) else []

            if bars:
                import pandas as pd
                import altair as alt

                bars_df = pd.DataFrame([{"bar_index": idx, **bar} for idx, bar in enumerate(bars)])
                if {"date", "open", "high", "low", "close", "bar_index"}.issubset(bars_df.columns):
                    for col in ["open", "high", "low", "close", "sma9", "sma20"]:
                        if col in bars_df.columns:
                            bars_df[col] = pd.to_numeric(bars_df[col], errors="coerce")
                    bars_df["date"] = pd.to_datetime(bars_df["date"], errors="coerce")
                    chart_df = bars_df.dropna(subset=["date", "open", "high", "low", "close"]).copy()

                    if not chart_df.empty:
                        chart_df["candle_low"] = chart_df[["open", "close"]].min(axis=1)
                        chart_df["candle_high"] = chart_df[["open", "close"]].max(axis=1)
                        chart_df["candle_color"] = chart_df.apply(
                            lambda row: "#2ca02c" if row["close"] >= row["open"] else "#d62728", axis=1
                        )

                        price_scale = alt.Scale(zero=False)
                        x_scale_utc = alt.Scale(type="utc")

                        wick = alt.Chart(chart_df).mark_rule().encode(
                            x=alt.X("date:T", title="Time (UTC)", scale=x_scale_utc),
                            y=alt.Y("low:Q", title="Price", scale=price_scale),
                            y2="high:Q",
                            color=alt.value("#9aa0a6"),
                        )

                        candle = alt.Chart(chart_df).mark_bar(size=8).encode(
                            x=alt.X("date:T", scale=x_scale_utc),
                            y=alt.Y("candle_low:Q", scale=price_scale),
                            y2="candle_high:Q",
                            color=alt.Color("candle_color:N", scale=None, legend=None),
                        )

                        chart = wick + candle

                        if "sma9" in chart_df.columns and chart_df["sma9"].notna().any():
                            chart = chart + alt.Chart(chart_df).mark_line(color="#1f77b4", strokeWidth=2).encode(
                                x=alt.X("date:T", scale=x_scale_utc),
                                y=alt.Y("sma9:Q", scale=price_scale),
                            )
                        if "sma20" in chart_df.columns and chart_df["sma20"].notna().any():
                            chart = chart + alt.Chart(chart_df).mark_line(color="#ff7f0e", strokeWidth=2).encode(
                                x=alt.X("date:T", scale=x_scale_utc),
                                y=alt.Y("sma20:Q", scale=price_scale),
                            )

                        swings_df = pd.DataFrame(swings)
                        if {"bar_index", "type", "price"}.issubset(swings_df.columns):
                            swings_df["bar_index"] = pd.to_numeric(swings_df["bar_index"], errors="coerce")
                            swings_df["price"] = pd.to_numeric(swings_df["price"], errors="coerce")
                            swings_df = swings_df.dropna(subset=["bar_index", "price"]).copy()
                            swings_df["bar_index"] = swings_df["bar_index"].astype(int)
                            marker_df = swings_df.merge(chart_df[["bar_index", "date"]], on="bar_index", how="left")
                            marker_df = marker_df.dropna(subset=["date", "price"])

                            if not marker_df.empty:
                                markers = alt.Chart(marker_df).mark_point(
                                    filled=True,
                                    size=320,
                                    stroke="black",
                                    strokeWidth=1.8,
                                    opacity=0.95,
                                ).encode(
                                    x=alt.X("date:T", scale=x_scale_utc),
                                    y=alt.Y("price:Q", scale=price_scale),
                                    color=alt.Color(
                                        "type:N",
                                        scale=alt.Scale(domain=["HIGH", "LOW"], range=["#ff0033", "#00b4ff"]),
                                        legend=alt.Legend(title="Swing Type"),
                                    ),
                                    shape=alt.Shape(
                                        "type:N",
                                        scale=alt.Scale(domain=["HIGH", "LOW"], range=["triangle-up", "triangle-down"]),
                                        legend=None,
                                    ),
                                    tooltip=["type:N", "bar_index:Q", "price:Q", "date:T"],
                                )
                                chart = chart + markers

                        st.caption(
                            "Legend: Green = Up candle | Red = Down candle | Blue = SMA9 | Orange = SMA20 | Markers = Swings"
                        )
                        st.altair_chart(chart.properties(height=380), use_container_width=True)

    st.divider()

    # ── Calculate Candidate Bias ──────────────────────────────────────
    st.subheader("Calculate Candidate Bias")

    with st.form("calculate_candidate_bias_form"):
        cb_cols = st.columns(7)
        with cb_cols[0]:
            cb_symbol = st.text_input("Symbol", placeholder="e.g. AAPL or EURUSD", key="cb_symbol")
        with cb_cols[1]:
            cb_provider = st.selectbox(
                "Provider",
                PROVIDERS,
                index=PROVIDERS.index(selected_provider) if selected_provider in PROVIDERS else 0,
                key="cb_provider",
            )
        with cb_cols[2]:
            cb_timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=0, key="cb_tf")
        with cb_cols[3]:
            cb_sec_type = st.selectbox("Security Type", SEC_TYPES, index=0, key="cb_sec")
        with cb_cols[4]:
            cb_lookback = st.number_input("Lookback", min_value=1, max_value=10, value=2, step=1, key="cb_lb")
        with cb_cols[5]:
            cb_pw = st.number_input(
                "Persistence Window", min_value=5, max_value=200, value=20, step=1, key="cb_pw"
            )
        with cb_cols[6]:
            cb_pt = st.number_input(
                "Persistence Threshold", min_value=1, max_value=200, value=15, step=1, key="cb_pt"
            )

        cb_submitted = st.form_submit_button("Calculate Candidate Bias", use_container_width=True)
        if cb_submitted:
            if not cb_symbol or not cb_symbol.strip():
                st.error("Symbol is required.")
            else:
                try:
                    cb_result = api_client.calculate_candidate_bias(
                        symbol=cb_symbol,
                        provider=cb_provider,
                        timeframe=cb_timeframe,
                        sec_type=cb_sec_type,
                        lookback=int(cb_lookback),
                        persistence_window=int(cb_pw),
                        persistence_threshold=int(cb_pt),
                    )
                    st.session_state["candidate_bias_result"] = cb_result
                except APIError as e:
                    st.error(f"Calculate candidate bias failed: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    if "candidate_bias_result" in st.session_state:
        cb_data = st.session_state["candidate_bias_result"]
        with st.container(border=True):
            st.markdown(
                f"**{cb_data.get('symbol', '')}** — {cb_data.get('timeframe', '')} "
                f"— Lookback: {cb_data.get('lookback', '')} — Total bars: {cb_data.get('total_bars', '')}"
            )
            st.caption(
                f"Can calculate bias: {cb_data.get('can_calculate_bias', False)}"
                + (f" | Reason: {cb_data.get('reason')}" if cb_data.get("reason") else "")
            )

            bias_cols = st.columns(4)
            with bias_cols[0]:
                st.markdown(
                    f"**MA Bar Bias**<br>{_bias_colored_html(cb_data.get('ma_bar_bias', 'NEUTRAL'))}",
                    unsafe_allow_html=True,
                )
            with bias_cols[1]:
                st.markdown(
                    f"**MA Persistent Bias**<br>{_bias_colored_html(cb_data.get('ma_persistent_bias', 'NEUTRAL'))}",
                    unsafe_allow_html=True,
                )
            with bias_cols[2]:
                st.markdown(
                    f"**Structure Bias**<br>{_bias_colored_html(cb_data.get('structure_bias', 'NEUTRAL'))}",
                    unsafe_allow_html=True,
                )
            with bias_cols[3]:
                st.markdown(
                    f"**Candidate Bias**<br>{_bias_colored_html(cb_data.get('candidate_bias', 'NEUTRAL'))}",
                    unsafe_allow_html=True,
                )

            count_cols = st.columns(2)
            with count_cols[0]:
                st.metric("Bull Count", cb_data.get("bull_count", 0))
            with count_cols[1]:
                st.metric("Bear Count", cb_data.get("bear_count", 0))

            bars = cb_data.get("bars", [])
            swings = cb_data.get("swings", [])

            if bars:
                import pandas as pd
                import altair as alt

                bars_df = pd.DataFrame([{"bar_index": idx, **bar} for idx, bar in enumerate(bars)])
                display_cols = [
                    c
                    for c in ["bar_index", "date", "open", "high", "low", "close", "sma9", "sma20"]
                    if c in bars_df.columns
                ]
                st.dataframe(bars_df, column_order=display_cols, use_container_width=True, hide_index=True)

                if {"date", "open", "high", "low", "close", "bar_index"}.issubset(bars_df.columns):
                    for col in ["open", "high", "low", "close", "sma9", "sma20"]:
                        if col in bars_df.columns:
                            bars_df[col] = pd.to_numeric(bars_df[col], errors="coerce")
                    bars_df["date"] = pd.to_datetime(bars_df["date"], errors="coerce")
                    chart_df = bars_df.dropna(subset=["date", "open", "high", "low", "close"]).copy()

                    if not chart_df.empty:
                        chart_df["candle_low"] = chart_df[["open", "close"]].min(axis=1)
                        chart_df["candle_high"] = chart_df[["open", "close"]].max(axis=1)
                        chart_df["candle_color"] = chart_df.apply(
                            lambda row: "#2ca02c" if row["close"] >= row["open"] else "#d62728", axis=1
                        )

                        price_scale = alt.Scale(zero=False)
                        x_scale_utc = alt.Scale(type="utc")

                        wick = alt.Chart(chart_df).mark_rule().encode(
                            x=alt.X("date:T", title="Time (UTC)", scale=x_scale_utc),
                            y=alt.Y("low:Q", title="Price", scale=price_scale),
                            y2="high:Q",
                            color=alt.value("#9aa0a6"),
                        )

                        candle = alt.Chart(chart_df).mark_bar(size=8).encode(
                            x=alt.X("date:T", scale=x_scale_utc),
                            y=alt.Y("candle_low:Q", scale=price_scale),
                            y2="candle_high:Q",
                            color=alt.Color("candle_color:N", scale=None, legend=None),
                        )

                        chart = wick + candle

                        if "sma9" in chart_df.columns and chart_df["sma9"].notna().any():
                            chart = chart + alt.Chart(chart_df).mark_line(color="#1f77b4", strokeWidth=2).encode(
                                x=alt.X("date:T", scale=x_scale_utc),
                                y=alt.Y("sma9:Q", scale=price_scale),
                            )
                        if "sma20" in chart_df.columns and chart_df["sma20"].notna().any():
                            chart = chart + alt.Chart(chart_df).mark_line(color="#ff7f0e", strokeWidth=2).encode(
                                x=alt.X("date:T", scale=x_scale_utc),
                                y=alt.Y("sma20:Q", scale=price_scale),
                            )

                        swings_df = pd.DataFrame(swings)
                        if {"bar_index", "type", "price"}.issubset(swings_df.columns):
                            swings_df["bar_index"] = pd.to_numeric(swings_df["bar_index"], errors="coerce")
                            swings_df["price"] = pd.to_numeric(swings_df["price"], errors="coerce")
                            swings_df = swings_df.dropna(subset=["bar_index", "price"]).copy()
                            swings_df["bar_index"] = swings_df["bar_index"].astype(int)
                            marker_df = swings_df.merge(chart_df[["bar_index", "date"]], on="bar_index", how="left")
                            marker_df = marker_df.dropna(subset=["date", "price"])

                            if not marker_df.empty:
                                markers = alt.Chart(marker_df).mark_point(
                                    filled=True,
                                    size=320,
                                    stroke="black",
                                    strokeWidth=1.8,
                                    opacity=0.95,
                                ).encode(
                                    x=alt.X("date:T", scale=x_scale_utc),
                                    y=alt.Y("price:Q", scale=price_scale),
                                    color=alt.Color(
                                        "type:N",
                                        scale=alt.Scale(domain=["HIGH", "LOW"], range=["#ff0033", "#00b4ff"]),
                                        legend=alt.Legend(title="Swing Type"),
                                    ),
                                    shape=alt.Shape(
                                        "type:N",
                                        scale=alt.Scale(domain=["HIGH", "LOW"], range=["triangle-up", "triangle-down"]),
                                        legend=None,
                                    ),
                                    tooltip=["type:N", "bar_index:Q", "price:Q", "date:T"],
                                )
                                chart = chart + markers

                        st.caption(
                            "Legend: Green = Up candle | Red = Down candle | Blue = SMA9 | Orange = SMA20 | Markers = Swings"
                        )
                        st.altair_chart(chart.properties(height=420), use_container_width=True)

            with st.expander("View raw response"):
                st.json(cb_data)


def _knob_html(initial_value: int) -> str:
    return f"""
    <style>
        .knob-container {{ text-align: center; padding: 10px; }}
        .knob-dial {{
            width: 90px; height: 90px; margin: 0 auto 8px;
            border-radius: 50%;
            background: linear-gradient(145deg, #2a2d35 0%, #1a1d24 50%, #252830 100%);
            border: 3px solid #3b3f47;
            box-shadow: inset 0 2px 6px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3);
            position: relative; cursor: grab; user-select: none;
        }}
        .knob-dial:active {{ cursor: grabbing; }}
        .knob-pointer {{
            width: 4px; height: 32px;
            background: linear-gradient(180deg, #f0ad4e 0%, #d4892a 100%);
            border-radius: 2px; position: absolute;
            top: 6px; left: 50%;
            transform-origin: 50% 39px;
            transform: translateX(-50%) rotate(var(--angle, -135deg));
            box-shadow: 0 0 6px rgba(240, 173, 78, 0.5);
        }}
        .knob-value {{ font-size: 1.2rem; font-weight: 800; color: #f0c048; letter-spacing: 0.05em; }}
    </style>
    <div class="knob-container">
        <div class="tcp-knob-panel-label" style="font-size:0.7rem;color:#888;margin-bottom:6px;">SESSION ID</div>
        <div class="knob-dial" id="knob" role="slider" aria-valuemin="1" aria-valuemax="10" tabindex="0">
            <div class="knob-pointer" id="pointer"></div>
        </div>
        <div class="knob-value" id="value">{initial_value}</div>
        <form id="knob-form" method="GET" target="_top" style="display:none;">
            <input type="hidden" name="tcp_knob" id="knob-input" value="{initial_value}" />
        </form>
    </div>
    <script>
        (function() {{
            const minVal = 1, maxVal = 10;
            const startAngle = -135, endAngle = 135;
            const angleRange = endAngle - startAngle;

            function angleToValue(angle) {{
                const pct = (angle - startAngle) / angleRange;
                return Math.round(minVal + pct * (maxVal - minVal));
            }}
            function valueToAngle(val) {{
                const pct = (val - minVal) / (maxVal - minVal);
                return startAngle + pct * angleRange;
            }}

            const knob = document.getElementById('knob');
            const pointer = document.getElementById('pointer');
            const valueEl = document.getElementById('value');
            const knobForm = document.getElementById('knob-form');
            const knobInput = document.getElementById('knob-input');
            let value = Math.max(minVal, Math.min(maxVal, {initial_value}));
            let isDragging = false;

            function updateDisplay() {{
                value = Math.max(minVal, Math.min(maxVal, value));
                const angle = valueToAngle(value);
                pointer.style.setProperty('--angle', angle + 'deg');
                pointer.style.transform = 'translateX(-50%) rotate(' + angle + 'deg)';
                valueEl.textContent = value;
            }}

            function setFromEvent(e) {{
                const rect = knob.getBoundingClientRect();
                const cx = rect.left + rect.width / 2;
                const cy = rect.top + rect.height / 2;
                const ex = e.clientX !== undefined ? e.clientX : e.touches[0].clientX;
                const ey = e.clientY !== undefined ? e.clientY : e.touches[0].clientY;
                const dx = ex - cx, dy = ey - cy;
                let angle = Math.atan2(dx, -dy) * 180 / Math.PI;
                angle = Math.max(startAngle, Math.min(endAngle, angle));
                value = angleToValue(angle);
                updateDisplay();
            }}

            function applyValue() {{
                const targetWindow = window.top || window.parent || window;
                const url = new URL(targetWindow.location.href);
                url.searchParams.set('tcp_knob', value);
                const nextUrl = url.toString();
                // Streamlit renders components in an iframe; form submit is often the most reliable.
                try {{
                    knobInput.value = String(value);
                    // Submit a single tcp_knob value (avoid duplicates from existing query).
                    knobForm.action = url.pathname;
                    knobForm.submit();
                    return;
                }} catch (err) {{}}
                try {{
                    window.open(nextUrl, "_top");
                    return;
                }} catch (err) {{}}
                try {{
                    targetWindow.location.assign(nextUrl);
                    return;
                }} catch (err) {{}}
                try {{
                    targetWindow.location.replace(nextUrl);
                }} catch (err) {{}}
            }}

            knob.addEventListener('pointerdown', function(e) {{
                e.preventDefault();
                isDragging = true;
                if (knob.setPointerCapture) knob.setPointerCapture(e.pointerId);
                setFromEvent(e);
            }});
            knob.addEventListener('pointermove', function(e) {{
                if (isDragging) setFromEvent(e);
            }});
            knob.addEventListener('pointerup', function(e) {{
                if (isDragging) {{
                    isDragging = false;
                    if (knob.releasePointerCapture) knob.releasePointerCapture(e.pointerId);
                    applyValue();
                }}
            }});
            knob.addEventListener('pointercancel', function(e) {{
                if (isDragging) {{
                    isDragging = false;
                    if (knob.releasePointerCapture) knob.releasePointerCapture(e.pointerId);
                    applyValue();
                }}
            }});

            knob.addEventListener('keydown', function(e) {{
                if (e.key === 'ArrowUp' || e.key === 'Right') {{ value = Math.min(maxVal, value + 1); updateDisplay(); applyValue(); }}
                else if (e.key === 'ArrowDown' || e.key === 'Left') {{ value = Math.max(minVal, value - 1); updateDisplay(); applyValue(); }}
            }});

            updateDisplay();
        }})();
    </script>
    """


@st.dialog("Trading Rules", width="large")
def _show_trading_rules_dialog():
    import html
    try:
        info = api_client.get_trading_info()
    except Exception:
        info = {}
    rules = info.get("trading_rules")
    if rules is None:
        rules = "No trading rules available."
    if isinstance(rules, str):
        normalized = rules.replace("\r\n", "\n").replace("\r", "\n")
        escaped = html.escape(normalized)
        with_breaks = escaped.replace("\n", "<br>")
        st.markdown(
            f'<div class="info-rich-text" style="max-height:360px; overflow-y:auto;">{with_breaks}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.write(rules)
    if st.button("Close", key="tcp_rules_dialog_close"):
        st.rerun()


@st.dialog("AI Guardian Angel", width="large")
def _show_guardian_angel_dialog():
    st.markdown("### AI Guardian Angel")
    g1, g2, g3 = st.columns(3)
    with g1:
        ga_symbol = st.text_input(
            "symbol",
            value=str(st.session_state.get("ga_symbol", "BTCUSD")),
            key="ga_symbol_ui",
        )
    with g2:
        ga_timeframe = st.text_input(
            "timeframe",
            value=str(st.session_state.get("ga_timeframe", "15m")),
            key="ga_timeframe_ui",
        )
    with g3:
        ga_provider = st.text_input(
            "provider",
            value=str(st.session_state.get("ga_provider", "BYBIT")),
            key="ga_provider_ui",
        )

    g4, g5 = st.columns(2)
    with g4:
        ga_sec_type = st.text_input(
            "sec_type",
            value=str(st.session_state.get("ga_sec_type", "SPOT")),
            key="ga_sec_type_ui",
        )
    with g5:
        ga_num_bars = st.number_input(
            "num_bars",
            min_value=1,
            max_value=200,
            value=int(st.session_state.get("ga_num_bars", 50)),
            step=1,
            key="ga_num_bars_ui",
        )

    ga_news_raw = st.text_area(
        "News",
        value=str(st.session_state.get("ga_news_raw", "")),
        key="ga_news_raw_ui",
        height=120,
        placeholder="One news snippet per line (or paragraph).",
    )

    st.session_state["ga_symbol"] = ga_symbol
    st.session_state["ga_timeframe"] = ga_timeframe
    st.session_state["ga_provider"] = ga_provider
    st.session_state["ga_sec_type"] = ga_sec_type
    st.session_state["ga_num_bars"] = int(ga_num_bars)
    st.session_state["ga_news_raw"] = ga_news_raw

    if st.button("Guard Me", key="ga_guard_me_btn", use_container_width=True):
        if not str(ga_symbol).strip():
            st.warning("Please enter symbol.")
        elif not str(ga_timeframe).strip():
            st.warning("Please enter timeframe.")
        else:
            try:
                test_bars_resp = api_client.get_test_bars(
                    symbol=str(ga_symbol),
                    provider=str(ga_provider),
                    timeframe=str(ga_timeframe),
                    sec_type=str(ga_sec_type),
                    num_bars=int(ga_num_bars),
                )

                bars_raw = []
                if isinstance(test_bars_resp, dict):
                    if isinstance(test_bars_resp.get("bars"), list):
                        bars_raw = test_bars_resp.get("bars", [])
                    else:
                        bars_raw = [test_bars_resp]
                elif isinstance(test_bars_resp, list):
                    bars_raw = test_bars_resp

                bars_payload = []
                for b in bars_raw:
                    if not isinstance(b, dict):
                        continue
                    bars_payload.append(
                        {
                            "date": b.get("date"),
                            "open": b.get("open"),
                            "high": b.get("high"),
                            "low": b.get("low"),
                            "close": b.get("close"),
                        }
                    )

                signal_bar_time = None
                if bars_payload and isinstance(bars_payload[-1], dict):
                    signal_bar_time = bars_payload[-1].get("date")

                news_snippets = [
                    line.strip()
                    for line in str(ga_news_raw).splitlines()
                    if line and line.strip()
                ]

                assessment_resp = api_client.create_trend_assessment(
                    symbol=str(ga_symbol),
                    timeframe=str(ga_timeframe),
                    session_id=int(st.session_state.get("ga_session_id", 0) or 0) or None,
                    signal_bar_time=signal_bar_time,
                    news_snippets=news_snippets if news_snippets else None,
                    bars=bars_payload,
                )
                st.session_state["ga_test_bars_result"] = test_bars_resp
                st.session_state["ga_trend_assessment_result"] = assessment_resp
                st.session_state.pop("ga_error", None)
            except APIError as e:
                st.session_state["ga_error"] = f"Guardian Angel call failed: {e.detail}"
            except Exception as e:
                st.session_state["ga_error"] = f"Connection error: {e}"

    if st.session_state.get("ga_error"):
        st.error(st.session_state["ga_error"])

    ga_result = st.session_state.get("ga_trend_assessment_result")
    if isinstance(ga_result, dict):
        st.markdown("**LLM Trend Assessment**")
        llm_part = ga_result.get("llm_trend_assessment")
        if isinstance(llm_part, dict):
            st.json(llm_part)
        else:
            st.json(ga_result)


def trading_control_panel_page():
    # Knob-selected session id is the single source of truth.
    if "tcp_session_knob" not in st.session_state:
        st.session_state["tcp_session_knob"] = 1

    backend_ok = False
    try:
        api_client.health_check()
        backend_ok = True
    except Exception:
        pass

    led_class = "tcp-led-online" if backend_ok else "tcp-led-offline"
    status_class = "tcp-status-online" if backend_ok else "tcp-status-offline"
    status_text = "SYSTEM ONLINE" if backend_ok else "SYSTEM OFFLINE"

    st.markdown(
        f"""
        <div class="tcp-top-bar">
            <div style="width: 140px;"></div>
            <div class="tcp-title">TRADING CONTROL PANEL</div>
            <div class="tcp-status">
                <span class="tcp-led {led_class}"></span>
                <span class="tcp-status-text {status_class}">{status_text}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    knob_val = max(1, min(10, int(st.session_state.get("tcp_session_knob", 1))))
    st.session_state["tcp_session_knob"] = knob_val
    session_id_tcp = knob_val
    knob_changed = int(st.session_state.get("tcp_current_session_id") or 0) != int(session_id_tcp)
    if knob_changed:
        st.session_state["tcp_current_session_id"] = session_id_tcp
        st.session_state.pop("tcp_error", None)
        st.session_state.pop("tcp_last_fetch_ts", None)
        # Do NOT clear tcp_panel_result here - keep showing previous data until new fetch succeeds.
    auto_on = st.session_state.get("tcp_auto_refresh_enabled", False)
    tcp_cfg = st.session_state.get("tcp_auto_refresh_cfg")
    if not isinstance(tcp_cfg, dict) or tcp_cfg.get("session_id") != int(session_id_tcp):
        st.session_state["tcp_auto_refresh_cfg"] = {
            "session_id": int(session_id_tcp),
            "timeframe": "1m",
            "interval_seconds": _refresh_seconds_for_timeframe("1m"),
        }

    tcp_cfg = st.session_state.get("tcp_auto_refresh_cfg") or {}
    tcp_tf = str(tcp_cfg.get("timeframe", "1m"))
    tcp_interval_seconds = int(tcp_cfg.get("interval_seconds", _refresh_seconds_for_timeframe(tcp_tf)))
    tcp_last_fetch_ts = float(st.session_state.get("tcp_last_fetch_ts", 0.0))
    tcp_elapsed = max(0.0, time.time() - tcp_last_fetch_ts)
    tcp_remaining = max(0, int(tcp_interval_seconds - tcp_elapsed))

    status_col, refresh_col = st.columns([20, 1])
    with refresh_col:
        if st.button("↻", key="tcp_refresh_now_btn", help="Refresh all trading panels now"):
            st.session_state["tcp_force_refresh"] = True
            st.rerun()

    with status_col:
        _tcp_auto_refresh_fragment()
    force_refresh = bool(st.session_state.pop("tcp_force_refresh", False))
    panel_data = st.session_state.get("tcp_panel_result")
    panel_session_id = None
    if isinstance(panel_data, dict):
        panel_session_id = panel_data.get("session_id")
        if panel_session_id is None and isinstance(panel_data.get("session"), dict):
            panel_session_id = panel_data.get("session", {}).get("id")
    try:
        panel_session_id = int(panel_session_id) if panel_session_id is not None else None
    except (TypeError, ValueError):
        panel_session_id = None
    need_fetch = force_refresh or knob_changed or (not panel_data) or (panel_session_id != int(session_id_tcp))
    if need_fetch:
        try:
            # Validate the selected session id first, then load TCP payload
            session_detail = api_client.get_session(int(session_id_tcp))
            st.session_state["tcp_session_detail"] = session_detail if isinstance(session_detail, dict) else {}
            panel = api_client.get_trading_control_panel(int(session_id_tcp))
            panel_sid = panel.get("session_id") if panel else None
            try:
                panel_sid = int(panel_sid) if panel_sid is not None else None
            except (TypeError, ValueError):
                panel_sid = None
            if panel and panel_sid is not None and panel_sid == int(session_id_tcp):
                st.session_state["tcp_panel_result"] = panel
                st.session_state["tcp_last_fetch_ts"] = time.time()
                tf = panel.get("session", {}).get("timeframe", "1m")
                st.session_state["tcp_auto_refresh_cfg"] = {
                    "session_id": int(session_id_tcp),
                    "timeframe": tf,
                    "interval_seconds": _refresh_seconds_for_timeframe(tf),
                }
                st.session_state.pop("tcp_error", None)
                panel_data = panel
            else:
                st.session_state["tcp_error"] = f"No such session exists with id {session_id_tcp}"
                st.session_state.pop("tcp_panel_result", None)
        except APIError:
            st.session_state["tcp_error"] = f"No such session exists with id {session_id_tcp}"
            st.session_state.pop("tcp_panel_result", None)
            st.session_state.pop("tcp_session_detail", None)
        except Exception:
            st.session_state["tcp_error"] = f"No such session exists with id {session_id_tcp}"
            st.session_state.pop("tcp_panel_result", None)
            st.session_state.pop("tcp_session_detail", None)

    if st.session_state.get("tcp_error"):
        st.error(st.session_state["tcp_error"])

    panel_data = st.session_state.get("tcp_panel_result")

    # Minimal trend chart data for TCP (50 bars + up to 4 latest swing points).
    tcp_viz_data = st.session_state.get("tcp_viz_result")
    tcp_viz_session_id = None
    if isinstance(tcp_viz_data, dict):
        tcp_viz_session_id = (tcp_viz_data.get("session") or {}).get("id")
    try:
        tcp_viz_session_id = int(tcp_viz_session_id) if tcp_viz_session_id is not None else None
    except (TypeError, ValueError):
        tcp_viz_session_id = None

    need_viz_fetch = force_refresh or knob_changed or (not isinstance(tcp_viz_data, dict)) or (
        tcp_viz_session_id != int(session_id_tcp)
    )
    if need_viz_fetch:
        try:
            viz = api_client.visualize_session(int(session_id_tcp), 50)
            if isinstance(viz, dict):
                st.session_state["tcp_viz_result"] = viz
                st.session_state.pop("tcp_viz_error", None)
                tcp_viz_data = viz
        except Exception:
            st.session_state["tcp_viz_error"] = f"Could not load chart data for session {session_id_tcp}"

    last_bias_ts = None
    if isinstance(panel_data, dict):
        # Try common locations/keys for the bias calculation object.
        bias_objs_to_check = []
        bias_objs_to_check.extend(
            [
                panel_data.get("bias_calculation"),
                panel_data.get("latest_bias_calculation"),
                panel_data.get("latest_bias"),
            ]
        )
        session_obj = panel_data.get("session") if isinstance(panel_data.get("session"), dict) else {}
        bias_objs_to_check.extend(
            [
                session_obj.get("bias_calculation"),
                session_obj.get("latest_bias_calculation"),
                session_obj.get("latest_bias"),
            ]
        )

        bias_obj = next((b for b in bias_objs_to_check if isinstance(b, dict)), None)
        if isinstance(bias_obj, dict):
            for ts_key in (
                "calculated_at",
                "updated_at",
                "created_at",
                "timestamp",
                "last_updated_at",
            ):
                if bias_obj.get(ts_key):
                    last_bias_ts = bias_obj.get(ts_key)
                    break
        else:
            # If the bias field itself is a timestamp-like scalar.
            scalar_obj = next(
                (b for b in bias_objs_to_check if b is not None and not isinstance(b, (dict, list))),
                None,
            )
            if scalar_obj is not None:
                last_bias_ts = scalar_obj

    with status_col:
        st.caption(f"Last data for session: {_fmt_dt(last_bias_ts)}")

    with st.container(border=True):
        tcp_viz = st.session_state.get("tcp_viz_result")
        bars = tcp_viz.get("bars", []) if isinstance(tcp_viz, dict) else []
        if bars:
            import pandas as pd
            import altair as alt

            bars_df = pd.DataFrame([{"bar_index": idx, **bar} for idx, bar in enumerate(bars)])
            if "close" in bars_df.columns:
                bars_df["close"] = pd.to_numeric(bars_df["close"], errors="coerce")
            bars_df["date"] = pd.to_datetime(bars_df.get("date"), errors="coerce", utc=True)
            chart_df = bars_df.dropna(subset=["date", "close"]).copy()

            if chart_df.empty:
                st.caption("No chart bars available.")
            else:
                base = alt.Chart(chart_df).encode(
                    x=alt.X("date:T", title="Time (UTC)", scale=alt.Scale(type="utc")),
                    y=alt.Y("close:Q", title="Price", scale=alt.Scale(zero=False)),
                )
                line = base.mark_line(color="#5aa0ff", strokeWidth=1.8)

                swings = []
                for key in ["previous_high_swing", "latest_high_swing", "previous_low_swing", "latest_low_swing"]:
                    sp = tcp_viz.get(key) if isinstance(tcp_viz, dict) else None
                    if isinstance(sp, dict):
                        swings.append(sp)

                marker_layer = None
                if swings:
                    swings_df = pd.DataFrame(swings)
                    if {"bar_index", "price", "type"}.issubset(swings_df.columns):
                        swings_df["bar_index"] = pd.to_numeric(swings_df["bar_index"], errors="coerce").astype("Int64")
                        swings_df["price"] = pd.to_numeric(swings_df["price"], errors="coerce")
                        swings_df = swings_df.dropna(subset=["bar_index", "price"])
                        swings_df = swings_df.sort_values("bar_index").tail(4)
                        marker_df = swings_df.merge(chart_df[["bar_index", "date"]], on="bar_index", how="left")
                        marker_df = marker_df.dropna(subset=["date", "price"])
                        if not marker_df.empty:
                            marker_layer = alt.Chart(marker_df).mark_point(
                                filled=True, size=90, strokeWidth=1.2, stroke="black"
                            ).encode(
                                x=alt.X("date:T", scale=alt.Scale(type="utc")),
                                y=alt.Y("price:Q", scale=alt.Scale(zero=False)),
                                color=alt.Color(
                                    "type:N",
                                    scale=alt.Scale(domain=["HIGH", "LOW"], range=["#22c55e", "#ef4444"]),
                                    legend=None,
                                ),
                            )

                chart = line if marker_layer is None else (line + marker_layer)
                st.altair_chart(chart.properties(height=170), use_container_width=True)
        else:
            st.caption("No chart bars available.")

    sess_status = str((panel_data or {}).get("session_status") or "—").upper()
    state_bias = (panel_data or {}).get("state_bias") or "NEUTRAL"
    state_bias = str(state_bias).upper()
    lv = (panel_data or {}).get("latest_volatility_calculation") or {}
    latest_alert = (panel_data or {}).get("latest_alert")
    latest_pb = (panel_data or {}).get("latest_pullback_calculation") or {}
    trend_strength = (panel_data or {}).get("trend_strenght") or {}
    session_data_tcp = st.session_state.get("tcp_session_detail", {}) or {}
    alert_freeze_raw = session_data_tcp.get("alert_freeze")
    if alert_freeze_raw is None:
        alert_freeze_raw = (panel_data or {}).get("alert_freeze")
    if alert_freeze_raw is None:
        alert_freeze_raw = ((panel_data or {}).get("session") or {}).get("alert_freeze")

    if isinstance(alert_freeze_raw, bool):
        alert_freeze_on = alert_freeze_raw
    elif isinstance(alert_freeze_raw, (int, float)):
        alert_freeze_on = bool(alert_freeze_raw)
    elif isinstance(alert_freeze_raw, str):
        alert_freeze_on = alert_freeze_raw.strip().lower() in ("true", "1", "yes", "on")
    else:
        alert_freeze_on = False
    vol_status = (lv.get("volatility_status") or "NORMAL").upper()
    vr = lv.get("vol_ratio")
    try:
        vol_ratio = f"{float(vr):.2f}" if vr is not None else "—"
    except (TypeError, ValueError):
        vol_ratio = "—"

    alert_text = "NO ALERT" if not latest_alert or latest_alert.get("outcome_status") != "OPEN" else f"{latest_alert.get('direction', '—')} @ {latest_alert.get('entry_signal_price', '—')}"
    alert_color = "#f0c048"  # amber: no alert
    if latest_alert and latest_alert.get("outcome_status") == "OPEN":
        direction = str(latest_alert.get("direction", "")).upper()
        alert_color = "#22c55e" if direction == "LONG" else "#ef4444" if direction == "SHORT" else "#f0c048"

    alert_risky_html = ""
    if latest_alert and latest_alert.get("outcome_status") == "OPEN":
        risky_flag = _tcp_alert_risky_bool(latest_alert)
        if risky_flag is True:
            alert_risky_html = '<span class="tcp-risk-pill tcp-risk-pill-risky">RISKY</span>'
        elif risky_flag is False:
            alert_risky_html = '<span class="tcp-risk-pill tcp-risk-pill-safe">SAFE</span>'
        else:
            alert_risky_html = '<span class="tcp-risk-pill tcp-risk-pill-unknown">N/A</span>'
    pb_state = latest_pb.get("pullback_state", "NONE") if latest_pb else "NONE"
    trend_level = str(trend_strength.get("level", "WEAK")).upper()
    trend_direction = str(trend_strength.get("direction", "NEUTRAL")).upper()
    if trend_level not in ("WEAK", "VALID", "STRONG"):
        trend_level = "WEAK"
    if trend_direction not in ("BULLISH", "BEARISH", "NEUTRAL"):
        trend_direction = "NEUTRAL"
    trend_dir_class = f"tcp-trend-direction-{trend_direction.lower()}"
    trend_bar_active_class = f"tcp-trend-bar-active-{trend_direction.lower()}"
    trend_level_count = 1 if trend_level == "WEAK" else 2 if trend_level == "VALID" else 3
    trend_bar_1 = trend_bar_active_class if trend_level_count >= 1 else ""
    trend_bar_2 = trend_bar_active_class if trend_level_count >= 2 else ""
    trend_bar_3 = trend_bar_active_class if trend_level_count >= 3 else ""

    bias_arrow_class = f"tcp-bias-arrow-{state_bias.lower()}"
    bias_label_class = f"tcp-bias-{state_bias.lower()}"

    low_active = " tcp-vol-light-active" if vol_status == "LOW" else ""
    norm_active = " tcp-vol-light-active" if vol_status == "NORMAL" else ""
    high_active = " tcp-vol-light-active" if vol_status == "HIGH" else ""

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                f"""
            <div class="tcp-panel">
                <div class="tcp-panel-label">STATE BIAS</div>
                <div class="tcp-bias-gauge-wrap">
                    <div class="tcp-bias-gauge">
                        <div class="tcp-bias-gauge-inner"></div>
                        <div class="tcp-bias-arrow {bias_arrow_class}">▲</div>
                    </div>
                </div>
                <div class="tcp-bias-label {bias_label_class}">{state_bias}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
            <div class="tcp-panel">
                <div class="tcp-panel-label">VOLATILITY</div>
                <div class="tcp-vol-lights">
                    <span class="tcp-vol-light tcp-vol-light-low{low_active}" title="LOW"></span>
                    <span class="tcp-vol-light tcp-vol-light-normal{norm_active}" title="NORMAL"></span>
                    <span class="tcp-vol-light tcp-vol-light-high{high_active}" title="HIGH"></span>
                </div>
                <div class="tcp-vol-data">VOL RATIO {vol_ratio}</div>
                <div class="tcp-vol-data">STATUS: {vol_status}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""
            <div class="tcp-panel">
                <div class="tcp-panel-label">ALERT STATUS</div>
                <div class="tcp-alert-status-body">
                    <div class="tcp-alert-main-line" style="color: {alert_color};">{alert_text}</div>
                    <div class="tcp-alert-risk-row">{alert_risky_html}</div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
            <div class="tcp-panel">
                <div class="tcp-panel-label">TREND</div>
                <div class="tcp-trend-wrap">
                    <div class="tcp-trend-direction {trend_dir_class}">{trend_direction}</div>
                    <div class="tcp-trend-level-badge">{trend_level}</div>
                    <div class="tcp-trend-bars">
                        <span class="tcp-trend-bar {trend_bar_1}"></span>
                        <span class="tcp-trend-bar {trend_bar_2}"></span>
                        <span class="tcp-trend-bar {trend_bar_3}"></span>
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col3:
            pb_state_upper = str(pb_state).upper()
            if pb_state_upper == "NONE":
                st.markdown(
                '<div class="tcp-panel"><div class="tcp-panel-label">PULLBACK STATUS</div>'
                '<div class="tcp-pb-gauge-wrap" style="display:flex;align-items:center;justify-content:center;min-height:90px;">'
                    '<span class="tcp-pb-label tcp-pb-label-none">NONE</span></div></div>',
                    unsafe_allow_html=True,
                )
            else:
                pb_arrow_class = "tcp-pb-arrow-invalid" if pb_state_upper == "INVALID" else "tcp-pb-arrow-ready" if pb_state_upper == "READY" else "tcp-pb-arrow-forming"
                pb_label_class = "tcp-pb-label-invalid" if pb_state_upper == "INVALID" else "tcp-pb-label-ready" if pb_state_upper == "READY" else "tcp-pb-label-forming"
                st.markdown(
                f'<div class="tcp-panel"><div class="tcp-panel-label">PULLBACK STATUS</div>'
                f'<div class="tcp-pb-gauge-wrap"><div class="tcp-pb-gauge"><div class="tcp-pb-gauge-inner"></div>'
                f'<div class="tcp-pb-gauge-labels"><span>INVALID</span><span>READY</span><span>FORMING</span></div>'
                f'<div class="tcp-pb-arrow {pb_arrow_class}">&#9650;</div></div>'
                    f'<div class="tcp-pb-label {pb_label_class}">{pb_state_upper}</div></div></div>',
                    unsafe_allow_html=True,
                )
            sess_led = "tcp-session-led-active" if sess_status == "ACTIVE" else "tcp-session-led-paused" if sess_status == "PAUSED" else "tcp-session-led-completed" if sess_status == "COMPLETED" else "tcp-session-led-none"
            sess_txt = "tcp-session-status-active" if sess_status == "ACTIVE" else "tcp-session-status-paused" if sess_status == "PAUSED" else "tcp-session-status-completed" if sess_status == "COMPLETED" else "tcp-session-status-none"

            st.markdown(
                f"""
            <div class="tcp-panel tcp-panel-controls">
                <div class="tcp-panel-label">CONTROLS</div>
                <div style="height: 90px; display: flex; align-items: center; justify-content: center;">
                    <div class="tcp-session-status">
                        <span class="tcp-session-led {sess_led}"></span>
                        <span class="tcp-session-status-text {sess_txt}">SESSION: {sess_status if sess_status != "—" else "NO SESSION"}</span>
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with st.container(border=True):
        st.caption("Quick Controls")
        qc1, qc2, qc3, qc4 = st.columns(4)
        with qc1:
            with st.container(border=True, height=140):
                st.markdown('<div class="tcp-quick-subpanel-label">SESSION ID</div>', unsafe_allow_html=True)
                knob_ui_value = st.slider(
                    "SESSION ID",
                    min_value=1,
                    max_value=10,
                    value=int(st.session_state.get("tcp_session_knob", 1)),
                    key="tcp_session_knob_ui",
                    label_visibility="collapsed",
                )
                if int(st.session_state.get("tcp_session_knob", 1)) != int(knob_ui_value):
                    st.session_state["tcp_session_knob"] = int(knob_ui_value)
                    st.rerun()
        with qc2:
            with st.container(border=True, height=140):
                st.markdown('<div class="tcp-quick-subpanel-label">AUTO REFRESH</div>', unsafe_allow_html=True)
                _left, mid, _right = st.columns([1, 1, 1])
                with mid:
                    auto_refresh_simple = st.toggle(
                        "Auto Refresh",
                        value=bool(auto_on),
                        key="tcp_auto_refresh_toggle",
                        label_visibility="collapsed",
                    )
                st.session_state["tcp_auto_refresh_enabled"] = bool(auto_refresh_simple)
        with qc3:
            with st.container(border=True, height=140):
                st.markdown('<div class="tcp-quick-subpanel-label">ALERT FREEZE</div>', unsafe_allow_html=True)
                freeze_class = "tcp-freeze-light-on" if alert_freeze_on else "tcp-freeze-light-off"
                freeze_text = "ON" if alert_freeze_on else "OFF"
                freeze_color = "#7fd4ff" if alert_freeze_on else "#9aa0a6"
                st.markdown(
                    f'<div style="height:34px;display:flex;align-items:center;justify-content:center;gap:0.5rem;">'
                    f'<span class="tcp-freeze-light {freeze_class}"></span>'
                    f'<span style="font-size:0.78rem;font-weight:700;letter-spacing:0.06em;color:{freeze_color};">{freeze_text}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with qc4:
            with st.container(border=True, height=140):
                st.markdown('<div class="tcp-quick-subpanel-label">RULES</div>', unsafe_allow_html=True)
                st.markdown('<span id="tcp-rules-btn-marker"></span>', unsafe_allow_html=True)
                if st.button("RULES", key="tcp_rules_btn", use_container_width=True):
                    _show_trading_rules_dialog()

    guardian_left, guardian_mid, guardian_right = st.columns([4, 2, 4])
    with guardian_mid:
        st.markdown('<span id="tcp-guardian-btn-marker"></span>', unsafe_allow_html=True)
        if st.button(
            "AI Guardian Angel",
            key="tcp_ai_guardian_angel_btn",
            use_container_width=False,
        ):
            st.session_state["ga_session_id"] = int(session_id_tcp)
            _show_guardian_angel_dialog()

def information_page():
    import html
    import json

    st.header("Information")
    info_tab, news_tab = st.tabs(["Trading Info", "News"])

    with news_tab:
        st.subheader("AI Trader News")
        st.caption("Fetch Finnhub news, then summarize via AI Trader.")

        news_symbol = st.text_input(
            "Instrument (e.g. BTCUSD, AAPL, EURUSD)",
            value=str(st.session_state.get("ai_news_symbol", "")),
            key="ai_news_symbol_ui",
        )
        # Keep the source of truth in session_state for repeatable reruns.
        st.session_state["ai_news_symbol"] = news_symbol

        news_category = st.text_input(
            "CATEGORY (general, forex, crypto, merger)",
            value=str(st.session_state.get("ai_news_category", "")),
            key="ai_news_category_ui",
        )
        st.session_state["ai_news_category"] = news_category

        lookback_hours = st.number_input(
            "Loopback hours",
            min_value=1,
            max_value=72,
            value=int(st.session_state.get("ai_news_lookback_hours", 12)),
            step=1,
            key="ai_news_lookback_hours_ui",
        )
        st.session_state["ai_news_lookback_hours"] = int(lookback_hours)

        ask_news = st.button(
            "Ask the AI Trader about News",
            use_container_width=True,
            key="ai_news_ask_btn",
        )

        if ask_news:
            if not str(news_symbol).strip():
                st.warning("Please enter an instrument/symbol.")
            else:
                try:
                    news_resp = api_client.get_daily_news(
                        symbol=news_symbol,
                        category=news_category if str(news_category).strip() else None,
                        lookback_hours=int(lookback_hours),
                    )
                    items = news_resp.get("items", []) if isinstance(news_resp, dict) else []
                    summary_resp = api_client.summarize_news(
                        symbol=news_symbol,
                        lookback_hours=int(lookback_hours),
                        news_items=items if isinstance(items, list) else [],
                    )
                    st.session_state["ai_news_feed_result"] = news_resp
                    st.session_state["ai_news_result"] = summary_resp
                    st.session_state.pop("ai_news_error", None)
                except APIError as e:
                    st.session_state["ai_news_error"] = f"Failed to load news: {e.detail}"
                except Exception as e:
                    st.session_state["ai_news_error"] = f"Connection error: {e}"

        if st.session_state.get("ai_news_error"):
            st.error(st.session_state["ai_news_error"])

        news_result = st.session_state.get("ai_news_result")
        if isinstance(news_result, dict):
            st.markdown("**News Answer**")
            st.write(news_result.get("text", ""))
            st.divider()
            st.markdown("**Raw JSON Response**")
            st.json(news_result)
            news_feed_result = st.session_state.get("ai_news_feed_result")
            if isinstance(news_feed_result, dict):
                with st.expander("Raw News Feed JSON"):
                    st.json(news_feed_result)

    with info_tab:
        top_cols = st.columns([2, 1])
        with top_cols[0]:
            st.caption("Strategy information returned by backend `/tradinginfo`.")
        with top_cols[1]:
            refresh_clicked = st.button("↻ Refresh Info", use_container_width=True, key="trading_info_refresh")

        if refresh_clicked or "trading_info_result" not in st.session_state:
            try:
                st.session_state["trading_info_result"] = api_client.get_trading_info()
                st.session_state.pop("trading_info_error", None)
            except APIError as e:
                st.session_state["trading_info_error"] = f"Failed to load trading info: {e.detail}"
            except Exception as e:
                st.session_state["trading_info_error"] = f"Connection error: {e}"

        if st.session_state.get("trading_info_error"):
            st.error(st.session_state["trading_info_error"])
            return

        info = st.session_state.get("trading_info_result")
        if not isinstance(info, dict):
            st.info("No information returned yet.")
            return

        strategy_sections = [
            "session",
            "bias_calculation",
            "pullback_calculation",
            "volatility_calculation",
            "alert",
            "trading_control_panel",
        ]
        has_strategy_text_payload = all(
            isinstance(info.get(section), str) for section in strategy_sections if section in info
        ) and any(section in info for section in strategy_sections)

        if has_strategy_text_payload:
            st.subheader("Trading Strategy Information")
            st.caption("Structured strategy notes returned by `/tradinginfo`.")
            panel_height = st.slider(
                "Text panel height",
                min_value=140,
                max_value=560,
                value=240,
                step=20,
                key="trading_info_panel_height",
            )

            section_titles = {
                "session": "Session",
                "bias_calculation": "Bias Calculation",
                "pullback_calculation": "Pullback Calculation",
                "volatility_calculation": "Volatility Calculation",
                "alert": "Alert",
                "trading_control_panel": "Trading Control Panel",
            }

            for section_key in strategy_sections:
                if section_key not in info:
                    continue
                section_text = info.get(section_key, "")
                with st.container(border=True):
                    st.markdown(f"**{section_titles.get(section_key, section_key.title())}**")
                    st.markdown(
                        (
                            f"<div class='info-rich-text' "
                            f"style='max-height:{panel_height}px; overflow-y:auto;'>"
                            f"{html.escape(section_text)}</div>"
                        ),
                        unsafe_allow_html=True,
                    )

            with st.expander("View raw JSON"):
                st.json(info)
            return

        def _show_textbox_grid(data: dict, key_prefix: str):
            if not data:
                st.caption("No fields available.")
                return
            items = list(data.items())
            cols = st.columns(2)
            for idx, (k, v) in enumerate(items):
                with cols[idx % 2]:
                    if isinstance(v, (dict, list)):
                        st.text_area(
                            k.replace("_", " ").title(),
                            value=json.dumps(v, indent=2),
                            disabled=True,
                            height=120,
                            key=f"{key_prefix}_{idx}",
                        )
                    else:
                        st.text_input(
                            k.replace("_", " ").title(),
                            value="" if v is None else str(v),
                            disabled=True,
                            key=f"{key_prefix}_{idx}",
                        )

        st.subheader("Trading Info Overview")
        overview = {
            "openapi": info.get("openapi"),
            "title": (info.get("info") or {}).get("title"),
            "version": (info.get("info") or {}).get("version"),
        }
        with st.container(border=True):
            _show_textbox_grid(overview, "ti_overview")

        paths = info.get("paths", {}) if isinstance(info.get("paths"), dict) else {}
        session_paths = {k: v for k, v in paths.items() if k.startswith("/api/sessions")}

        st.subheader("Sessions Endpoints")
        if not session_paths:
            st.info("No session endpoints found in trading info.")
        else:
            for p_idx, (path_name, path_data) in enumerate(session_paths.items()):
                if not isinstance(path_data, dict):
                    continue
                with st.container(border=True):
                    st.markdown(f"**{path_name}**")
                    for m_idx, method in enumerate(["get", "post", "patch", "delete", "put"]):
                        method_obj = path_data.get(method)
                        if not isinstance(method_obj, dict):
                            continue

                        st.markdown(f"`{method.upper()}`")
                        params = method_obj.get("parameters", [])
                        param_names = []
                        if isinstance(params, list):
                            for p in params:
                                if isinstance(p, dict) and p.get("name"):
                                    param_names.append(str(p.get("name")))

                        req_schema = ""
                        req_body = method_obj.get("requestBody", {})
                        if isinstance(req_body, dict):
                            req_schema = (
                                req_body.get("content", {})
                                .get("application/json", {})
                                .get("schema", {})
                                .get("$ref", "")
                            )

                        ok_schema = ""
                        responses = method_obj.get("responses", {})
                        if isinstance(responses, dict):
                            ok_schema = (
                                responses.get("200", {})
                                .get("content", {})
                                .get("application/json", {})
                                .get("schema", {})
                                .get("$ref", "")
                            )

                        endpoint_box = {
                            "summary": method_obj.get("summary", ""),
                            "operation_id": method_obj.get("operationId", ""),
                            "query_parameters": ", ".join(param_names),
                            "request_schema": req_schema,
                            "response_200_schema": ok_schema,
                        }
                        _show_textbox_grid(endpoint_box, f"ti_ep_{p_idx}_{m_idx}")
                        st.divider()

        schemas = (
            info.get("components", {}).get("schemas", {})
            if isinstance(info.get("components"), dict)
            else {}
        )
        if not isinstance(schemas, dict):
            schemas = {}

        st.subheader("Session Schemas")
        relevant_schema_names = [
            "SessionCreate",
            "SessionRead",
            "SessionUpdate",
            "SessionMetadataResponse",
            "SessionVisualizationResponse",
        ]
        found_any_schema = False
        for s_idx, schema_name in enumerate(relevant_schema_names):
            schema_obj = schemas.get(schema_name)
            if not isinstance(schema_obj, dict):
                continue
            found_any_schema = True
            with st.container(border=True):
                st.markdown(f"**{schema_name}**")
                properties = schema_obj.get("properties", {})
                required = schema_obj.get("required", [])
                required_set = set(required) if isinstance(required, list) else set()

                if not isinstance(properties, dict) or not properties:
                    st.caption("No properties.")
                    continue

                for f_idx, (field_name, field_schema) in enumerate(properties.items()):
                    if not isinstance(field_schema, dict):
                        field_schema = {}
                    field_type = field_schema.get("type")
                    if not field_type and "$ref" in field_schema:
                        field_type = str(field_schema.get("$ref"))
                    if not field_type and "anyOf" in field_schema:
                        field_type = " | ".join(
                            [
                                str(x.get("type") or x.get("$ref"))
                                for x in field_schema.get("anyOf", [])
                                if isinstance(x, dict)
                            ]
                        )

                    field_box = {
                        "field": field_name,
                        "type": field_type or "-",
                        "required": "yes" if field_name in required_set else "no",
                        "default": field_schema.get("default", "-"),
                    }
                    _show_textbox_grid(field_box, f"ti_schema_{s_idx}_{f_idx}")
                    st.divider()

        if not found_any_schema:
            st.info("No relevant session schemas found in trading info.")

        with st.expander("View raw JSON"):
            st.json(info)


# ── Router ────────────────────────────────────────────────────────────

if page == "Trading Control Panel":
    trading_control_panel_page()
elif page == "Session":
    sessions_page()
elif page == "Provider":
    provider_page()
elif page == "Information":
    information_page()

_visualize_auto_refresh_fragment(show_caption=False)
_system_clock_widget()
