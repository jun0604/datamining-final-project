"""Recommendation trace logging utilities.

This module records every major reasoning step of the recommendation engine.
It is intentionally lightweight and has no external dependency.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = BASE_DIR / "logs"

_SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
    "HALLYM_API_KEY",
}


def _safe_json_default(obj: Any) -> str:
    try:
        return str(obj)
    except Exception:
        return "<unserializable>"


def sanitize_payload(payload: Any) -> Any:
    """Mask sensitive fields while preserving evidence, scores, and decisions."""
    if isinstance(payload, dict):
        clean: Dict[str, Any] = {}
        for key, value in payload.items():
            if str(key) in _SENSITIVE_KEYS or any(s in str(key).lower() for s in ["api_key", "password", "secret", "token"]):
                clean[key] = "***MASKED***"
            else:
                clean[key] = sanitize_payload(value)
        return clean
    if isinstance(payload, list):
        return [sanitize_payload(x) for x in payload]
    return payload


class TraceLogger:
    """File + in-memory trace logger for recommendation inference steps."""

    def __init__(self, enabled: bool = True, log_dir: Optional[str | os.PathLike[str]] = None, trace_id: Optional[str] = None):
        self.enabled = enabled
        self.trace_id = trace_id or datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
        self.log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"recommendation_trace_{self.trace_id}.log"
        self.steps = []

        self.logger = logging.getLogger(f"recommendation.trace.{self.trace_id}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.handlers.clear()

        if self.enabled:
            handler = logging.FileHandler(self.log_file, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
            self.logger.addHandler(handler)

    def step(self, name: str, payload: Any = None, level: str = "INFO") -> None:
        safe_payload = sanitize_payload(payload)
        record = {
            "step_no": len(self.steps) + 1,
            "step_name": name,
            "payload": safe_payload,
        }
        self.steps.append(record)

        if not self.enabled:
            return

        message = "=" * 80 + f"\n[STEP {record['step_no']}] {name}"
        if safe_payload is not None:
            message += "\n" + json.dumps(safe_payload, ensure_ascii=False, indent=2, default=_safe_json_default)
        log_fn = getattr(self.logger, level.lower(), self.logger.info)
        log_fn(message)

    def error(self, name: str, error: Exception | str, payload: Any = None) -> None:
        self.step(name, {"error": str(error), "payload": payload}, level="ERROR")

    def to_result_meta(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "trace_log_file": str(self.log_file),
            "trace_steps": self.steps,
        }


def create_trace_logger(enabled: bool = True, log_dir: Optional[str | os.PathLike[str]] = None, trace_id: Optional[str] = None) -> TraceLogger:
    return TraceLogger(enabled=enabled, log_dir=log_dir, trace_id=trace_id)
