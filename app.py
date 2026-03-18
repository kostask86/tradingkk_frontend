import streamlit as st
import api_client
from api_client import APIError
from datetime import datetime, timezone

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

st.set_page_config(page_title="Tradingkk", page_icon="📈", layout="wide")

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


def _bias_colored_html(value: str | None) -> str:
    bias = (value or "NEUTRAL").upper()
    color_map = {
        "BULLISH": "#2ca02c",
        "BEARISH": "#d62728",
        "NEUTRAL": "#9aa0a6",
    }
    color = color_map.get(bias, "#9aa0a6")
    return f"<span style='color: {color}; font-weight: 700;'>{bias}</span>"


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


# ── Sidebar ───────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📈 Tradingkk")
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
    page = st.radio("Navigation", ["Sessions", "Provider"], index=0, label_visibility="collapsed")


# ── Sessions page ─────────────────────────────────────────────────────

def sessions_page():
    st.header("Sessions")
    sessions_tab, bias_tab, pullback_tab, visualize_tab, alerts_tab = st.tabs(
        ["Sessions", "Bias Calculations", "Pullback Calculations", "Visualize", "Alerts"]
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

    with visualize_tab:
        st.subheader("Visualize Session")

        with st.container(border=True):
            with st.form("visualize_session_form"):
                viz_cols = st.columns(2)
                with viz_cols[0]:
                    viz_session_id = st.number_input("Session ID", min_value=1, value=1, step=1, key="viz_session_id")
                with viz_cols[1]:
                    viz_num_bars = st.number_input("Num Bars", min_value=20, max_value=1000, value=200, step=20, key="viz_num_bars")

                if st.form_submit_button("Run Visualize", use_container_width=True):
                    try:
                        viz_result = api_client.visualize_session(int(viz_session_id), int(viz_num_bars))
                        st.session_state["session_visualization_result"] = viz_result
                    except APIError as e:
                        st.error(f"Visualize failed: {e.detail}")
                    except Exception as e:
                        st.error(f"Connection error: {e}")

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
            list_cols = st.columns(6)
            with list_cols[0]:
                al_session_id_filter = st.text_input(
                    "Session ID (optional)",
                    value="",
                    placeholder="e.g. 12",
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
                al_limit = st.number_input("Limit", min_value=1, max_value=1000, value=100, step=10, key="al_list_limit")
            with list_cols[5]:
                al_offset = st.number_input("Offset", min_value=0, value=0, step=10, key="al_list_offset")

            if st.button("Get Alerts", use_container_width=True, key="al_get_list"):
                try:
                    session_id_filter = None
                    if al_session_id_filter and al_session_id_filter.strip():
                        session_id_filter = int(al_session_id_filter.strip())
                    alerts = api_client.list_alerts(
                        session_id=session_id_filter,
                        outcome_status=al_status_filter if al_status_filter != "All" else None,
                        direction=al_direction_filter if al_direction_filter != "All" else None,
                        type=al_type_filter if al_type_filter != "All" else None,
                        limit=int(al_limit),
                        offset=int(al_offset),
                    )
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
                detail_cols = st.columns(5)
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

                md_cols_2 = st.columns(3)
                with md_cols_2[0]:
                    st.metric("strong_close_max_wick_ratio", metadata.get("strong_close_max_wick_ratio", "—"))
                with md_cols_2[1]:
                    st.metric("persistence_threshold", metadata.get("persistence_threshold", "—"))
                with md_cols_2[2]:
                    st.metric("strength_threshold", metadata.get("strength_threshold", "—"))
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
                    persistence_threshold = st.number_input("Persistence Threshold", min_value=1, value=15, step=1)
                with bottom_col2:
                    swing_lookback = st.number_input("Swing Lookback", min_value=1, value=2, step=1)

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
                            )
                            st.success(f"Session **#{new_session['id']}** created for **{new_session['symbol']}**")
                            st.rerun()
                        except APIError as e:
                            st.error(f"Failed to create session: {e.detail}")
                        except Exception as e:
                            st.error(f"Connection error: {e}")

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

            param_cols = st.columns(4)
            with param_cols[0]:
                st.caption(f"Persist. Window: **{sess['persistence_window']}**")
            with param_cols[1]:
                st.caption(f"Persist. Threshold: **{sess['persistence_threshold']}**")
            with param_cols[2]:
                st.caption(f"Started: **{_fmt_dt(sess.get('started_at'))}**")
            with param_cols[3]:
                st.caption(f"Ended: **{_fmt_dt(sess.get('ended_at'))}**")

            pullback_cols = st.columns(4)
            with pullback_cols[0]:
                st.caption(f"Swing Lookback: **{sess.get('swing_lookback', '—')}**")
            with pullback_cols[1]:
                st.caption(f"Pullback State: **{sess.get('pullback_state', 'NONE')}**")
            with pullback_cols[2]:
                st.caption(f"Pullback Direction: **{sess.get('pullback_direction', 'NONE')}**")
            with pullback_cols[3]:
                touched = "Yes" if sess.get("touched_sma20") else "No"
                st.caption(f"Touched SMA20: **{touched}**")

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


# ── Router ────────────────────────────────────────────────────────────

if page == "Sessions":
    sessions_page()
elif page == "Provider":
    provider_page()

_system_clock_widget()
