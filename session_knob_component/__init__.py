import os

import streamlit.components.v1 as components

_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

session_knob = components.declare_component("tcp_session_knob_v1", path=_FRONTEND)


def render_session_knob(session: int, *, key: str, height: int = 48):
    """Session 1–10 rotary knob; drag to change. Updates Streamlit on pointer release only."""
    session = max(1, min(10, int(session)))
    return session_knob(session=session, key=key, default=session, height=height)
