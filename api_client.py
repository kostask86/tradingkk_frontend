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
    cooldown_until: int = 5,
    trade_mode: bool = False,
    trade_auto_prealert: bool = False,
    trade_auto_trigger: bool = False,
    trade_auto_trend_strength: bool = False,
    trade_take_profit_pct: float = 0.4,
    trade_stop_loss_pct: float = 0.3,
    tp_percentage: Optional[float] = None,
    sl_percentage: Optional[float] = None,
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
        "cooldown_until": cooldown_until,
        "trade_mode": bool(trade_mode),
        "trade_auto_prealert": bool(trade_auto_prealert),
        "trade_auto_trigger": bool(trade_auto_trigger),
        "trade_auto_trend_strength": bool(trade_auto_trend_strength),
        "trade_take_profit_pct": float(trade_take_profit_pct),
        "trade_stop_loss_pct": float(trade_stop_loss_pct),
    }
    if tp_percentage is not None:
        payload["tp_percentage"] = float(tp_percentage)
    if sl_percentage is not None:
        payload["sl_percentage"] = float(sl_percentage)
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


def get_trading_control_panel(session_id: int) -> dict:
    resp = requests.get(
        f"{BASE_URL}/api/sessions/tradingcontrolpanel",
        params={"session_id": session_id},
    )
    return _handle_response(resp)


def get_session_metadata(session_id: int) -> dict:
    resp = requests.get(
        f"{BASE_URL}/api/sessions/metadata",
        params={"session_id": session_id},
    )
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


# ── Volatility Calculations ──────────────────────────────────────────

def get_volatility_calculation(volatility_calculation_id: int) -> dict:
    resp = requests.get(
        f"{BASE_URL}/api/volatility-calculations/detail",
        params={"volatility_calculation_id": volatility_calculation_id},
    )
    return _handle_response(resp)


def list_volatility_calculations(session_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/api/volatility-calculations/",
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
    risky: Optional[bool] = None,
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
    if risky is not None:
        params["risky"] = bool(risky)
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


# ── Trades ────────────────────────────────────────────────────────────

def list_session_trades(session_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
    """GET /api/trades/ — list trades for a session."""
    resp = requests.get(
        f"{BASE_URL}/api/trades/",
        params={"session_id": int(session_id), "limit": int(limit), "offset": int(offset)},
    )
    return _handle_response(resp)


def get_trade(trade_id: int) -> dict:
    """GET /api/trades/detail — get a single trade by id."""
    resp = requests.get(f"{BASE_URL}/api/trades/detail", params={"trade_id": int(trade_id)})
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


def get_provider_assets(provider: str) -> dict:
    """GET /api/provider/assets — wallet / balance rows for the given provider (e.g. BYBIT)."""
    resp = requests.get(
        f"{BASE_URL}/api/provider/assets",
        params={"provider": str(provider).strip()},
    )
    return _handle_response(resp)


def get_provider_positions(
    provider: str,
    category: str = "linear",
    symbol: Optional[str] = None,
) -> dict:
    """GET /api/provider/positions (e.g. Bybit). Omits settle_coin / base_coin query params."""
    params: dict = {
        "provider": str(provider).strip(),
        "category": str(category).strip() or "linear",
    }
    if symbol and str(symbol).strip():
        params["symbol"] = str(symbol).strip().upper()
    resp = requests.get(f"{BASE_URL}/api/provider/positions", params=params)
    return _handle_response(resp)


def set_provider_leverage(
    provider: str,
    instrument: str,
    leverage: float,
    category: str = "inverse",
) -> dict:
    """POST /api/provider/setleverage — set leverage for a symbol (Bybit)."""
    payload = {
        "provider": str(provider).strip(),
        "instrument": str(instrument).strip().upper(),
        "leverage": float(leverage),
        "category": str(category).strip() or "inverse",
    }
    resp = requests.post(f"{BASE_URL}/api/provider/setleverage", json=payload)
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


def get_trading_info() -> dict:
    resp = requests.get(f"{BASE_URL}/tradinginfo")
    return _handle_response(resp)


# ── AI Trader News ─────────────────────────────────────────────────
def get_daily_news(
    symbol: Optional[str] = None,
    lookback_hours: int = 12,
    category: Optional[str] = None,
) -> dict:
    """
    Fetch Finnhub news.

    Backend endpoint: GET /api/ai-trader/news
    """
    params: dict = {"lookback_hours": int(lookback_hours)}
    if symbol is not None and str(symbol).strip():
        params["symbol"] = str(symbol).upper().strip()
    if category is not None and str(category).strip():
        params["category"] = str(category).strip().lower()
    resp = requests.get(f"{BASE_URL}/api/ai-trader/news", params=params)
    return _handle_response(resp)


def summarize_news(
    symbol: str,
    lookback_hours: int = 12,
    news_items: Optional[list[dict]] = None,
) -> dict:
    """
    Summarize fetched news using AI Trader summarize endpoint.

    Backend endpoint: POST /api/ai-trader/news/summarize
    """
    payload = {
        "symbol": str(symbol).upper().strip(),
        "lookback_hours": int(lookback_hours),
        "news_items": news_items or [],
    }
    resp = requests.post(f"{BASE_URL}/api/ai-trader/news/summarize", json=payload)
    return _handle_response(resp)


def create_trend_assessment(
    symbol: str,
    timeframe: str,
    bars: list[dict],
    session_id: Optional[int] = None,
    signal_bar_time: Optional[str] = None,
    news_snippets: Optional[list[str]] = None,
) -> dict:
    """
    Create AI trend assessment from bars/news context.

    Backend endpoint: POST /api/ai-trader/trend-assessments
    """
    payload: dict = {
        "symbol": str(symbol).upper().strip(),
        "timeframe": str(timeframe).strip(),
        "bars": bars,
    }
    if session_id is not None:
        payload["session_id"] = int(session_id)
    if signal_bar_time:
        payload["signal_bar_time"] = str(signal_bar_time)
    if news_snippets:
        payload["news_snippets"] = news_snippets
    resp = requests.post(f"{BASE_URL}/api/ai-trader/trend-assessments", json=payload)
    return _handle_response(resp, 201)
