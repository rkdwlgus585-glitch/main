from __future__ import annotations

from typing import Any
from collections.abc import Mapping

from core_engine.api_response import _compact

__all__ = ["RESERVED_WRAPPER_KEYS", "normalize_v1_request"]


RESERVED_WRAPPER_KEYS = {"request", "inputs", "input", "selector", "target", "meta", "context"}


def _dict(value: Any) -> dict[str, Any]:
    """Safely coerce *value* to a dict; return empty dict for non-dict input."""
    return dict(value) if isinstance(value, dict) else {}


def normalize_v1_request(
    payload: dict[str, Any] | None,
    *,
    headers: Mapping[str, Any] | None = None,
    default_source: str = "",
    default_page_url: str = "",
) -> dict[str, Any]:
    """Normalise a v1 API request payload into a canonical structure.

    Accept multiple input formats (nested ``request``/``inputs``/``selector``
    blocks or flat fields) and unify them into a consistent dict with
    ``request_meta``, ``fields``, ``inputs``, ``selector``, and ``raw`` keys.
    """
    raw = dict(payload or {})
    headers = headers or {}

    request_block = _dict(raw.get("request"))
    meta_block = _dict(raw.get("meta")) or _dict(raw.get("context"))
    selector_block = _dict(raw.get("selector")) or _dict(raw.get("target"))
    inputs_block = _dict(raw.get("inputs")) or _dict(raw.get("input"))

    flat_fields = {k: v for k, v in raw.items() if str(k or "") not in RESERVED_WRAPPER_KEYS}

    request_meta: dict[str, Any] = {}
    request_meta.update(meta_block)
    request_meta.update(request_block)

    channel_id_hint = _compact(request_meta.get("channel_id") or flat_fields.get("channel_id"), 80)
    tenant_id_hint = _compact(request_meta.get("tenant_id") or flat_fields.get("tenant_id"), 80)
    requested_at = _compact(request_meta.get("requested_at") or request_meta.get("timestamp") or flat_fields.get("requested_at"), 80)
    page_url = _compact(
        request_meta.get("page_url")
        or request_meta.get("page")
        or flat_fields.get("page_url")
        or headers.get("Referer")
        or headers.get("Origin")
        or default_page_url,
        500,
    )
    source = _compact(
        request_meta.get("source")
        or flat_fields.get("source")
        or headers.get("Origin")
        or headers.get("Host")
        or default_source,
        120,
    )
    request_id_hint = _compact(
        request_meta.get("request_id")
        or headers.get("X-Request-Id")
        or headers.get("X-Correlation-Id"),
        80,
    )

    fields = dict(selector_block)
    fields.update(flat_fields)
    merged_inputs = dict(fields)
    merged_inputs.update(inputs_block)

    return {
        "request_meta": {
            "source": source,
            "page_url": page_url,
            "requested_at": requested_at,
            "channel_id_hint": channel_id_hint,
            "tenant_id_hint": tenant_id_hint,
            "request_id_hint": request_id_hint,
        },
        "fields": fields,
        "inputs": merged_inputs,
        "selector": selector_block,
        "raw": raw,
    }

