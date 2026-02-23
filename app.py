import streamlit as st
import api_client
from api_client import APIError
from datetime import datetime

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
            persistence_threshold = st.number_input("Persistence Threshold", min_value=1, value=15, step=1)

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

            detail_cols = st.columns(4)
            with detail_cols[0]:
                st.metric("Timeframe", sess["timeframe"])
            with detail_cols[1]:
                st.metric("Bias", sess["current_bias"])
            with detail_cols[2]:
                st.metric("Consec. Count", sess["consecutive_count"])
            with detail_cols[3]:
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
                            st.rerun()
                        except APIError as e:
                            st.error(e.detail)

            with btn_cols[1]:
                if status == "ACTIVE":
                    if st.button("⏸ Pause", key=f"pause_{sid}", use_container_width=True):
                        try:
                            api_client.pause_session(sid)
                            st.rerun()
                        except APIError as e:
                            st.error(e.detail)

            with btn_cols[2]:
                if status in ("ACTIVE", "PAUSED"):
                    if st.button("⏹ End", key=f"end_{sid}", use_container_width=True):
                        try:
                            api_client.end_session(sid)
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
    st.subheader("Test Bar")

    with st.form("test_bar_form"):
        tb_cols = st.columns(3)
        with tb_cols[0]:
            tb_symbol = st.text_input("Symbol", placeholder="e.g. AAPL or EURUSD")
        with tb_cols[1]:
            tb_timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=0)
        with tb_cols[2]:
            tb_sec_type = st.selectbox("Security Type", SEC_TYPES, index=0)

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
                    )
                    st.session_state["test_bar_result"] = bar_data
                except APIError as e:
                    st.error(f"Test bar failed: {e.detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    if "test_bar_result" in st.session_state:
        bar = st.session_state["test_bar_result"]
        with st.container(border=True):
            st.markdown(f"**{bar.get('symbol', '')}** — {bar.get('timeframe', '')} — {bar.get('date', '')}")

            price_cols = st.columns(4)
            with price_cols[0]:
                st.metric("Open", bar.get("open"))
            with price_cols[1]:
                st.metric("High", bar.get("high"))
            with price_cols[2]:
                st.metric("Low", bar.get("low"))
            with price_cols[3]:
                st.metric("Close", bar.get("close"))

            vol_cols = st.columns(2)
            with vol_cols[0]:
                st.metric("Volume", f"{bar.get('volume', 0):,}")
            with vol_cols[1]:
                st.metric("VWAP", bar.get("vwap"))


# ── Router ────────────────────────────────────────────────────────────

if page == "Sessions":
    sessions_page()
elif page == "IBKR":
    ibkr_page()
