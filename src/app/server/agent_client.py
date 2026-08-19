"""Shared client for invoking Databricks Agent Framework serving endpoints.

All app-side chat/agent routes go through this helper so every interaction
hits a real governed endpoint (not a direct Foundation-Model-API call) and
the tool trace + token usage comes back in a consistent shape for audit
logging.

`invoke_agent` is async — it runs the blocking HTTP/SDK work on a thread pool
so a slow agent call (typical: 10-30s of tool-use loop) does not stall the
FastAPI event loop. Always await it from route handlers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import requests

from server.config import get_workspace_client

logger = logging.getLogger(__name__)

# Transient errors from the underlying Foundation Model endpoint surface here
# as 400 BAD_REQUEST wrapping a 503/502/504 from databricks-claude-sonnet-4-6.
# A single short retry absorbs most of these flakes during a demo.
_TRANSIENT_FM_HINTS = ("503 Server Error", "502 Server Error", "504 Server Error", "Service Unavailable")


def _invoke_sync(endpoint_name: str,
                 question: str,
                 custom_inputs: dict[str, Any] | None,
                 history: list[dict] | None,
                 timeout: int) -> dict:
    """Sync invocation — kept private. Wrap with asyncio.to_thread."""
    try:
        w = get_workspace_client()
        try:
            ep = w.serving_endpoints.get(endpoint_name)
            state = str(ep.state.ready) if ep.state and ep.state.ready else ""
            if state and "READY" not in state:
                # Not a hard failure: a scale-to-zero endpoint waking up, or one
                # mid-update, often still serves (or will inside the retry
                # window below). Log and attempt anyway rather than bailing.
                logger.info("Endpoint %s state=%s — attempting anyway", endpoint_name, state)
        except Exception as e:
            return {"ok": False, "error": f"endpoint lookup failed: {e}"}

        host  = w.config.host.rstrip("/")
        token = w.config._header_factory()

        messages = list(history) if history else []
        messages.append({"role": "user", "content": question})

        # ChatAgent (Mosaic AI Agent Framework) serving contract: a native chat
        # request — messages + optional custom_inputs. NOT a pyfunc
        # `dataframe_records` wrapper (that was the old custom-pyfunc shape and a
        # source of 400s).
        body: dict[str, Any] = {"messages": messages}
        if custom_inputs:
            body["custom_inputs"] = custom_inputs

        # Retry on cold-start / transient upstream errors. Scale-to-zero
        # endpoints return 503 on the first hit while they warm (~30s), and the
        # FM endpoint occasionally 429/502/503/504s under load — all transient.
        # Backoff grows so a cold endpoint gets time to come up.
        backoffs = [3.0, 8.0, 15.0]
        last_error: Exception | None = None
        data = None
        for attempt in range(len(backoffs) + 1):
            try:
                resp = requests.post(
                    f"{host}/serving-endpoints/{endpoint_name}/invocations",
                    headers={**token, "Content-Type": "application/json"},
                    json=body, timeout=timeout,
                )
                if resp.status_code >= 400:
                    msg = resp.text[:500]
                    transient = (resp.status_code in (429, 502, 503, 504)
                                 or any(h in msg for h in _TRANSIENT_FM_HINTS))
                    if transient and attempt < len(backoffs):
                        wait = backoffs[attempt]
                        logger.info("Transient/cold-start on %s (%s) — retry in %.0fs: %s",
                                    endpoint_name, resp.status_code, wait, msg[:160])
                        time.sleep(wait)
                        last_error = requests.HTTPError(f"{resp.status_code}: {msg}")
                        continue
                resp.raise_for_status()
                data = resp.json()
                break
            except requests.HTTPError as e:
                last_error = e
                break  # non-transient HTTP error, give up
            except Exception as e:
                # network/timeout — treat as transient and back off
                last_error = e
                if attempt < len(backoffs):
                    time.sleep(backoffs[attempt])
                    continue
                break
        if data is None:
            raise last_error or RuntimeError("agent invocation failed with no response")
    except Exception as e:
        logger.warning("Agent endpoint %s failed: %s", endpoint_name, e)
        return {"ok": False, "error": str(e)[:300]}

    # Parse the response. ChatAgent endpoints return {messages:[...],
    # custom_outputs:{...}}; a pyfunc fallback returns {predictions:[{...}]}.
    if isinstance(data, dict) and "messages" in data:
        pred = data
    else:
        pred = data.get("predictions") or data.get("outputs") or data
        if isinstance(pred, list):
            pred = pred[0] if pred else {}
    if not isinstance(pred, dict):
        return {"ok": False, "error": f"unexpected response shape: {type(pred).__name__}"}

    msgs = pred.get("messages") or []
    answer = ""
    if msgs:
        # The agent appends its reply; the answer is the last assistant message.
        assistants = [m for m in msgs if isinstance(m, dict) and m.get("role") == "assistant"]
        chosen = assistants[-1] if assistants else (msgs[-1] if isinstance(msgs[-1], dict) else {})
        answer = chosen.get("content") or ""

    # ChatAgent puts trace/persona/usage under custom_outputs; keep a top-level
    # fallback for pyfunc-shaped responses.
    custom = pred.get("custom_outputs") or {}
    return {
        "ok":      True,
        "answer":  answer,
        "trace":   custom.get("trace", pred.get("trace", [])),
        "model":   custom.get("model", pred.get("model", endpoint_name)),
        "usage":   custom.get("usage", pred.get("usage", {})),
        "persona": custom.get("persona", pred.get("persona")),
    }


async def invoke_agent(endpoint_name: str,
                       question: str,
                       custom_inputs: dict[str, Any] | None = None,
                       history: list[dict] | None = None,
                       timeout: int = 240) -> dict:
    """Call an Agent Framework serving endpoint. Returns a dict with:

        ok:      bool
        answer:  str (assistant text) — populated when ok
        trace:   list (tool-call trace) — populated when ok
        model:   str (underlying FM endpoint name)
        usage:   dict (prompt/completion/total tokens)
        persona: str | None (echoed back by the agent if set)
        error:   str — populated when not ok
        cached:  bool — true if returned from the AI response cache

    `history` is an optional list of prior messages ({role, content}); if
    omitted a single user-message is sent.

    Cache behaviour: when the global AI mode is `cached`, this call looks
    up a deterministic hash of (endpoint, question, custom_inputs) in the
    on-volume cache first and returns the stored response on hit. On miss
    it falls through to the live endpoint and writes the response back so
    a subsequent identical call lands fast and verbatim.
    """
    from server import ai_cache
    mode = ai_cache.get_mode()
    key  = ai_cache.cache_key(endpoint_name, question, custom_inputs)
    if mode == "cached":
        hit = ai_cache.get_cached(key)
        if hit is not None:
            hit = dict(hit)
            hit["cached"] = True
            return hit

    result = await asyncio.to_thread(
        _invoke_sync, endpoint_name, question, custom_inputs, history, timeout,
    )

    # Robustness: if the live call failed (agent down, still warming, transient
    # upstream error), serve a cached answer for this key if one exists — in ANY
    # mode. A broken/warming agent degrades to a stored answer instead of
    # surfacing an error to the user.
    if not result.get("ok"):
        try:
            hit = ai_cache.get_cached(key)
        except Exception as e:
            hit = None
            logger.warning("ai_cache fallback lookup failed for %s: %s", endpoint_name, e)
        if hit is not None:
            hit = dict(hit)
            hit["cached"] = True
            hit["stale"] = True  # served as a fallback, not a fresh answer
            logger.info("Agent %s failed live (%s) — serving cached fallback.",
                        endpoint_name, (result.get("error") or "")[:120])
            return hit

    if mode == "cached" and result.get("ok"):
        # Don't cache history-driven conversations — only single-question
        # invocations are reliably reproducible.
        if not history:
            try:
                ai_cache.put_cached(key, result, endpoint_name, question, custom_inputs)
            except Exception as e:
                logger.warning("ai_cache.put_cached failed for %s: %s", endpoint_name, e)
    result["cached"] = False
    return result
