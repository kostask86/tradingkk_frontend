import requests
from typing import Optional

BASE_URL = "http://localhost:8000"


class APIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


def _handle_response(resp: requests.Response, expected_status: int = 200):
    if resp.status_code == expected_status:
        if expected_status == 204:
            return None
        return resp.json()
    try:
        body = resp.json()
        detail = body.get("detail", str(body))
    except Exception:
        detail = resp.text
    raise APIError(resp.status_code, str(detail))


# ── Sessions ─────────────────────────────────────────────────────────

def create_session(
    symbol: str,
    provider: str = "IBKR",
    timeframe: str = "1m",
    sec_type: str = "STK",
    hysteresis_k: int = 2,
    persistence_window: int = 20,
    persistence_threshold: int = 15,
    swing_lookback: int = 2,
) -> dict:
    payload = {
        "symbol": symbol.upper().strip(),
        "provider": provider,
        "timeframe": timeframe,
        "sec_type": sec_type,
        "hysteresis_k": hysteresis_k,
        "persistence_window": persistence_window,
        "persistence_threshold": persistence_threshold,
        "swing_lookback": swing_lookback,
    }
    resp = requests.post(f"{BASE_URL}/api/sessions/", json=payload)
    return _handle_response(resp, 201)


def list_sessions(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    provider: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    params: dict = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status
    if symbol:
        params["symbol"] = symbol
    if provider:
        params["provider"] = provider
    resp = requests.get(f"{BASE_URL}/api/sessions/", params=params)
    return _handle_response(resp)


def get_session(session_id: int) -> dict:
    resp = requests.get(f"{BASE_URL}/api/sessions/detail", params={"session_id": session_id})
    return _handle_response(resp)


def update_session(session_id: int, **fields) -> dict:
    payload = {k: v for k, v in fields.items() if v is not None}
    resp = requests.patch(f"{BASE_URL}/api/sessions/", params={"session_id": session_id}, json=payload)
    return _handle_response(resp)


def start_session(session_id: int, sec_type: Optional[str] = None) -> dict:
    params: dict = {"session_id": session_id}
    if sec_type:
        params["sec_type"] = sec_type
    resp = requests.post(f"{BASE_URL}/api/sessions/start", params=params)
    return _handle_response(resp)


def pause_session(session_id: int) -> dict:
    resp = requests.post(f"{BASE_URL}/api/sessions/pause", params={"session_id": session_id})
    return _handle_response(resp)


def end_session(session_id: int) -> dict:
    resp = requests.post(f"{BASE_URL}/api/sessions/end", params={"session_id": session_id})
    return _handle_response(resp)


def visualize_session(session_id: int, num_bars: int = 200) -> dict:
    resp = requests.get(
        f"{BASE_URL}/api/sessions/visualize",
        params={"session_id": session_id, "num_bars": num_bars},
    )
    return _handle_response(resp)


def get_alert_performance(session_id: int) -> dict:
    resp = requests.get(
        f"{BASE_URL}/api/sessions/alert_performance",
        params={"session_id": session_id},
    )
    return _handle_response(resp)


def get_session_metadata() -> dict:
    resp = requests.get(f"{BASE_URL}/api/sessions/metadata")
    return _handle_response(resp)


def delete_session(session_id: int) -> None:
    resp = requests.delete(f"{BASE_URL}/api/sessions/", params={"session_id": session_id})
    return _handle_response(resp, 204)


# ── Bias Calculations ────────────────────────────────────────────────

def get_bias_calculation(bias_calculation_id: int) -> dict:
    resp = requests.get(
        f"{BASE_URL}/api/bias-calculations/detail",
        params={"bias_calculation_id": bias_calculation_id},
    )
    return _handle_response(resp)


def list_bias_calculations(session_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/api/bias-calculations/",
        params={"session_id": session_id, "limit": limit, "offset": offset},
    )
    return _handle_response(resp)


def delete_bias_calculation(bias_calculation_id: int) -> None:
    resp = requests.delete(
        f"{BASE_URL}/api/bias-calculations/",
        params={"bias_calculation_id": bias_calculation_id},
    )
    return _handle_response(resp, 204)


# ── Pullback Calculations ────────────────────────────────────────────

def get_pullback_calculation(pullback_calculation_id: int) -> dict:
    resp = requests.get(
        f"{BASE_URL}/api/pullback-calculations/detail",
        params={"pullback_calculation_id": pullback_calculation_id},
    )
    return _handle_response(resp)


def list_pullback_calculations(session_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/api/pullback-calculations/",
        params={"session_id": session_id, "limit": limit, "offset": offset},
    )
    return _handle_response(resp)


# ── Alerts ───────────────────────────────────────────────────────────

def create_alert(
    session_id: int,
    direction: str,
    entry_signal_price: float,
    stop_price: float,
    target_price: Optional[float] = None,
    reason: Optional[str] = None,
    status: str = "OPEN",
) -> dict:
    payload = {
        "session_id": session_id,
        "direction": direction,
        "entry_signal_price": entry_signal_price,
        "stop_price": stop_price,
        "target_price": target_price,
        "reason": reason,
        "status": status,
    }
    resp = requests.post(f"{BASE_URL}/api/alerts/", json=payload)
    return _handle_response(resp, 201)


def list_alerts(
    session_id: Optional[int] = None,
    outcome_status: Optional[str] = None,
    direction: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    params: dict = {"limit": limit, "offset": offset}
    if session_id is not None:
        params["session_id"] = session_id
    if outcome_status:
        params["outcome_status"] = outcome_status
    if direction:
        params["direction"] = direction
    if type:
        params["type"] = type
    resp = requests.get(f"{BASE_URL}/api/alerts/", params=params)
    return _handle_response(resp)


def get_alert(alert_id: int) -> dict:
    resp = requests.get(f"{BASE_URL}/api/alerts/detail", params={"alert_id": alert_id})
    return _handle_response(resp)


def delete_alert(alert_id: int) -> None:
    resp = requests.delete(f"{BASE_URL}/api/alerts/", params={"alert_id": alert_id})
    return _handle_response(resp, 204)


def cancel_session_alerts(session_id: int) -> dict:
    resp = requests.post(
        f"{BASE_URL}/api/sessions/cancel-alerts",
        params={"session_id": session_id},
    )
    return _handle_response(resp)


# ── Provider ──────────────────────────────────────────────────────────

def provider_connect(provider: str = "IBKR") -> dict:
    resp = requests.post(f"{BASE_URL}/api/provider/connect", params={"provider": provider})
    return _handle_response(resp)


def provider_disconnect(provider: str = "IBKR") -> dict:
    resp = requests.post(f"{BASE_URL}/api/provider/disconnect", params={"provider": provider})
    return _handle_response(resp)


def provider_status(provider: str = "IBKR") -> dict:
    resp = requests.get(f"{BASE_URL}/api/provider/status", params={"provider": provider})
    return _handle_response(resp)


def get_test_bars(
    symbol: str,
    provider: str = "IBKR",
    timeframe: str = "1m",
    sec_type: str = "STK",
    num_bars: int = 20,
) -> dict:
    params = {
        "symbol": symbol.upper().strip(),
        "provider": provider,
        "timeframe": timeframe,
        "sec_type": sec_type,
        "num_bars": num_bars,
    }
    resp = requests.get(f"{BASE_URL}/api/scalp/test-bars", params=params)
    return _handle_response(resp)


# ── Scalp ─────────────────────────────────────────────────────────────

def detect_swings(
    symbol: str,
    provider: str = "IBKR",
    timeframe: str = "1m",
    sec_type: str = "STK",
    lookback: int = 2,
) -> dict:
    params = {
        "symbol": symbol.upper().strip(),
        "provider": provider,
        "timeframe": timeframe,
        "sec_type": sec_type,
        "lookback": lookback,
    }
    resp = requests.get(f"{BASE_URL}/api/scalp/detect-swings", params=params)
    return _handle_response(resp)


def calculate_candidate_bias(
    symbol: str,
    provider: str = "IBKR",
    timeframe: str = "1m",
    sec_type: str = "STK",
    lookback: int = 2,
    persistence_window: int = 20,
    persistence_threshold: int = 15,
) -> dict:
    params = {
        "symbol": symbol.upper().strip(),
        "provider": provider,
        "timeframe": timeframe,
        "sec_type": sec_type,
        "lookback": lookback,
        "persistence_window": persistence_window,
        "persistence_threshold": persistence_threshold,
    }
    resp = requests.get(f"{BASE_URL}/api/scalp/calculate-candidate-bias", params=params)
    return _handle_response(resp)


# ── Health ────────────────────────────────────────────────────────────

def health_check() -> dict:
    resp = requests.get(f"{BASE_URL}/health")
    return _handle_response(resp)
