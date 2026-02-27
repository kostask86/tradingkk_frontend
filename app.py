import streamlit as st
import api_client
from api_client import APIError
from datetime import datetime, timezone

TIMEFRAMES = ["1m", "15m", "30m", "1h", "4h"]
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
    </style>
    """,
    unsafe_allow_html=True,
)


def _fmt_dt(val: str | None) -> str:
    if not val:
        return "—"
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
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
    page = st.radio("Navigation", ["Sessions", "IBKR"], index=0, label_visibility="collapsed")


# ── Sessions page ─────────────────────────────────────────────────────

def sessions_page():
    st.header("Sessions")
    sessions_tab, bias_tab = st.tabs(["Sessions", "Bias Calculations"])

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
                    labels = [f"#{s['id']} {s['symbol']} ({s['status']})" for s in clock_candidates]
                    selected_label = st.selectbox("Session", labels, key="session_clock_select")
                    selected = clock_candidates[labels.index(selected_label)]
                    sid = selected["id"]
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
            if st.button("Get All", use_container_width=True, key="bc_get_all"):
                try:
                    st.session_state["bias_calculations_list"] = api_client.list_bias_calculations(
                        session_id=int(bc_session_id),
                        limit=int(bc_limit),
                        offset=int(bc_offset),
                    )
                    st.success("Loaded bias calculations.")
                except APIError as e:
                    st.error(f"Failed to list bias calculations: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

        action_cols = st.columns(2)
        with action_cols[0]:
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

        with action_cols[1]:
            delete_id = st.number_input(
                "Bias Calculation ID (Delete One)", min_value=1, value=1, step=1, key="bc_delete_id"
            )
            if st.button("Delete One", use_container_width=True, key="bc_delete_one", type="primary"):
                try:
                    api_client.delete_bias_calculation(int(delete_id))
                    st.success(f"Deleted bias calculation #{int(delete_id)}")
                    st.session_state.pop("bias_calculation_detail", None)
                    if "bias_calculations_list" in st.session_state:
                        st.session_state["bias_calculations_list"] = [
                            row
                            for row in st.session_state["bias_calculations_list"]
                            if int(row.get("id", -1)) != int(delete_id)
                        ]
                except APIError as e:
                    st.error(f"Failed to delete bias calculation: {e.detail}")
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
                    for col in ["ma_bar_bias", "ma_persistent_bias", "structure_bias", "candidate_bias", "state_bias"]
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
            bias_cols = st.columns(4)
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
                    f"**Candidate Bias**<br>{_bias_colored_html(detail.get('candidate_bias', 'NEUTRAL'))}",
                    unsafe_allow_html=True,
                )
            st.json(detail)

    # ── Create session form ───────────────────────────────────────────
    with st.expander("➕ Create new session", expanded=False):
        with st.form("create_session_form"):
            col1, col2 = st.columns(2)
            with col1:
                symbol = st.text_input("Symbol", placeholder="e.g. AAPL, EURUSD")
                timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=0)
            with col2:
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
                            timeframe=timeframe,
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
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "ACTIVE", "PAUSED", "COMPLETED"],
            index=0,
        )
    with filter_col2:
        symbol_filter = st.text_input("Filter by symbol", placeholder="Leave blank for all")

    # ── Fetch sessions ────────────────────────────────────────────────
    try:
        sessions = api_client.list_sessions(
            status=status_filter if status_filter != "All" else None,
            symbol=symbol_filter.strip().upper() if symbol_filter.strip() else None,
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
                st.metric("Timeframe", sess["timeframe"])
            with detail_cols[1]:
                state_bias = sess.get("state_bias", sess.get("current_bias", "NEUTRAL"))
                st.markdown(f"**State Bias**<br>{_bias_colored_html(state_bias)}", unsafe_allow_html=True)
            with detail_cols[2]:
                st.markdown(
                    f"**Candidate Bias**<br>{_bias_colored_html(sess.get('candidate_bias', 'NEUTRAL'))}",
                    unsafe_allow_html=True,
                )
            with detail_cols[3]:
                st.metric("Consec. Count", sess["consecutive_count"])
            with detail_cols[4]:
                st.metric("Hysteresis K", sess["hysteresis_k"])

            param_cols = st.columns(4)
            with param_cols[0]:
                st.caption(f"Persist. Window: **{sess['persistence_window']}**")
            with param_cols[1]:
                st.caption(f"Persist. Threshold: **{sess['persistence_threshold']}**")
            with param_cols[2]:
                st.caption(f"Started: **{_fmt_dt(sess.get('started_at'))}**")
            with param_cols[3]:
                st.caption(f"Ended: **{_fmt_dt(sess.get('ended_at'))}**")

            # ── Action buttons ────────────────────────────────────────
            btn_cols = st.columns(5)

            with btn_cols[0]:
                if status != "ACTIVE":
                    if st.button("▶ Start", key=f"start_{sid}", use_container_width=True):
                        try:
                            api_client.start_session(sid)
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


# ── IBKR page ─────────────────────────────────────────────────────────

SEC_TYPES = ["STK", "FOREX"]

def ibkr_page():
    st.header("IBKR Gateway")

    # ── Connection controls ───────────────────────────────────────────
    st.subheader("Connection")
    conn_cols = st.columns(3)

    with conn_cols[0]:
        if st.button("Connect", use_container_width=True):
            try:
                result = api_client.ibkr_connect()
                st.success(f"Connected: {result}")
            except APIError as e:
                st.error(f"Connect failed: {e.detail}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    with conn_cols[1]:
        if st.button("Disconnect", use_container_width=True):
            try:
                result = api_client.ibkr_disconnect()
                st.success(f"Disconnected: {result}")
            except APIError as e:
                st.error(f"Disconnect failed: {e.detail}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    with conn_cols[2]:
        if st.button("Check Status", use_container_width=True):
            try:
                status = api_client.ibkr_status()
                st.session_state["ibkr_status"] = status
            except APIError as e:
                st.error(f"Status check failed: {e.detail}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    if "ibkr_status" in st.session_state:
        with st.container(border=True):
            st.markdown("**Gateway Status**")
            st.json(st.session_state["ibkr_status"])

    st.divider()

    # ── Test Bar ──────────────────────────────────────────────────────
    st.subheader("Test Bars")

    with st.form("test_bar_form"):
        tb_cols = st.columns(4)
        with tb_cols[0]:
            tb_symbol = st.text_input("Symbol", placeholder="e.g. AAPL or EURUSD")
        with tb_cols[1]:
            tb_timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=0)
        with tb_cols[2]:
            tb_sec_type = st.selectbox("Security Type", SEC_TYPES, index=0)
        with tb_cols[3]:
            tb_num_bars = st.number_input("Num Bars", min_value=5, max_value=200, value=20, step=5)

        tb_submitted = st.form_submit_button("Fetch Test Bar", use_container_width=True)
        if tb_submitted:
            if not tb_symbol or not tb_symbol.strip():
                st.error("Symbol is required.")
            else:
                try:
                    bar_data = api_client.ibkr_test_bar(
                        symbol=tb_symbol,
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

            indexed_bars = [{"bar_index": idx, **bar} for idx, bar in enumerate(bars)]
            display_cols = [
                c
                for c in ["bar_index", "date", "open", "high", "low", "close", "sma9", "sma20", "volume", "vwap"]
                if c in indexed_bars[0]
            ]
            st.dataframe(indexed_bars, column_order=display_cols, use_container_width=True, hide_index=True)

            # Basic candlestick chart with optional SMA overlays.
            df = pd.DataFrame(indexed_bars)
            if {"date", "open", "high", "low", "close"}.issubset(df.columns):
                for col in ["open", "high", "low", "close", "sma9", "sma20"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                chart_df = df.dropna(subset=["date", "open", "high", "low", "close"]).copy()

                if not chart_df.empty:
                    st.caption("Legend: Green = Up candle | Red = Down candle | Blue = SMA9 | Orange = SMA20")

                    chart_df["candle_low"] = chart_df[["open", "close"]].min(axis=1)
                    chart_df["candle_high"] = chart_df[["open", "close"]].max(axis=1)
                    chart_df["candle_color"] = chart_df.apply(
                        lambda row: "#2ca02c" if row["close"] >= row["open"] else "#d62728", axis=1
                    )

                    price_scale = alt.Scale(zero=False)

                    wick = alt.Chart(chart_df).mark_rule().encode(
                        x=alt.X("date:T", title="Time"),
                        y=alt.Y("low:Q", title="Price", scale=price_scale),
                        y2="high:Q",
                        color=alt.value("#9aa0a6"),
                    )

                    candle = alt.Chart(chart_df).mark_bar(size=8).encode(
                        x=alt.X("date:T"),
                        y=alt.Y("candle_low:Q", scale=price_scale),
                        y2="candle_high:Q",
                        color=alt.Color("candle_color:N", scale=None, legend=None),
                    )

                    chart = wick + candle

                    if "sma9" in chart_df.columns and chart_df["sma9"].notna().any():
                        sma9_line = alt.Chart(chart_df).mark_line(color="#1f77b4", strokeWidth=2).encode(
                            x="date:T",
                            y=alt.Y("sma9:Q", scale=price_scale),
                        )
                        chart = chart + sma9_line

                    if "sma20" in chart_df.columns and chart_df["sma20"].notna().any():
                        sma20_line = alt.Chart(chart_df).mark_line(color="#ff7f0e", strokeWidth=2).encode(
                            x="date:T",
                            y=alt.Y("sma20:Q", scale=price_scale),
                        )
                        chart = chart + sma20_line

                    st.altair_chart(chart.properties(height=380), use_container_width=True)
                else:
                    st.info("Bars returned, but date/price values are not chartable.")

    st.divider()

    # ── Detect Swings ─────────────────────────────────────────────────
    st.subheader("Detect Swings")

    with st.form("detect_swings_form"):
        sw_cols = st.columns(4)
        with sw_cols[0]:
            sw_symbol = st.text_input("Symbol", placeholder="e.g. AAPL or EURUSD", key="sw_symbol")
        with sw_cols[1]:
            sw_timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=0, key="sw_tf")
        with sw_cols[2]:
            sw_sec_type = st.selectbox("Security Type", SEC_TYPES, index=0, key="sw_sec")
        with sw_cols[3]:
            sw_lookback = st.number_input("Lookback", min_value=1, max_value=10, value=2, step=1, key="sw_lb")

        sw_submitted = st.form_submit_button("Detect Swings", use_container_width=True)
        if sw_submitted:
            if not sw_symbol or not sw_symbol.strip():
                st.error("Symbol is required.")
            else:
                try:
                    swing_data = api_client.detect_swings(
                        symbol=sw_symbol,
                        timeframe=sw_timeframe,
                        sec_type=sw_sec_type,
                        lookback=int(sw_lookback),
                    )
                    st.session_state["swing_result"] = swing_data
                    try:
                        chart_bars = int(swing_data.get("total_bars", 20))
                        chart_bars = max(1, min(200, chart_bars))
                        swing_bars_data = api_client.ibkr_test_bar(
                            symbol=sw_symbol,
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

                        wick = alt.Chart(chart_df).mark_rule().encode(
                            x=alt.X("date:T", title="Time"),
                            y=alt.Y("low:Q", title="Price", scale=price_scale),
                            y2="high:Q",
                            color=alt.value("#9aa0a6"),
                        )

                        candle = alt.Chart(chart_df).mark_bar(size=8).encode(
                            x=alt.X("date:T"),
                            y=alt.Y("candle_low:Q", scale=price_scale),
                            y2="candle_high:Q",
                            color=alt.Color("candle_color:N", scale=None, legend=None),
                        )

                        chart = wick + candle

                        if "sma9" in chart_df.columns and chart_df["sma9"].notna().any():
                            chart = chart + alt.Chart(chart_df).mark_line(color="#1f77b4", strokeWidth=2).encode(
                                x="date:T",
                                y=alt.Y("sma9:Q", scale=price_scale),
                            )
                        if "sma20" in chart_df.columns and chart_df["sma20"].notna().any():
                            chart = chart + alt.Chart(chart_df).mark_line(color="#ff7f0e", strokeWidth=2).encode(
                                x="date:T",
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
                                    x="date:T",
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
        cb_cols = st.columns(6)
        with cb_cols[0]:
            cb_symbol = st.text_input("Symbol", placeholder="e.g. AAPL or EURUSD", key="cb_symbol")
        with cb_cols[1]:
            cb_timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=0, key="cb_tf")
        with cb_cols[2]:
            cb_sec_type = st.selectbox("Security Type", SEC_TYPES, index=0, key="cb_sec")
        with cb_cols[3]:
            cb_lookback = st.number_input("Lookback", min_value=1, max_value=10, value=2, step=1, key="cb_lb")
        with cb_cols[4]:
            cb_pw = st.number_input(
                "Persistence Window", min_value=5, max_value=200, value=20, step=1, key="cb_pw"
            )
        with cb_cols[5]:
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

                        wick = alt.Chart(chart_df).mark_rule().encode(
                            x=alt.X("date:T", title="Time"),
                            y=alt.Y("low:Q", title="Price", scale=price_scale),
                            y2="high:Q",
                            color=alt.value("#9aa0a6"),
                        )

                        candle = alt.Chart(chart_df).mark_bar(size=8).encode(
                            x=alt.X("date:T"),
                            y=alt.Y("candle_low:Q", scale=price_scale),
                            y2="candle_high:Q",
                            color=alt.Color("candle_color:N", scale=None, legend=None),
                        )

                        chart = wick + candle

                        if "sma9" in chart_df.columns and chart_df["sma9"].notna().any():
                            chart = chart + alt.Chart(chart_df).mark_line(color="#1f77b4", strokeWidth=2).encode(
                                x="date:T",
                                y=alt.Y("sma9:Q", scale=price_scale),
                            )
                        if "sma20" in chart_df.columns and chart_df["sma20"].notna().any():
                            chart = chart + alt.Chart(chart_df).mark_line(color="#ff7f0e", strokeWidth=2).encode(
                                x="date:T",
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
                                    x="date:T",
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
elif page == "IBKR":
    ibkr_page()
