import base64
import html
import io
import streamlit as st
import streamlit.components.v1 as components
import api_client
from session_knob_component import render_session_knob
from api_client import APIError
from datetime import datetime, timezone
import time

TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h"]
PROVIDERS = ["IBKR", "BYBIT"]
ALERT_STATUSES = ["OPEN", "TP_HIT", "SL_HIT", "CANCELED"]
ALERT_DIRECTIONS = ["LONG", "SHORT"]
ALERT_TYPES = ["PREALERT", "TRIGGER_ALERT", "TREND_STRENGTH_ALERT", "BREAKOUT"]
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
    .tcp-status-stack {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 0.2rem;
        line-height: 1;
    }
    .tcp-status-main {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }
    .tcp-led {
        width: 12px;
        height: 12px;
        border-radius: 50%;
    }
    .tcp-led-pulse {
        animation: tcp-led-pulse 1.05s ease-in-out infinite;
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
    .tcp-updated-line {
        font-size: 0.67rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        color: #9aa0a6;
        white-space: nowrap;
    }
    .tcp-updated-line-refreshing {
        color: #7dd3fc;
        text-shadow: 0 0 8px rgba(125, 211, 252, 0.35);
    }
    @keyframes tcp-led-pulse {
        0% { transform: scale(1); opacity: 0.86; }
        50% { transform: scale(1.18); opacity: 1; }
        100% { transform: scale(1); opacity: 0.86; }
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
        min-height: 96px;
        display: flex;
        align-items: flex-end;
        justify-content: center;
    }
    .tcp-bias-gauge {
        width: 150px;
        height: 84px;
        position: relative;
        border-radius: 150px 150px 0 0;
        background: linear-gradient(
            90deg,
            #ef4444 0%,
            #ef4444 33.33%,
            #9aa0a6 33.33%,
            #9aa0a6 66.66%,
            #22c55e 66.66%,
            #22c55e 100%
        );
        border: 1px solid rgba(120, 130, 150, 0.35);
        box-shadow: inset 0 2px 8px rgba(0,0,0,0.45), 0 2px 10px rgba(0,0,0,0.28);
        overflow: hidden;
    }
    .tcp-bias-gauge::before {
        content: "";
        position: absolute;
        left: 50%;
        bottom: 6px;
        transform: translateX(-50%);
        width: 116px;
        height: 62px;
        border-radius: 116px 116px 0 0;
        background: linear-gradient(180deg, #252830 0%, #1a1d24 100%);
        border: 1px solid rgba(90, 100, 120, 0.35);
    }
    .tcp-bias-gauge::after {
        content: "";
        position: absolute;
        left: 50%;
        bottom: 0;
        transform: translateX(-50%);
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #d5d9e0;
        border: 2px solid #12151b;
        box-shadow: 0 0 8px rgba(213,217,224,0.45);
        z-index: 4;
    }
    .tcp-bias-gauge-inner {
        display: none;
    }
    .tcp-bias-arrow {
        position: absolute;
        left: 50%;
        bottom: 5px;
        width: 2px;
        height: 56px;
        background: currentColor;
        transform-origin: 50% calc(100% - 2px);
        border-radius: 2px;
        z-index: 3;
        box-shadow: 0 0 8px currentColor;
        font-size: 0; /* hide old text glyph if present */
        line-height: 0;
    }
    .tcp-bias-arrow::before {
        content: "";
        position: absolute;
        left: 50%;
        top: -6px;
        transform: translateX(-50%);
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-bottom: 8px solid currentColor;
        filter: drop-shadow(0 0 3px currentColor);
    }
    .tcp-bias-arrow-bearish { transform: translateX(-50%) rotate(-62deg); color: #ef4444; }
    .tcp-bias-arrow-neutral { transform: translateX(-50%) rotate(0deg); color: #9aa0a6; }
    .tcp-bias-arrow-bullish { transform: translateX(-50%) rotate(62deg); color: #22c55e; }
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
        min-height: 96px;
        display: flex;
        align-items: flex-end;
        justify-content: center;
    }
    .tcp-pb-gauge {
        width: 150px;
        height: 84px;
        position: relative;
        border-radius: 150px 150px 0 0;
        background: linear-gradient(
            90deg,
            #ef4444 0%,
            #ef4444 33.33%,
            #f0ad4e 33.33%,
            #f0ad4e 66.66%,
            #3b82f6 66.66%,
            #3b82f6 100%
        );
        border: 1px solid rgba(120, 130, 150, 0.35);
        box-shadow: inset 0 2px 8px rgba(0,0,0,0.45), 0 2px 10px rgba(0,0,0,0.28);
        overflow: hidden;
    }
    .tcp-pb-gauge::before {
        content: "";
        position: absolute;
        left: 50%;
        bottom: 6px;
        transform: translateX(-50%);
        width: 116px;
        height: 62px;
        border-radius: 116px 116px 0 0;
        background: linear-gradient(180deg, #252830 0%, #1a1d24 100%);
        border: 1px solid rgba(90, 100, 120, 0.35);
    }
    .tcp-pb-gauge::after {
        content: "";
        position: absolute;
        left: 50%;
        bottom: 0;
        transform: translateX(-50%);
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #d5d9e0;
        border: 2px solid #12151b;
        box-shadow: 0 0 8px rgba(213,217,224,0.45);
        z-index: 4;
    }
    .tcp-pb-arrow {
        position: absolute;
        left: 50%;
        bottom: 5px;
        width: 2px;
        height: 56px;
        background: currentColor;
        transform-origin: 50% calc(100% - 2px);
        border-radius: 2px;
        z-index: 3;
        box-shadow: 0 0 8px currentColor;
        font-size: 0;
        line-height: 0;
    }
    .tcp-pb-arrow::before {
        content: "";
        position: absolute;
        left: 50%;
        top: -6px;
        transform: translateX(-50%);
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-bottom: 8px solid currentColor;
        filter: drop-shadow(0 0 3px currentColor);
    }
    .tcp-pb-arrow-invalid { transform: translateX(-50%) rotate(-62deg); color: #ef4444; }
    .tcp-pb-arrow-ready { transform: translateX(-50%) rotate(0deg); color: #f0ad4e; }
    .tcp-pb-arrow-forming { transform: translateX(-50%) rotate(62deg); color: #3b82f6; }
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
    .tcp-vol-light-normal { background: #f59e0b; }
    .tcp-vol-light-elevated { background: #22c55e; }
    .tcp-vol-light-high { background: #ef4444; }
    .tcp-vol-light-active { box-shadow: 0 0 10px currentColor, 0 0 20px currentColor; }
    .tcp-vol-light-low.tcp-vol-light-active { color: #3b82f6; }
    .tcp-vol-light-normal.tcp-vol-light-active { color: #f59e0b; }
    .tcp-vol-light-elevated.tcp-vol-light-active { color: #22c55e; }
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
    .tcp-sess-knob-wrap {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 50px;
        margin: 0 0 0.2rem 0;
    }
    .tcp-sess-knob-dial {
        position: relative;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: radial-gradient(circle at 42% 32%, #5a6578 0%, #343c4c 42%, #181d28 100%);
        border: none;
        box-shadow:
            0 0 0 0.5px rgba(92, 239, 255, 0.75),
            inset 0 2px 6px rgba(0,0,0,0.55),
            0 0 3px rgba(92,239,255,0.2),
            0 0 5px rgba(92,239,255,0.1);
    }
    .tcp-sess-knob-pointer {
        position: absolute;
        left: 50%;
        bottom: 50%;
        width: 3px;
        height: 17px;
        margin-left: -1.5px;
        transform-origin: 50% 100%;
        transform: rotate(var(--knob-deg, 0deg));
        background: linear-gradient(to top, #3a8fa8 0%, #5cefff 100%);
        border-radius: 2px;
        z-index: 1;
        box-shadow: 0 0 3px rgba(92,239,255,0.35);
    }
    .tcp-sess-knob-hub {
        position: absolute;
        left: 50%;
        top: 50%;
        width: 10px;
        height: 10px;
        margin: -5px 0 0 -5px;
        border-radius: 50%;
        background: linear-gradient(180deg, #2d3545 0%, #1a1f2a 100%);
        border: none;
        z-index: 2;
        box-shadow:
            0 0 0 0.5px rgba(92, 239, 255, 0.65),
            0 0 2px rgba(92, 239, 255, 0.22),
            0 1px 3px rgba(0,0,0,0.45);
    }
    /* SESSION ID tile: match 140px siblings; kill Streamlit's fixed-height inner scroll */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#tcp-session-knob-marker) {
        overflow: hidden !important;
        min-height: 140px !important;
        max-height: 140px !important;
        height: 140px !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#tcp-session-knob-marker) > div {
        padding-top: 0.45rem !important;
        padding-bottom: 0.45rem !important;
        box-sizing: border-box !important;
        min-height: 0 !important;
        overflow: visible !important;
        overflow-y: visible !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#tcp-session-knob-marker) [data-testid="stVerticalBlock"] {
        gap: 0 !important;
        min-height: 0 !important;
        overflow: visible !important;
        overflow-y: visible !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#tcp-session-knob-marker) [data-testid="stElementContainer"] {
        margin-bottom: 0 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#tcp-session-knob-marker)
        [data-testid="stElementContainer"]:not(:has(iframe)) {
        margin-top: 0 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#tcp-session-knob-marker)
        [data-testid="stElementContainer"]:has(iframe) {
        margin-top: 1.4rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#tcp-session-knob-marker) iframe {
        height: 48px !important;
        min-height: 48px !important;
        max-height: 48px !important;
        width: 100% !important;
        display: block !important;
        border: none !important;
        vertical-align: top !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#tcp-session-knob-marker)
        [data-testid="stElementContainer"]:has(.tcp-sess-knob-session-num) {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#tcp-session-knob-marker) .tcp-sess-knob-session-num {
        text-align: center !important;
        display: block !important;
        width: 100% !important;
        box-sizing: border-box !important;
        margin: 0.1rem 0 0 0 !important;
        padding: 0 !important;
        line-height: 1.1 !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        color: #5cefff !important;
        letter-spacing: 0.06em !important;
        font-variant-numeric: tabular-nums !important;
        text-shadow: 0 0 8px rgba(92, 239, 255, 0.28) !important;
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
    div:has(#tcp-guardian-btn-marker) + div {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
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
        min-width: 220px !important;
        white-space: nowrap !important;
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


def _volatility_band_from_vol_ratio(vol_ratio: object) -> str | None:
    """LOW < 0.80, NORMAL [0.80, 1.00), ELEVATED [1.00, 1.2), HIGH >= 1.2."""
    try:
        x = float(vol_ratio)
    except (TypeError, ValueError):
        return None
    if x < 0.80:
        return "LOW"
    if x < 1.00:
        return "NORMAL"
    if x < 1.2:
        return "ELEVATED"
    return "HIGH"


def _tcp_resolve_volatility_status(latest_vol: dict) -> str:
    raw = str((latest_vol or {}).get("volatility_status") or "").strip().upper()
    if raw in ("LOW", "NORMAL", "ELEVATED", "HIGH"):
        return raw
    derived = _volatility_band_from_vol_ratio((latest_vol or {}).get("vol_ratio"))
    return derived if derived else "NORMAL"


def _volatility_status_colored_html(value: str | None) -> str:
    status = (value or "—").upper()
    color_map = {
        "LOW": "#3b82f6",
        "NORMAL": "#f59e0b",
        "ELEVATED": "#22c55e",
        "HIGH": "#ef4444",
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
        # The small chart on the TCP page uses `tcp_viz_result`, so refresh it too.
        # Keep bar count aligned with the TCP chart (50 bars).
        try:
            viz_result = api_client.visualize_session(int(session_id), 50)
            if isinstance(viz_result, dict):
                st.session_state["tcp_viz_result"] = viz_result
                st.session_state.pop("tcp_viz_error", None)
        except Exception:
            # If chart refresh fails, keep the previous `tcp_viz_result`.
            pass

        # Keep the auto-refresh cadence aligned with the backend session timeframe when available.
        if isinstance(panel_result, dict):
            tf = (panel_result.get("session") or {}).get("timeframe", "1m")
            st.session_state["tcp_auto_refresh_cfg"] = {
                "session_id": int(session_id),
                "timeframe": tf,
                "interval_seconds": _refresh_seconds_for_timeframe(tf),
            }

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
    sessions_tab, bias_tab, pullback_tab, breakout_tab, volatility_tab, visualize_tab, alerts_tab, trades_tab = st.tabs(
        [
            "Session",
            "Bias Calculations",
            "Pullback Calculations",
            "Breakout Calculations",
            "Volatility Calculations",
            "Visualize",
            "Alerts",
            "Trades",
        ]
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

    with breakout_tab:
        st.subheader("Breakout Calculations")
        list_cols = st.columns(4)
        with list_cols[0]:
            boc_session_id = st.number_input("Session ID", min_value=1, value=1, step=1, key="boc_session_id")
        with list_cols[1]:
            boc_limit = st.number_input("Limit", min_value=1, max_value=1000, value=100, step=10, key="boc_limit")
        with list_cols[2]:
            boc_offset = st.number_input("Offset", min_value=0, value=0, step=10, key="boc_offset")
        with list_cols[3]:
            st.write("")
            if st.button("Get By Session", use_container_width=True, key="boc_get_all"):
                try:
                    session_breakouts = api_client.list_breakout_calculations(
                        session_id=int(boc_session_id),
                        limit=int(boc_limit),
                        offset=int(boc_offset),
                    )
                    st.session_state["breakout_calculations_list"] = session_breakouts
                    st.success(
                        f"Loaded {len(session_breakouts)} breakout calculation(s) for session #{int(boc_session_id)}."
                    )
                except APIError as e:
                    st.error(f"Failed to list breakout calculations: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

        boc_detail_id = st.number_input(
            "Breakout Calculation ID (Get One)", min_value=1, value=1, step=1, key="boc_detail_id"
        )
        if st.button("Get One", use_container_width=True, key="boc_get_one"):
            try:
                st.session_state["breakout_calculation_detail"] = api_client.get_breakout_calculation(int(boc_detail_id))
            except APIError as e:
                st.error(f"Failed to get breakout calculation: {e.detail}")
            except Exception as e:
                st.error(f"Connection error: {e}")

        if "breakout_calculations_list" in st.session_state:
            with st.container(border=True):
                st.markdown("**Session Breakout Calculations**")
                import pandas as pd

                df = pd.DataFrame(st.session_state["breakout_calculations_list"])
                for dt_col in ["calculated_at", "created_at", "updated_at"]:
                    if dt_col in df.columns:
                        df[dt_col] = df[dt_col].apply(_fmt_dt)
                st.dataframe(df, use_container_width=True, hide_index=True)

        if "breakout_calculation_detail" in st.session_state:
            detail = st.session_state["breakout_calculation_detail"]
            with st.container(border=True):
                st.markdown("**Breakout Calculation Detail**")
                top_cols = st.columns(4)
                with top_cols[0]:
                    st.metric("State", detail.get("breakout_state", "NONE"))
                with top_cols[1]:
                    st.metric("Direction", detail.get("setup_direction", "—"))
                with top_cols[2]:
                    st.metric("Breakout Level", detail.get("breakout_level", "—"))
                with top_cols[3]:
                    st.metric("Alert Emitted", "Yes" if detail.get("alert_emitted") else "No")
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
                        return "color: #3b82f6; font-weight: 700;"
                    if s == "NORMAL":
                        return "color: #f59e0b; font-weight: 700;"
                    if s == "ELEVATED":
                        return "color: #22c55e; font-weight: 700;"
                    if s == "HIGH":
                        return "color: #ef4444; font-weight: 700;"
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

                # Breakout status panel.
                st.markdown("### Breakout")
                bo_cols = st.columns(4)
                with bo_cols[0]:
                    st.metric("Breakout State", session.get("breakout_state", "NONE"))
                with bo_cols[1]:
                    st.metric("Direction", session.get("breakout_setup_direction", "—"))
                with bo_cols[2]:
                    st.metric("Breakout Level", session.get("breakout_level", "—"))
                with bo_cols[3]:
                    st.metric("Breakout Q.", int(session.get("breakout_quality", 0) or 0))
                latest_breakout = data.get("latest_breakout_calculation")
                if latest_breakout:
                    st.markdown("**Latest Breakout Calculation**")
                    lbc_cols = st.columns(4)
                    with lbc_cols[0]:
                        st.metric("State", latest_breakout.get("breakout_state", "NONE"))
                    with lbc_cols[1]:
                        st.metric("Direction", latest_breakout.get("setup_direction", "—"))
                    with lbc_cols[2]:
                        st.metric("Breakout Level", latest_breakout.get("breakout_level", "—"))
                    with lbc_cols[3]:
                        st.metric("Alert Emitted", "Yes" if latest_breakout.get("alert_emitted") else "No")
                    st.caption(f"Reset Reason: **{latest_breakout.get('reset_reason', '—')}**")
                    st.json(latest_breakout)
                else:
                    st.info("No latest breakout calculation available.")

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
                    alert_q = st.columns(4)
                    with alert_q[0]:
                        st.metric("Bias Strength", int(latest_alert.get("bias_strength", 0) or 0))
                    with alert_q[1]:
                        st.metric("Structure Q.", int(latest_alert.get("structure_quality", 0) or 0))
                    with alert_q[2]:
                        st.metric("Pullback Q.", int(latest_alert.get("pullback_quality", 0) or 0))
                    with alert_q[3]:
                        st.metric("Vol. Fitness", int(latest_alert.get("volatility_fitness", 0) or 0))
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
                    "bias_strength",
                    "structure_quality",
                    "pullback_quality",
                    "volatility_fitness",
                    "entry_signal_price",
                    "stop_price",
                    "target_price",
                    "reason",
                ]
                display_cols = [c for c in preferred_cols if c in alerts_df.columns] + [
                    c for c in alerts_df.columns if c not in preferred_cols
                ]
                display_df = alerts_df[display_cols].copy()
                display_df.insert(0, "Radar", "📡")

                st.caption(
                    "Select a row in the table, then click **📡 Open radar chart** below "
                    "(bias strength, structure quality, pullback quality, volatility fitness)."
                )

                event = st.dataframe(
                    display_df,
                    key="alerts_list_radar_df",
                    on_select="rerun",
                    selection_mode="single-row",
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Radar": st.column_config.TextColumn(
                            "📡",
                            width="small",
                            help="Select the row, then use Open radar chart below.",
                        ),
                    },
                )

                def _alert_table_selection_rows(ev: object) -> list[int]:
                    if ev is None:
                        return []
                    try:
                        sel = ev.selection
                    except (AttributeError, KeyError):
                        return []
                    if sel is None:
                        return []
                    try:
                        rows = sel.rows
                    except AttributeError:
                        rows = sel.get("rows", []) if isinstance(sel, dict) else []
                    return list(rows) if rows else []

                if st.button("📡 Open radar chart", key="al_open_radar_chart_btn"):
                    sel_rows = _alert_table_selection_rows(event)
                    if not sel_rows:
                        st.warning("Select a row in the table first (click the row to highlight it).")
                    else:
                        st.session_state["_alert_radar_payload"] = alerts_df.iloc[int(sel_rows[0])].to_dict()
                        _show_alert_radar_dialog()

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
                detail_cols_q = st.columns(4)
                with detail_cols_q[0]:
                    st.metric("Bias Strength", int(ad.get("bias_strength", 0) or 0))
                with detail_cols_q[1]:
                    st.metric("Structure Q.", int(ad.get("structure_quality", 0) or 0))
                with detail_cols_q[2]:
                    st.metric("Pullback Q.", int(ad.get("pullback_quality", 0) or 0))
                with detail_cols_q[3]:
                    st.metric("Vol. Fitness", int(ad.get("volatility_fitness", 0) or 0))
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

    with trades_tab:
        st.subheader("Trades")

        with st.container(border=True):
            st.markdown("**List Session Trades**")
            list_cols = st.columns(4)
            with list_cols[0]:
                tr_session_id = st.number_input(
                    "Session ID",
                    min_value=1,
                    value=1,
                    step=1,
                    key="tr_list_session_id",
                )
            with list_cols[1]:
                tr_limit = st.number_input("Limit", min_value=1, max_value=1000, value=100, step=10, key="tr_list_limit")
            with list_cols[2]:
                tr_offset = st.number_input("Offset", min_value=0, value=0, step=10, key="tr_list_offset")
            with list_cols[3]:
                st.write("")
                if st.button("Get Trades", use_container_width=True, key="tr_get_list"):
                    try:
                        trades = api_client.list_session_trades(
                            session_id=int(tr_session_id),
                            limit=int(tr_limit),
                            offset=int(tr_offset),
                        )
                        st.session_state["trades_list"] = trades
                        st.success(f"Loaded {len(trades)} trade(s) for session #{int(tr_session_id)}.")
                    except APIError as e:
                        st.error(f"Failed to list trades: {e.detail}")
                    except Exception as e:
                        st.error(f"Connection error: {e}")

            if "trades_list" in st.session_state:
                import pandas as pd

                trades_df = pd.DataFrame(st.session_state["trades_list"])
                for dt_col in ["created_at", "closed_at"]:
                    if dt_col in trades_df.columns:
                        trades_df[dt_col] = trades_df[dt_col].apply(_fmt_dt)

                preferred_cols = [
                    "id",
                    "session_id",
                    "alert_id",
                    "created_at",
                    "direction",
                    "status",
                    "entry_price",
                    "take_profit_price",
                    "stop_loss_price",
                    "closed_at",
                ]
                display_cols = [c for c in preferred_cols if c in trades_df.columns] + [
                    c for c in trades_df.columns if c not in preferred_cols
                ]
                st.dataframe(trades_df[display_cols], use_container_width=True, hide_index=True)

        with st.container(border=True):
            st.markdown("**Get One Trade**")
            tr_detail_id = st.number_input("Trade ID (Get One)", min_value=1, value=1, step=1, key="tr_detail_id")
            if st.button("Get One Trade", use_container_width=True, key="tr_get_one"):
                try:
                    st.session_state["trade_detail"] = api_client.get_trade(int(tr_detail_id))
                except APIError as e:
                    st.error(f"Failed to get trade: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")
            if "trade_detail" in st.session_state:
                st.markdown("**Trade Detail**")
                st.json(st.session_state["trade_detail"])

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
                    st.metric("breakout_buffer_atr_k", metadata.get("breakout_buffer_atr_k", "—"))
                with md_cols_2[3]:
                    st.metric("retest_band_atr_k", metadata.get("retest_band_atr_k", "—"))

                md_cols_3 = st.columns(4)
                with md_cols_3[0]:
                    st.metric("stop_buffer_atr_k", metadata.get("stop_buffer_atr_k", "—"))
                with md_cols_3[1]:
                    st.metric("persistence_threshold", metadata.get("persistence_threshold", "—"))
                with md_cols_3[2]:
                    st.metric("strength_threshold", metadata.get("strength_threshold", "—"))
                with md_cols_3[3]:
                    st.metric("cooldown_until", metadata.get("cooldown_until", "—"))

                md_cols_4 = st.columns(4)
                with md_cols_4[0]:
                    st.metric("trade_mode", metadata.get("trade_mode", "—"))
                with md_cols_4[1]:
                    st.metric("trade_auto_prealert", metadata.get("trade_auto_prealert", "—"))
                with md_cols_4[2]:
                    st.metric("trade_auto_trigger", metadata.get("trade_auto_trigger", "—"))
                with md_cols_4[3]:
                    st.metric("trade_auto_trend_strength", metadata.get("trade_auto_trend_strength", "—"))
                md_cols_5 = st.columns(3)
                with md_cols_5[0]:
                    st.metric("trade_auto_breakout", metadata.get("trade_auto_breakout", "—"))
                with md_cols_5[1]:
                    st.metric("Take Profit %", metadata.get("tp_percentage", "—"))
                with md_cols_5[2]:
                    st.metric("Stop Loss %", metadata.get("sl_percentage", "—"))
                st.json(metadata)

        # ── Create session form ───────────────────────────────────────
        with st.expander("➕ Create new session", expanded=False):
            with st.form("create_session_form"):
                col1, col2 = st.columns(2)
                with col1:
                    symbol = st.text_input("Symbol", value="BTCUSD", placeholder="e.g. AAPL, EURUSD")
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
                    persistence_threshold = st.number_input("Persistence Threshold", min_value=1, value=12, step=1)
                with bottom_col2:
                    swing_lookback = st.number_input("Swing Lookback", min_value=1, value=2, step=1)
                cooldown_until = st.number_input("Cooldown Until", min_value=0, value=10, step=1)

                trade_cols = st.columns(3)
                with trade_cols[0]:
                    trade_mode = st.toggle("Trade Mode", value=False)
                with trade_cols[1]:
                    tp_percentage_raw = st.text_input(
                        "Take Profit % (optional)",
                        value="",
                        placeholder="e.g. 0.4 — leave empty for none",
                        key="create_session_tp_percentage",
                    )
                with trade_cols[2]:
                    sl_percentage_raw = st.text_input(
                        "Stop Loss % (optional)",
                        value="",
                        placeholder="e.g. 0.3 — leave empty for none",
                        key="create_session_sl_percentage",
                    )

                auto_trade_cols = st.columns(4)
                with auto_trade_cols[0]:
                    trade_auto_prealert = st.toggle("Auto Trade PREALERT", value=False)
                with auto_trade_cols[1]:
                    trade_auto_trigger = st.toggle("Auto Trade TRIGGER", value=False)
                with auto_trade_cols[2]:
                    trade_auto_trend_strength = st.toggle("Auto Trade TREND STRENGTH", value=False)
                with auto_trade_cols[3]:
                    trade_auto_breakout = st.toggle("Auto Trade BREAKOUT", value=False)

                submitted = st.form_submit_button("Create Session", use_container_width=True)
                if submitted:
                    if not symbol or not symbol.strip():
                        st.error("Symbol is required.")
                    else:
                        try:
                            tp_percentage = (
                                float(str(tp_percentage_raw).strip())
                                if isinstance(tp_percentage_raw, str) and str(tp_percentage_raw).strip()
                                else None
                            )
                            sl_percentage = (
                                float(str(sl_percentage_raw).strip())
                                if isinstance(sl_percentage_raw, str) and str(sl_percentage_raw).strip()
                                else None
                            )
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
                                trade_mode=bool(trade_mode),
                                trade_auto_prealert=bool(trade_auto_prealert),
                                trade_auto_trigger=bool(trade_auto_trigger),
                                trade_auto_trend_strength=bool(trade_auto_trend_strength),
                                trade_auto_breakout=bool(trade_auto_breakout),
                                tp_percentage=tp_percentage,
                                sl_percentage=sl_percentage,
                            )
                            st.success(f"Session **#{new_session['id']}** created for **{new_session['symbol']}**")
                            st.rerun()
                        except ValueError:
                            st.error("Take Profit % and Stop Loss % must be numeric when provided (or leave empty for none).")
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

                quality_cols = st.columns(4)
                with quality_cols[0]:
                    st.metric("Bias Strength", int(sess.get("bias_strength", 0) or 0))
                with quality_cols[1]:
                    st.metric("Structure Q.", int(sess.get("structure_quality", 0) or 0))
                with quality_cols[2]:
                    st.metric("Pullback Q.", int(sess.get("pullback_quality", 0) or 0))
                with quality_cols[3]:
                    st.metric("Vol. Fitness", int(sess.get("volatility_fitness", 0) or 0))

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
                breakout_cols = st.columns(4)
                with breakout_cols[0]:
                    breakout_state = str(sess.get("breakout_state", "NONE") or "NONE").upper()
                    breakout_state_color = (
                        "#f59e0b"
                        if breakout_state == "AWAITING_RETEST"
                        else "#22c55e"
                        if breakout_state == "RETEST_VALID"
                        else "#9aa0a6"
                    )
                    st.markdown(
                        (
                            "Breakout State: "
                            f"<span style='color:{breakout_state_color};font-weight:700;'>{html.escape(breakout_state)}</span>"
                        ),
                        unsafe_allow_html=True,
                    )
                with breakout_cols[1]:
                    breakout_direction = str(sess.get("breakout_setup_direction", "—") or "—").upper()
                    breakout_direction_color = (
                        "#22c55e" if breakout_direction == "LONG" else "#ef4444" if breakout_direction == "SHORT" else "#9aa0a6"
                    )
                    st.markdown(
                        (
                            "Breakout Direction: "
                            f"<span style='color:{breakout_direction_color};font-weight:700;'>{html.escape(breakout_direction)}</span>"
                        ),
                        unsafe_allow_html=True,
                    )
                with breakout_cols[2]:
                    st.caption(f"Breakout Level: **{sess.get('breakout_level', '—')}**")
                with breakout_cols[3]:
                    st.caption(f"Breakout Quality: **{int(sess.get('breakout_quality', 0) or 0)}**")

                # Trade controls (optional fields added to SessionRead)
                trade_info_cols = st.columns(3)
                with trade_info_cols[0]:
                    _tm = sess.get("trade_mode")
                    if _tm is None:
                        st.caption("Trade Mode: **—**")
                    else:
                        st.caption(f"Trade Mode: **{'ON' if bool(_tm) else 'OFF'}**")
                with trade_info_cols[1]:
                    st.caption(f"Take Profit %: **{sess.get('tp_percentage', '—')}**")
                with trade_info_cols[2]:
                    st.caption(f"Stop Loss %: **{sess.get('sl_percentage', '—')}**")

                auto_trade_info_cols = st.columns(4)
                with auto_trade_info_cols[0]:
                    st.caption(f"Auto PREALERT: **{'ON' if bool(sess.get('trade_auto_prealert', False)) else 'OFF'}**")
                with auto_trade_info_cols[1]:
                    st.caption(f"Auto TRIGGER: **{'ON' if bool(sess.get('trade_auto_trigger', False)) else 'OFF'}**")
                with auto_trade_info_cols[2]:
                    st.caption(
                        f"Auto TREND STRENGTH: **{'ON' if bool(sess.get('trade_auto_trend_strength', False)) else 'OFF'}**"
                    )
                with auto_trade_info_cols[3]:
                    st.caption(f"Auto BREAKOUT: **{'ON' if bool(sess.get('trade_auto_breakout', False)) else 'OFF'}**")

                trade_toggle_cols = st.columns([1, 1, 1, 1, 1, 1.2])
                with trade_toggle_cols[0]:
                    _trade_mode_ui = st.toggle(
                        "Trade Mode",
                        value=bool(sess.get("trade_mode", False)),
                        key=f"trade_mode_toggle_{sid}",
                    )
                with trade_toggle_cols[1]:
                    _trade_auto_prealert_ui = st.toggle(
                        "Auto PREALERT",
                        value=bool(sess.get("trade_auto_prealert", False)),
                        key=f"trade_auto_prealert_toggle_{sid}",
                    )
                with trade_toggle_cols[2]:
                    _trade_auto_trigger_ui = st.toggle(
                        "Auto TRIGGER",
                        value=bool(sess.get("trade_auto_trigger", False)),
                        key=f"trade_auto_trigger_toggle_{sid}",
                    )
                with trade_toggle_cols[3]:
                    _trade_auto_trend_strength_ui = st.toggle(
                        "Auto TREND",
                        value=bool(sess.get("trade_auto_trend_strength", False)),
                        key=f"trade_auto_trend_strength_toggle_{sid}",
                    )
                with trade_toggle_cols[4]:
                    _trade_auto_breakout_ui = st.toggle(
                        "Auto BREAKOUT",
                        value=bool(sess.get("trade_auto_breakout", False)),
                        key=f"trade_auto_breakout_toggle_{sid}",
                    )
                with trade_toggle_cols[5]:
                    if st.button("Update", key=f"trade_mode_update_{sid}", use_container_width=True):
                        try:
                            api_client.update_session(
                                sid,
                                trade_mode=bool(_trade_mode_ui),
                                trade_auto_prealert=bool(_trade_auto_prealert_ui),
                                trade_auto_trigger=bool(_trade_auto_trigger_ui),
                                trade_auto_trend_strength=bool(_trade_auto_trend_strength_ui),
                                trade_auto_breakout=bool(_trade_auto_breakout_ui),
                            )
                            st.success(
                                f"Session #{sid} trade switches updated "
                                f"(mode: {'ON' if bool(_trade_mode_ui) else 'OFF'})."
                            )
                            st.rerun()
                        except APIError as e:
                            st.error(f"Failed to update trade switches: {e.detail}")
                        except Exception as e:
                            st.error(f"Connection error: {e}")

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
                        auto_trade_edit_cols = st.columns(4)
                        with auto_trade_edit_cols[0]:
                            new_trade_auto_prealert = st.toggle(
                                "Auto Trade PREALERT",
                                value=bool(sess.get("trade_auto_prealert", False)),
                                key=f"trade_auto_prealert_{sid}",
                            )
                        with auto_trade_edit_cols[1]:
                            new_trade_auto_trigger = st.toggle(
                                "Auto Trade TRIGGER",
                                value=bool(sess.get("trade_auto_trigger", False)),
                                key=f"trade_auto_trigger_{sid}",
                            )
                        with auto_trade_edit_cols[2]:
                            new_trade_auto_trend_strength = st.toggle(
                                "Auto Trade TREND STRENGTH",
                                value=bool(sess.get("trade_auto_trend_strength", False)),
                                key=f"trade_auto_trend_strength_{sid}",
                            )
                        with auto_trade_edit_cols[3]:
                            new_trade_auto_breakout = st.toggle(
                                "Auto Trade BREAKOUT",
                                value=bool(sess.get("trade_auto_breakout", False)),
                                key=f"trade_auto_breakout_{sid}",
                            )
                        _tp_cur = sess.get("tp_percentage")
                        _sl_cur = sess.get("sl_percentage")
                        new_tp_pct = st.number_input(
                            "Take Profit %",
                            min_value=0.0,
                            value=float(_tp_cur) if _tp_cur is not None else 0.4,
                            step=0.1,
                            key=f"tp_pct_{sid}",
                        )
                        new_sl_pct = st.number_input(
                            "Stop Loss %",
                            min_value=0.0,
                            value=float(_sl_cur) if _sl_cur is not None else 0.3,
                            step=0.1,
                            key=f"sl_pct_{sid}",
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
                                        trade_auto_prealert=bool(new_trade_auto_prealert),
                                        trade_auto_trigger=bool(new_trade_auto_trigger),
                                        trade_auto_trend_strength=bool(new_trade_auto_trend_strength),
                                        trade_auto_breakout=bool(new_trade_auto_breakout),
                                        tp_percentage=float(new_tp_pct),
                                        sl_percentage=float(new_sl_pct),
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
PROVIDER_POSITION_CATEGORIES = ["linear", "inverse", "option"]

def provider_page():
    st.header("Provider Gateway")
    selected_provider = st.selectbox(
        "Provider",
        PROVIDERS,
        index=PROVIDERS.index("BYBIT") if "BYBIT" in PROVIDERS else 0,
        key="provider_gateway_select",
    )

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

    # ── Provider assets (wallet) ─────────────────────────────────────
    st.subheader("Provider assets")
    _pa_pick, _pa_go = st.columns([3, 1])
    with _pa_pick:
        assets_provider = st.selectbox(
            "Provider",
            PROVIDERS,
            index=PROVIDERS.index(selected_provider) if selected_provider in PROVIDERS else 0,
            key="provider_assets_provider",
        )
    with _pa_go:
        fetch_assets = st.button("Fetch assets", key="provider_assets_fetch", use_container_width=True)

    if fetch_assets:
        try:
            st.session_state["provider_assets_result"] = api_client.get_provider_assets(provider=str(assets_provider))
            st.session_state.pop("provider_assets_error", None)
        except APIError as e:
            st.session_state["provider_assets_error"] = e.detail
            st.session_state.pop("provider_assets_result", None)
        except Exception as e:
            st.session_state["provider_assets_error"] = str(e)
            st.session_state.pop("provider_assets_result", None)

    _pa_err = st.session_state.get("provider_assets_error")
    if _pa_err:
        st.error(f"Assets request failed: {_pa_err}")

    _pa_res = st.session_state.get("provider_assets_result")
    if isinstance(_pa_res, dict):
        with st.container(border=True):
            st.markdown("**Response**")
            _sum = st.columns(4)
            with _sum[0]:
                st.metric("Provider", str(_pa_res.get("provider") or "—"))
            with _sum[1]:
                st.metric("Account type", str(_pa_res.get("account_type") or "—"))
            with _sum[2]:
                st.metric("Total equity", str(_pa_res.get("total_equity") or "—"))
            with _sum[3]:
                st.metric("Total wallet", str(_pa_res.get("total_wallet_balance") or "—"))
            _sum2 = st.columns(2)
            with _sum2[0]:
                st.metric("Available balance", str(_pa_res.get("total_available_balance") or "—"))

            _assets_list = _pa_res.get("assets")
            if isinstance(_assets_list, list) and _assets_list:
                st.markdown("**Balances by coin**")
                _rows = []
                for _a in _assets_list:
                    if not isinstance(_a, dict):
                        continue
                    _rows.append(
                        {
                            "Coin": _a.get("coin"),
                            "Wallet balance": _a.get("wallet_balance"),
                        }
                    )
                if _rows:
                    st.dataframe(_rows, use_container_width=True, hide_index=True)
                else:
                    st.caption("No asset rows to display.")
            else:
                st.caption("No `assets` array in response.")

            with st.expander("Full JSON", expanded=False):
                st.json(_pa_res)

    st.divider()

    # ── Provider positions ────────────────────────────────────────────
    st.subheader("Provider positions")
    _pp_row1 = st.columns([2, 1, 2, 1])
    with _pp_row1[0]:
        pp_provider = st.selectbox(
            "Provider",
            PROVIDERS,
            index=PROVIDERS.index(selected_provider) if selected_provider in PROVIDERS else 0,
            key="provider_positions_provider",
        )
    with _pp_row1[1]:
        pp_category = st.selectbox(
            "Category",
            PROVIDER_POSITION_CATEGORIES,
            index=0,
            key="provider_positions_category",
        )
    with _pp_row1[2]:
        pp_instrument = st.text_input(
            "Instrument",
            placeholder="Optional, e.g. BTCUSDT",
            key="provider_positions_instrument",
        )
    with _pp_row1[3]:
        fetch_positions = st.button("Fetch positions", key="provider_positions_fetch", use_container_width=True)

    if fetch_positions:
        try:
            _pp_sym = pp_instrument.strip() if pp_instrument else None
            st.session_state["provider_positions_result"] = api_client.get_provider_positions(
                provider=str(pp_provider),
                category=str(pp_category),
                symbol=_pp_sym,
            )
            st.session_state.pop("provider_positions_error", None)
        except APIError as e:
            st.session_state["provider_positions_error"] = e.detail
            st.session_state.pop("provider_positions_result", None)
        except Exception as e:
            st.session_state["provider_positions_error"] = str(e)
            st.session_state.pop("provider_positions_result", None)

    _pp_err = st.session_state.get("provider_positions_error")
    if _pp_err:
        st.error(f"Positions request failed: {_pp_err}")

    _pp_res = st.session_state.get("provider_positions_result")
    if isinstance(_pp_res, dict):
        with st.container(border=True):
            st.markdown("**Response**")
            _ppc = st.columns(2)
            with _ppc[0]:
                st.metric("Provider", str(_pp_res.get("provider") or "—"))
            with _ppc[1]:
                st.metric("Category", str(_pp_res.get("category") or "—"))

            _pos_list = _pp_res.get("positions")
            if isinstance(_pos_list, list) and _pos_list:
                st.markdown("**Open positions**")
                _prows = []
                for _p in _pos_list:
                    if not isinstance(_p, dict):
                        continue
                    _prows.append(
                        {
                            "Symbol": _p.get("symbol"),
                            "Side": _p.get("side"),
                            "Size": _p.get("size"),
                            "Avg price": _p.get("avg_price"),
                            "Unrealised PnL": _p.get("unrealised_pnl"),
                        }
                    )
                if _prows:
                    st.dataframe(_prows, use_container_width=True, hide_index=True)
                else:
                    st.caption("No position rows to display.")
            else:
                st.caption("No `positions` array in response.")

            with st.expander("Full JSON", expanded=False):
                st.json(_pp_res)

    with st.container(border=True):
        st.markdown("**Set leverage**")
        lev_cols = st.columns([2, 2, 2, 1])
        with lev_cols[0]:
            lev_provider = st.selectbox(
                "Provider",
                PROVIDERS,
                index=PROVIDERS.index(selected_provider) if selected_provider in PROVIDERS else 0,
                key="provider_leverage_provider",
            )
        with lev_cols[1]:
            lev_instrument = st.text_input(
                "Instrument",
                placeholder="e.g. BTCUSDT",
                key="provider_leverage_instrument",
            )
        with lev_cols[2]:
            lev_value = st.number_input(
                "Leverage",
                min_value=0.01,
                max_value=200.0,
                value=5.0,
                step=1.0,
                key="provider_leverage_value",
            )
        with lev_cols[3]:
            st.write("")
            do_set_leverage = st.button("Set", use_container_width=True, key="provider_leverage_set_btn")

        # Use the positions category when compatible (linear/inverse); otherwise fall back.
        lev_category_default = pp_category if str(pp_category) in ("linear", "inverse") else "inverse"
        lev_category = st.selectbox(
            "Category",
            ["linear", "inverse"],
            index=0 if lev_category_default == "linear" else 1,
            key="provider_leverage_category",
        )

        if do_set_leverage:
            if not lev_instrument or not lev_instrument.strip():
                st.error("Instrument is required.")
            else:
                try:
                    st.session_state["provider_leverage_result"] = api_client.set_provider_leverage(
                        provider=str(lev_provider),
                        instrument=str(lev_instrument),
                        leverage=float(lev_value),
                        category=str(lev_category),
                    )
                    st.session_state.pop("provider_leverage_error", None)
                except APIError as e:
                    st.session_state["provider_leverage_error"] = e.detail
                    st.session_state.pop("provider_leverage_result", None)
                except Exception as e:
                    st.session_state["provider_leverage_error"] = str(e)
                    st.session_state.pop("provider_leverage_result", None)

        _lev_err = st.session_state.get("provider_leverage_error")
        if _lev_err:
            st.error(f"Set leverage failed: {_lev_err}")
        _lev_res = st.session_state.get("provider_leverage_result")
        if isinstance(_lev_res, dict):
            st.success("Leverage updated.")
            with st.expander("Response JSON", expanded=False):
                st.json(_lev_res)

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
    st.markdown('<span id="tcp-rules-dialog-style-scope"></span>', unsafe_allow_html=True)
    st.markdown(
        """
        <style>
        /* Rules dialog only: top-right X same style as RULES button */
        div[data-testid="stDialog"]:has(#tcp-rules-dialog-style-scope) button[aria-label="Close"] {
            border: 1px solid rgba(58, 144, 184, 0.5) !important;
            background: linear-gradient(180deg, #2a3f4d 0%, #1a2835 100%) !important;
            color: #7eb8d4 !important;
            box-shadow: 0 0 6px rgba(58, 144, 184, 0.25) !important;
        }
        div[data-testid="stDialog"]:has(#tcp-rules-dialog-style-scope) button[aria-label="Close"]:hover {
            color: #9ecde8 !important;
            box-shadow: 0 0 10px rgba(58, 144, 184, 0.35) !important;
        }

        /* Rules dialog only: bottom Close same style as RULES button */
        div:has(#tcp-rules-dialog-close-marker) + div button {
            background: linear-gradient(180deg, #2a3f4d 0%, #1a2835 100%) !important;
            color: #7eb8d4 !important;
            border: 1px solid rgba(58, 144, 184, 0.5) !important;
            box-shadow: 0 0 6px rgba(58, 144, 184, 0.25) !important;
            font-weight: 700 !important;
            letter-spacing: 0.06em !important;
        }
        div:has(#tcp-rules-dialog-close-marker) + div button:hover {
            color: #9ecde8 !important;
            box-shadow: 0 0 10px rgba(58, 144, 184, 0.35) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
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
            (
                '<div class="info-rich-text" '
                'style="max-height:360px; overflow-y:auto; color:#9ecde8; '
                'background:#10202b; border:1px solid rgba(58, 144, 184, 0.5);">'
                f"{with_breaks}</div>"
            ),
            unsafe_allow_html=True,
        )
    else:
        st.write(rules)
    _close_left, _close_mid, _close_right = st.columns([4, 1, 4])
    with _close_mid:
        st.markdown('<span id="tcp-rules-dialog-close-marker"></span>', unsafe_allow_html=True)
        if st.button("Close", key="tcp_rules_dialog_close", use_container_width=False):
            st.rerun()


def _tcp_session_quality_scores(panel_data: object, session_detail: object) -> dict:
    """Resolve quality scores for the TCP session radar."""
    keys = ("bias_strength", "structure_quality", "pullback_quality", "breakout_quality", "volatility_fitness")
    panel = panel_data if isinstance(panel_data, dict) else {}
    nested = panel.get("session") if isinstance(panel.get("session"), dict) else {}
    sd = session_detail if isinstance(session_detail, dict) else {}
    out = {}
    for k in keys:
        v = panel.get(k)
        if v is None:
            v = nested.get(k)
        if v is None:
            v = sd.get(k)
        out[k] = v
    return out


def _build_alert_radar_figure(
    bias_strength: object,
    structure_quality: object,
    pullback_quality: object,
    breakout_quality: object,
    volatility_fitness: object,
):
    """Polar radar (0–100): structure, bias, breakout, volatility, pullback.

    Raw scores are 0–100; a value of 0 is drawn at a small radius (5) only for visibility,
    with a footnote on the figure. Numeric metrics elsewhere use true values.
    """
    import matplotlib

    try:
        matplotlib.use("Agg")
    except Exception:
        pass
    import matplotlib.pyplot as plt
    import numpy as np

    # Cool dark + fluorescent cyan accent (matches TCP session radar ring).
    _bg = "#1e2430"
    _bg_ax = "#252b38"
    _text = "#f7f9fc"
    _text_muted = "#d2dce8"
    _grid = "#4a5568"
    _accent = "#5cefff"
    _fill = "#4a8fd9"
    _line = "#7eb8ff"

    def _f(v: object) -> float:
        try:
            return max(0.0, min(100.0, float(v if v is not None else 0.0)))
        except (TypeError, ValueError):
            return 0.0

    # Display-only: map exact 0 → small radius so the polygon does not collapse to the center.
    _RADAR_DISPLAY_FLOOR = 5.0

    def _r_for_draw(score: float) -> float:
        return _RADAR_DISPLAY_FLOOR if score <= 0.0 else score

    # Clockwise from top: Structure, Bias, Breakout, Volatility, Pullback
    s = _f(structure_quality)
    b = _f(bias_strength)
    bo = _f(breakout_quality)
    v = _f(volatility_fitness)
    p = _f(pullback_quality)

    theta_core = np.linspace(0, 2 * np.pi, 5, endpoint=False)
    theta = np.concatenate([theta_core, [theta_core[0]]])
    r = np.array(
        [
            _r_for_draw(s),
            _r_for_draw(b),
            _r_for_draw(bo),
            _r_for_draw(v),
            _r_for_draw(p),
            _r_for_draw(s),
        ]
    )

    fig, ax = plt.subplots(figsize=(3.8, 3.8), subplot_kw=dict(projection="polar"))
    fig.patch.set_facecolor(_bg)
    ax.set_facecolor(_bg_ax)

    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_rlabel_position(22)
    ax.tick_params(axis="y", labelsize=7, colors=_text_muted)
    # Multiline labels + modest pad: stay outside the fill without shrinking the polar area too much.
    ax.tick_params(axis="x", colors=_text, labelsize=7, pad=14)
    ax.grid(True, color=_grid, linestyle="-", linewidth=0.7, alpha=0.85)

    ax.set_xticks(theta_core)
    ax.set_xticklabels(
        [
            "Structure\nQuality",
            "Bias\nStrength",
            "Breakout\nQuality",
            "Volatility\nFitness",
            "Pullback\nQuality",
        ],
        fontsize=7,
        color=_text,
    )

    ax.fill(theta, r, color=_fill, alpha=0.4, zorder=3)
    ax.plot(theta, r, color=_line, linewidth=1.8, zorder=4)

    spine = ax.spines.get("polar")
    if spine is not None:
        spine.set_edgecolor(_accent)
        spine.set_linewidth(1.0)

    ax.set_title(
        "Trading Session Radar Snapshot",
        fontsize=10,
        fontweight="bold",
        color=_text,
        pad=14,
    )

    fig.text(
        0.5,
        0.02,
        f"0 shown as minimum radius ({int(_RADAR_DISPLAY_FLOOR)}) for visibility — scores below are unchanged in metrics.",
        ha="center",
        va="bottom",
        fontsize=6,
        color=_text_muted,
        transform=fig.transFigure,
    )
    fig.tight_layout(rect=[0.0, 0.06, 1.0, 1.0])
    return fig


def _alert_radar_figure_to_png(fig: object, *, pad_inches: float = 0.2) -> bytes:
    """Encode figure to PNG bytes. Avoids st.pyplot + plt.close races in dialogs."""
    import matplotlib.pyplot as plt

    buf = io.BytesIO()
    _fc = fig.get_facecolor()
    fig.savefig(
        buf,
        format="png",
        dpi=100,
        bbox_inches="tight",
        facecolor=_fc,
        pad_inches=pad_inches,
    )
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


@st.dialog("Alert quality radar", width="large")
def _show_alert_radar_dialog() -> None:
    payload = st.session_state.get("_alert_radar_payload")
    if not isinstance(payload, dict):
        st.warning("No alert data.")
        return
    aid = payload.get("id", "—")
    st.caption(f"Alert **#{html.escape(str(aid))}** — scores 0–100 on each axis.")
    try:
        fig = _build_alert_radar_figure(
            payload.get("bias_strength"),
            payload.get("structure_quality"),
            payload.get("pullback_quality"),
            payload.get("breakout_quality"),
            payload.get("volatility_fitness"),
        )
        png = _alert_radar_figure_to_png(fig)
        _r1, _radar_mid, _r2 = st.columns([1, 2, 1])
        with _radar_mid:
            st.image(png, use_container_width=False, width=400)
    except Exception as e:
        st.error(f"Could not render radar chart: {e}")

    def _radar_metric_int(v: object) -> int:
        try:
            return int(round(float(v if v is not None else 0)))
        except (TypeError, ValueError):
            return 0

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        st.metric("Structure quality", _radar_metric_int(payload.get("structure_quality")))
    with q2:
        st.metric("Bias strength", _radar_metric_int(payload.get("bias_strength")))
    with q3:
        st.metric("Volatility fitness", _radar_metric_int(payload.get("volatility_fitness")))
    with q4:
        st.metric("Pullback quality", _radar_metric_int(payload.get("pullback_quality")))


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

    _guard_left, _guard_mid, _guard_right = st.columns([4, 1, 4])
    with _guard_mid:
        guard_clicked = st.button("Guard Me", key="ga_guard_me_btn", use_container_width=False)
    if guard_clicked:
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

    _knob_w = st.session_state.get("tcp_sess_knob_widget")
    if _knob_w is not None:
        try:
            knob_val = max(1, min(10, int(_knob_w)))
        except (TypeError, ValueError):
            knob_val = max(1, min(10, int(st.session_state.get("tcp_session_knob", 1))))
    else:
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
    last_fetch_label = "Updated · waiting for first fetch"
    if tcp_last_fetch_ts > 0:
        fetched_at = datetime.fromtimestamp(tcp_last_fetch_ts, tz=timezone.utc).strftime("%H:%M:%S UTC")
        seconds_ago = int(max(0.0, tcp_elapsed))
        last_fetch_label = f"Updated · {fetched_at} ({seconds_ago}s ago)"

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
    force_refresh_pending = bool(st.session_state.get("tcp_force_refresh", False))
    need_fetch = force_refresh_pending or knob_changed or (not panel_data) or (panel_session_id != int(session_id_tcp))

    led_class = "tcp-led-online" if backend_ok else "tcp-led-offline"
    led_pulse_class = "tcp-led-pulse" if need_fetch else ""
    status_class = "tcp-status-online" if backend_ok else "tcp-status-offline"
    status_text = "SYSTEM ONLINE" if backend_ok else "SYSTEM OFFLINE"
    freshness_class = "tcp-updated-line tcp-updated-line-refreshing" if need_fetch else "tcp-updated-line"
    freshness_text = "Refreshing data..." if need_fetch else last_fetch_label

    st.markdown(
        f"""
        <div class="tcp-top-bar">
            <div style="width: 140px;"></div>
            <div class="tcp-title">TRADING CONTROL PANEL</div>
            <div class="tcp-status">
                <div class="tcp-status-stack">
                    <span class="tcp-status-main">
                        <span class="tcp-led {led_class} {led_pulse_class}"></span>
                        <span class="tcp-status-text {status_class}">{status_text}</span>
                    </span>
                    <span class="{freshness_class}">{html.escape(freshness_text)}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    status_col, refresh_col = st.columns([20, 1])
    with refresh_col:
        if st.button("↻", key="tcp_refresh_now_btn", help="Refresh all trading panels now"):
            st.session_state["tcp_force_refresh"] = True
            st.rerun()

    with status_col:
        _tcp_auto_refresh_fragment()
    force_refresh = bool(st.session_state.pop("tcp_force_refresh", False))
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
    trade_mode_raw = session_data_tcp.get("trade_mode")
    if trade_mode_raw is None:
        trade_mode_raw = (panel_data or {}).get("trade_mode")
    if trade_mode_raw is None:
        trade_mode_raw = ((panel_data or {}).get("session") or {}).get("trade_mode")
    if isinstance(trade_mode_raw, bool):
        trade_mode_on = trade_mode_raw
    elif isinstance(trade_mode_raw, (int, float)):
        trade_mode_on = bool(trade_mode_raw)
    elif isinstance(trade_mode_raw, str):
        trade_mode_on = trade_mode_raw.strip().lower() in ("true", "1", "yes", "on")
    else:
        trade_mode_on = False
    trade_mode_text = "ON" if trade_mode_on else "OFF"
    trade_mode_color = "#22c55e" if trade_mode_on else "#9aa0a6"
    vol_status = _tcp_resolve_volatility_status(lv if isinstance(lv, dict) else {})
    vr = lv.get("vol_ratio") if isinstance(lv, dict) else None
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
    breakout_state_raw = session_data_tcp.get("breakout_state")
    if breakout_state_raw is None:
        breakout_state_raw = (panel_data or {}).get("breakout_state")
    if breakout_state_raw is None:
        breakout_state_raw = ((panel_data or {}).get("session") or {}).get("breakout_state")
    breakout_state = str(breakout_state_raw or "NONE").upper()
    breakout_dir_raw = session_data_tcp.get("breakout_setup_direction")
    if breakout_dir_raw is None:
        breakout_dir_raw = (panel_data or {}).get("breakout_setup_direction")
    if breakout_dir_raw is None:
        breakout_dir_raw = ((panel_data or {}).get("session") or {}).get("breakout_setup_direction")
    breakout_direction = str(breakout_dir_raw or "NONE").upper()
    if breakout_direction not in ("LONG", "SHORT", "NONE"):
        breakout_direction = "NONE"
    breakout_dir_color = "#22c55e" if breakout_direction == "LONG" else "#ef4444" if breakout_direction == "SHORT" else "#9aa0a6"
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
    elev_active = " tcp-vol-light-active" if vol_status == "ELEVATED" else ""
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
                        <div class="tcp-bias-arrow {bias_arrow_class}"></div>
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
                    <span class="tcp-vol-light tcp-vol-light-low{low_active}" title="LOW (vol_ratio &lt; 0.80)"></span>
                    <span class="tcp-vol-light tcp-vol-light-normal{norm_active}" title="NORMAL (0.80–1.00)"></span>
                    <span class="tcp-vol-light tcp-vol-light-elevated{elev_active}" title="ELEVATED (1.00–1.2)"></span>
                    <span class="tcp-vol-light tcp-vol-light-high{high_active}" title="HIGH (≥ 1.2)"></span>
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
                    '<div class="tcp-pb-gauge-wrap" style="align-items:center;">'
                    '<span class="tcp-pb-label tcp-pb-label-none">NONE</span></div></div>',
                    unsafe_allow_html=True,
                )
            else:
                pb_arrow_class = (
                    "tcp-pb-arrow-invalid"
                    if pb_state_upper == "INVALID"
                    else "tcp-pb-arrow-ready"
                    if pb_state_upper == "READY"
                    else "tcp-pb-arrow-forming"
                )
                pb_label_class = (
                    "tcp-pb-label-invalid"
                    if pb_state_upper == "INVALID"
                    else "tcp-pb-label-ready"
                    if pb_state_upper == "READY"
                    else "tcp-pb-label-forming"
                )
                st.markdown(
                    f"""
            <div class="tcp-panel">
                <div class="tcp-panel-label">PULLBACK STATUS</div>
                <div class="tcp-pb-gauge-wrap">
                    <div class="tcp-pb-gauge">
                        <div class="tcp-pb-arrow {pb_arrow_class}"></div>
                    </div>
                </div>
                <div class="tcp-pb-label {pb_label_class}">{pb_state_upper}</div>
            </div>
            """,
                    unsafe_allow_html=True,
                )
            sess_led = "tcp-session-led-active" if sess_status == "ACTIVE" else "tcp-session-led-paused" if sess_status == "PAUSED" else "tcp-session-led-completed" if sess_status == "COMPLETED" else "tcp-session-led-none"
            sess_txt = "tcp-session-status-active" if sess_status == "ACTIVE" else "tcp-session-status-paused" if sess_status == "PAUSED" else "tcp-session-status-completed" if sess_status == "COMPLETED" else "tcp-session-status-none"

            st.markdown(
                f"""
            <div class="tcp-panel tcp-panel-controls">
                <div class="tcp-panel-label">CONTROLS</div>
                <div style="height: 90px; display: flex; align-items: center; justify-content: center;">
                    <div class="tcp-session-status" style="flex-direction:column;gap:0.28rem;">
                        <div style="display:flex;align-items:center;gap:0.5rem;">
                        <span class="tcp-session-led {sess_led}"></span>
                        <span class="tcp-session-status-text {sess_txt}">SESSION: {sess_status if sess_status != "—" else "NO SESSION"}</span>
                        </div>
                        <div style="font-size:0.69rem;font-weight:700;letter-spacing:0.05em;color:{trade_mode_color};">
                            TRADE MODE: {trade_mode_text}
                        </div>
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    breakout_row_left, breakout_row_mid, breakout_row_right = st.columns([3, 2, 3])
    with breakout_row_mid:
        st.markdown(
            f"""
        <div class="tcp-panel">
            <div class="tcp-panel-label">BREAKOUT STATUS</div>
            <div style="height:90px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:0.35rem;">
                <div style="font-size:0.78rem;font-weight:700;letter-spacing:0.06em;color:#cfd8e3;">STATE: {breakout_state}</div>
                <div style="font-size:0.76rem;font-weight:700;letter-spacing:0.06em;color:{breakout_dir_color};">DIRECTION: {breakout_direction}</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.caption("Quick Controls")
        qc1, qc2, qc3, qc4 = st.columns(4)
        with qc1:
            # gap=None: default "small" gap stacks ~1rem between every child and blows past height=140 → scrollbar.
            with st.container(border=True, height=140, gap=None):
                st.markdown(
                    '<div class="tcp-quick-subpanel-label" style="margin:0 0 1.7rem 0;line-height:1.25;text-align:center;position:relative;z-index:1;">SESSION ID</div>'
                    '<span id="tcp-session-knob-marker" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                render_session_knob(knob_val, key="tcp_sess_knob_widget", height=48)
                st.markdown(
                    f'<div class="tcp-sess-knob-session-num" style="text-align:center;width:100%;display:block;box-sizing:border-box;">{knob_val}</div>',
                    unsafe_allow_html=True,
                )
        with qc2:
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
        with qc3:
            with st.container(border=True, height=140):
                st.markdown('<div class="tcp-quick-subpanel-label">AUTO REFRESH</div>', unsafe_allow_html=True)
                st.markdown(
                    '<div style="height:28px;"></div>',
                    unsafe_allow_html=True,
                )
                _ar_left, _ar_mid, _ar_right = st.columns([3, 2, 3])
                with _ar_mid:
                    auto_refresh_simple = st.toggle(
                        "Auto Refresh",
                        value=bool(auto_on),
                        key="tcp_auto_refresh_toggle",
                        label_visibility="collapsed",
                    )
                st.session_state["tcp_auto_refresh_enabled"] = bool(auto_refresh_simple)
        with qc4:
            with st.container(border=True, height=140):
                st.markdown('<div class="tcp-quick-subpanel-label">RULES</div>', unsafe_allow_html=True)
                st.markdown('<span id="tcp-rules-btn-marker"></span>', unsafe_allow_html=True)
                if st.button("RULES", key="tcp_rules_btn", use_container_width=True):
                    _show_trading_rules_dialog()

    with st.container(border=True):
        st.markdown(
            '<div class="tcp-quick-subpanel-label" style="margin-bottom:0.35rem;">SESSION RADAR</div>',
            unsafe_allow_html=True,
        )
        _sr_scores = _tcp_session_quality_scores(
            panel_data,
            st.session_state.get("tcp_session_detail"),
        )
        try:
            _sr_fig = _build_alert_radar_figure(
                _sr_scores.get("bias_strength"),
                _sr_scores.get("structure_quality"),
                _sr_scores.get("pullback_quality"),
                _sr_scores.get("breakout_quality"),
                _sr_scores.get("volatility_fitness"),
            )
            _sr_png = _alert_radar_figure_to_png(_sr_fig, pad_inches=0.42)
            _sr_b64 = base64.b64encode(_sr_png).decode("ascii")
            st.markdown(
                f'''<div style="display:flex;justify-content:center;width:100%;margin:0.15rem 0 0.35rem 0;">
<div style="box-sizing:border-box;width:400px;height:400px;border-radius:50%;overflow:hidden;background:#1e2430;
box-shadow:0 0 0 0.5px #5cefff,0 0 8px rgba(92,239,255,0.22),0 0 1px rgba(180,250,255,0.4);
flex-shrink:0;display:flex;align-items:center;justify-content:center;">
<img src="data:image/png;base64,{_sr_b64}" alt="Session radar"
style="max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;object-position:center;display:block;" />
</div></div>''',
                unsafe_allow_html=True,
            )
        except Exception:
            st.caption("Session radar could not be drawn. Load a valid session or refresh the panel.")

    guardian_left, guardian_mid, guardian_right = st.columns([4, 2, 4])
    with guardian_mid:
        st.markdown(
            '<span id="tcp-guardian-btn-marker" style="display:block;height:0;margin:0;padding:0;line-height:0;overflow:hidden;width:0" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        if st.button(
            "👼 AI Guardian Angel",
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
